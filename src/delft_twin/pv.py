"""PV layout, hourly yield, self-consumption and value before / after the end of net metering.

Per roof plane: usable cells (sky-visible, not obstacle, 0.5 m from plane edges and obstacles) ->
module layout (flush on pitched roofs, east-west 12 deg on flat roofs) -> kWp and annual kWh with a
performance ratio. Hourly shape: unobstructed plane-of-array irradiance for the plane's orientation
(pvlib, Hay-Davies, same TMY), scaled to the plane's shaded annual total.

Households: dwellings per BAG building x CBS 2024 grid delivery per dwelling, shaped by the
MFFBAS/NEDU 2026 E1A profile for connections without PV. Values use CBS 85592NED tariffs.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pvlib
import requests

from . import city, data, solar

CBS_PRICES = "https://opendata.cbs.nl/ODataApi/odata/85592NED/TypedDataSet"
PROFILE_CSV = data.RAW / "profiles" / "e2026" / "Profielen elektriciteit 2026 v1.00" / "Standaardprofielen elektriciteit 2026 versie 1.00.csv"


# --------------------------------------------------------------------------- inputs

def prices(cfg) -> dict:
    """Average of the latest N months: variable supply tariff and energy tax, incl. and excl. VAT (EUR/kWh)."""
    path = data.RAW / "cbs_85592NED.json"
    if not path.exists():
        rows = []
        for btw in ("A048944", "A048945"):  # incl. / excl. VAT
            r = requests.get(CBS_PRICES, params={"$filter": f"Btw eq '{btw}'", "$top": 1000}, timeout=120)
            r.raise_for_status()
            rows += r.json()["value"]
        path.write_text(json.dumps(rows))
    df = pd.DataFrame(json.loads(path.read_text()))
    df = df[df.Perioden.str.contains("MM")]
    n = cfg["pv"]["price_months"]
    out = {}
    for btw, tag in (("A048944", "incl_vat"), ("A048945", "excl_vat")):
        d = df[df.Btw == btw].sort_values("Perioden").tail(n)
        out[f"supply_{tag}"] = float(d.VariabelLeveringstariefContractprijs_9.mean())
        out[f"energy_tax_{tag}"] = float(d.Energiebelasting_14.mean())
        out["months"] = f"{d.Perioden.iloc[0]}..{d.Perioden.iloc[-1]}"
    out["retail_marginal"] = out["supply_incl_vat"] + out["energy_tax_incl_vat"]
    out["export_2027"] = cfg["pv"]["export_share_of_bare_tariff_2027"] * out["supply_excl_vat"]
    return out


def household_profile(index: pd.DatetimeIndex) -> np.ndarray:
    """E1A_AZI_A (small connections without PV, consumption) as hourly fractions on the TMY index (sums to 1)."""
    raw = pd.read_csv(PROFILE_CSV, sep=None, engine="python", header=None, skiprows=7, dtype=str)
    hdr = pd.read_csv(PROFILE_CSV, sep=None, engine="python", header=None, nrows=1, dtype=str).iloc[0].tolist()
    col = hdr.index("1.00_E1A_AZI_A")
    t_end_cet = pd.to_datetime(raw[0], format="%d-%m-%Y %H:%M")
    utc = (t_end_cet - pd.Timedelta(minutes=15) - pd.Timedelta(hours=1)).dt.tz_localize("UTC")
    v = pd.to_numeric(raw[col].str.replace(",", "."), errors="coerce").values
    s = pd.Series(v, index=utc).resample("1h").sum()
    hours = index.floor("h")
    prof = s.reindex(hours).fillna(0).values
    return prof / prof.sum()


def orientation_profiles(weather: pd.DataFrame, cfg) -> tuple[dict, float]:
    """Normalised hourly POA (unobstructed) per (tilt bin, azimuth bin); plus annual E-W factor vs horizontal."""
    sp = pvlib.solarposition.get_solarposition(weather.index, cfg["site"]["lat"], cfg["site"]["lon"])
    e0 = pvlib.irradiance.get_extra_radiation(weather.index)

    def poa(tilt, az):
        return pvlib.irradiance.get_total_irradiance(
            tilt, az, sp.apparent_zenith, sp.azimuth, weather.dni, weather.ghi, weather.dhi,
            dni_extra=e0, model="haydavies", albedo=cfg["solar"]["albedo"]).poa_global.fillna(0).clip(lower=0).values

    profiles = {}
    for tilt in range(0, 75, 5):
        for az in range(0, 360, 15):
            p = poa(tilt, az)
            profiles[(tilt, az)] = p / p.sum()
            if tilt == 0:
                break
    t = cfg["pv"]["flat_tilt_deg"]
    ew = (poa(t, 90) + poa(t, 270)) / 2
    profiles["EW"] = ew / ew.sum()
    f_ew = float(ew.sum() / weather.ghi.clip(lower=0).sum())
    return profiles, f_ew


# --------------------------------------------------------------------------- layout

NEIGHBOURS8 = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]


def _shift(a, dr, dc, fill):
    out = np.full_like(a, fill)
    h, w = a.shape
    out[max(dr, 0):h + min(dr, 0), max(dc, 0):w + min(dc, 0)] = a[max(-dr, 0):h + min(-dr, 0), max(-dc, 0):w + min(-dc, 0)]
    return out


def fill_holes(lab: np.ndarray, obs: np.ndarray, passes: int = 2) -> np.ndarray:
    """Give unlabelled cells enclosed by roof the majority label of their 8 neighbours (>= 4 votes)."""
    from scipy import ndimage
    lab = lab.copy()
    inside = ndimage.binary_fill_holes(lab >= 0)
    for _ in range(passes):
        hole = inside & (lab < 0) & ~obs
        if not hole.any():
            break
        nb = np.stack([_shift(lab, dr, dc, -1)[hole] for dr, dc in NEIGHBOURS8], axis=1)
        nb_sorted = np.sort(nb, axis=1)
        best, votes = np.full(nb.shape[0], -1), np.zeros(nb.shape[0], int)
        for k in range(8):  # mode of each row (labels >= 0 only)
            v = nb_sorted[:, k]
            cnt = (nb_sorted == v[:, None]).sum(1)
            better = (v >= 0) & (cnt > votes)
            best[better], votes[better] = v[better], cnt[better]
        new = lab[hole]
        new[votes >= 4] = best[votes >= 4]
        lab[hole] = new
    return lab


def usable_cells(cells: pd.DataFrame, planes: pd.DataFrame, origin, res: float, setback: int,
                 max_angle_deg: float = 10.0, max_dz: float = 0.3) -> pd.DataFrame:
    """Cells usable for modules, with their panel field (connected component) id.

    A cell is usable if it is not an obstacle and no neighbour within `setback` cells is an obstacle or a
    roof cell of an *incompatible* plane (normals beyond `max_angle_deg` or heights beyond `max_dz` at the
    cell): ridges, hips and steps get the setback, over-segmented coplanar fragments do not. The roof
    outline gets none here, because segmentation only used points >= 0.5 m inside the BAG footprint.
    Interior holes (cells without a labelled point) are filled first; filled cells have NaN irradiance.
    """
    from scipy import ndimage
    x0, y1 = origin
    r0, c0 = cells.row.min() - setback, cells.col.min() - setback
    h, w = cells.row.max() - r0 + 1 + setback, cells.col.max() - c0 + 1 + setback
    lab = np.full((h, w), -1, np.int64)
    obs = np.zeros((h, w), bool)
    rr, cc = cells.row.values - r0, cells.col.values - c0
    lab[rr, cc] = cells.plane_id.values
    obs[rr, cc] = cells.obstacle.values
    lab = fill_holes(lab, obs)

    pl = planes.set_index("plane_id")
    ids = np.unique(lab[lab >= 0])
    lut = np.full(int(ids.max()) + 1 if ids.size else 1, -1)
    lut[ids] = np.arange(ids.size)
    P = pl.loc[ids, ["nx", "ny", "nz", "cx", "cy", "cz"]].to_numpy(np.float64)
    gy, gx = np.mgrid[0:h, 0:w]
    X = x0 + (gx + c0 + 0.5) * res
    Y = y1 - (gy + r0 + 0.5) * res
    roof = lab >= 0
    k = np.where(roof, lut[np.clip(lab, 0, None)], 0)

    def z_of(kk):
        p = P[kk]
        return p[..., 5] - ((X - p[..., 3]) * p[..., 0] + (Y - p[..., 4]) * p[..., 1]) / p[..., 2]

    z_self = z_of(k)
    n_self = P[k][..., :3]
    cos_t = np.cos(np.radians(max_angle_deg))
    ok = roof & ~obs
    for dr in range(-setback, setback + 1):
        for dc in range(-setback, setback + 1):
            if dr == dc == 0:
                continue
            ln = _shift(lab, dr, dc, -1)
            on = _shift(obs, dr, dc, True)
            kn = np.where(ln >= 0, lut[np.clip(ln, 0, None)], 0)
            same = ln == lab
            compat = (ln >= 0) & ((P[kn][..., :3] * n_self).sum(-1) >= cos_t) & (np.abs(z_of(kn) - z_self) <= max_dz)
            outside = ln < 0  # roof outline: already 0.5 m inside the footprint (segmentation inner buffer)
            ok &= ~on & (same | compat | outside)
    comp, _ = ndimage.label(ok, structure=np.ones((3, 3), bool))
    r, c = np.nonzero(ok)
    out = pd.DataFrame({"row": r + r0, "col": c + c0, "plane_id": lab[r, c], "field": comp[r, c]})
    return out.merge(cells[["row", "col", "kwh_m2"]], on=["row", "col"], how="left")


def plane_layout(ctx, f_ew: float) -> pd.DataFrame:
    cfg, res = ctx.cfg, ctx.cfg["preprocess"]["raster_res"]
    pc = cfg["pv"]
    planes = pd.read_parquet(city.CITY / "roof_planes_solar.parquet")
    x0, _, _, y1 = city.extent(ctx.tiles)
    origin = (x0 - cfg["shadow_buffer_m"], y1 + cfg["shadow_buffer_m"])  # city grid origin (see build_mosaics)
    flat_max = cfg["segmentation"]["flat_slope_deg"]
    rows = []
    for t in ctx.tiles:
        c = pd.read_parquet(data.PROCESSED / t / "roof_cells_solar.parquet")
        tp = pd.read_parquet(data.PROCESSED / t / "roof_planes.parquet")
        u = usable_cells(c, tp, origin, res, pc["edge_setback_cells"])
        sl = tp.set_index("plane_id").slope_deg.reindex(u.plane_id).values
        u["flat"] = sl < flat_max
        u["area3d"] = res * res / np.cos(np.radians(sl))
        u["h_poa"] = np.where(u.flat, u.kwh_m2 * f_ew, u.kwh_m2)
        u["tile"] = t
        # suitability per panel field (connected usable cells), not per (possibly fragmented) plane
        u["f_ok"] = field_suitability(u, pc)
        u.to_parquet(data.PROCESSED / t / "pv_usable_cells.parquet")  # reused by the heritage filter
        rows.append(u)
    return planes_from_cells(planes, pd.concat(rows), cfg)


def field_suitability(u: pd.DataFrame, pc: dict) -> pd.Series:
    """Per usable cell: does its panel field (connected cells) reach the minimum area and irradiation?"""
    f = u.groupby(["tile", "field"]).agg(f_area=("area3d", "sum"), f_h=("h_poa", "mean"))
    ok = (f.f_area >= pc["min_usable_area_m2"]) & (f.f_h >= pc["min_irradiation_kwh_m2"])
    return ok.reindex(pd.MultiIndex.from_frame(u[["tile", "field"]])).values


def planes_from_cells(planes: pd.DataFrame, u: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Module layout, kWp and annual yield per plane from its usable cells (column f_ok = in a suitable field)."""
    pc, res = cfg["pv"], cfg["preprocess"]["raster_res"]
    flat_max = cfg["segmentation"]["flat_slope_deg"]
    agg = u.groupby(["tile", "plane_id"]).agg(n_usable=("row", "size"), n_suitable=("f_ok", "sum"))
    # filled hole cells have no irradiance of their own: use their panel field's mean
    h = u.h_poa.fillna(u.groupby(["tile", "field"]).h_poa.transform("mean"))
    agg["h_poa_kwh_m2"] = h[u.f_ok].groupby([u.tile[u.f_ok], u.plane_id[u.f_ok]]).mean()
    agg["n_fields"] = u[u.f_ok].groupby(["tile", "plane_id"]).field.nunique()
    p = planes.merge(agg.reset_index(), on=["tile", "plane_id"], how="left") \
        .fillna({"n_usable": 0, "n_suitable": 0, "n_fields": 0})
    flat = p.slope_deg < flat_max
    cosb = np.cos(np.radians(p.slope_deg))
    p["usable_area_m2"] = p.n_usable * res * res / cosb
    p["suitable_area_2d_m2"] = p.n_suitable * res * res
    p["suitable_area_m2"] = p.suitable_area_2d_m2 / cosb
    p["layout"] = np.where(flat, "east_west", "flush")
    module_area = np.where(flat, p.suitable_area_2d_m2 * pc["flat_gcr"] / np.cos(np.radians(pc["flat_tilt_deg"])),
                           p.suitable_area_m2 * pc["packing_pitched"])
    p["suitable"] = (p.n_suitable > 0) & p.h_poa_kwh_m2.notna()
    # continuous module count per plane (fields can span coplanar fragments, so no per-plane rounding)
    p["n_modules"] = np.where(p.suitable, module_area / pc["module_area_m2"], 0.0)
    p["kwp"] = p.n_modules * pc["module_wp"] / 1000
    p["kwh_yr"] = p.kwp * p.h_poa_kwh_m2 * pc["performance_ratio"]
    p["kwh_per_kwp"] = np.where(p.kwp > 0, p.kwh_yr / p.kwp.where(p.kwp > 0), np.nan)
    p["profile_key"] = [profile_key(f, s, a) for f, s, a in zip(flat, p.slope_deg, p.aspect_deg)]
    return p


