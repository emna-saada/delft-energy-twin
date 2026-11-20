from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
from rasterio.transform import from_origin
from shapely.geometry import box

from climarisk.config import load_yaml, project_root
from climarisk.portfolio import Grids, generate_portfolio


@pytest.fixture
def tiny_world():
    """Two square 'governorates' on a 20x20 grid (0.05 deg pixels)."""
    govs = gpd.GeoDataFrame({"governorate": ["Alpha", "Beta"]},
                            geometry=[box(10.0, 35.5, 10.5, 36.0), box(10.5, 35.5, 11.0, 36.0)],
                            crs="EPSG:4326")
    tr = from_origin(10.0, 36.0, 0.05, 0.05)
    gov = np.zeros((10, 20), dtype="int16")
    gov[:, 10:] = 1
    pop = np.ones((10, 20))
    coast = np.zeros((10, 20), bool)
    coast[:, -2:] = True
    crop = np.ones((10, 20), bool)
    grids = Grids(pop, tr, gov, coast, crop, tr, gov)
    cfg = load_yaml("portfolio.yaml")
    cfg["n_loans"] = 300
    for s in cfg["sectors"].values():
        s.pop("govs", None)
    return govs, grids, cfg


def test_tiny_portfolio_inside_polygons(tiny_world):
    govs, grids, cfg = tiny_world
    pf = generate_portfolio(cfg, grids, govs)
    assert len(pf) == 300
    assert pf.within(govs.union_all()).all()
    assert set(pf.governorate) == {"Alpha", "Beta"}
    assert pf["loan_id"].is_unique
    assert pf["pd_base"].between(0, 1).all() and pf["lgd_base"].between(0, 1).all()
    shares = pf.groupby("sector")["ead_tnd"].sum() / pf["ead_tnd"].sum()
    target = {k: v["ead_share"] for k, v in cfg["sectors"].items()}
    for k, v in shares.items():
        assert abs(v - target[k] / sum(target.values())) < 0.01


def test_seed_is_reproducible(tiny_world):
    govs, grids, cfg = tiny_world
    a = generate_portfolio(cfg, grids, govs)
    b = generate_portfolio(cfg, grids, govs)
    assert a[["lon", "lat", "ead_tnd"]].equals(b[["lon", "lat", "ead_tnd"]])


REAL = project_root() / "outputs/portfolio.parquet"


@pytest.mark.skipif(not REAL.exists(), reason="run `make portfolio` first")
def test_real_portfolio_acceptance():
    """M2 acceptance: 2 000 loans, 24 governorates covered, no coordinate at sea."""
    pf = gpd.read_parquet(REAL)
    govs = gpd.read_file(Path(project_root()) / "data/raw/tun_adm1.geojson")
    assert len(pf) == 2000
    assert pf["governorate"].nunique() == 24
    assert pf.within(govs.union_all()).all()
