"""Monte Carlo uncertainty of district PV yield (in the spirit of Biljecki et al. 2015).

Factors (independent):
  * geometry  - per-building height offset (sigma = validation RMSE) and per-plane normal tilt noise; the shading kernel
                is re-run on a fixed random sample of study-area roof cells (paired with an unperturbed base run);
  * weather   - each PVGIS-SARAH3 year 2005-2023 instead of the TMY, transposed per panel orientation;
  * PR        - performance ratio uniform in [0.75, 0.85];
  * trees     - crown transmissivity uniform between the 'sparse' and 'dense' sensitivity scenarios;
  * layout    - flat-roof ground coverage ratio uniform in [0.55, 0.75] (applied to the flat-roof share of yield).
Total = base x product of factors; reported as 5 / 50 / 95 % per study area, plus one-at-a-time ranges.
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
import pvlib
from rasterio.features import rasterize

from . import city, data, pv, solar

CFG = {"n_geometry": 30, "cell_fraction": 0.10, "sigma_height_m": 0.27, "sigma_tilt_deg": 1.5,
       "pr_range": (0.75, 0.85), "gcr_range": (0.55, 0.75), "n_draws": 2000, "seed": 42}


# --------------------------------------------------------------------------- weather years

def pvgis_years(cache) -> pd.DataFrame:
    j = json.loads(cache.read_text())
    df = pd.DataFrame(j["outputs"]["hourly"])
    t = pd.to_datetime(df.time, format="%Y%m%d:%H%M", utc=True)
    el = np.radians(df.H_sun.clip(lower=0))
    ghi = df["Gb(i)"] + df["Gd(i)"]
    dni = np.where(df.H_sun > 2, df["Gb(i)"] / np.sin(el), 0.0)
    return pd.DataFrame({"ghi": ghi.values, "dhi": df["Gd(i)"].values, "dni": dni}, index=t)


def year_factors(planes_ok: pd.DataFrame, cfg: dict, weather_tmy: pd.DataFrame) -> pd.DataFrame:
    """Per study area and year: yield(year) / yield(TMY), weighting each orientation by its planes' kWh."""
    series = pvgis_years(data.RAW / "pvgis_series_2005_2023.json")
    lat, lon, alb, t = cfg["site"]["lat"], cfg["site"]["lon"], cfg["solar"]["albedo"], cfg["pv"]["flat_tilt_deg"]

    def poa_sum(w, key):
        sp = pvlib.solarposition.get_solarposition(w.index, lat, lon)
        e0 = pvlib.irradiance.get_extra_radiation(w.index)
        def one(tilt, az):
            return pvlib.irradiance.get_total_irradiance(tilt, az, sp.apparent_zenith, sp.azimuth, w.dni, w.ghi, w.dhi,
                                                         dni_extra=e0, model="haydavies", albedo=alb).poa_global.clip(lower=0).sum()
        return (one(t, 90) + one(t, 270)) / 2 if key == "EW" else one(*key)

    keys = planes_ok.profile_key.unique()
    tmy = {k: poa_sum(weather_tmy, k) for k in keys}
    rows = []
    for y, w in series.groupby(series.index.year):
        f = {k: poa_sum(w, k) / tmy[k] for k in keys}
        g = planes_ok.assign(f=planes_ok.profile_key.map(f))
        for aoi, ga in g.groupby("aoi"):
            rows.append({"year": y, "aoi": aoi, "factor": float((ga.kwh_yr * ga.f).sum() / ga.kwh_yr.sum())})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- geometry

def geometry_samples(ctx, cell_inputs_fn) -> pd.DataFrame:
    cfg, res = ctx.cfg, ctx.cfg["preprocess"]["raster_res"]
    rng = np.random.default_rng(CFG["seed"])
    dsm, dsm_nv, cb = ctx.mosaics
    weather, _ = solar.pvgis_tmy(cfg["site"]["lat"], cfg["site"]["lon"], data.RAW / "pvgis_tmy.json")
    b = ctx.buildings[~ctx.buildings.incomplete].reset_index(drop=True)
    from rasterio.transform import from_origin
    lab = rasterize(((g, i + 1) for i, g in enumerate(b.geometry)), out_shape=dsm.shape,
                    transform=from_origin(cb.left, cb.top, res, res), fill=0, dtype="int32")
    bidx = {k: i + 1 for i, k in enumerate(b.identificatie)}
    aoi_of = b.set_index("identificatie").aoi

    # fixed random subset of study-area roof cells
    parts = []
    for t in ctx.tiles:
        c = cell_inputs_fn(ctx, t)
        ident = c["planes"].identificatie.reindex(c["pids"]).values
        a = aoi_of.reindex(ident).values
        keep = pd.notna(a) & (rng.random(len(ident)) < CFG["cell_fraction"])
        if keep.any():
            parts.append(pd.DataFrame({"row": c["rows"][keep], "col": c["cols"][keep], "z": c["z"][keep],
                                       "nx": c["nrm"][keep, 0], "ny": c["nrm"][keep, 1], "nz": c["nrm"][keep, 2],
                                       "plane": [f"{t}:{p}" for p in c["pids"][keep]], "bld": [bidx.get(i, 0) for i in ident[keep]],
                                       "aoi": a[keep]}))
    s = pd.concat(parts, ignore_index=True)
    planes_u, plane_i = np.unique(s.plane, return_inverse=True)

    def run(dsm_, nov_, z, nrm):
        irr, _, _ = solar.run_tile(s.row.values.astype(np.int64), s.col.values.astype(np.int64), z, nrm, dsm_, nov_, res, weather, cfg)
        return pd.Series(irr[:, 0]).groupby(s.aoi.values).sum()

    nrm0 = s[["nx", "ny", "nz"]].to_numpy(np.float64)
    base = run(dsm, dsm_nv, s.z.values, nrm0)
    rows = []
    for k in range(CFG["n_geometry"]):
        t0 = time.time()
        off = np.concatenate([[0.0], rng.normal(0, CFG["sigma_height_m"], len(b))]).astype(np.float32)
        d_off = off[lab]
        tilt = rng.normal(0, np.sin(np.radians(CFG["sigma_tilt_deg"])), (len(planes_u), 2))[plane_i]
        n = nrm0.copy()
        n[:, :2] += tilt
        n /= np.linalg.norm(n, axis=1, keepdims=True)
        r = run(dsm + d_off, dsm_nv + d_off, s.z.values + off[s.bld.values], n) / base
        rows += [{"sample": k, "aoi": a, "factor": float(v)} for a, v in r.items()]
        print(f"geometry sample {k}: {time.time() - t0:.0f}s", flush=True)
    return pd.DataFrame(rows).assign(n_cells=len(s))


