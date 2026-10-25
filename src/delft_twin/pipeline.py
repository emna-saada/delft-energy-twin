"""Command-line entry points.

    python -m delft_twin.pipeline <stage> [--tile T | --all] [--workers N]

Stages run per AHN6 tile; with --all they loop over the 14 tiles of the study areas and
then write city-level outputs to data/processed/city/. Each building is processed by the
tile that owns it (see city.py), using points and surfaces from neighbouring tiles.
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor

import geopandas as gpd
import numpy as np
import pandas as pd

from . import city, data, preprocess, segment, solar, validate


def tile_bounds(tile: str):
    x, y = map(int, tile.split("_"))
    return (x, y, x + 1000, y + 1000)


class Context:
    """Lazily loaded city-wide inputs shared by all tiles in one run."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.tiles = city.tile_ids(cfg)
        self._cache = {}

    def get(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    @property
    def buildings(self):
        return self.get("buildings", lambda: city.assign_buildings(self.cfg, self.tiles))

    @property
    def mosaics(self):
        return self.get("mosaics", lambda: city.load_mosaics(self.cfg, self.tiles))


# --------------------------------------------------------------------------- stages

def stage_data(ctx, tile):
    aois = data.build_aois(ctx.cfg)
    idx = data.tiles_for_aois(ctx.cfg, aois, ctx.cfg["ahn"]["main_epoch"])
    row = idx[idx.AHN == tile].iloc[0]
    data.fetch_ahn_tile(row, "AHN6", ("Puntenwolk", "Oppervlaktemodel (DSM) ½m", "Maaiveldmodel (DTM) ½m"))


def _preprocess(tile):
    cfg = data.load_config()
    out = data.PROCESSED / tile
    meta = preprocess.prepare_tile(data.RAW / "AHN6" / f"AHN6_2026_C_{tile}.LAZ", out, tile_bounds(tile), cfg)
    qa = {"dsm_vs_official": preprocess.compare_rasters(out / "dsm.tif", data.RAW / "AHN6" / f"AHN6_2026_R_{tile}.TIF"),
          "dtm_vs_official": preprocess.compare_rasters(out / "dtm.tif", data.RAW / "AHN6" / f"AHN6_2026_M_{tile}.TIF")}
    (out / "qa_rasters.json").write_text(json.dumps(qa, indent=2))
    return {"meta": meta, "qa": qa}


def stage_preprocess(ctx, tile):
    return _preprocess(tile)


def stage_segment(ctx, tile):
    out = data.PROCESSED / tile
    b = ctx.buildings
    own = b[(b.tile == tile) & ~b.incomplete].reset_index(drop=True)
    x0, y0, x1, y1 = own.total_bounds
    ext = (x0 - 1, y0 - 1, x1 + 1, y1 + 1)
    pts = city.gather_points(ext, ctx.tiles)
    t = time.time()
    planes, pp = segment.segment_buildings(pts, own, ext, ctx.cfg)
    secs = time.time() - t
    planes["tile"] = tile
    planes.to_parquet(out / "roof_planes.parquet")
    k = pp["keep"]
    np.savez_compressed(out / "owned_points.npz", x=pts["x"][k], y=pts["y"][k], z=pts["z"][k],
                        bag_idx=pp["bag_idx"], plane_id=pp["plane_id"], obstacle=pp["obstacle"])
    own.to_file(out / "footprints.gpkg", driver="GPKG")
    stats = {
        "seconds": round(secs, 1), "n_buildings": len(own),
        "n_crossing_tile_edge": int((~own.within(city.tile_box(tile))).sum()),
        "n_buildings_with_planes": int(planes.bag_idx.nunique()), "n_planes": len(planes),
        "pts_in_footprints": int(k.sum()), "frac_pts_on_planes": float((pp["plane_id"] >= 0).mean()),
        "frac_pts_obstacle": float(pp["obstacle"].mean()),
        "median_fit_rmse_m": float(planes.fit_rmse.median()),
        "share_flat_area": float(planes.loc[planes.roof_type == "flat", "area_3d_m2"].sum() / planes.area_3d_m2.sum()),
    }
    (out / "segment_stats.json").write_text(json.dumps(stats, indent=2))
    return stats


def _owned(tile):
    out = data.PROCESSED / tile
    p = dict(np.load(out / "owned_points.npz"))
    pts = {k: p[k] for k in ("x", "y", "z")}
    labels = {"keep": np.ones(p["x"].size, bool), "bag_idx": p["bag_idx"],
              "plane_id": p["plane_id"], "obstacle": p["obstacle"]}
    return pts, labels


def stage_validate(ctx, tile):
    out = data.PROCESSED / tile
    planes = pd.read_parquet(out / "roof_planes.parquet")
    foot = gpd.read_file(out / "footprints.gpkg")
    pts, labels = _owned(tile)
    ref_h = ctx.get("ref_h", lambda: city.ref_heights_all(ctx.tiles))
    ref_r = ctx.get("ref_r", lambda: city.ref_roofs_all(ctx.tiles))
    ref_r = ref_r[ref_r.identificatie.isin(set(foot.identificatie))].reset_index(drop=True)
    h, hm = validate.validate_heights(planes, foot, pts, labels, ref_h)
    p, pm = validate.validate_planes(planes, ref_r)
    hm["tile"], pm["tile"] = tile, tile
    hm.to_csv(out / "val_heights.csv", index=False)
    pm.to_parquet(out / "val_planes.parquet")
    res = {"reference": "Kadaster 3D Basisvoorziening 2025 (roofer on AHN5 2023)",
           "heights": h, "planes": p, "n_ref_roof_surfaces": len(ref_r)}
    (out / "validation.json").write_text(json.dumps(res, indent=2))
    return res


def roof_cells(pts: dict, labels: dict, origin, res: float, ncols: int):
    """Per cell of the city grid: plane of the highest labelled point; rows, cols, plane ids, obstacle flag."""
    x0, y1 = origin
    x, y, z = pts["x"], pts["y"], pts["z"]
    pid = labels["plane_id"]
    cell = ((y1 - y) // res).astype(np.int64) * ncols + ((x - x0) // res).astype(np.int64)
    obst_cells = np.unique(cell[labels["obstacle"]])
    on = pid >= 0
    order = np.lexsort((z[on], cell[on]))
    c_sorted, p_sorted = cell[on][order], pid[on][order]
    last = np.r_[c_sorted[1:] != c_sorted[:-1], True] if c_sorted.size else np.zeros(0, bool)
    cells, pids = c_sorted[last], p_sorted[last]
    return cells // ncols, cells % ncols, pids, np.isin(cells, obst_cells)


def cell_inputs(ctx, tile):
    """Roof cells of a tile on the city grid with their plane height and normal (inputs of the solar kernel)."""
    res = ctx.cfg["preprocess"]["raster_res"]
    planes = pd.read_parquet(data.PROCESSED / tile / "roof_planes.parquet").set_index("plane_id")
    pts, labels = _owned(tile)
    dsm, _, cb = ctx.mosaics
    rows, cols, pids, obst = roof_cells(pts, labels, (cb.left, cb.top), res, dsm.shape[1])
    p = planes.loc[pids]
    cx = cb.left + (cols + 0.5) * res
    cy = cb.top - (rows + 0.5) * res
    zc = p.cz.values - ((cx - p.cx.values) * p.nx.values + (cy - p.cy.values) * p.ny.values) / p.nz.values
    nrm = p[["nx", "ny", "nz"]].values.astype(np.float64)
    return {"rows": rows.astype(np.int64), "cols": cols.astype(np.int64), "pids": pids, "obst": obst,
            "z": zc, "nrm": nrm, "planes": planes}


def tmy(ctx):
    cfg = ctx.cfg
    return ctx.get("tmy", lambda: solar.pvgis_tmy(cfg["site"]["lat"], cfg["site"]["lon"], data.RAW / "pvgis_tmy.json"))


def stage_solar(ctx, tile):
    out = data.PROCESSED / tile
    cfg = ctx.cfg
    res = cfg["preprocess"]["raster_res"]
    c = cell_inputs(ctx, tile)
    rows, cols, pids, obst, planes = c["rows"], c["cols"], c["pids"], c["obst"], c["planes"]
    dsm, dsm_nv, _ = ctx.mosaics
    weather, tmy_meta = tmy(ctx)
    t = time.time()
    irr, svf, wx = solar.run_tile(rows, cols, c["z"], c["nrm"], dsm, dsm_nv, res, weather, cfg)
    secs = time.time() - t

    cells = pd.DataFrame({"row": rows, "col": cols, "plane_id": pids, "obstacle": obst,
                          "kwh_m2": irr[:, 0], "kwh_m2_notrees": irr[:, 1], "kwh_m2_free": irr[:, 2], "svf": svf})
    cells.to_parquet(out / "roof_cells_solar.parquet")
    agg = cells.groupby("plane_id").agg(n_cells=("kwh_m2", "size"), kwh_m2=("kwh_m2", "mean"),
                                        kwh_m2_notrees=("kwh_m2_notrees", "mean"), kwh_m2_free=("kwh_m2_free", "mean"),
                                        svf=("svf", "mean"), obstacle_frac=("obstacle", "mean"))
    planes.join(agg, how="inner").reset_index().to_parquet(out / "roof_planes_solar.parquet")
    a = cells.kwh_m2
    stats = {"seconds": round(secs, 1), "n_roof_cells": len(cells), "weather": wx, "tmy": tmy_meta["meteo_data"],
             "roof_kwh_m2_mean": float(a.mean()), "roof_kwh_m2_p10_p50_p90": [float(v) for v in a.quantile([.1, .5, .9])],
             "loss_all_obstructions": float(1 - a.sum() / cells.kwh_m2_free.sum()),
             "loss_trees_only": float(1 - a.sum() / cells.kwh_m2_notrees.sum())}
    (out / "solar_stats.json").write_text(json.dumps(stats, indent=2))
    return stats


STAGES = {"data": stage_data, "preprocess": stage_preprocess, "segment": stage_segment,
          "validate": stage_validate, "solar": stage_solar}


# --------------------------------------------------------------------------- city level

def city_outputs(ctx) -> dict:
    """Merge tile outputs; write city tables, irradiation raster, AOI summary and PVGIS check."""
    cfg, res = ctx.cfg, ctx.cfg["preprocess"]["raster_res"]
    out = city.CITY
    b = ctx.buildings
    planes = pd.concat([pd.read_parquet(data.PROCESSED / t / "roof_planes_solar.parquet") for t in ctx.tiles],
                       ignore_index=True)
    planes = planes.merge(b[["identificatie", "aoi", "bouwjaar"]], on="identificatie", how="left")
    # sky-visible area: cells where this plane is the top surface (excludes overhung / stacked parts)
    planes["area_top_3d_m2"] = planes.n_cells * res * res / np.cos(np.radians(planes.slope_deg))
    planes.to_parquet(out / "roof_planes_solar.parquet")

    dsm, _, cb = ctx.mosaics
    grid = np.full(dsm.shape, np.nan, np.float32)
    cells_all = []
    for t in ctx.tiles:
        c = pd.read_parquet(data.PROCESSED / t / "roof_cells_solar.parquet")
        grid[c.row.values, c.col.values] = c.kwh_m2.values
        c["identificatie"] = pd.read_parquet(data.PROCESSED / t / "roof_planes.parquet") \
            .set_index("plane_id").identificatie.reindex(c.plane_id).values
        cells_all.append(c[["kwh_m2", "kwh_m2_notrees", "kwh_m2_free", "identificatie"]])
    preprocess.write_tif(out / "roof_irradiation_kwh_m2.tif", grid,
                         preprocess.Grid((cb.left, cb.bottom, cb.right, cb.top), res))
    cells = pd.concat(cells_all).merge(b[["identificatie", "aoi"]], on="identificatie", how="left")

    rows = []
    for aoi, g in cells.groupby(cells.aoi.fillna("outside_aoi")):
        pa = planes[planes.aoi.fillna("outside_aoi") == aoi]
        rows.append({
            "aoi": aoi, "n_buildings": int(pa.identificatie.nunique()), "n_planes": len(pa),
            "plane_area_3d_km2": float(pa.area_3d_m2.sum() / 1e6),
            "sky_visible_roof_area_3d_km2": float(pa.area_top_3d_m2.sum() / 1e6),
            "share_flat_area": float(pa.loc[pa.roof_type == "flat", "area_top_3d_m2"].sum() / pa.area_top_3d_m2.sum()),
            "roof_kwh_m2_median": float(g.kwh_m2.median()),
            "loss_all_obstructions": float(1 - g.kwh_m2.sum() / g.kwh_m2_free.sum()),
            "loss_trees_only": float(1 - g.kwh_m2.sum() / g.kwh_m2_notrees.sum()),
        })
    summary = pd.DataFrame(rows)
    summary.to_csv(out / "aoi_summary.csv", index=False)

    # validation pooled over all tiles
    vh = pd.concat([pd.read_csv(data.PROCESSED / t / "val_heights.csv", dtype={"identificatie": str}) for t in ctx.tiles])
    vp = pd.concat([pd.read_parquet(data.PROCESSED / t / "val_planes.parquet") for t in ctx.tiles])
    vp = vp.merge(b[["identificatie", "aoi"]], on="identificatie", how="left")
    val = {}
    for aoi, g in vp.groupby(vp.aoi.fillna("outside_aoi")):
        pitched = g[(g.slope_deg >= 10) & (g.ref_slope >= 10)]
        da = validate.angle_diff(pitched.aspect_deg, pitched.ref_azimuth)
        val[aoi] = {"n_planes_matched": len(g), "slope_median_abs_deg": float(g.d_slope.abs().median()),
                    "slope_mae_deg": float(g.d_slope.abs().mean()),
                    "aspect_within_15deg_pitched": float((da <= 15).mean()) if len(da) else None,
                    "dz_median_m": float(g.dz.median()), "frac_dz_lt_0p5m": float((g.dz < 0.5).mean())}
    match = {t: json.loads((data.PROCESSED / t / "validation.json").read_text())["planes"] for t in ctx.tiles}
    val["all"] = {"match_rate": sum(m["n_matched"] for m in match.values()) /
                  sum(m["n_planes_ge_min_area"] for m in match.values()),
                  "slope_median_abs_deg": float(vp.d_slope.abs().median()),
                  "dz_median_m": float(vp.dz.median()), "frac_dz_lt_0p5m": float((vp.dz < 0.5).mean()),
                  "h70_median_abs_m": float(vh.d_h70.abs().median()), "n_buildings_heights": len(vh)}
    ghi = json.loads((data.PROCESSED / ctx.tiles[0] / "solar_stats.json").read_text())["weather"]["ghi_kwh"]
    pv, table = validate.validate_vs_pvgis(planes, cfg, data.RAW / "pvgis_poa_cache.json", ghi)
    table.to_csv(out / "val_pvgis.csv", index=False)
    val["irradiance_vs_pvgis"] = pv
    (out / "validation.json").write_text(json.dumps(val, indent=2))

    b = ctx.buildings
    res_ = {"n_tiles": len(ctx.tiles), "n_buildings_total": len(b), "n_incomplete_skipped": int(b.incomplete.sum()),
            "n_incomplete_in_aoi": int((b.incomplete & b.aoi.notna()).sum()),
            "n_buildings_crossing_tile_edges": sum(json.loads((data.PROCESSED / t / "segment_stats.json").read_text())
                                                   ["n_crossing_tile_edge"] for t in ctx.tiles),
            "aoi_summary": summary.round(4).to_dict("records"), "validation": val}
    (out / "city_stats.json").write_text(json.dumps(res_, indent=2, default=str))
    return res_


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=list(STAGES) + ["city"])
    ap.add_argument("--tile", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--workers", type=int, default=3, help="parallel tiles for preprocess --all")
    a = ap.parse_args()
    ctx = Context(data.load_config())
    if a.stage == "city":
        print(json.dumps(city_outputs(ctx), indent=1, default=str))
        return
    tiles = ctx.tiles if a.all else [a.tile or ctx.cfg["test_tile"]]
    if a.stage == "preprocess" and len(tiles) > 1:
        todo = [t for t in tiles if not (data.PROCESSED / t / "meta.json").exists()]
        with ProcessPoolExecutor(a.workers) as ex:
            for t, r in zip(todo, ex.map(_preprocess, todo)):
                print(t, json.dumps(r["meta"]), flush=True)
        return
    for t in tiles:
        r = STAGES[a.stage](ctx, t)
        print(t, json.dumps(r, default=str) if r is not None else "", flush=True)


if __name__ == "__main__":
    main()
