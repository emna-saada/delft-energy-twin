import numpy as np
import rasterio
import xarray as xr
from rasterio.transform import from_origin

from climarisk.hazards import climate, flood, wildfire


def test_flood_sampling_picks_return_period(tmp_path):
    path = tmp_path / "f.tif"
    data = np.stack([np.full((4, 4), v, "float32") for v in (0.1, 0.5, 1.5)])
    data[:, 0, 0] = -9999
    with rasterio.open(path, "w", driver="GTiff", height=4, width=4, count=3, dtype="float32",
                       crs="EPSG:4326", transform=from_origin(10, 36, 0.5, 0.5)) as d:
        d.write(data)
        d.update_tags(return_periods="10.0,100.0,1000.0")
    v = flood.sample_depth(path, [10.75, 10.1], [35.25, 35.9], rp=100)
    assert v[0] == 0.5
    assert v[1] == 0.0  # negative nodata -> 0


def test_climate_sample_fills_coastal_nan():
    lat = np.array([35.0, 35.25])
    lon = np.array([10.0, 10.25])
    a = np.array([[[[1.0, np.nan], [3.0, 4.0]]]])
    ds = xr.Dataset({"hot35": (("model", "period", "lat", "lon"), a)},
                    coords={"model": ["m"], "period": ["baseline"], "lat": lat, "lon": lon})
    pts = climate.sample_points(ds, np.array([10.25]), np.array([35.0]))
    assert np.isfinite(pts.hot35.values).all()


def test_fuel_grid_in_unit_interval(tmp_path):
    path = tmp_path / "wc.tif"
    wc = np.full((30, 30), 60, "uint8")
    wc[10:20, 10:20] = 10  # forest patch
    with rasterio.open(path, "w", driver="GTiff", height=30, width=30, count=1, dtype="uint8",
                       crs="EPSG:4326", transform=from_origin(9, 36, 0.003, 0.003)) as d:
        d.write(wc, 1)
    g, _ = wildfire.fuel_grid(path, window_km=0.5)
    assert g.min() >= 0 and g.max() <= 1
    assert g[15, 15] > g[0, 0]