# --------------------------------------------------------------------------- combine

def combine(geo: pd.DataFrame, years: pd.DataFrame, ctx) -> dict:
    rng = np.random.default_rng(CFG["seed"] + 1)
    pvs = json.loads((city.CITY / "pv_summary.json").read_text())["by_aoi"]
    her = json.loads((city.CITY / "heritage_summary.json").read_text())["by_aoi"]
    sens = pd.read_csv(city.CITY / "tree_sensitivity.csv")
    planes = pd.read_parquet(city.CITY / "pv_planes.parquet")
    pr0 = ctx.cfg["pv"]["performance_ratio"]
    gcr0 = ctx.cfg["pv"]["flat_gcr"]
    n = CFG["n_draws"]
    out = {}
    for aoi in ["binnenstad", "campus", "voorhof"]:
        s = sens[sens.aoi == aoi].set_index("scenario")
        lo = (1 - s.loc["dense", "tree_loss"]) / (1 - s.loc["base", "tree_loss"])
        hi = (1 - s.loc["sparse", "tree_loss"]) / (1 - s.loc["base", "tree_loss"])
        pa = planes[(planes.aoi == aoi) & (planes.kwp > 0)]
        flat_share = float(pa.loc[pa.layout == "east_west", "kwh_yr"].sum() / pa.kwh_yr.sum())
        f = {
            "geometry": rng.choice(geo[geo.aoi == aoi].factor.values, n),
            "weather_year": rng.choice(years[years.aoi == aoi].factor.values, n),
            "performance_ratio": rng.uniform(*CFG["pr_range"], n) / pr0,
            "trees": rng.uniform(lo, hi, n),
            "flat_layout": 1 - flat_share + flat_share * rng.uniform(*CFG["gcr_range"], n) / gcr0,
        }
        total = np.prod(np.vstack(list(f.values())), axis=0)
        res = {"flat_share_of_yield": flat_share, "factor_5_50_95": [float(v) for v in np.percentile(total, [5, 50, 95])],
               "one_at_a_time_5_95": {k: [float(v) for v in np.percentile(x, [5, 95])] for k, x in f.items()}}
        for scen, base in [("technical", pvs[aoi]["gwh_yr"]),
                           ("permitted_incl_permit", her[aoi]["permitted_incl_permit"]["gwh_yr"]),
                           ("permitted_no_permit", her[aoi]["permitted_no_permit"]["gwh_yr"])]:
            res[f"{scen}_gwh_5_50_95"] = [float(v) for v in np.percentile(base * total, [5, 50, 95])]
            res[f"{scen}_gwh_point"] = base
        out[aoi] = res
    return out


def run(ctx, cell_inputs_fn) -> dict:
    planes = pd.read_parquet(city.CITY / "pv_planes.parquet")
    flat = planes.slope_deg < ctx.cfg["segmentation"]["flat_slope_deg"]
    planes["profile_key"] = [pv.profile_key(f, s, a) for f, s, a in zip(flat, planes.slope_deg, planes.aspect_deg)]
    ok = planes[(planes.kwp > 0) & planes.aoi.notna()]
    weather, _ = solar.pvgis_tmy(ctx.cfg["site"]["lat"], ctx.cfg["site"]["lon"], data.RAW / "pvgis_tmy.json")
    years = year_factors(ok, ctx.cfg, weather)
    years.to_csv(city.CITY / "uncertainty_years.csv", index=False)
    geo = geometry_samples(ctx, cell_inputs_fn)
    geo.to_csv(city.CITY / "uncertainty_geometry.csv", index=False)
    out = {"config": {k: list(v) if isinstance(v, tuple) else v for k, v in CFG.items()},
           "n_cells_geometry": int(geo.n_cells.iloc[0]), "by_aoi": combine(geo, years, ctx)}
    (city.CITY / "uncertainty_summary.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    from .pipeline import Context, cell_inputs
    print(json.dumps(run(Context(data.load_config()), cell_inputs), indent=1))