def profile_key(flat: bool, slope: float, aspect: float):
    """Orientation bin of a plane: 'EW' for flat roofs (east-west racks), else (tilt 5-deg bin, azimuth 15-deg bin)."""
    if flat:
        return "EW"
    tilt = int(min(70, 5 * round(slope / 5)))
    return (tilt, int(15 * round(aspect / 15)) % 360) if tilt > 0 else (0, 0)


# --------------------------------------------------------------------------- hourly balance

def battery_dispatch(prod, dem, cap, power, eff):
    """Greedy self-consumption battery; arrays (hours, buildings). Returns grid import, export."""
    soc = np.zeros(prod.shape[1])
    imp = np.zeros_like(prod)
    exp = np.zeros_like(prod)
    ch_eff = dis_eff = np.sqrt(eff)
    for h in range(prod.shape[0]):
        net = prod[h] - dem[h]
        surplus = np.clip(net, 0, None)
        deficit = np.clip(-net, 0, None)
        charge = np.minimum(np.minimum(surplus, power), (cap - soc) / ch_eff)
        soc += charge * ch_eff
        discharge = np.minimum(np.minimum(deficit, power), soc * dis_eff)
        soc -= discharge / dis_eff
        exp[h] = surplus - charge
        imp[h] = deficit - discharge
    return imp, exp


