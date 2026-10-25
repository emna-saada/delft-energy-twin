"""Point cloud preparation: class filtering, outlier removal, DSM / DTM / vegetation rasters.

AHN classes: 1 unclassified (mostly vegetation + street furniture), 2 ground,
6 building, 9 water, 26 civil structures (bridges).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import laspy
import numpy as np
import rasterio
from rasterio.fill import fillnodata
from rasterio.transform import from_origin
from scipy.spatial import cKDTree

NODATA = -9999.0
GPS_EPOCH = datetime(1980, 1, 6, tzinfo=timezone.utc)
GPS_LEAP_S = 18  # GPS-UTC offset since 2017


def read_points(path: Path, keep_classes) -> dict[str, np.ndarray]:
    las = laspy.read(path)
    cls = np.asarray(las.classification)
    m = np.isin(cls, list(keep_classes) + [26])
    pts = {
        "x": np.asarray(las.x)[m], "y": np.asarray(las.y)[m], "z": np.asarray(las.z)[m],
        "cls": cls[m],
        "rn": np.asarray(las.return_number)[m], "nr": np.asarray(las.number_of_returns)[m],
    }
    pts["gps"] = np.asarray(las.gps_time)[m]
    return pts


def flight_dates(gps_time: np.ndarray) -> tuple[str, str]:
    """AHN stores adjusted standard GPS time (GPS seconds - 1e9)."""
    lo, hi = np.percentile(gps_time, [0.1, 99.9])
    f = lambda s: (GPS_EPOCH + timedelta(seconds=float(s) + 1e9 - GPS_LEAP_S)).date().isoformat()
    return f(lo), f(hi)


def statistical_outliers(xyz: np.ndarray, k: int, n_std: float) -> np.ndarray:
    """True for inliers: mean distance to k neighbours within mean + n_std * std."""
    tree = cKDTree(xyz)
    d, _ = tree.query(xyz, k=k + 1, workers=-1)
    md = d[:, 1:].mean(axis=1)
    return md <= md.mean() + n_std * md.std()


class Grid:
    def __init__(self, bounds, res):
        self.x0, self.y0, self.x1, self.y1 = bounds
        self.res = res
        self.nx = int(round((self.x1 - self.x0) / res))
        self.ny = int(round((self.y1 - self.y0) / res))
        self.transform = from_origin(self.x0, self.y1, res, res)

    def index(self, x, y):
        col = np.floor((x - self.x0) / self.res).astype(np.int64)
        row = np.floor((self.y1 - y) / self.res).astype(np.int64)
        ok = (col >= 0) & (col < self.nx) & (row >= 0) & (row < self.ny)
        return row, col, ok

    def reduce(self, x, y, v, how: str) -> np.ndarray:
        row, col, ok = self.index(x, y)
        flat = row[ok] * self.nx + col[ok]
        out = np.full(self.nx * self.ny, np.nan)
        if how == "max":
            np.fmax.at(out, flat, v[ok])
        elif how == "min":
            np.fmin.at(out, flat, v[ok])
        elif how == "mean":
            s = np.bincount(flat, v[ok], self.nx * self.ny)
            c = np.bincount(flat, minlength=self.nx * self.ny)
            with np.errstate(invalid="ignore"):
                out = np.where(c > 0, s / c, np.nan)
        return out.reshape(self.ny, self.nx)

    def sample(self, arr, x, y):
        row, col, ok = self.index(x, y)
        out = np.full(x.shape, np.nan)
        out[ok] = arr[row[ok], col[ok]]
        return out


def fill(arr: np.ndarray, max_dist_px: int) -> np.ndarray:
    mask = np.isfinite(arr)
    if mask.all():
        return arr
    src = np.where(mask, arr, 0).astype(np.float32)
    return fillnodata(src, mask=mask.astype(np.uint8), max_search_distance=max_dist_px,
                      smoothing_iterations=0).astype(np.float64)


def write_tif(path: Path, arr: np.ndarray, grid: Grid, crs="EPSG:28992"):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.where(np.isfinite(arr), arr, NODATA).astype(np.float32)
    with rasterio.open(path, "w", driver="GTiff", height=grid.ny, width=grid.nx, count=1,
                       dtype="float32", crs=crs, transform=grid.transform, nodata=NODATA,
                       compress="deflate", predictor=3, tiled=True) as dst:
        dst.write(data, 1)


def prepare_tile(laz: Path, out_dir: Path, bounds, cfg: dict) -> dict:
    """Rasterise one tile. Returns metadata (counts, flight dates) written to meta.json."""
    pc = cfg["preprocess"]
    res = pc["raster_res"]
    p = read_points(laz, pc["keep_classes"])
    meta = {"n_points_kept": int(p["x"].size)}
    meta["flight_first"], meta["flight_last"] = flight_dates(p["gps"])

    # outlier removal on above-ground classes only (ground/water are flat and dense)
    ag = np.isin(p["cls"], [1, 6, 26])
    xyz = np.column_stack([p["x"][ag], p["y"][ag], p["z"][ag]])
    inl = np.ones(p["x"].size, bool)
    inl[np.flatnonzero(ag)] = statistical_outliers(xyz, pc["outlier_k"], pc["outlier_std"])
    meta["n_outliers"] = int((~inl).sum())
    for k in p:
        p[k] = p[k][inl]

    g = Grid(bounds, res)
    gr = np.isin(p["cls"], [2, 9])
    dtm = fill(g.reduce(p["x"][gr], p["y"][gr], p["z"][gr], "mean"), max_dist_px=200)
    dsm = fill(g.reduce(p["x"], p["y"], p["z"], "max"), max_dist_px=4)
    dsm = np.where(np.isfinite(dsm), dsm, dtm)

    # vegetation: class 1 points well above terrain (drops cars, street furniture)
    hag = p["z"] - g.sample(dtm, p["x"], p["y"])
    veg = (p["cls"] == 1) & (hag > pc["veg_min_height"])
    veg_top = g.reduce(p["x"][veg], p["y"][veg], p["z"][veg], "max")
    bld = p["cls"] == 6
    bld_top = g.reduce(p["x"][bld], p["y"][bld], p["z"][bld], "max")

    write_tif(out_dir / "dtm.tif", dtm, g)
    write_tif(out_dir / "dsm.tif", dsm, g)
    write_tif(out_dir / "ndsm.tif", dsm - dtm, g)
    write_tif(out_dir / "veg_height.tif", veg_top - dtm, g)
    write_tif(out_dir / "bld_dsm.tif", bld_top, g)

    np.savez_compressed(out_dir / "building_points.npz",
                        x=p["x"][bld], y=p["y"][bld], z=p["z"][bld])
    meta.update({
        "res_m": res, "shape": [g.ny, g.nx],
        "n_building_pts": int(bld.sum()), "n_veg_pts": int(veg.sum()),
        "veg_cover_frac": float(np.isfinite(veg_top).mean()),
        "density_building_pts_m2": float(bld.sum() / max(np.isfinite(bld_top).sum() * res**2, 1)),
    })
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def compare_rasters(a: Path, b: Path) -> dict:
    """Bias / RMSE / MAE between two co-registered rasters (e.g. our DSM vs official AHN DSM)."""
    with rasterio.open(a) as ra, rasterio.open(b) as rb:
        if ra.shape != rb.shape or ra.transform != rb.transform:
            raise ValueError("rasters not aligned")
        x, y = ra.read(1, masked=True), rb.read(1, masked=True)
    d = (x - y).compressed()
    d = d[np.isfinite(d)]
    return {"n": int(d.size), "bias": float(d.mean()), "rmse": float(np.sqrt((d**2).mean())),
            "mae": float(np.abs(d).mean()), "p95_abs": float(np.percentile(np.abs(d), 95))}
