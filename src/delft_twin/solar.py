"""Shadow-aware annual irradiation on roof cells.

Method (per 0.5 m roof cell, numba-parallel):
  * Horizon scan in N_AZ directions up to `max_dist` m over two surfaces: the full DSM
    (buildings + trees) and a DSM with trees removed. Sun / sky blocked only by trees is
    attenuated by a seasonal transmissivity instead of fully blocked.
  * Direct: hourly TMY DNI binned into a sun map (azimuth x elevation) per season; each bin
    contributes DNI * cos(incidence) if the sun is above the horizon in that direction.
  * Diffuse (Hay-Davies): circumsolar part travels with the beam (and is shaded with it);
    the isotropic part is integrated over sky patches above the effective horizon
    (obstructions and the plane's own tilt), weighted by cos(incidence) / pi.
  * Ground-reflected: albedo * GHI * (1 - cos(tilt)) / 2.
Three variants are accumulated in one pass: full, no trees, unobstructed (for loss shares).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib
import requests
from numba import njit, prange

N_AZ = 72
N_EL = 18
PVGIS = "https://re.jrc.ec.europa.eu/api/v5_3"


# --------------------------------------------------------------------------- weather

def pvgis_tmy(lat: float, lon: float, cache: Path) -> tuple[pd.DataFrame, dict]:
    if not cache.exists():
        r = requests.get(f"{PVGIS}/tmy", params={"lat": lat, "lon": lon, "outputformat": "json",
                                                 "usehorizon": 0}, timeout=120)
        r.raise_for_status()
        cache.write_bytes(r.content)
    j = json.loads(cache.read_text())
    df = pd.DataFrame(j["outputs"]["tmy_hourly"])
    t = pd.to_datetime(df["time(UTC)"], format="%Y%m%d:%H%M", utc=True)
    # TMY months come from different years: map onto one reference year for sun geometry
    t = t.map(lambda x: x.replace(year=2026))
    df.index = t + pd.Timedelta(hours=j["inputs"]["location"]["irradiance_time_offset"])
    df = df.rename(columns={"G(h)": "ghi", "Gb(n)": "dni", "Gd(h)": "dhi", "T2m": "temp_air", "WS10m": "wind"})
    return df.sort_index(), j["inputs"]


def sun_maps(tmy: pd.DataFrame, lat: float, lon: float, leaf_on_months=(5, 6, 7, 8, 9, 10)):
    """Wh/m2 of beam per (season, azimuth bin, elevation bin), plus seasonal isotropic-DHI and GHI sums.

    Hay-Davies: the circumsolar share Ai = DNI / E0 of DHI behaves like beam from the sun
    direction (DHI * Ai / sin(e) added to DNI, so horizontal totals are preserved); the
    remaining DHI * (1 - Ai) is isotropic.
    """
    sp = pvlib.solarposition.get_solarposition(tmy.index, lat, lon)
    el, az = sp["apparent_elevation"].values, sp["azimuth"].values
    season = np.isin(tmy.index.month, leaf_on_months).astype(int)  # 1 = leaf-on
    e0 = pvlib.irradiance.get_extra_radiation(tmy.index).values
    ai = np.clip(tmy.dni.values / e0, 0, 1)
    sin_e = np.maximum(np.sin(np.radians(el)), np.sin(np.radians(1.0)))
    beam_eq = tmy.dni.values + np.where(el > 0, tmy.dhi.values * ai / sin_e, 0)
    dhi_iso = tmy.dhi.values * (1 - np.where(el > 0, ai, 0))
    ok = (el > 0) & (beam_eq > 0)
    ia = (az[ok] / (360 / N_AZ)).astype(int) % N_AZ
    ie = np.clip((el[ok] / (90 / (N_EL * 5))).astype(int), 0, N_EL * 5 - 1)  # 1 deg elevation bins
    beam = np.zeros((2, N_AZ, N_EL * 5))
    np.add.at(beam, (season[ok], ia, ie), beam_eq[ok])
    # mean sun vector per bin
    sx = np.zeros_like(beam); sy = np.zeros_like(beam); sz = np.zeros_like(beam)
    w = beam_eq[ok]
    e, a = np.radians(el[ok]), np.radians(az[ok])
    np.add.at(sx, (season[ok], ia, ie), w * np.cos(e) * np.sin(a))
    np.add.at(sy, (season[ok], ia, ie), w * np.cos(e) * np.cos(a))
    np.add.at(sz, (season[ok], ia, ie), w * np.sin(e))
    nz = beam > 0
    norm = np.sqrt(sx**2 + sy**2 + sz**2)
    vec = np.zeros(beam.shape + (3,))
    vec[nz, 0], vec[nz, 1], vec[nz, 2] = sx[nz] / norm[nz], sy[nz] / norm[nz], sz[nz] / norm[nz]
    s, i, j = np.nonzero(nz)
    bins = np.column_stack([s, i, beam[s, i, j], vec[s, i, j]])  # season, az_bin, Wh, ux, uy, uz
    dhi = np.array([dhi_iso[season == k].sum() for k in (0, 1)])
    ghi = float(tmy.ghi.sum())
    return bins, dhi, ghi


# --------------------------------------------------------------------------- irradiance kernel

@njit(parallel=True, cache=True)
def _irradiance(rows, cols, z0, nrm, dsm, dsm_noveg, res, steps, cos_az, sin_az,
                bins, dhi, ghi, albedo, tau, sky_dir, sky_w):
    n = rows.size
    ny, nx = dsm.shape
    out = np.zeros((n, 3))  # full, no trees, unobstructed  (kWh/m2/yr)
    svf = np.zeros(n)
    for c in prange(n):
        r0, c0, h0 = rows[c], cols[c], z0[c]
        hf = np.full(N_AZ, -1.0)  # tan(horizon) full surface
        hb = np.full(N_AZ, -1.0)  # tan(horizon) without trees
        for a in range(N_AZ):
            for d in steps:
                rr = int(r0 - d * cos_az[a] / res + 0.5)
                cc = int(c0 + d * sin_az[a] / res + 0.5)
                if rr < 0 or rr >= ny or cc < 0 or cc >= nx:
                    break
                v = dsm[rr, cc]
                if v == v:
                    t = (v - h0) / d
                    if t > hf[a]:
                        hf[a] = t
                v = dsm_noveg[rr, cc]
                if v == v:
                    t = (v - h0) / d
                    if t > hb[a]:
                        hb[a] = t
        nx_, ny_, nz_ = nrm[c, 0], nrm[c, 1], nrm[c, 2]
        # direct
        dfull = 0.0; dnov = 0.0; dfree = 0.0
        for k in range(bins.shape[0]):
            s = int(bins[k, 0]); a = int(bins[k, 1])
            ux, uy, uz = bins[k, 3], bins[k, 4], bins[k, 5]
            ci = ux * nx_ + uy * ny_ + uz * nz_
            if ci <= 0:
                continue
            e = bins[k, 2] * ci
            dfree += e
            tsun = uz / max(np.sqrt(ux * ux + uy * uy), 1e-6)
            if tsun > hb[a]:
                dnov += e
                if tsun > hf[a]:
                    dfull += e
                else:
                    dfull += e * tau[s]
        # diffuse: isotropic, patches above horizon, weighted by cos incidence on plane
        sf = np.zeros(2); sb = 0.0; s0 = 0.0
        for p in range(sky_dir.shape[0]):
            a = int(sky_dir[p, 3])
            ci = sky_dir[p, 0] * nx_ + sky_dir[p, 1] * ny_ + sky_dir[p, 2] * nz_
            if ci <= 0:
                continue
            w = sky_w[p] * ci
            s0 += w
            tp = sky_dir[p, 2] / max(np.sqrt(sky_dir[p, 0] ** 2 + sky_dir[p, 1] ** 2), 1e-6)
            if tp > hb[a]:
                sb += w
                if tp > hf[a]:
                    sf[0] += w; sf[1] += w
                else:
                    sf[0] += w * tau[0]; sf[1] += w * tau[1]
        refl = albedo * ghi * (1 - nz_) / 2
        out[c, 0] = (dfull + dhi[0] * sf[0] + dhi[1] * sf[1] + refl) / 1000
        out[c, 1] = (dnov + (dhi[0] + dhi[1]) * sb + refl) / 1000
        out[c, 2] = (dfree + (dhi[0] + dhi[1]) * s0 + refl) / 1000
        svf[c] = sf[1] / s0 if s0 > 0 else 0.0
    return out, svf


def sky_patches():
    """Unit vectors + az bin + weights (solid angle / pi) so that a horizontal plane sums to 1."""
    dirs, w = [], []
    de = np.radians(90 / N_EL)
    for i in range(N_EL):
        e = (i + 0.5) * de
        for a in range(N_AZ):
            az = np.radians((a + 0.5) * 360 / N_AZ)
            dirs.append([np.cos(e) * np.sin(az), np.cos(e) * np.cos(az), np.sin(e), a])
            w.append(np.cos(e) * de * np.radians(360 / N_AZ) / np.pi)  # dOmega/pi, cos factor applied later
    return np.array(dirs), np.array(w)


def ray_steps(max_dist: float, res: float) -> np.ndarray:
    d, out = res, []
    while d <= max_dist:
        out.append(d)
        d += max(res, 0.04 * d)
    return np.array(out)


def run_tile(roof_rows, roof_cols, roof_z, roof_nrm, dsm, dsm_noveg, res, tmy, cfg):
    sc = cfg["solar"]
    bins, dhi, ghi = sun_maps(tmy, cfg["site"]["lat"], cfg["site"]["lon"])
    az = np.radians((np.arange(N_AZ) + 0.5) * 360 / N_AZ)
    sky_dir, sky_w = sky_patches()
    tau = np.array([sc["tree_tau_leaf_off"], sc["tree_tau_leaf_on"]])  # index = season (0 off, 1 on)
    out, svf = _irradiance(roof_rows, roof_cols, roof_z + sc["observer_offset"], roof_nrm, dsm, dsm_noveg,
                           res, ray_steps(sc["max_dist"], res), np.cos(az), np.sin(az),
                           bins, dhi, ghi, sc["albedo"], tau, sky_dir, sky_w)
    return out, svf, {"ghi_kwh": ghi / 1000, "dhi_kwh": float(tmy.dhi.sum() / 1000),
                      "dhi_isotropic_kwh": float(dhi.sum() / 1000), "dni_kwh": float(tmy.dni.sum() / 1000),
                      "sky_model": "Hay-Davies", "n_sun_bins": int(len(bins))}
