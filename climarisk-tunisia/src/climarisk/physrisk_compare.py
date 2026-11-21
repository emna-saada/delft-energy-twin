"""Milestone 6: compare our asset-level indicators with OS-Climate physrisk hazard indicators.

We read physrisk's published hazard indicator arrays (Apache-2.0 library; data on AWS Open
Data, s3://os-climate-physical-risk) at the same 2 000 asset locations:
  - chronic heat: days_tas_above_35c_<model>_<scenario>_<year>  (physrisk OSC v2)
  - drought:      months_spei12m_below_threshold_multi_model_0_<scenario>_<year>  (SPEI-12 < -1.5)
and compare them with our own heat (Tmax > 35 °C days) and drought scores.
"""
from __future__ import annotations

import json

import fsspec
import numpy as np
import pandas as pd
import zarr
from scipy.stats import spearmanr

from .config import project_root

STORE = "https://os-climate-physical-risk.s3.amazonaws.com/hazard-indicators/hazard.zarr"


def _sample(path: str, lon, lat, band: int = 0) -> np.ndarray:
    arr = zarr.open_array(fsspec.get_mapper(f"{STORE}/{path}"), mode="r")
    attrs = json.loads(fsspec.open(f"{STORE}/{path}/.zattrs").open().read())
    a, _, c, _, e, f = attrs["transform_mat3x3"][:6]
    cols = ((np.asarray(lon) - c) / a).astype(int)
    rows = ((np.asarray(lat) - f) / e).astype(int)
    r0, r1, c0, c1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
    block = arr[band, r0:r1, c0:c1]
    return block[rows - r0, cols - c0].astype("float64")


def compare() -> dict:
    root = project_root()
    assets = pd.read_parquet(root / "outputs/asset_results.parquet")
    base = assets[assets.period == "baseline"].sort_values("loan_id")
    fut = assets[assets.period == "ssp585_2050"].sort_values("loan_id")
    lon, lat = base.lon.to_numpy(), base.lat.to_numpy()

    heat_b = _sample("chronic_heat/osc/v2/days_tas_above_35c_ACCESS-CM2_historical_2005", lon, lat)
    heat_f = _sample("chronic_heat/osc/v2/days_tas_above_35c_ACCESS-CM2_ssp585_2050", lon, lat)
    dr = "drought/osc/v2/months_spei12m_below_threshold_multi_model_0_{}/indicator"
    drought_b = _sample(dr.format("historical_2005"), lon, lat, band=2)  # SPEI-12 < -1.5
    drought_f = _sample(dr.format("ssp585_2050"), lon, lat, band=2)

    df = pd.DataFrame({
        "loan_id": base.loan_id.to_numpy(), "sector": base.sector.to_numpy(),
        "ours_hot35_base": base.hot35.to_numpy(), "ours_hot35_2050": fut.hot35.to_numpy(),
        "physrisk_tas35_base": heat_b, "physrisk_tas35_2050": heat_f,
        "ours_drought_base": base.drought.to_numpy(), "ours_drought_2050": fut.drought.to_numpy(),
        "physrisk_spei_months_base": drought_b, "physrisk_spei_months_2050": drought_f,
    })
    df.to_csv(root / "outputs/physrisk_comparison.csv", index=False)

    def rho(a, b):
        m = np.isfinite(a) & np.isfinite(b)
        return float(spearmanr(a[m], b[m]).statistic) if m.sum() > 10 else float("nan")

    summary = {
        "n_assets": len(df),
        "heat_spearman_base": rho(df.ours_hot35_base.values, df.physrisk_tas35_base.values),
        "heat_spearman_2050": rho(df.ours_hot35_2050.values, df.physrisk_tas35_2050.values),
        "heat_mean_ours_base": float(df.ours_hot35_base.mean()),
        "heat_mean_physrisk_base": float(np.nanmean(heat_b)),
        "heat_mean_ours_2050": float(df.ours_hot35_2050.mean()),
        "heat_mean_physrisk_2050": float(np.nanmean(heat_f)),
        "drought_spearman_change": rho((df.ours_drought_2050 - df.ours_drought_base).values,
                                       (df.physrisk_spei_months_2050 - df.physrisk_spei_months_base).values),
        "drought_spearman_2050": rho(df.ours_drought_2050.values, df.physrisk_spei_months_2050.values),
        "drought_months_physrisk_base": float(np.nanmean(drought_b)),
        "drought_months_physrisk_2050": float(np.nanmean(drought_f)),
        "share_assets_drought_worsening_ours": float((df.ours_drought_2050 > df.ours_drought_base).mean()),
        "share_assets_drought_worsening_physrisk": float((drought_f > drought_b).mean()),
    }
    (root / "outputs/physrisk_comparison.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2))
