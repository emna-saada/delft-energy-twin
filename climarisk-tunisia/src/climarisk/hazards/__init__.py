"""Asset-level hazard scores for every period and climate model."""
from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

from ..config import load_yaml
from . import climate, flood, scoring, wildfire

HAZARDS = ("heat", "drought", "flood", "fire")


def asset_hazards(portfolio: pd.DataFrame, clim: xr.Dataset | None = None,
                  flood_by_period: dict | None = None, fuel: np.ndarray | None = None,
                  assumptions: dict | None = None) -> pd.DataFrame:
    """Long table: one row per (loan_id, period, model) with raw indicators and 0-1 scores.

    Model ``i`` of CMIP6 (heat, drought, fire weather) is paired with Aqueduct GCM ``i``
    (flood) to build per-model realisations used for the uncertainty band.
    """
    a = assumptions or load_yaml("assumptions.yaml")
    lon, lat = portfolio["lon"].to_numpy(), portfolio["lat"].to_numpy()
    clim = clim if clim is not None else climate.load_period_means()
    pts = climate.sample_points(clim, lon, lat)
    if flood_by_period is None:
        flood_by_period = flood.flood_depths(lon, lat, a["flood_return_period"])
    if fuel is None:
        fuel = wildfire.sample_fuel(lon, lat, a["hazard_normalisation"]["fire_fuel_window_km"])

    rows = []
    models = list(pts.model.values)
    for p in pts.period.values:
        for mi, m in enumerate(models):
            sel = pts.sel(period=p, model=m)
            hot35 = sel.hot35.values
            cdd = sel.cdd.values
            prc = sel.prchange.values
            depth = flood_by_period[str(p)][mi % flood_by_period[str(p)].shape[0]]
            h = scoring.heat_score(hot35, a)
            d = scoring.drought_score(cdd, prc, a)
            rows.append(pd.DataFrame({
                "loan_id": portfolio["loan_id"].to_numpy(),
                "period": str(p), "model": str(m),
                "hot35": hot35, "hot40": sel.hot40.values, "cdd": cdd, "prchange": prc,
                "flood_depth_m": depth, "fuel": fuel,
                "heat": h, "drought": d,
                "flood": scoring.flood_score(depth, a),
                "fire": scoring.fire_score(fuel, h, d, a),
            }))
    return pd.concat(rows, ignore_index=True)
