"""Data acquisition: AOIs, AHN tile index, LAZ/raster downloads, BAG footprints.

All sources are open and need no login. Every download is cached: an existing
file is never fetched again.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
import yaml
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
CONFIGS = ROOT / "configs"

PDOK_CBS = "https://service.pdok.nl/cbs/wijkenbuurten/2024/wfs/v1_0"
PDOK_BAG = "https://service.pdok.nl/lv/bag/wfs/v2_0"
ELLIPSIS = "https://api.ellipsis-drive.com/v3/ogc/wfs"


def load_config() -> dict:
    with open(CONFIGS / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get(url: str, params: dict | None = None, timeout: int = 120) -> requests.Response:
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r


def download(url: str, dest: Path, chunk: int = 1 << 20) -> Path:
    """Stream a file to disk; skip if it already exists with the expected size."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    head = requests.head(url, allow_redirects=True, timeout=60)
    size = int(head.headers.get("content-length", 0))
    if dest.exists() and (size == 0 or dest.stat().st_size == size):
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for block in r.iter_content(chunk):
                f.write(block)
    tmp.replace(dest)
    return dest


# --------------------------------------------------------------------------- CBS

def cbs_layer(layer: str, gemeente: str = "GM0503") -> gpd.GeoDataFrame:
    """CBS 2024 wijken/buurten for one municipality (default Delft)."""
    path = RAW / f"cbs_{layer}_delft.geojson"
    if not path.exists():
        filt = (f"<Filter><PropertyIsEqualTo><PropertyName>gemeentecode</PropertyName>"
                f"<Literal>{gemeente}</Literal></PropertyIsEqualTo></Filter>")
        r = _get(PDOK_CBS, {
            "service": "WFS", "version": "2.0.0", "request": "GetFeature",
            "typeNames": f"wijkenbuurten:{layer}", "outputFormat": "application/json",
            "srsName": "EPSG:28992", "count": 1000, "filter": filt,
        })
        path.write_bytes(r.content)
    return gpd.read_file(path).set_crs("EPSG:28992", allow_override=True)


def build_aois(cfg: dict) -> gpd.GeoDataFrame:
    """Dissolve CBS units into one polygon per AOI; write configs/aois.geojson."""
    wijken, buurten = cbs_layer("wijken"), cbs_layer("buurten")
    rows = []
    for name, spec in cfg["aois"].items():
        parts = []
        if "cbs_wijk" in spec:
            parts.append(wijken[wijken["wijkcode"].isin(spec["cbs_wijk"])])
        if "cbs_buurt" in spec:
            parts.append(buurten[buurten["buurtcode"].isin(spec["cbs_buurt"])])
        geom = pd.concat(parts).union_all()
        rows.append({"aoi": name, "label": spec["label"], "area_km2": geom.area / 1e6, "geometry": geom})
    aois = gpd.GeoDataFrame(rows, crs=cfg["crs"])
    aois.to_file(CONFIGS / "aois.geojson", driver="GeoJSON")
    return aois


# --------------------------------------------------------------------------- AHN

def ahn_index(epoch: str, cfg: dict, bounds_rd: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    """AHN tile index (with download URLs) intersecting an RD bounding box."""
    key = "_".join(str(int(v)) for v in bounds_rd)
    path = RAW / f"ahn_index_{epoch}_{key}.geojson"
    if not path.exists():
        wgs = gpd.GeoSeries([box(*bounds_rd)], crs=cfg["crs"]).to_crs(4326).total_bounds
        ds, layer = cfg["ahn"]["wfs"][epoch]
        r = _get(f"{ELLIPSIS}/{ds}", {
            "service": "WFS", "version": "2.0.0", "request": "GetFeature",
            "typeNames": layer, "count": 500, "outputFormat": "application/json",
            "bbox": f"{wgs[1]},{wgs[0]},{wgs[3]},{wgs[2]},urn:ogc:def:crs:EPSG::4326",
        })
        path.write_bytes(r.content)
    idx = gpd.read_file(path).to_crs(cfg["crs"])
    return idx[idx.intersects(box(*bounds_rd))].reset_index(drop=True)


def tiles_for_aois(cfg: dict, aois: gpd.GeoDataFrame, epoch: str = "AHN6") -> gpd.GeoDataFrame:
    buffered = aois.buffer(cfg["shadow_buffer_m"]).union_all()
    idx = ahn_index(epoch, cfg, buffered.bounds)
    idx = idx[idx.intersects(buffered)].copy()
    idx["aois"] = [",".join(aois.loc[aois.buffer(cfg["shadow_buffer_m"]).intersects(g), "aoi"])
                   for g in idx.geometry]
    return idx.sort_values("AHN").reset_index(drop=True)


def fetch_ahn_tile(tile: gpd.GeoSeries | pd.Series, epoch: str, products=("Puntenwolk",)) -> dict[str, Path]:
    out = {}
    for prod in products:
        url = tile[prod]
        out[prod] = download(url, RAW / epoch / url.rsplit("/", 1)[-1])
    return out


# --------------------------------------------------------------------------- BAG

def bag_footprints(bounds_rd: tuple[float, float, float, float], name: str) -> gpd.GeoDataFrame:
    """BAG 2.0 'pand' polygons (with bouwjaar, status) from PDOK WFS, paged."""
    path = RAW / f"bag_pand_{name}.gpkg"
    if path.exists():
        return gpd.read_file(path)
    feats, start, page = [], 0, 1000
    while True:
        r = _get(PDOK_BAG, {
            "service": "WFS", "version": "2.0.0", "request": "GetFeature",
            "typeNames": "bag:pand", "outputFormat": "application/json", "srsName": "EPSG:28992",
            "bbox": ",".join(map(str, bounds_rd)) + ",urn:ogc:def:crs:EPSG::28992",
            "count": page, "startIndex": start,
        })
        batch = json.loads(r.content)["features"]
        feats += batch
        if len(batch) < page:
            break
        start += page
    gdf = gpd.GeoDataFrame.from_features(feats, crs="EPSG:28992")
    # existing buildings; 'Verbouwing pand' (under renovation) includes Delft's medieval churches
    existing = gdf["status"].str.contains("in gebruik|verbouwing", case=False, na=False)
    gdf = gdf[existing].reset_index(drop=True)
    gdf.to_file(path, driver="GPKG")
    return gdf
