"""Web data: per-buurt aggregates (GeoJSON) and per-building attributes (JSON keyed by BAG id).

Everything is written to web/public/data/ in WGS84 with rounded coordinates/values; all numbers come from
data/processed/city (pipeline outputs) — nothing is computed here that is not in those files.
"""
from __future__ import annotations

import json

import geopandas as gpd
import numpy as np
import pandas as pd

from . import city, data

WEB = data.ROOT / "web" / "public" / "data"


def _r(x, n=1):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


def _s(x):
    """String or None (pandas NaN -> None) so the JSON stays valid."""
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else str(x)


def building_table() -> gpd.GeoDataFrame:
    pvb = gpd.read_parquet(city.CITY / "pv_buildings.parquet")
    her = gpd.read_parquet(city.CITY / "heritage_buildings.parquet").drop(columns="geometry")
    chg = pd.read_parquet(city.CITY / "change_buildings.parquet")[["identificatie", "change", "d_median", "h6_median"]]
    cols = ["identificatie", "bouwjaar", "gebruiksdoel", "aoi", "buurtcode", "buurtnaam", "dwellings", "demand_kwh",
            "kwp", "kwh_yr", "self_consumed_kwh", "export_kwh", "self_consumed_batt_kwh", "scr", "scr_batt",
            "value_2026_eur", "value_2027_eur", "value_2027_batt_eur", "coverage", "geometry"]
    b = pvb[cols].merge(her[["kwp_permitted", "kwh_yr_permitted", "kwp_nopermit", "kwh_yr_nopermit",
                             "in_protected_view", "rijksmonument"]].reset_index(), on="identificatie", how="left")
    b = b.merge(chg, on="identificatie", how="left")
    planes = pd.read_parquet(city.CITY / "pv_planes.parquet")
    pa = planes.groupby("identificatie").agg(n_planes=("plane_id", "size"), roof_area_m2=("area_top_3d_m2", "sum"),
                                             roof_kwh_m2=("kwh_m2", "mean"), roof_kwh_m2_free=("kwh_m2_free", "mean"),
                                             roof_kwh_m2_notrees=("kwh_m2_notrees", "mean"))
    b = b.merge(pa.reset_index(), on="identificatie", how="left")
    b["shading_loss"] = 1 - b.roof_kwh_m2 / b.roof_kwh_m2_free
    b["tree_loss"] = 1 - b.roof_kwh_m2 / b.roof_kwh_m2_notrees
    return gpd.GeoDataFrame(b, geometry="geometry", crs="EPSG:28992")


