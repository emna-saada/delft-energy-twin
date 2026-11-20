"""CMIP6 (NEX-GDDP) annual indicators -> period means per model.

Periods: ``baseline`` (historical 2010-2014) and ``<ssp>_<horizon>`` (3-year windows
centred on 2030 and 2050). Each future value is also expressed relative to the
same model's baseline, which removes most of the model's own bias.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr

from ..config import load_yaml, project_root

VARS = ("hot35", "hot40", "cdd", "prtot")


def periods() -> list[str]:
    sc = load_yaml("scenarios.yaml")
    return ["baseline"] + [f"{s}_{h}" for s in ("ssp245", "ssp585") for h in sc["horizons"]]


def load_period_means(raw_dir: Path | None = None) -> xr.Dataset:
    """Return Dataset(model, period, lat, lon) of period-mean indicators."""
    raw_dir = raw_dir or project_root() / "data/raw/cmip6"
    sc = load_yaml("scenarios.yaml")
    models = [m["name"] for m in sc["cmip6_models"]]
    out = []
    for model in models:
        per = []
        files = {"baseline": [raw_dir / f"{model}_historical_{y}.nc" for y in sc["years"]["historical"]]}
        for s in ("ssp245", "ssp585"):
            for h, yrs in sc["horizons"].items():
                files[f"{s}_{h}"] = [raw_dir / f"{model}_{s}_{y}.nc" for y in yrs]
        for p, fl in files.items():
            fl = [f for f in fl if f.exists()]
            if not fl:
                raise FileNotFoundError(f"no CMIP6 files for {model} {p}")
            ds = xr.concat([xr.open_dataset(f)[list(VARS)] for f in fl], dim="year").mean("year")
            per.append(ds.expand_dims(period=[p]))
        out.append(xr.concat(per, dim="period").expand_dims(model=[model]))
    ds = xr.concat(out, dim="model")
    ds["prchange"] = 100 * (ds.prtot / ds.prtot.sel(period="baseline") - 1)
    return ds.load()


def _fill_nearest(da: xr.DataArray) -> xr.DataArray:
    """Replace NaN cells by the nearest valid cell in (lat, lon) (coastal cells)."""
    from scipy.ndimage import distance_transform_edt

    da = da.transpose(..., "lat", "lon")
    vals = da.values.copy()
    flat = vals.reshape(-1, *vals.shape[-2:])
    for k in range(flat.shape[0]):
        nan = ~np.isfinite(flat[k])
        if nan.any() and not nan.all():
            _, (ir, ic) = distance_transform_edt(nan, return_indices=True)
            flat[k] = flat[k][ir, ic]
    return da.copy(data=flat.reshape(vals.shape))


def sample_points(ds: xr.Dataset, lon: np.ndarray, lat: np.ndarray) -> xr.Dataset:
    """Nearest valid grid cell for every point."""
    filled = xr.Dataset({v: _fill_nearest(ds[v]) for v in ds.data_vars})
    return filled.sel(lon=xr.DataArray(lon, dims="asset"), lat=xr.DataArray(lat, dims="asset"),
                      method="nearest")
