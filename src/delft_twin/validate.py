"""Validation of our reconstruction against Kadaster 3D Basisvoorziening 2025.

That reference is built with `roofer` (the 3DBAG reconstruction tool) on the AHN5 2023
point cloud, so it is an independent model from a different LiDAR epoch than ours (AHN6, 2026).
Differences therefore mix method error with real 2023 -> 2026 change.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import STRtree, points
from shapely.geometry import Polygon


def load_ref_heights(gpkg: Path, bounds) -> pd.DataFrame:
    """Per BAG pand: reference ground, roof 70th percentile (max over parts), roof max — all in m NAP.

    The rf_h_roof_* attributes are heights above the building's ground level (rf_h_ground, NAP):
    verified on 18,598 Delft buildings, where (ours - ref) correlates 0.95 with rf_h_ground.
    """
    g = gpd.read_file(gpkg, bbox=tuple(bounds), ignore_geometry=True)
    g = g[g.rf_success].copy()
    for c in ("rf_h_roof_70p", "rf_h_roof_max"):
        g[c] = g[c] + g["rf_h_ground"]
    agg = g.groupby("identificatie").agg(
        n_parts=("rf_h_roof_70p", "size"), ref_h_ground=("rf_h_ground", "first"),
        ref_h_70p=("rf_h_roof_70p", "max"), ref_h_max=("rf_h_roof_max", "max"),
        ref_roof_type=("rf_roof_type", "first"), ref_pc_year=("rf_pc_year", "first"))
    return agg.reset_index()


def load_ref_roofs(cityjson: Path, bounds) -> gpd.GeoDataFrame:
    """LoD2.2 RoofSurfaces as 2D polygons with slope, azimuth and a fitted plane."""
    cj = json.loads(Path(cityjson).read_text(encoding="utf-8"))
    sc, tr = np.array(cj["transform"]["scale"]), np.array(cj["transform"]["translate"])
    V = np.array(cj["vertices"]) * sc + tr
    x0, y0, x1, y1 = bounds
    rows = []
    for oid, o in cj["CityObjects"].items():
        if o["type"] != "BuildingPart":
            continue
        pand = oid.split("NL.IMBAG.Pand.")[-1].split("-")[0]
        for geom in o.get("geometry", []):
            if geom["lod"] != "2.2":
                continue
            surfs = geom["semantics"]["surfaces"]
            for shell, vals in zip(geom["boundaries"], geom["semantics"]["values"]):
                for face, v in zip(shell, vals):
                    if v is None or surfs[v]["type"] != "RoofSurface":
                        continue
                    ring = V[face[0]]
                    if not (x0 <= ring[:, 0].mean() <= x1 and y0 <= ring[:, 1].mean() <= y1):
                        continue
                    poly = Polygon(ring[:, :2])
                    if poly.area < 0.5 or not poly.is_valid:
                        continue
                    c = ring.mean(axis=0)
                    _, _, vt = np.linalg.svd(ring - c)
                    n = vt[2] if vt[2, 2] >= 0 else -vt[2]
                    rows.append({"identificatie": pand, "ref_slope": surfs[v].get("rf_slope"),
                                 "ref_azimuth": surfs[v].get("rf_azimuth"),
                                 "ref_area_2d": poly.area, "pcx": c[0], "pcy": c[1], "pcz": c[2],
                                 "pnx": n[0], "pny": n[1], "pnz": n[2], "geometry": poly})
    if not rows:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:28992")
    return gpd.GeoDataFrame(rows, crs="EPSG:28992")


def pvgis_poa(lat, lon, tilt, aspect_north, cache: dict) -> float:
    """PVGIS v5.3 annual in-plane irradiation H(i)_y [kWh/m2], no horizon. Aspect: ours 0=N -> PVGIS 0=S."""
    import requests
    key = f"{tilt:.0f}_{aspect_north:.0f}"
    if key not in cache:
        az = (aspect_north % 360) - 180
        r = requests.get("https://re.jrc.ec.europa.eu/api/v5_3/PVcalc", timeout=120, params={
            "lat": lat, "lon": lon, "peakpower": 1, "loss": 14, "angle": tilt, "aspect": az,
            "usehorizon": 0, "outputformat": "json"})
        r.raise_for_status()
        cache[key] = r.json()["outputs"]["totals"]["fixed"]["H(i)_y"]
    return cache[key]


def validate_vs_pvgis(planes_solar: pd.DataFrame, cfg: dict, cache_path: Path, tmy_ghi_kwh: float,
                      n_max: int = 40) -> tuple[dict, pd.DataFrame]:
    """Unshaded planes (svf > 0.97, < 2 % obstruction loss) vs PVGIS for the same tilt/aspect (5 deg bins).

    PVGIS PVcalc reports the 2005-2023 mean while our input is one TMY year; the "tmy_adjusted"
    metrics scale PVGIS by TMY GHI / PVGIS horizontal so only the model (transposition, shading) is compared.
    """
    p = planes_solar[(planes_solar.area_3d_m2 >= 10) & (planes_solar.svf > 0.97)
                     & (planes_solar.kwh_m2 >= 0.98 * planes_solar.kwh_m2_free)].copy()
    p["tilt_b"] = (p.slope_deg / 5).round() * 5
    p["asp_b"] = ((p.aspect_deg / 15).round() * 15) % 360
    p.loc[p.tilt_b == 0, "asp_b"] = 180
    g = p.groupby(["tilt_b", "asp_b"]).agg(n=("kwh_m2", "size"), ours=("kwh_m2", "mean")).reset_index()
    g = g.sort_values("n", ascending=False).head(n_max)
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    lat, lon = cfg["site"]["lat"], cfg["site"]["lon"]
    g["pvgis"] = [pvgis_poa(lat, lon, t, a, cache) for t, a in zip(g.tilt_b, g.asp_b)]
    k = tmy_ghi_kwh / pvgis_poa(lat, lon, 0, 180, cache)
    cache_path.write_text(json.dumps(cache))
    rel = g.ours / g.pvgis - 1
    rel_adj = g.ours / (g.pvgis * k) - 1
    w = g.n / g.n.sum()
    g["rel_pct"], g["rel_tmy_adj_pct"] = 100 * rel, 100 * rel_adj
    return {"n_planes": int(g.n.sum()), "n_bins": len(g), "bias_pct_weighted": float(100 * (rel * w).sum()),
            "rmse_pct": float(100 * np.sqrt((rel**2).mean())), "max_abs_pct": float(100 * rel.abs().max()),
            "tmy_vs_longterm_ghi_ratio": float(k), "bias_pct_tmy_adjusted": float(100 * (rel_adj * w).sum()),
            "rmse_pct_tmy_adjusted": float(100 * np.sqrt((rel_adj**2).mean()))}, g


ZHOU_2022 = {
    "reference": "Zhou, Verkou, Zeman, Ziar & Isabella, Solar RRL 6(5) 2100478 (2022), doi:10.1002/solr.202100478",
    "total_roofs_and_facades_gwh": 8.1,      # abstract and p. 15
    "roofs_gwh": 4.7,                        # p. 15: "roofs contribute around 4.7 GWh/yr", facades 3.4
    "campus_demand_gwh": 82.6,               # p. 15
    # methods (pp. 5-16): AHN3 (campus flown 2014), trees opaque; Solarge SOLO/DUWO 365 Wp, 2.066 x 0.997 m;
    # flat roofs dual-tilt 12 deg (0.2 m row clearance) or 15 deg rows (0.7 m); module dropped if any of its points
    # gets < 600 kWh/m2/yr or its specific yield < 650 kWh/kWp; AC losses: SNL inverter + MPPT 0.98, ohmic 0.99,
    # mismatch 0.99, soiling 0.98; monumental / protected-view buildings get flat-mounted (0 deg) modules.
    "module_wp": 365, "module_area_m2": 2.066 * 0.997, "min_specific_yield_kwh_kwp": 650,
}


def campus_vs_zhou(buildings_pv: pd.DataFrame, buurten: gpd.GeoDataFrame) -> dict:
    """Our roof-only yield for TU Delft (non-residential) buildings vs Zhou et al. (campus roofs + facades).

    Scopes: (a) non-residential buildings in the campus AOI (CBS TU-Noord + TU-Campus);
            (b) (a) plus the Delftech business park buurt next to it.
    """
    b = buildings_pv.copy()
    nonres = ~b.gebruiksdoel.fillna("").str.contains("woonfunctie")
    rp = gpd.GeoDataFrame(b[["identificatie"]], geometry=gpd.GeoSeries(b.geometry).representative_point(), crs="EPSG:28992")
    j = gpd.sjoin(rp, buurten[["buurtcode", "buurtnaam", "geometry"]], predicate="within").drop_duplicates("identificatie")
    code = b.identificatie.map(j.set_index("identificatie").buurtcode)
    scopes = {"campus_aoi_nonresidential": code.isin(["BU05032801", "BU05032805"]) & nonres,
              "campus_aoi_plus_delftech_nonresidential": code.isin(["BU05032801", "BU05032805", "BU05032807"]) & nonres}
    out = {"zhou": ZHOU_2022}
    for k, m in scopes.items():
        g = b[m]
        gwh = float(g.kwh_yr.sum() / 1e6)
        out[k] = {"n_buildings": int(m.sum()), "n_with_pv": int((g.kwp > 0).sum()), "kwp": float(g.kwp.sum()),
                  "roof_gwh_yr": gwh, "ratio_to_zhou_total": gwh / ZHOU_2022["total_roofs_and_facades_gwh"],
                  "ratio_to_zhou_roofs": gwh / ZHOU_2022["roofs_gwh"],
                  "share_of_campus_demand": gwh / ZHOU_2022["campus_demand_gwh"]}
    return out


def campus_zhou_like(ctx, buildings_pv: pd.DataFrame, buurten: gpd.GeoDataFrame) -> pd.DataFrame:
    """Step-wise move our campus roof estimate towards Zhou et al.'s assumptions to attribute the difference."""
    import copy
    from . import city, data, pv
    b = buildings_pv
    nonres = ~b.gebruiksdoel.fillna("").str.contains("woonfunctie")
    rp = gpd.GeoDataFrame(b[["identificatie"]], geometry=gpd.GeoSeries(b.geometry).representative_point(), crs="EPSG:28992")
    j = gpd.sjoin(rp, buurten[["buurtcode", "geometry"]], predicate="within").drop_duplicates("identificatie")
    code = b.identificatie.map(j.set_index("identificatie").buurtcode)
    scope = code.isin(["BU05032801", "BU05032805"]) & nonres
    yr = pd.to_numeric(b.bouwjaar, errors="coerce")
    ids_all, ids_2014 = set(b.identificatie[scope]), set(b.identificatie[scope & (yr <= 2014)])

    planes = pd.read_parquet(city.CITY / "roof_planes_solar.parquet")
    u = pd.concat([pd.read_parquet(data.PROCESSED / t / "pv_usable_cells.parquet") for t in ctx.tiles], ignore_index=True)
    u = u.merge(planes[["tile", "plane_id", "identificatie"]], on=["tile", "plane_id"], how="left")
    u = u[u.identificatie.isin(ids_all)].copy()

    def gwh(cfg_mod, ids):
        uu = u[u.identificatie.isin(ids)].copy()
        uu["f_ok"] = pv.field_suitability(uu, cfg_mod["pv"])
        p = pv.planes_from_cells(planes[planes.identificatie.isin(ids)], uu, cfg_mod)
        return float(p.kwh_yr.sum() / 1e6), float(p.kwp.sum())

    base = copy.deepcopy(ctx.cfg)
    dens = copy.deepcopy(base)
    dens["pv"]["module_wp"], dens["pv"]["module_area_m2"] = ZHOU_2022["module_wp"], ZHOU_2022["module_area_m2"]
    thr = copy.deepcopy(dens)
    thr["pv"]["min_irradiation_kwh_m2"] = ZHOU_2022["min_specific_yield_kwh_kwp"] / base["pv"]["performance_ratio"]
    steps = [("ours (technical, 2026 campus)", base, ids_all),
             ("+ Zhou module density (177 vs 221 Wp/m2)", dens, ids_all),
             ("+ Zhou threshold (>= 650 kWh/kWp)", thr, ids_all),
             ("+ only buildings built <= 2014 (AHN3 campus)", thr, ids_2014)]
    rows = []
    for name, c, ids in steps:
        g, kwp = gwh(c, ids)
        rows.append({"step": name, "n_buildings": len(ids), "kwp": kwp, "roof_gwh_yr": g,
                     "ratio_to_zhou_roofs": g / ZHOU_2022["roofs_gwh"]})
    return pd.DataFrame(rows)


