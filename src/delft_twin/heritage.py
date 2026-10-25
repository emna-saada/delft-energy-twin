"""Indicative heritage filter: technical vs permitted rooftop PV potential.

Encoded rules (Delft protected-cityscape quick check as reported in 2019; the current municipal criteria must be
checked before any decision — this layer is indicative only):
  * applies inside the RCE protected city/village views (beschermde stads- en dorpsgezichten);
  * public space = BGT road parts (wegdeel, incl. footpaths and squares) + water (waterdeel, canals);
  * a "front" facade = outline piece whose outward view reaches public space within 15 m before another building;
  * not permitted: cells within 4 m of a front facade, and pitched-roof cells that slope down towards a front
    facade (the roof face borders public space);
  * national monuments (RCE rijksmonumenten) always need an individual permit -> "permit required".
Each scenario re-checks panel-field suitability (>= 10 m2, >= 650 kWh/m2) on the remaining cells.
"""
from __future__ import annotations

import json
import time

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from rasterio.features import rasterize
from rasterio.transform import from_origin
from scipy import ndimage
from shapely.geometry import box

from . import city, data, pv, solar

RCE = "https://api.pdok.nl/rce/beschermde-gebieden-cultuurhistorie/ogc/v1/collections/{}/items"
BGT = "https://api.pdok.nl/lv/bgt/ogc/v1/collections/{}/items"
RD = "http://www.opengis.net/def/crs/EPSG/0/28992"
RULES = {"front_ray_m": 15.0, "front_setback_m": 4.0, "downslope_search_m": 20.0, "front_band_m": 1.0}


def _get(url, params, tries=4):
    for k in range(tries):
        try:
            r = requests.get(url, params=params, timeout=180)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if k == tries - 1:
                raise
            time.sleep(5 * (k + 1))


def ogc_features(url: str, bounds, cache_name: str, chunk: float | None = None, id_col: str = "lokaal_id") -> gpd.GeoDataFrame:
    """All features in `bounds` (paged, retried); optionally queried in square chunks to keep paging short."""
    path = data.RAW / f"{cache_name}.gpkg"
    if path.exists():
        return gpd.read_file(path)
    x0, y0, x1, y1 = bounds
    step = chunk or max(x1 - x0, y1 - y0)
    feats = []
    for cx in np.arange(x0, x1, step):
        for cy in np.arange(y0, y1, step):
            nxt = url
            params = {"f": "json", "limit": 1000, "bbox": f"{cx},{cy},{min(cx + step, x1)},{min(cy + step, y1)}",
                      "bbox-crs": RD, "crs": RD}
            while nxt:
                j = _get(nxt, params)
                feats += j["features"]
                nxt = next((l["href"] for l in j.get("links", []) if l.get("rel") == "next"), None)
                params = None  # the next link carries all parameters
    g = gpd.GeoDataFrame.from_features(feats, crs="EPSG:28992")
    if id_col in g:
        g = g.drop_duplicates(id_col)
    g.to_file(path, driver="GPKG")
    return g


def layers(bounds):
    poly = ogc_features(RCE.format("rce_inspire_polygons"), bounds, "rce_polygons")
    pts = ogc_features(RCE.format("rce_inspire_points"), bounds, "rce_points")
    views = poly[poly.namespace == "nlps-stadsendorpsgezichten"]
    mon_poly = poly[poly.namespace == "nlps-rijksmonumenten"]
    mon_pts = pts[pts.namespace == "nlps-rijksmonumenten"]
    # public space is only needed around the protected views (inside AOI bounds)
    vx0, vy0, vx1, vy1 = views.total_bounds
    vb = (max(vx0, bounds[0]) - 50, max(vy0, bounds[1]) - 50, min(vx1, bounds[2]) + 50, min(vy1, bounds[3]) + 50)
    road = ogc_features(BGT.format("wegdeel"), vb, "bgt_wegdeel", chunk=500)
    water = ogc_features(BGT.format("waterdeel"), vb, "bgt_waterdeel", chunk=500)
    public = pd.concat([g[g.get("eind_registratie").isna()] if "eind_registratie" in g else g for g in (road, water)])
    if "relatieve_hoogteligging" in public:
        public = public[pd.to_numeric(public.relatieve_hoogteligging, errors="coerce").fillna(0) >= 0]
    return views, mon_poly, mon_pts, gpd.GeoDataFrame(public, crs="EPSG:28992")


