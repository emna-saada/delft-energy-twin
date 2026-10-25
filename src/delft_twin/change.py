"""AHN5 (2023) -> AHN6 (Dec 2025 / Jan 2026) change analysis.

* Per current building: height change inside the footprint (0.5 m inner buffer) ->
  new since 2023 / raised or extended / lowered / unchanged.
* Demolitions: 2023 BAG footprints (Kadaster hoogtestatistieken 2023 edition) that are no longer in
  the current BAG, checked against AHN6.
* Installed PV: "PV-like" planes (tilted 5-40 deg, 0.15-1.5 m above a flat reference roof) split into
  "present in 2023" (no height change) and "installed 2023-2026" (raised 0.15-1.5 m since AHN5).
Both DSMs are top-of-surface models from winter flights; tree overhang changes show up as change too.
"""
from __future__ import annotations

import json
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.features import rasterize

from . import city, data, preprocess

AHN5_DSM = {t: f"https://basisdata.nl/hwh-ahn/AHN5/03a_DSM_50cm/2023_R_{t}.TIF" for t in ("37EN1", "37EN2")}
HOOGTESTAT_2023 = "https://download.pdok.nl/kadaster/basisvoorziening-3d/v1_0/2023/hoogtestatistieken/{}_2023_hoogtestatistieken_gebouwen.zip"
BAG_WFS = "https://service.pdok.nl/lv/bag/wfs/v2_0"
THRESH = {"new_h5_max": 1.5, "new_h6_min": 2.5, "change_m": 1.0, "change_area_m2": 10.0}


def ahn5_on_grid(dsm6_shape, bounds, res):
    a5 = np.full(dsm6_shape, np.nan, np.float32)
    for t, url in AHN5_DSM.items():
        p = data.download(url, data.RAW / "AHN5" / url.rsplit("/", 1)[-1])
        city.paste_into(a5, p, bounds, res)
    return a5


def dtm_on_grid(shape, bounds, res, tiles):
    d = np.full(shape, np.nan, np.float32)
    for t in tiles:
        city.paste_into(d, data.PROCESSED / t / "dtm.tif", bounds, res)
    return d


def bag_status(status: str, bounds) -> gpd.GeoDataFrame:
    x0, y0, x1, y1 = bounds
    env = (f"<BBOX><PropertyName>geom</PropertyName><gml:Envelope xmlns:gml='http://www.opengis.net/gml/3.2' "
           f"srsName='urn:ogc:def:crs:EPSG::28992'><gml:lowerCorner>{x0} {y0}</gml:lowerCorner>"
           f"<gml:upperCorner>{x1} {y1}</gml:upperCorner></gml:Envelope></BBOX>")
    filt = (f"<Filter><And>{env}<PropertyIsEqualTo><PropertyName>status</PropertyName>"
            f"<Literal>{status}</Literal></PropertyIsEqualTo></And></Filter>")
    r = requests.get(BAG_WFS, params={"service": "WFS", "version": "2.0.0", "request": "GetFeature",
                                      "typeNames": "bag:pand", "outputFormat": "application/json",
                                      "srsName": "EPSG:28992", "count": 1000, "filter": filt}, timeout=120)
    r.raise_for_status()
    f = r.json()["features"]
    return gpd.GeoDataFrame.from_features(f, crs="EPSG:28992") if f else gpd.GeoDataFrame(geometry=[], crs="EPSG:28992")


def footprints_2023(bounds) -> gpd.GeoDataFrame:
    parts = []
    for blad in ("37EN1", "37EN2"):
        z = data.RAW / "ref3d" / f"{blad}_2023_hoogtestatistieken_gebouwen.zip"
        if not z.exists():
            z.write_bytes(requests.get(HOOGTESTAT_2023.format(blad), timeout=600).content)
        out = data.RAW / "ref3d" / "hoogtestat_2023"
        zipfile.ZipFile(z).extractall(out)
        g = gpd.read_file(next(out.glob(f"{blad}*.gpkg")), bbox=tuple(bounds))
        parts.append(g[["identificatie", "oorspronkelijkbouwjaar", "rf_h_ground", "rf_h_roof_70p", "geometry"]])
    g = pd.concat(parts).drop_duplicates("identificatie")
    return gpd.GeoDataFrame(g.dissolve("identificatie").reset_index(), crs="EPSG:28992")


