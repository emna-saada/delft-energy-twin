"""WRI Aqueduct Floods v2 depth at a given return period (riverine + coastal)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

from ..config import project_root

GCMS = ["00000NorESM1-M", "0000GFDL-ESM2M", "0000HadGEM2-ES", "00IPSL-CM5A-LR", "MIROC-ESM-CHEM"]
RCP = {"ssp245": "rcp4p5", "ssp585": "rcp8p5"}  # CMIP5 RCP used as proxy for the CMIP6 SSP


def _band(src, rp: int) -> int:
    rps = [float(v) for v in src.tags()["return_periods"].split(",")]
    return rps.index(float(rp)) + 1


def sample_depth(path: Path, lon, lat, rp: int = 100) -> np.ndarray:
    with rasterio.open(path) as s:
        b = _band(s, rp)
        vals = np.array([v[0] for v in s.sample(zip(lon, lat), indexes=b)], dtype="float64")
    vals[~np.isfinite(vals) | (vals < 0)] = 0.0
    return vals


def flood_depths(lon, lat, rp: int = 100, flood_dir: Path | None = None) -> dict[str, np.ndarray]:
    """Return {period: array(n_gcm, n_assets)} of max(riverine, coastal) depth in metres."""
    d = flood_dir or project_root() / "data/raw/flood"
    coast_base = sample_depth(d / "inuncoast_historical_nosub_hist_0.tif", lon, lat, rp)
    river_base = sample_depth(d / "inunriver_historical_000000000WATCH_1980.tif", lon, lat, rp)
    out = {"baseline": np.tile(np.maximum(coast_base, river_base), (len(GCMS), 1))}
    for ssp, rcp in RCP.items():
        for h in ("2030", "2050"):
            coast = sample_depth(d / f"inuncoast_{rcp}_nosub_{h}_0_perc_50.tif", lon, lat, rp)
            river = np.stack([sample_depth(d / f"inunriver_{rcp}_{g}_{h}.tif", lon, lat, rp) for g in GCMS])
            out[f"{ssp}_{h}"] = np.maximum(river, coast[None, :])
    return out