def classify_buildings(b: gpd.GeoDataFrame, views, mon_poly, mon_pts) -> gpd.GeoDataFrame:
    b = b.copy()
    vu = views.union_all()
    b["in_protected_view"] = b.representative_point().within(vu)
    hit = gpd.sjoin(mon_pts[["geometry"]], b[["identificatie", "geometry"]], predicate="within")
    mon = set(hit.identificatie)
    if len(mon_poly):
        ov = gpd.overlay(b[["identificatie", "geometry"]], mon_poly[["geometry"]], how="intersection")
        share = ov.assign(a=ov.area).groupby("identificatie").a.sum() / b.set_index("identificatie").area
        mon |= set(share[share > 0.5].index)
    b["rijksmonument"] = b.identificatie.isin(mon)
    return b


def front_edges(b: gpd.GeoDataFrame, public: gpd.GeoDataFrame, res: float = 0.5) -> gpd.GeoSeries:
    """Outline pieces of protected-view buildings that look onto public space.

    For every <= 1 m piece of the outer footprint ring, walk along the outward normal up to `front_ray_m`: the piece
    is a front facade if the walk reaches public space (BGT road / water) before entering another building. Private
    front strips, steps and verges between facade and street (mapped separately in BGT) therefore do not hide a
    front, while party walls and facades onto enclosed courtyards are not fronts.
    """
    from shapely.geometry import LineString
    from shapely.geometry.polygon import orient
    pv_b = b[b.in_protected_view]
    x0, y0, x1, y1 = pv_b.total_bounds
    m = RULES["front_ray_m"] + 2
    x0, y0, x1, y1 = x0 - m, y0 - m, x1 + m, y1 + m
    h, w = int((y1 - y0) / res) + 1, int((x1 - x0) / res) + 1
    tr = from_origin(x0, y1, res, res)
    pub = rasterize(((g, 1) for g in public.geometry if g is not None), out_shape=(h, w), transform=tr, fill=0, dtype="uint8")
    near_b = b[b.intersects(box(x0, y0, x1, y1))]
    bld = rasterize(((g, i + 1) for i, g in enumerate(near_b.geometry)), out_shape=(h, w), transform=tr, fill=0, dtype="int32")
    own_id = dict(zip(near_b.identificatie, range(1, len(near_b) + 1)))

    segs, owner, idents = [], [], []
    for ident, geom in zip(pv_b.identificatie, pv_b.geometry):
        for poly in getattr(geom, "geoms", [geom]):
            ring = np.asarray(orient(poly, 1.0).exterior.coords)
            for (ax, ay), (bx, by) in zip(ring[:-1], ring[1:]):
                n = max(1, int(np.ceil(np.hypot(bx - ax, by - ay) / 1.0)))
                t = np.linspace(0, 1, n + 1)
                for t0, t1 in zip(t[:-1], t[1:]):
                    segs.append((ax + (bx - ax) * t0, ay + (by - ay) * t0, ax + (bx - ax) * t1, ay + (by - ay) * t1))
                    owner.append(own_id.get(ident, 0))
                    idents.append(ident)
    s = np.asarray(segs)
    owner = np.asarray(owner)
    mx, my = (s[:, 0] + s[:, 2]) / 2, (s[:, 1] + s[:, 3]) / 2
    dx, dy = s[:, 2] - s[:, 0], s[:, 3] - s[:, 1]
    L = np.hypot(dx, dy)
    nx, ny = dy / L, -dx / L  # outward normal of a counter-clockwise ring
    front = np.zeros(len(s), bool)
    blocked = np.zeros(len(s), bool)
    for d in np.arange(res, RULES["front_ray_m"] + res, res):
        c = ((mx + nx * d - x0) / res).astype(int)
        r = ((y1 - (my + ny * d)) / res).astype(int)
        inb = (r >= 0) & (r < h) & (c >= 0) & (c < w)
        r, c = np.clip(r, 0, h - 1), np.clip(c, 0, w - 1)
        other = inb & (bld[r, c] > 0) & (bld[r, c] != owner)
        hit = inb & (pub[r, c] == 1) & ~blocked
        front |= hit
        blocked |= other
    return gpd.GeoDataFrame({"identificatie": np.asarray(idents)[front]},
                            geometry=[LineString([(a, b_), (c_, d_)]) for a, b_, c_, d_ in s[front]], crs="EPSG:28992")


