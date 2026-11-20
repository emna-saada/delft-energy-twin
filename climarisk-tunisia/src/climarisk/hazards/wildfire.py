"""Wildfire fuel proxy from ESA WorldCover: share of burnable vegetation around an asset."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import uniform_filter

from ..config import project_root

# burnable weight per WorldCover class (10 tree, 20 shrub, 30 grassland, 40 cropland, 90 wetland)
BURNABLE = {10: 1.0, 20: 0.8, 30: 0.5, 40: 0.15, 90: 0.2}


def fuel_grid(path: Path | None = None, window_km: float = 2.0):
    path = path or project_root() / "data/raw/worldcover_tun_320m.tif"
    with rasterio.open(path) as s:
        wc = s.read(1)
        tr = s.transform
    w = np.zeros(wc.shape, dtype="float32")
    for cls, val in BURNABLE.items():
        w[wc == cls] = val
    px_km = abs(tr.a) * 111.0 * np.cos(np.deg2rad(34.0))
    size = max(1, round(2 * window_km / px_km) | 1)
    return uniform_filter(w, size=size, mode="nearest"), tr


def sample_fuel(lon, lat, window_km: float = 2.0, path: Path | None = None) -> np.ndarray:
    grid, tr = fuel_grid(path, window_km)
    cols = ((np.asarray(lon) - tr.c) / tr.a).astype(int)
    rows = ((np.asarray(lat) - tr.f) / tr.e).astype(int)
    rows = np.clip(rows, 0, grid.shape[0] - 1)
    cols = np.clip(cols, 0, grid.shape[1] - 1)
    return grid[rows, cols].astype("float64")