def buildings_balance(ctx, p: pd.DataFrame, profiles: dict, weather: pd.DataFrame, pr: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg, pc = ctx.cfg, ctx.cfg["pv"]
    b = ctx.buildings
    b = b[~b.incomplete].copy()
    # demand: dwellings x CBS 2024 grid delivery per dwelling (buurt), fallback municipality mean
    bu = data.cbs_layer("buurten")
    lev = pd.to_numeric(bu.gemiddeldeElektriciteitslevering, errors="coerce").where(lambda s: s > 0)
    bu = bu.assign(kwh_dwelling=lev)[["buurtcode", "buurtnaam", "kwh_dwelling", "geometry"]]
    rp = gpd.GeoDataFrame(b[["identificatie"]], geometry=b.representative_point(), crs=b.crs)
    j = gpd.sjoin(rp, bu, how="left", predicate="within").drop_duplicates("identificatie")
    b = b.merge(j[["identificatie", "buurtcode", "buurtnaam", "kwh_dwelling"]], on="identificatie", how="left")
    fallback = float(np.nanmedian(lev))
    b["kwh_dwelling"] = b.kwh_dwelling.fillna(fallback)
    resid = b.gebruiksdoel.fillna("").str.contains("woonfunctie")
    b["dwellings"] = np.where(resid, pd.to_numeric(b.aantal_verblijfsobjecten, errors="coerce").fillna(0), 0)
    b["demand_kwh"] = b.dwellings * b.kwh_dwelling

    pb = p[p.kwp > 0].groupby("identificatie").agg(kwp=("kwp", "sum"), kwh_yr=("kwh_yr", "sum"),
                                                   n_planes_pv=("kwp", "size"))
    b = b.merge(pb, on="identificatie", how="left").fillna({"kwp": 0, "kwh_yr": 0, "n_planes_pv": 0})

    # hourly production matrix via orientation profiles: (hours x buildings)
    keys = list(profiles)
    kidx = {k: i for i, k in enumerate(keys)}
    P = np.stack([profiles[k] for k in keys], axis=1)                       # hours x profiles
    pp = p[p.kwp > 0]
    bid = {g: i for i, g in enumerate(b.identificatie)}
    W = np.zeros((len(keys), len(b)))
    np.add.at(W, (pp.profile_key.map(kidx).values, pp.identificatie.map(bid).values), np.nan_to_num(pp.kwh_yr.values))
    hh = household_profile(weather.index)

    res = np.zeros((len(b), 8))
    sel = np.flatnonzero((b.demand_kwh.values > 0) & (b.kwh_yr.values > 0))
    buurt_export = {}
    for s in range(0, len(sel), 2000):
        i = sel[s:s + 2000]
        prod = P @ W[:, i]
        dem = np.outer(hh, b.demand_kwh.values[i])
        sc = np.minimum(prod, dem)
        exp = prod - sc
        n_dw = b.dwellings.values[i]
        imp_b, exp_b = battery_dispatch(prod, dem, pc["battery_kwh_per_dwelling"] * n_dw,
                                        pc["battery_kw_per_dwelling"] * n_dw, pc["battery_roundtrip"])
        res[i, 0] = sc.sum(0)
        res[i, 1] = exp.sum(0)
        res[i, 2] = dem.sum(0) - imp_b.sum(0)           # demand covered by PV incl. battery (losses excluded)
        res[i, 3] = exp_b.sum(0)
        for code, grp in pd.Series(np.arange(len(i)), index=b.buurtcode.values[i]).groupby(level=0):
            buurt_export[code] = buurt_export.get(code, 0) + exp[:, grp.values].sum(1)
    b["self_consumed_kwh"], b["export_kwh"] = res[:, 0], res[:, 1]
    b["self_consumed_batt_kwh"], b["export_batt_kwh"] = res[:, 2], res[:, 3]
    # buildings without residential demand: everything exported (not valued below)
    nores = b.demand_kwh <= 0
    b.loc[nores, "export_kwh"] = b.loc[nores, "kwh_yr"]

    r, x = pr["retail_marginal"], pr["export_2027"]
    has = (b.demand_kwh > 0) & (b.kwh_yr > 0)
    netted = np.minimum(b.kwh_yr, b.demand_kwh)
    b["value_2026_eur"] = np.where(has, netted * r + (b.kwh_yr - netted) * x, np.nan)
    b["value_2027_eur"] = np.where(has, b.self_consumed_kwh * r + b.export_kwh * x, np.nan)
    b["value_2027_batt_eur"] = np.where(has, b.self_consumed_batt_kwh * r + b.export_batt_kwh * x, np.nan)
    b["scr"] = np.where(has, b.self_consumed_kwh / b.kwh_yr, np.nan)
    b["scr_batt"] = np.where(has, b.self_consumed_batt_kwh / b.kwh_yr, np.nan)
    b["coverage"] = np.where(b.demand_kwh > 0, b.kwh_yr / b.demand_kwh, np.nan)

    hours = weather.index
    june_noon = (hours.month == 6) & (hours.hour >= 10) & (hours.hour < 13)  # UTC 10-13 = 12-15 CEST
    ex = pd.DataFrame({k: {"export_peak_kw": float(v.max()), "export_june_midday_mean_kw": float(v[june_noon].mean()),
                           "peak_hour_utc": str(hours[int(v.argmax())])} for k, v in buurt_export.items()}).T
    return gpd.GeoDataFrame(b, crs="EPSG:28992"), ex


def run(ctx) -> dict:
    cfg = ctx.cfg
    weather, _ = solar.pvgis_tmy(cfg["site"]["lat"], cfg["site"]["lon"], data.RAW / "pvgis_tmy.json")
    pr = prices(cfg)
    profiles, f_ew = orientation_profiles(weather, cfg)
    p = plane_layout(ctx, f_ew)
    p.drop(columns=["profile_key"]).to_parquet(city.CITY / "pv_planes.parquet")
    b, ex = buildings_balance(ctx, p, profiles, weather, pr)
    b.to_parquet(city.CITY / "pv_buildings.parquet")
    ex.to_csv(city.CITY / "pv_buurt_export.csv")
    from .validate import campus_vs_zhou, campus_zhou_like
    bu = data.cbs_layer("buurten")
    cmp_ = campus_vs_zhou(b, bu)
    cmp_["zhou_like_steps"] = campus_zhou_like(ctx, b, bu).round(4).to_dict("records")
    (city.CITY / "campus_comparison.json").write_text(json.dumps(cmp_, indent=2))

    sp = p[p.kwp > 0]
    summary = {"prices_eur_kwh": pr, "east_west_factor_vs_horizontal": f_ew,
               "specific_yield_kwh_kwp": {"median": float(sp.kwh_per_kwp.median()),
                                          "p10": float(sp.kwh_per_kwp.quantile(.1)), "p90": float(sp.kwh_per_kwp.quantile(.9)),
                                          "share_within_10pct_of_875": float(((sp.kwh_per_kwp / 875 - 1).abs() <= 0.10).mean())},
               "by_aoi": {}}
    for aoi, g in b.groupby(b.aoi.fillna("outside_aoi")):
        r = g[g.demand_kwh > 0]
        rr = r[r.kwh_yr > 0]
        summary["by_aoi"][aoi] = {
            "n_buildings": len(g), "n_with_pv_potential": int((g.kwp > 0).sum()),
            "kwp_total": float(g.kwp.sum()), "gwh_yr": float(g.kwh_yr.sum() / 1e6),
            "dwellings": int(g.dwellings.sum()), "residential_demand_gwh": float(r.demand_kwh.sum() / 1e6),
            "residential_pv_gwh": float(r.kwh_yr.sum() / 1e6),
            "residential_coverage": float(r.kwh_yr.sum() / r.demand_kwh.sum()) if len(r) else None,
            "scr_aggregate": float(rr.self_consumed_kwh.sum() / rr.kwh_yr.sum()) if len(rr) else None,
            "scr_aggregate_battery": float(rr.self_consumed_batt_kwh.sum() / rr.kwh_yr.sum()) if len(rr) else None,
            "value_2026_meur": float(rr.value_2026_eur.sum() / 1e6), "value_2027_meur": float(rr.value_2027_eur.sum() / 1e6),
            "value_2027_battery_meur": float(rr.value_2027_batt_eur.sum() / 1e6),
            "value_change_2027_pct": float(100 * (rr.value_2027_eur.sum() / rr.value_2026_eur.sum() - 1)) if len(rr) else None,
        }
    (city.CITY / "pv_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    from .pipeline import Context
    print(json.dumps(run(Context(data.load_config())), indent=1, default=str))