def cell_categories(u: pd.DataFrame, tp: pd.DataFrame, b: gpd.GeoDataFrame, fronts: gpd.GeoSeries,
                    origin, res) -> np.ndarray:
    """'permitted' / 'permit_required' / 'not_permitted' for each usable cell of one tile."""
    x0, y1 = origin
    pl = tp.set_index("plane_id")
    ident = pl.identificatie.reindex(u.plane_id).values
    binfo = b.set_index("identificatie")
    in_view = binfo.in_protected_view.reindex(ident).fillna(False).values.astype(bool)
    monument = binfo.rijksmonument.reindex(ident).fillna(False).values.astype(bool)
    cat = np.where(monument, "permit_required", "permitted").astype(object)
    if not in_view.any():
        return cat
    # local raster around the tile's protected-view cells
    m = 60  # cells of margin (30 m) so nearby front edges are seen
    r0, c0 = u.row[in_view].min() - m, u.col[in_view].min() - m
    h, w = u.row[in_view].max() - r0 + m + 1, u.col[in_view].max() - c0 + m + 1
    tr = from_origin(x0 + c0 * res, y1 - r0 * res, res, res)
    bb = box(x0 + c0 * res, y1 - (r0 + h) * res, x0 + (c0 + w) * res, y1 - r0 * res)
    fr = fronts[fronts.intersects(bb)]
    front = rasterize(((g, 1) for g in fr.geometry), out_shape=(h, w), transform=tr, fill=0, all_touched=True, dtype="uint8") \
        if len(fr) else np.zeros((h, w), np.uint8)
    dist = ndimage.distance_transform_edt(front == 0) * res
    bl = b[b.intersects(bb)].reset_index(drop=True)
    blab = rasterize(((g, i + 1) for i, g in enumerate(bl.geometry)), out_shape=(h, w), transform=tr, fill=0, dtype="int32")
    bid = dict(zip(bl.identificatie, range(1, len(bl) + 1)))

    rr, cc = u.row.values - r0, u.col.values - c0
    sel = np.flatnonzero(in_view)
    near = dist[rr[sel], cc[sel]] < RULES["front_setback_m"]
    # pitched cells sloping down towards a front facade (within the same building)
    slope = pl.slope_deg.reindex(u.plane_id.values[sel]).values
    asp = np.radians(pl.aspect_deg.reindex(u.plane_id.values[sel]).values)
    pitched = ~u.flat.values[sel]
    own = np.array([bid.get(i, 0) for i in ident[sel]])
    facing = np.zeros(sel.size, bool)
    for d in np.arange(res, RULES["downslope_search_m"] + res, res):
        r = np.round(rr[sel] - d * np.cos(asp) / res).astype(int)
        c = np.round(cc[sel] + d * np.sin(asp) / res).astype(int)
        inside = (r >= 0) & (r < h) & (c >= 0) & (c < w)
        r, c = np.clip(r, 0, h - 1), np.clip(c, 0, w - 1)
        still = inside & (blab[r, c] == own)
        facing |= still & (dist[r, c] <= RULES["front_band_m"])
    blocked = near | (pitched & facing & (slope >= 5))
    cat[sel[blocked]] = "not_permitted"
    return cat


