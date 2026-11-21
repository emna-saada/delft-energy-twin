"""Synthetic loan portfolio geolocated over Tunisia.

The portfolio is 100 % synthetic (Tunisian organic law n° 2004-63 on personal data):
loan identifiers are random, locations are sampled from open population (WorldPop)
and land-cover (ESA WorldCover) grids, financial attributes from documented
distributions in ``config/portfolio.yaml``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize

from .config import load_yaml, project_root

UTM = "EPSG:32632"


@dataclass
class Grids:
    """Rasters used to sample locations, all aligned on their own grid."""

    pop: np.ndarray
    pop_transform: rasterio.Affine
    pop_gov: np.ndarray  # governorate index per pop pixel (-1 outside)
    pop_coast: np.ndarray  # bool: within coast buffer
    crop: np.ndarray  # bool cropland on WorldCover grid
    crop_transform: rasterio.Affine
    crop_gov: np.ndarray


def load_governorates(path: Path | None = None) -> gpd.GeoDataFrame:
    path = path or project_root() / "data/raw/tun_adm1.geojson"
    gdf = gpd.read_file(path)[["shapeName", "geometry"]].rename(columns={"shapeName": "governorate"})
    return gdf.sort_values("governorate").reset_index(drop=True)


def load_coastline(govs: gpd.GeoDataFrame, path: Path | None = None) -> gpd.GeoSeries:
    path = path or project_root() / "data/raw/ne_coast.zip"
    coast = gpd.read_file(f"zip://{path}")
    minx, miny, maxx, maxy = govs.total_bounds
    return coast.clip((minx - 0.5, miny - 0.5, maxx + 0.5, maxy + 0.5)).geometry


def _gov_raster(govs: gpd.GeoDataFrame, shape, transform) -> np.ndarray:
    shapes = [(geom, i) for i, geom in enumerate(govs.geometry)]
    return rasterize(shapes, out_shape=shape, transform=transform, fill=-1, dtype="int16")


def build_grids(govs: gpd.GeoDataFrame, coast_buffer_km: float) -> Grids:
    root = project_root()
    with rasterio.open(root / "data/raw/worldpop_tun_2020_1km.tif") as s:
        pop = s.read(1).astype("float64")
        pop[(pop < 0) | ~np.isfinite(pop)] = 0
        pt = s.transform
    pop_gov = _gov_raster(govs, pop.shape, pt)
    pop[pop_gov < 0] = 0

    # coast buffer mask on the pop grid
    coast = load_coastline(govs).to_crs(UTM).buffer(coast_buffer_km * 1000).union_all()
    rows, cols = np.nonzero(pop > 0)
    xs, ys = rasterio.transform.xy(pt, rows, cols)
    pts = gpd.GeoSeries(gpd.points_from_xy(xs, ys), crs="EPSG:4326").to_crs(UTM)
    near = pts.within(coast).to_numpy()
    pop_coast = np.zeros(pop.shape, bool)
    pop_coast[rows[near], cols[near]] = True

    with rasterio.open(root / "data/raw/worldcover_tun_320m.tif") as s:
        wc = s.read(1)
        ct = s.transform
    crop_gov = _gov_raster(govs, wc.shape, ct)
    crop = (wc == 40) & (crop_gov >= 0)
    return Grids(pop, pt, pop_gov, pop_coast, crop, ct, crop_gov)


def _sample_pixels(weights: np.ndarray, transform, n: int, rng: np.random.Generator):
    flat = weights.ravel()
    p = flat / flat.sum()
    idx = rng.choice(flat.size, size=n, p=p)
    r, c = np.unravel_index(idx, weights.shape)
    # jitter inside the pixel (kept at 40 % of the pixel so points never leave it)
    dr = rng.uniform(0.1, 0.9, n)
    dc = rng.uniform(0.1, 0.9, n)
    x = transform.c + (c + dc) * transform.a
    y = transform.f + (r + dr) * transform.e
    return x, y


def _sample_inside(weights, transform, n, rng, polygon, max_iter: int = 50):
    """Sample pixel-jittered points and redraw those falling outside the polygon
    (rasterisation edge effects), so that no asset lands at sea or abroad."""
    from shapely import contains_xy

    x, y = _sample_pixels(weights, transform, n, rng)
    for _ in range(max_iter):
        bad = ~contains_xy(polygon, x, y)
        if not bad.any():
            return x, y
        x[bad], y[bad] = _sample_pixels(weights, transform, int(bad.sum()), rng)
    bad = ~contains_xy(polygon, x, y)
    if bad.any():  # last resort: a point guaranteed inside
        p = polygon.representative_point()
        x[bad], y[bad] = p.x, p.y
    return x, y


def generate_portfolio(cfg: dict | None = None, grids: Grids | None = None,
                       govs: gpd.GeoDataFrame | None = None) -> gpd.GeoDataFrame:
    cfg = cfg or load_yaml("portfolio.yaml")
    rng = np.random.default_rng(cfg["seed"])
    govs = govs if govs is not None else load_governorates()
    grids = grids or build_grids(govs, cfg["coast_buffer_km"])
    names = list(govs["governorate"])
    gov_pop = np.array([grids.pop[grids.pop_gov == i].sum() for i in range(len(names))])

    sectors = cfg["sectors"]
    shares = np.array([s["n_share"] for s in sectors.values()])
    counts = rng.multinomial(cfg["n_loans"], shares / shares.sum())

    frames = []
    for (key, s), n in zip(sectors.items(), counts):
        # 1) governorate allocation
        if "govs" in s:
            w = np.array([s["govs"].get(g, 0.0) for g in names], float)
        else:
            w = gov_pop.copy()
        g_idx = rng.choice(len(names), size=n, p=w / w.sum())
        xs, ys = np.empty(n), np.empty(n)
        for gi in np.unique(g_idx):
            m = g_idx == gi
            k = int(m.sum())
            if s["location"] == "cropland":
                weights = (grids.crop & (grids.crop_gov == gi)).astype(float)
                tr = grids.crop_transform
                if weights.sum() == 0:  # no cropland pixel: fall back on population
                    weights, tr = grids.pop * (grids.pop_gov == gi), grids.pop_transform
            elif s["location"] == "coast":
                weights = grids.pop * ((grids.pop_gov == gi) & grids.pop_coast)
                tr = grids.pop_transform
                if weights.sum() == 0:
                    weights = grids.pop * (grids.pop_gov == gi)
            else:
                weights, tr = grids.pop * (grids.pop_gov == gi), grids.pop_transform
            xs[m], ys[m] = _sample_inside(weights, tr, k, rng, govs.geometry.iloc[gi])

        lgd_lo, lgd_hi = cfg["lgd"][s["collateral"]]
        frames.append(pd.DataFrame({
            "sector": key,
            "sector_label": s["label"],
            "governorate_alloc": [names[i] for i in g_idx],
            "lon": xs, "lat": ys,
            "ead_tnd": np.round(s["ead_median"] * rng.lognormal(0, s["ead_sigma"], n), -2),
            "pd_base": rng.uniform(*s["pd"], n),
            "lgd_base": rng.uniform(lgd_lo, lgd_hi, n),
            "maturity_years": rng.integers(cfg["maturity_years"][0], cfg["maturity_years"][1] + 1, n),
            "collateral": s["collateral"],
        }))

    df = pd.concat(frames, ignore_index=True)
    # rescale EAD so that each sector matches its target share of the total book
    total = cfg["total_ead_tnd"]
    for key, s in sectors.items():
        m = df["sector"] == key
        if m.any():
            df.loc[m, "ead_tnd"] = np.round(df.loc[m, "ead_tnd"] * s["ead_share"] * total
                                            / df.loc[m, "ead_tnd"].sum(), -2)
    df = df.sample(frac=1.0, random_state=cfg["seed"]).reset_index(drop=True)
    df.insert(0, "loan_id", [f"SYN-{i:05d}" for i in rng.permutation(len(df))])
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
    # authoritative governorate = spatial join (points sampled inside rasterised polygons)
    joined = gpd.sjoin(gdf, govs, how="left", predicate="within").drop(columns="index_right")
    joined["governorate"] = joined["governorate"].fillna(joined["governorate_alloc"])
    return joined.drop(columns="governorate_alloc")


def main(out: Path | None = None) -> Path:
    out = out or project_root() / "outputs/portfolio.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    gdf = generate_portfolio()
    gdf.to_parquet(out)
    print(f"{len(gdf)} synthetic loans -> {out}")
    return out


if __name__ == "__main__":
    main()
