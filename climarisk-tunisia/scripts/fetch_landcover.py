"""Read ESA WorldCover 2021 v200 (10 m) over Tunisia at ~320 m using the COG
internal overviews (HTTP range requests on AWS Open Data, no account).

Output: data/raw/worldcover_tun_320m.tif  (class codes 10..100)
"""
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
URL = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{t}_Map.tif"
F = 32  # decimation factor: 10 m * 32 ~ 320 m (3 deg tile -> 1125 px)
N = 36000 // F


def main() -> None:
    lats, lons = (30, 33, 36), (6, 9)
    mosaic = np.zeros((len(lats) * N, len(lons) * N), dtype="uint8")
    for i, lat in enumerate(sorted(lats, reverse=True)):
        for j, lon in enumerate(lons):
            tile = f"N{lat:02d}E{lon:03d}"
            with rasterio.open(URL.format(t=tile)) as s:
                mosaic[i * N:(i + 1) * N, j * N:(j + 1) * N] = s.read(
                    1, out_shape=(N, N), resampling=Resampling.nearest)
            print("read", tile)
    res = 3.0 / N
    out = ROOT / "data/raw/worldcover_tun_320m.tif"
    with rasterio.open(out, "w", driver="GTiff", height=mosaic.shape[0], width=mosaic.shape[1],
                       count=1, dtype="uint8", crs="EPSG:4326",
                       transform=from_origin(6.0, 39.0, res, res), compress="deflate") as dst:
        dst.write(mosaic, 1)
        dst.update_tags(source="ESA WorldCover 10m 2021 v200 (CC BY 4.0), overview level 1/32")
    print("wrote", out)


if __name__ == "__main__":
    main()