def buurt_table(b: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    bu = data.cbs_layer("buurten")
    ex = pd.read_csv(city.CITY / "pv_buurt_export.csv", index_col=0)
    g = b.groupby("buurtcode")
    res = b[(b.demand_kwh > 0) & (b.kwh_yr > 0)].groupby("buurtcode")
    t = pd.DataFrame({
        "n_buildings": g.size(), "dwellings": g.dwellings.sum(),
        "kwp": g.kwp.sum(), "gwh": g.kwh_yr.sum() / 1e6,
        "gwh_permitted": g.kwh_yr_permitted.sum() / 1e6, "gwh_nopermit": g.kwh_yr_nopermit.sum() / 1e6,
        "demand_gwh": g.demand_kwh.sum() / 1e6,
        "res_pv_gwh": res.kwh_yr.sum() / 1e6, "res_self_gwh": res.self_consumed_kwh.sum() / 1e6,
        "res_self_batt_gwh": res.self_consumed_batt_kwh.sum() / 1e6,
        "value_2026_keur": res.value_2026_eur.sum() / 1e3, "value_2027_keur": res.value_2027_eur.sum() / 1e3,
        "value_2027_batt_keur": res.value_2027_batt_eur.sum() / 1e3,
        "n_new": g.change.apply(lambda s: (s == "new_since_2023").sum()),
        "n_raised": g.change.apply(lambda s: (s == "raised_or_extended").sum()),
        "n_protected": g.in_protected_view.sum(), "n_monuments": g.rijksmonument.sum(),
    })
    t["coverage"] = t.res_pv_gwh / t.demand_gwh.replace(0, np.nan)
    t["scr"] = t.res_self_gwh / t.res_pv_gwh.replace(0, np.nan)
    t["scr_batt"] = t.res_self_batt_gwh / t.res_pv_gwh.replace(0, np.nan)
    t["value_change_2027"] = t.value_2027_keur / t.value_2026_keur.replace(0, np.nan) - 1
    t = t.join(ex[["export_peak_kw", "export_june_midday_mean_kw"]])
    cbs = bu.set_index("buurtcode")
    t["cbs_pct_dwellings_with_pv"] = pd.to_numeric(cbs.percentageWoningenMetZonnestroom, errors="coerce").where(lambda s: s >= 0)
    t["cbs_kwh_delivered_per_dwelling"] = pd.to_numeric(cbs.gemiddeldeElektriciteitslevering, errors="coerce").where(lambda s: s >= 0)
    t["cbs_kwh_returned_per_dwelling"] = pd.to_numeric(cbs.gemiddeldeElektriciteitsteruglevering, errors="coerce").where(lambda s: s >= 0)
    out = bu[["buurtcode", "buurtnaam", "wijkcode", "geometry"]].merge(t.reset_index(), on="buurtcode", how="inner")
    aoi_w = {"WK050311": "binnenstad", "WK050324": "voorhof"}
    out["aoi"] = out.wijkcode.map(aoi_w)
    out.loc[out.buurtcode.isin(["BU05032801", "BU05032805"]), "aoi"] = "campus"
    return out


def write(b: gpd.GeoDataFrame, bu: gpd.GeoDataFrame) -> dict:
    WEB.mkdir(parents=True, exist_ok=True)
    # buurten (all processed, flagged by AOI) — polygons simplified to 2 m
    g = bu.copy()
    g["geometry"] = g.geometry.simplify(2)
    g = g.to_crs(4326)
    num = g.select_dtypes("number").columns
    g[num] = g[num].astype(float).round(3)
    path_b = WEB / "buurten.geojson"
    path_b.write_text(g.to_json(drop_id=True, na="null"))

    # building attributes for study-area buildings, keyed by BAG id
    a = b[b.aoi.notna()]
    rec = {}
    for r in a.itertuples():
        rec[r.identificatie] = {
            "aoi": r.aoi, "buurt": _s(r.buurtnaam), "bouwjaar": None if pd.isna(r.bouwjaar) else int(r.bouwjaar),
            "h": _r(r.h6_median, 1),
            "use": _s(r.gebruiksdoel), "dwellings": int(r.dwellings), "monument": bool(r.rijksmonument),
            "protected_view": bool(r.in_protected_view), "change": _s(r.change),
            "roof_m2": _r(r.roof_area_m2, 0), "roof_kwh_m2": _r(r.roof_kwh_m2, 0),
            "shading_loss": _r(r.shading_loss, 3), "tree_loss": _r(r.tree_loss, 3),
            "kwp": _r(r.kwp, 1), "kwh": _r(r.kwh_yr, 0), "kwp_permitted": _r(r.kwp_permitted, 1),
            "kwh_permitted": _r(r.kwh_yr_permitted, 0), "kwh_nopermit": _r(r.kwh_yr_nopermit, 0),
            "demand_kwh": _r(r.demand_kwh, 0), "scr": _r(r.scr, 3), "scr_batt": _r(r.scr_batt, 3),
            "eur_2026": _r(r.value_2026_eur, 0), "eur_2027": _r(r.value_2027_eur, 0),
            "eur_2027_batt": _r(r.value_2027_batt_eur, 0),
            "co2_t": _r(r.kwh_yr * CO2_KG_PER_KWH / 1000, 2) if CO2_KG_PER_KWH else None,
        }
    path_a = WEB / "buildings.json"
    path_a.write_text(json.dumps(rec, separators=(",", ":"), allow_nan=False))  # NaN is not valid JSON

    # footprints for click lookup / 2D layers, with the few properties the map colours by
    f = a[["identificatie", "geometry"]].copy()
    f["k"] = a.roof_kwh_m2.round(0)
    f["p"] = (a.kwh_yr_permitted / a.kwh_yr.where(a.kwh_yr > 0)).round(2)
    f["m"] = a.rijksmonument.fillna(False).astype(int)
    f["c"] = a.change.fillna("unchanged")
    f["geometry"] = f.geometry.simplify(0.3)
    f = f.to_crs(4326)
    path_f = WEB / "footprints.geojson"
    path_f.write_text(f.to_json(drop_id=True))
    return {p.name: round(p.stat().st_size / 1e6, 2) for p in (path_b, path_a, path_f)}


CO2_KG_PER_KWH = None  # no sourced emission factor yet: CO2 avoided is left empty rather than invented


def energy_profiles() -> dict:
    """Per study area: monthly PV vs household demand, an average June and December day, and the value split.

    Production: every PV plane's annual kWh spread over the year with its orientation profile (as in pv.py).
    Demand: dwellings x CBS delivery per dwelling, shaped by the 2026 E1A profile. Values in GWh / MW / M EUR.
    """
    from . import pv, solar
    cfg = data.load_config()
    weather, _ = solar.pvgis_tmy(cfg["site"]["lat"], cfg["site"]["lon"], data.RAW / "pvgis_tmy.json")
    profiles, _ = pv.orientation_profiles(weather, cfg)
    hh = pv.household_profile(weather.index)
    planes = pd.read_parquet(city.CITY / "pv_planes.parquet")
    planes = planes[(planes.kwp > 0) & planes.aoi.notna()]
    flat = planes.slope_deg < cfg["segmentation"]["flat_slope_deg"]
    planes = planes.assign(key=[pv.profile_key(f, s, a) for f, s, a in zip(flat, planes.slope_deg, planes.aspect_deg)])
    b = gpd.read_parquet(city.CITY / "pv_buildings.parquet")
    pr = json.loads((city.CITY / "pv_summary.json").read_text())["prices_eur_kwh"]
    local = weather.index.tz_convert("Europe/Amsterdam")
    out = {}
    for aoi in ["binnenstad", "campus", "voorhof"]:
        ba = b[b.aoi == aoi]
        res_ids = set(ba.identificatie[ba.demand_kwh > 0])
        pa = planes[planes.identificatie.isin(res_ids)]
        prod = sum(profiles[k] * kwh for k, kwh in pa.groupby("key").kwh_yr.sum().items())
        dem = hh * ba.demand_kwh.sum()
        s = pd.DataFrame({"pv": prod, "demand": dem}, index=local)
        monthly = s.groupby(s.index.month).sum() / 1e6
        day = {}
        for m, name in ((6, "june"), (12, "december")):
            d = s[s.index.month == m]
            day[name] = (d.groupby(d.index.hour).mean() / 1e3).round(3).to_dict("list")  # kWh per hour = kW -> MW
        r = ba[(ba.demand_kwh > 0) & (ba.kwh_yr > 0)]
        val = {k: float(v) for k, v in {
            "self_kwh": r.self_consumed_kwh.sum(), "export_kwh": r.export_kwh.sum(),
            "self_batt_kwh": r.self_consumed_batt_kwh.sum(), "export_batt_kwh": r.export_batt_kwh.sum(),
            "netted_kwh": np.minimum(r.kwh_yr, r.demand_kwh).sum(), "excess_kwh": (r.kwh_yr - np.minimum(r.kwh_yr, r.demand_kwh)).sum(),
        }.items()}
        out[aoi] = {"monthly_gwh": {"pv": monthly.pv.round(3).tolist(), "demand": monthly.demand.round(3).tolist()},
                    "day_mw": day, "residential_kwh": val}
    out["prices"] = {"retail": pr["retail_marginal"], "export_2027": pr["export_2027"]}
    return out


def site_summary() -> dict:
    """Every number shown as text or chart on the website, collected from the pipeline outputs."""
    C = city.CITY
    rd = lambda p: json.loads((C / p).read_text())  # noqa: E731
    pvs, her, unc, cmp_, chg = rd("pv_summary.json"), rd("heritage_summary.json"), rd("uncertainty_summary.json"), \
        rd("campus_comparison.json"), rd("change_stats.json")
    val, cst = rd("validation.json"), rd("city_stats.json")
    sens = pd.read_csv(C / "tree_sensitivity.csv")
    pvg = pd.read_csv(C / "val_pvgis.csv")
    years = pd.read_csv(C / "uncertainty_years.csv")
    meta = {t.name: json.loads((t / "meta.json").read_text()) for t in sorted(data.PROCESSED.glob("8*_4*"))}
    qa = {t.name: json.loads((t / "qa_rasters.json").read_text()) for t in sorted(data.PROCESSED.glob("8*_4*"))}
    vt = [json.loads((t / "validation.json").read_text())["heights"] for t in sorted(data.PROCESSED.glob("8*_4*"))]
    aois = ["binnenstad", "campus", "voorhof"]
    out = {
        "data": {
            "flights": sorted({m["flight_first"] for m in meta.values()} | {m["flight_last"] for m in meta.values()}),
            "n_tiles": len(meta), "points_million": round(sum(m["n_points_kept"] for m in meta.values()) / 1e6, 0),
            "building_pts_m2": [round(min(m["density_building_pts_m2"] for m in meta.values()), 1),
                                round(max(m["density_building_pts_m2"] for m in meta.values()), 1)],
            "n_buildings": cst["n_buildings_total"], "n_crossing_tile_edges": cst["n_buildings_crossing_tile_edges"],
            "dsm_rmse_m": [round(min(q["dsm_vs_official"]["rmse"] for q in qa.values()), 2),
                           round(max(q["dsm_vs_official"]["rmse"] for q in qa.values()), 2)],
        },
        "prices": pvs["prices_eur_kwh"], "east_west_factor": pvs["east_west_factor_vs_horizontal"],
        "specific_yield": pvs["specific_yield_kwh_kwp"],
        "aoi": {a: {"pv": pvs["by_aoi"][a], "heritage": her["by_aoi"][a], "uncertainty": unc["by_aoi"][a],
                    "buildings_heritage": her["buildings"].get(a), "change": chg["building_change_by_aoi"].get(a),
                    "aoi_summary": next(r for r in cst["aoi_summary"] if r["aoi"] == a),
                    "validation": val.get(a)} for a in aois},
        "validation": {"all": val["all"], "pvgis": val["irradiance_vs_pvgis"],
                       "pvgis_bins": pvg[["tilt_b", "asp_b", "n", "ours", "pvgis"]].round(1).to_dict("records"),
                       "heights_single_part_bias_m": round(float(np.mean([v["h70_bias_m"] for v in vt])), 3)},
        "trees": sens[sens.aoi.isin(aois)][["scenario", "aoi", "tree_loss", "share_bldg_tree_loss_gt10pct",
                                            "share_bldg_tree_loss_gt25pct"]].round(4).to_dict("records"),
        "weather_years": years.round(4).to_dict("records"),
        "change": {k: chg[k] for k in ("noise_unchanged_buildings", "building_change_counts", "validation_new",
                                       "demolitions", "pv_flat_roofs")},
        "campus": cmp_,
        "heritage_rules": her["rules"], "uncertainty_config": unc["config"],
        "heritage_buildings": her["buildings"], "heritage_cells": her["usable_cell_categories"],
        "energy": energy_profiles(),
    }
    return out


def run(ctx=None) -> dict:
    b = building_table()
    bu = buurt_table(b)
    bu.drop(columns="geometry").to_csv(city.CITY / "buurt_summary.csv", index=False)
    sizes = write(b, bu)
    (WEB / "site.json").write_text(json.dumps(site_summary(), default=str, allow_nan=False))
    sizes["site.json"] = round((WEB / "site.json").stat().st_size / 1e6, 3)
    return sizes


if __name__ == "__main__":
    print(json.dumps(run(), indent=1))