def run(ctx) -> dict:
    cfg, res = ctx.cfg, ctx.cfg["preprocess"]["raster_res"]
    aois = gpd.read_file(data.CONFIGS / "aois.geojson")
    x0, y0, x1, y1 = aois.total_bounds
    views, mon_poly, mon_pts, public = layers((x0 - 200, y0 - 200, x1 + 200, y1 + 200))
    b = classify_buildings(ctx.buildings[~ctx.buildings.incomplete], views, mon_poly, mon_pts)
    fronts = front_edges(b, public)
    ex = city.extent(ctx.tiles)
    origin = (ex[0] - cfg["shadow_buffer_m"], ex[3] + cfg["shadow_buffer_m"])

    cells = []
    for t in ctx.tiles:
        u = pd.read_parquet(data.PROCESSED / t / "pv_usable_cells.parquet")
        tp = pd.read_parquet(data.PROCESSED / t / "roof_planes.parquet")
        u["heritage"] = cell_categories(u, tp, b, fronts, origin, res)
        u.to_parquet(data.PROCESSED / t / "pv_usable_cells.parquet")
        cells.append(u)
    u = pd.concat(cells, ignore_index=True)

    planes = pd.read_parquet(city.CITY / "roof_planes_solar.parquet")
    weather, _ = solar.pvgis_tmy(cfg["site"]["lat"], cfg["site"]["lon"], data.RAW / "pvgis_tmy.json")
    pr = pv.prices(cfg)
    profiles, _ = pv.orientation_profiles(weather, cfg)
    scen = {"technical": np.ones(len(u), bool),
            "permitted_incl_permit": u.heritage.values != "not_permitted",
            "permitted_no_permit": u.heritage.values == "permitted"}
    out, per_bld = {}, {}
    for name, keep in scen.items():
        us = u[keep].copy()
        us["f_ok"] = pv.field_suitability(us, cfg["pv"])
        p = pv.planes_from_cells(planes, us, cfg)
        bb, _ = pv.buildings_balance(ctx, p, profiles, weather, pr)
        per_bld[name] = bb.set_index("identificatie")[["kwp", "kwh_yr", "value_2026_eur", "value_2027_eur"]]
        for aoi, g in bb.groupby(bb.aoi.fillna("outside_aoi")):
            r = g[(g.demand_kwh > 0) & (g.kwh_yr > 0)]
            out.setdefault(aoi, {})[name] = {
                "kwp": float(g.kwp.sum()), "gwh_yr": float(g.kwh_yr.sum() / 1e6),
                "n_buildings_with_pv": int((g.kwp > 0).sum()),
                "residential_coverage": float(g[g.demand_kwh > 0].kwh_yr.sum() / g.demand_kwh.sum()) if (g.demand_kwh > 0).any() else None,
                "value_2027_meur": float(r.value_2027_eur.sum() / 1e6)}
    for aoi in out:
        t = out[aoi]["technical"]["gwh_yr"]
        for name in ("permitted_incl_permit", "permitted_no_permit"):
            out[aoi][name]["share_of_technical"] = out[aoi][name]["gwh_yr"] / t if t else None

    bstat = b.groupby(b.aoi.fillna("outside_aoi")).agg(n=("identificatie", "size"), in_view=("in_protected_view", "sum"),
                                                       monuments=("rijksmonument", "sum")).astype(int).to_dict("index")
    cstat = u.merge(planes[["tile", "plane_id", "aoi"]], on=["tile", "plane_id"], how="left")
    cat_share = cstat.groupby(cstat.aoi.fillna("outside_aoi")).heritage.value_counts(normalize=True) \
        .unstack(fill_value=0).round(4).to_dict("index")

    bld = per_bld["technical"].join(per_bld["permitted_incl_permit"], rsuffix="_permitted") \
        .join(per_bld["permitted_no_permit"], rsuffix="_nopermit") \
        .join(b.set_index("identificatie")[["aoi", "in_protected_view", "rijksmonument"]])
    gpd.GeoDataFrame(bld.join(b.set_index("identificatie").geometry), crs="EPSG:28992").to_parquet(city.CITY / "heritage_buildings.parquet")
    in_view = b[b.in_protected_view]
    has_front = in_view.identificatie.isin(set(fronts.identificatie))
    fronts.to_file(city.CITY / "heritage_front_facades.gpkg", driver="GPKG")
    res_ = {"rules": RULES, "buildings": bstat, "usable_cell_categories": cat_share, "by_aoi": out,
            "front_facade_m": float(fronts.length.sum()),
            "share_protected_buildings_with_front": {a: float(g.mean()) for a, g in has_front.groupby(in_view.aoi.fillna("outside_aoi"))}}
    (city.CITY / "heritage_summary.json").write_text(json.dumps(res_, indent=2, default=str))
    return res_


if __name__ == "__main__":
    from .pipeline import Context
    print(json.dumps(run(Context(data.load_config())), indent=1, default=str))