def per_footprint(arrs: dict, foot: gpd.GeoDataFrame, shape, transform, inner=0.5) -> pd.DataFrame:
    """Median / area statistics of each array inside each (inner-buffered) footprint."""
    lab = rasterize(((g, i + 1) for i, g in enumerate(foot.geometry.buffer(-inner)) if not g.is_empty),
                    out_shape=shape, transform=transform, fill=0, dtype="int32")
    m = lab > 0
    df = pd.DataFrame({"i": lab[m] - 1, **{k: v[m] for k, v in arrs.items()}})
    return df


def run(ctx) -> dict:
    cfg, res = ctx.cfg, ctx.cfg["preprocess"]["raster_res"]
    dsm6, _, cb = ctx.mosaics
    big = (cb.left, cb.bottom, cb.right, cb.top)
    grid = preprocess.Grid(big, res)
    dsm5 = ahn5_on_grid(dsm6.shape, big, res)
    dtm = dtm_on_grid(dsm6.shape, big, res, ctx.tiles)
    d = dsm6 - dsm5
    preprocess.write_tif(city.CITY / "dsm_ahn5_2023.tif", dsm5, grid)
    preprocess.write_tif(city.CITY / "dsm_change_ahn6_minus_ahn5.tif", d, grid)
    h5, h6 = dsm5 - dtm, dsm6 - dtm

    # ---------------------------------------------------------------- current buildings
    b = ctx.buildings
    b = b[~b.incomplete].reset_index(drop=True)
    cells = per_footprint({"d": d, "h5": h5, "h6": h6}, b, dsm6.shape, grid.transform)
    cells = cells[np.isfinite(cells.d) & np.isfinite(cells.h5) & np.isfinite(cells.h6)]
    ca = res * res
    cells["up"] = (cells.d > THRESH["change_m"]) * ca
    cells["down"] = (cells.d < -THRESH["change_m"]) * ca
    g = cells.groupby("i")
    st = pd.DataFrame({
        "n": g.size(), "d_median": g.d.median(), "h5_median": g.h5.median(), "h6_median": g.h6.median(),
        "area_up_m2": g.up.sum(), "area_down_m2": g.down.sum(),
    })
    st["area_m2"] = st.n * ca
    out = b[["identificatie", "bouwjaar", "status", "aoi", "tile"]].join(st, how="inner")
    new = (out.h5_median < THRESH["new_h5_max"]) & (out.h6_median >= THRESH["new_h6_min"])
    up = ~new & (out.area_up_m2 >= THRESH["change_area_m2"]) & (out.area_up_m2 >= 0.05 * out.area_m2)
    down = ~new & ~up & (out.area_down_m2 >= THRESH["change_area_m2"]) & (out.area_down_m2 >= 0.05 * out.area_m2)
    out["change"] = np.select([new, up, down], ["new_since_2023", "raised_or_extended", "lowered"], "unchanged")
    out.to_parquet(city.CITY / "change_buildings.parquet")

    # noise on unchanged buildings
    unch = out[out.change == "unchanged"].d_median
    noise = {"median_m": float(unch.median()), "nmad_m": float(1.4826 * (unch - unch.median()).abs().median())}

    # validation against BAG construction year / status
    yr = pd.to_numeric(out.bouwjaar, errors="coerce")
    built_after = yr >= 2024  # completed after the 2023 AHN5 flights (2023 itself is ambiguous)
    big_new = built_after & (out.area_m2 >= 30) & (out.h5_median < THRESH["new_h5_max"])  # >= 30 m2, empty site in 2023
    val_new = {
        "n_bag_bouwjaar_ge_2024": int(built_after.sum()),
        "recall_new_for_bouwjaar_ge_2024": float((out.change[built_after] == "new_since_2023").mean()) if built_after.any() else None,
        "n_bouwjaar_ge_2024_ge30m2_empty_site_2023": int(big_new.sum()),
        "recall_new_ge30m2_empty_site_2023": float((out.change[big_new] == "new_since_2023").mean()) if big_new.any() else None,
        "share_bouwjaar_ge_2024_with_structure_in_2023": float((out.h5_median[built_after] >= 2.5).mean()) if built_after.any() else None,
        "n_detected_new": int(new.sum()),
        "detected_new_with_bouwjaar_ge_2023": float((yr[new] >= 2023).mean()) if new.any() else None,
        "detected_new_status_counts": out.status[new].value_counts().to_dict(),
    }

    # ---------------------------------------------------------------- demolitions
    x0, y0, x1, y1 = city.extent(ctx.tiles)
    f23 = footprints_2023((x0, y0, x1, y1))
    current = set(data.bag_footprints((x0 - 100, y0 - 100, x1 + 100, y1 + 100), "delft_all").identificatie)
    for st_name in ("Bouw gestart", "Sloopvergunning verleend", "Bouwvergunning verleend"):
        current |= set(bag_status(st_name, (x0, y0, x1, y1)).get("identificatie", []))
    gone = f23[~f23.identificatie.isin(current)].reset_index(drop=True)
    dem = {"n_2023_footprints_not_in_current_bag": len(gone)}
    if len(gone):
        gc = per_footprint({"h5": h5, "h6": h6}, gone, dsm6.shape, grid.transform)
        gs = gc.groupby("i").agg(h5=("h5", "median"), h6=("h6", "median"), n=("h5", "size"))
        gone = gone.join(gs, how="left")
        gone["confirmed_by_ahn"] = (gone.h5 >= 2.5) & (gone.h6 < 1.5)
        gone["rebuilt_on_site"] = (gone.h5 >= 2.5) & (gone.h6 >= 2.5)
        gone.to_parquet(city.CITY / "change_demolished.parquet")
        dem.update({"n_confirmed_demolished": int(gone.confirmed_by_ahn.sum()),
                    "area_confirmed_m2": float(gone.loc[gone.confirmed_by_ahn].area.sum()),
                    "n_footprint_replaced_rebuilt": int(gone.rebuilt_on_site.sum())})

    # ---------------------------------------------------------------- installed PV on flat roofs
    vp = pd.concat([pd.read_parquet(data.PROCESSED / t / "val_planes.parquet") for t in ctx.tiles])
    pv = vp[(vp.ref_slope < 3) & vp.slope_deg.between(5, 40) & vp.dz.between(0.15, 1.5)][["tile", "plane_id", "area_3d_m2"]]
    pvd = []
    for t in ctx.tiles:
        c = pd.read_parquet(data.PROCESSED / t / "roof_cells_solar.parquet", columns=["row", "col", "plane_id"])
        c = c[c.plane_id.isin(set(pv.loc[pv.tile == t, "plane_id"]))]
        c["d"] = d[c.row.values, c.col.values]
        pvd.append(c.groupby("plane_id").d.median().rename("d_median").reset_index().assign(tile=t))
    pv = pv.merge(pd.concat(pvd), on=["tile", "plane_id"], how="left")
    pv["pv_epoch"] = np.select([pv.d_median.between(0.15, 1.5), pv.d_median.abs() < 0.10],
                               ["installed_2023_2026", "present_2023"], "unclear")
    pv.to_parquet(city.CITY / "change_pv_planes.parquet")
    pv_sum = pv.groupby("pv_epoch").agg(n=("area_3d_m2", "size"), area_m2=("area_3d_m2", "sum")).round(0).to_dict("index")

    res_ = {"thresholds": THRESH, "noise_unchanged_buildings": noise,
            "building_change_counts": out.change.value_counts().to_dict(),
            "building_change_by_aoi": out.groupby(out.aoi.fillna("outside_aoi")).change.value_counts().unstack(fill_value=0).to_dict("index"),
            "validation_new": val_new, "demolitions": dem, "pv_flat_roofs": pv_sum}
    (city.CITY / "change_stats.json").write_text(json.dumps(res_, indent=2, default=str))
    return res_


if __name__ == "__main__":
    from .pipeline import Context
    print(json.dumps(run(Context(data.load_config())), indent=1, default=str))
