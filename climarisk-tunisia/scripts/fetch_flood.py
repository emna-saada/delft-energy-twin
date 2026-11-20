"""Extract WRI Aqueduct Floods v2 (riverine + coastal) depth grids over Tunisia
from the OS-Climate physrisk public Zarr store on AWS Open Data
(s3://os-climate-physical-risk, unsigned HTTPS, no account).

Output: data/raw/flood/<array>.tif   (band order = return periods in .zattrs)
"""
from __future__ import annotations

import json
from pathlib import Path

import fsspec
import numpy as np
import rasterio
import zarr
from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]
STORE = "https://os-climate-physical-risk.s3.amazonaws.com/hazard-indicators/hazard.zarr"
LON0, LON1, LAT0, LAT1 = 7.3, 11.8, 30.1, 37.7

GCMS = ["00000NorESM1-M", "0000GFDL-ESM2M", "0000HadGEM2-ES", "00IPSL-CM5A-LR", "MIROC-ESM-CHEM"]
ARRAYS = ["inundation/wri/v2/inunriver_historical_000000000WATCH_1980",
          "inundation/wri/v2/inuncoast_historical_nosub_hist_0"]
for rcp in ("rcp4p5", "rcp8p5"):
    for yr in ("2030", "2050"):
        ARRAYS += [f"inundation/wri/v2/inunriver_{rcp}_{g}_{yr}" for g in GCMS]
        ARRAYS.append(f"inundation/wri/v2/inuncoast_{rcp}_nosub_{yr}_0_perc_50")


def extract(path: str) -> None:
    out = ROOT / "data/raw/flood" / (path.split("/")[-1] + ".tif")
    if out.exists():
        print("skip", out.name)
        return
    mapper = fsspec.get_mapper(f"{STORE}/{path}")
    arr = zarr.open_array(mapper, mode="r")
    attrs = json.loads(fsspec.open(f"{STORE}/{path}/.zattrs").open().read())
    a, b, c, d, e, f = attrs["transform_mat3x3"][:6]
    col0, col1 = int((LON0 - c) / a), int(np.ceil((LON1 - c) / a))
    row0, row1 = int((LAT1 - f) / e), int(np.ceil((LAT0 - f) / e))
    data = arr[:, row0:row1, col0:col1].astype("float32")
    transform = Affine(a, b, c + col0 * a, d, e, f + row0 * e)
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out, "w", driver="GTiff", height=data.shape[1], width=data.shape[2],
                       count=data.shape[0], dtype="float32", crs="EPSG:4326",
                       transform=transform, compress="deflate") as dst:
        dst.write(data)
        dst.update_tags(return_periods=",".join(str(v) for v in attrs["index_values"]),
                        source="WRI Aqueduct Floods v2 via OS-Climate physrisk Zarr (CC BY 4.0)")
    print("done", out.name, data.shape, float(np.nanmax(data)))


if __name__ == "__main__":
    for p in ARRAYS:
        extract(p)
