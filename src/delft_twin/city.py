"""Multi-tile processing: building ownership, cross-tile point gathering, city-wide surfaces.

Tile-edge handling:
  * every BAG building is owned by exactly one tile (the tile holding its representative
    point), so nothing is reconstructed twice;
  * a tile's segmentation reads building points from all processed tiles that overlap the
    owned footprints, so buildings crossing a tile border get their complete point set;
  * shading uses one DSM mosaic over all tiles + buffer, so shadows cross tile borders too.
Buildings that reach outside the processed tiles are flagged `incomplete` and skipped.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from shapely.geometry import box

from . import data, preprocess

CITY = data.PROCESSED / "city"


def tile_ids(cfg) -> list[str]:
    aois = gpd.read_file(data.CONFIGS / "aois.geojson")
    return data.tiles_for_aois(cfg, aois, cfg["ahn"]["main_epoch"]).AHN.tolist()


def tile_box(tile: str):
    x, y = map(int, tile.split("_"))
    return box(x, y, x + 1000, y + 1000)


def extent(tiles) -> tuple[float, float, float, float]:
    return tuple(gpd.GeoSeries([tile_box(t) for t in tiles]).total_bounds.tolist())


def assign_buildings(cfg, tiles) -> gpd.GeoDataFrame:
    """One row per BAG building in the processed area, with owning tile and AOI membership."""
    path = CITY / "buildings.gpkg"
    if path.exists():
        return gpd.read_file(path)
    CITY.mkdir(parents=True, exist_ok=True)
    x0, y0, x1, y1 = extent(tiles)
    b = data.bag_footprints((x0 - 100, y0 - 100, x1 + 100, y1 + 100), "delft_all")
    covered = gpd.GeoSeries([tile_box(t) for t in tiles]).union_all()
    rp = b.representative_point()
    b["tile"] = None
    for t in tiles:
        b.loc[rp.within(tile_box(t)), "tile"] = t
    b = b[b.tile.notna()].copy()
    b["incomplete"] = ~b.within(covered)
    aois = gpd.read_file(data.CONFIGS / "aois.geojson")
    b["aoi"] = None
    for _, a in aois.iterrows():
        b.loc[b.intersects(a.geometry) & b.aoi.isna(), "aoi"] = a.aoi
    b = b.reset_index(drop=True)
    b.to_file(path, driver="GPKG")
    return b


def gather_points(bounds, tiles) -> dict[str, np.ndarray]:
    """Building points from every processed tile overlapping `bounds`, cropped to it."""
    x0, y0, x1, y1 = bounds
    parts = {"x": [], "y": [], "z": []}
    for t in tiles:
        if not tile_box(t).intersects(box(*bounds)):
            continue
        p = np.load(data.PROCESSED / t / "building_points.npz")
        m = (p["x"] >= x0) & (p["x"] <= x1) & (p["y"] >= y0) & (p["y"] <= y1)
        for k in parts:
            parts[k].append(p[k][m])
    return {k: np.concatenate(v) for k, v in parts.items()}


def paste_into(dst: np.ndarray, path: Path, big, res: float, arr: np.ndarray | None = None) -> None:
    """Write a raster (or `arr`, aligned to that raster) into `dst`, a grid with bounds `big`.

    All AHN rasters share the RD 0.5 m grid, so sources are placed by their own extent; NaN / out-of-range
    values leave `dst` untouched.
    """
    with rasterio.open(path) as s:
        sb = s.bounds
        r0 = int(round((big[3] - sb.top) / res)); c0 = int(round((sb.left - big[0]) / res))
        v = s.read(1, masked=True).astype(np.float32).filled(np.nan) if arr is None else arr
    h, wd = v.shape
    rs, cs = max(r0, 0), max(c0, 0)
    re, ce = min(r0 + h, dst.shape[0]), min(c0 + wd, dst.shape[1])
    if rs >= re or cs >= ce:
        return
    sub = v[rs - r0:re - r0, cs - c0:ce - c0]
    sub = np.where((sub < -50) | (sub > 500), np.nan, sub)
    dst[rs:re, cs:ce] = np.where(np.isfinite(sub), sub, dst[rs:re, cs:ce])


def build_mosaics(cfg, tiles) -> dict[str, Path]:
    """City DSM and tree-free DSM (float32) over all tiles + shadow buffer.

    Our tile rasters win; the outer ring is filled from official AHN6 DSMs (trees opaque there).
    """
    out = {"dsm": CITY / "city_dsm.tif", "dsm_noveg": CITY / "city_dsm_noveg.tif"}
    if all(p.exists() for p in out.values()):
        return out
    res = cfg["preprocess"]["raster_res"]
    buf = cfg["shadow_buffer_m"]
    x0, y0, x1, y1 = extent(tiles)
    big = (x0 - buf, y0 - buf, x1 + buf, y1 + buf)
    grid = preprocess.Grid(big, res)
    ring = data.ahn_index("AHN6", cfg, big)
    ring = ring[ring.intersects(box(*big)) & ~ring.AHN.isin(tiles)]
    ring_dsm = [data.fetch_ahn_tile(r, "AHN6", ("Oppervlaktemodel (DSM) ½m",))["Oppervlaktemodel (DSM) ½m"]
                for _, r in ring.iterrows()]
    paste = lambda dst, path, arr=None: paste_into(dst, path, big, res, arr)  # noqa: E731

    dsm = np.full((grid.ny, grid.nx), np.nan, np.float32)
    for p in ring_dsm:
        paste(dsm, p)
    nov = dsm.copy()
    for t in tiles:
        d = data.PROCESSED / t
        paste(dsm, d / "dsm.tif")
        with rasterio.open(d / "veg_height.tif") as v, rasterio.open(d / "bld_dsm.tif") as b, \
                rasterio.open(d / "dtm.tif") as m, rasterio.open(d / "dsm.tif") as s:
            veg, bld, dtm, ds = (r.read(1, masked=True).filled(np.nan) for r in (v, b, m, s))
        paste(nov, d / "dsm.tif", np.where(np.isfinite(veg) & ~np.isfinite(bld), dtm, ds).astype(np.float32))
    preprocess.write_tif(out["dsm"], dsm, grid)
    preprocess.write_tif(out["dsm_noveg"], nov, grid)
    return out


def load_mosaics(cfg, tiles):
    m = build_mosaics(cfg, tiles)
    with rasterio.open(m["dsm"]) as a, rasterio.open(m["dsm_noveg"]) as b:
        dsm = a.read(1, masked=True).filled(np.nan).astype(np.float32)
        nov = b.read(1, masked=True).filled(np.nan).astype(np.float32)
        return dsm, nov, a.bounds


def ref_roofs_all(tiles) -> gpd.GeoDataFrame:
    """All reference LoD2.2 roof surfaces in the area, parsed once into GeoParquet."""
    from . import validate
    path = CITY / "ref_roofs_2025.parquet"
    if path.exists():
        return gpd.read_parquet(path)
    ext = extent(tiles)
    parts = [validate.load_ref_roofs(f, ext) for f in sorted((data.RAW / "ref3d" / "gebouwen_2025").glob("*.city.json"))]
    r = pd.concat([p for p in parts if len(p)], ignore_index=True)
    r = gpd.GeoDataFrame(r, crs="EPSG:28992")
    r.to_parquet(path)
    return r


def ref_heights_all(tiles) -> pd.DataFrame:
    from . import validate
    ext = extent(tiles)
    files = sorted((data.RAW / "ref3d" / "hoogtestat_2025").glob("*.gpkg"))
    return pd.concat([validate.load_ref_heights(f, ext) for f in files]).drop_duplicates("identificatie")