def angle_diff(a, b):
    d = np.abs(np.asarray(a) - np.asarray(b)) % 360
    return np.minimum(d, 360 - d)


def validate_heights(planes: pd.DataFrame, foot: gpd.GeoDataFrame, pts: dict, labels: dict,
                     ref: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Compare per-building roof height (70th pct and max of roof points) to the reference."""
    z = pts["z"][labels["keep"]]
    b = labels["bag_idx"]
    on_roof = labels["plane_id"] >= 0
    df = pd.DataFrame({"bag_idx": b[on_roof], "z": z[on_roof]})
    ours = df.groupby("bag_idx").z.agg(h_70p=lambda s: np.percentile(s, 70), h_max="max").reset_index()
    ours["identificatie"] = foot["identificatie"].values[ours.bag_idx]
    m = ours.merge(ref, on="identificatie", how="inner")
    single = m[m.n_parts == 1]
    d70 = single.h_70p - single.ref_h_70p
    dmax = m.h_max - m.ref_h_max
    robust = d70[np.abs(d70) < 3]  # >3 m = probable demolition/new build or BAG mismatch
    out = {
        "n_matched": int(len(m)), "n_single_part": int(len(single)),
        "h70_bias_m": float(d70.mean()), "h70_rmse_m": float(np.sqrt((d70**2).mean())),
        "h70_median_abs_m": float(d70.abs().median()),
        "h70_rmse_m_excl_gt3m": float(np.sqrt((robust**2).mean())), "n_gt3m": int((d70.abs() >= 3).sum()),
        "hmax_bias_m": float(dmax.mean()), "hmax_median_abs_m": float(dmax.abs().median()),
    }
    m["d_h70"] = m.h_70p - m.ref_h_70p
    return out, m


def validate_planes(planes: pd.DataFrame, ref_roofs: gpd.GeoDataFrame, min_area: float = 10.0) -> tuple[dict, pd.DataFrame]:
    """Match each of our planes (>= min_area) to the reference roof surface under its centroid."""
    p = planes[planes.area_3d_m2 >= min_area].reset_index(drop=True)
    tree = STRtree(ref_roofs.geometry.values)
    pi, ri = tree.query(points(p.cx.values, p.cy.values), predicate="within")
    cand = pd.DataFrame({"pi": pi, "ri": ri})
    cand = cand[ref_roofs.identificatie.values[cand.ri] == p.identificatie.values[cand.pi]]
    r = ref_roofs.iloc[cand.ri]
    # reference plane height at our centroid -> pick the vertically closest surface
    zr = r.pcz.values - ((p.cx.values[cand.pi] - r.pcx.values) * r.pnx.values
                         + (p.cy.values[cand.pi] - r.pcy.values) * r.pny.values) / np.maximum(r.pnz.values, 0.05)
    cand["dz"] = np.abs(p.cz.values[cand.pi] - zr)
    best = cand.sort_values("dz").drop_duplicates("pi")
    mm = p.iloc[best.pi.values].reset_index(drop=True)
    rr = ref_roofs.iloc[best.ri.values].reset_index(drop=True)
    mm["ref_slope"], mm["ref_azimuth"], mm["dz"] = rr.ref_slope.values, rr.ref_azimuth.values, best.dz.values
    mm["d_slope"] = mm.slope_deg - mm.ref_slope
    pitched = mm[(mm.slope_deg >= 10) & (mm.ref_slope >= 10)]
    d_asp = angle_diff(pitched.aspect_deg, pitched.ref_azimuth)
    out = {
        "n_planes_ge_min_area": int(len(p)), "n_matched": int(len(mm)), "match_rate": float(len(mm) / max(len(p), 1)),
        "slope_mae_deg": float(mm.d_slope.abs().mean()),
        "slope_median_abs_deg": float(mm.d_slope.abs().median()),
        "slope_bias_deg": float(mm.d_slope.mean()),
        "aspect_median_abs_deg_pitched": float(np.median(d_asp)), "aspect_within_15deg_pitched": float((d_asp <= 15).mean()),
        "n_pitched": int(len(pitched)), "dz_median_m": float(mm.dz.median()),
        "frac_matched_dz_lt_0p5m": float((mm.dz < 0.5).mean()),
    }
    return out, mm
