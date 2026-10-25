"""LoD2-style building meshes from our roof planes -> CityJSON 2.0 and 3D Tiles 1.1 (glTF content).

Roofs: each footprint cell gets the plane of its nearest labelled roof cell of the same building; fragments < 4 m2
are merged into a neighbouring plane (display geometry only - solar results stay per original plane); the plane
regions are polygonised, simplified (0.4 m), clipped to the BAG footprint, triangulated and lifted onto the plane.
Walls: from ground to the roof height just inside the footprint, sampled every 1 m and simplified (RDP, 0.3 m).
3D Tiles: one glb per (study area, AHN tile) in local east-north-up metres with heights relative to ground, so the
tileset sits on Cesium's ellipsoid without terrain (no Cesium ion token needed).
"""
from __future__ import annotations

import json
import struct

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import rasterio
import shapely
from pyproj import Transformer
from rasterio.features import rasterize, shapes
from rasterio.transform import from_origin
from scipy import ndimage
from shapely.geometry import Polygon, shape
from shapely.geometry.polygon import orient

from . import city, data

WEB = data.ROOT / "web" / "public" / "data"
CMAP = matplotlib.colormaps["inferno"]
WALL_RGB = (190, 190, 190)
KWH_RANGE = (200.0, 1200.0)
MIN_FRAGMENT_M2 = 4.0  # roof fragments merged into a neighbouring plane for display only
TO_WGS = Transformer.from_crs(28992, 4326, always_xy=True)


def color_of(kwh):
    """RGB (uint8) for kWh/m2 values on the inferno ramp; NaN -> wall grey. Scalar in -> (3,), array in -> (n, 3)."""
    k = np.atleast_1d(np.asarray(kwh, float))
    t = np.clip((k - KWH_RANGE[0]) / (KWH_RANGE[1] - KWH_RANGE[0]), 0, 1)
    c = (CMAP(np.nan_to_num(t, nan=0.0))[:, :3] * 255).astype(np.uint8)
    c[~np.isfinite(k)] = WALL_RGB
    return c[0] if np.ndim(kwh) == 0 else c


# --------------------------------------------------------------------------- per building geometry

def plane_z(p, x, y):
    return p["cz"] - ((x - p["cx"]) * p["nx"] + (y - p["cy"]) * p["ny"]) / p["nz"]


def building_surfaces(fp: Polygon, lab: np.ndarray, own: np.ndarray, tr, planes: pd.DataFrame, res: float):
    """Roof polygons (plane_id, Polygon) covering the footprint, and a function giving roof z at (x, y)."""
    known = own & (lab >= 0)
    if not known.any():
        return [], None
    _, (ir, ic) = ndimage.distance_transform_edt(~known, return_indices=True)
    filled = np.where(own, lab[ir, ic], -1).astype(np.int32)
    # display geometry: merge fragments < MIN_FRAGMENT_M2 into the nearest larger plane of the same building
    ids, cnt = np.unique(filled[own], return_counts=True)
    big = ids[cnt * res * res >= MIN_FRAGMENT_M2]
    if 0 < len(big) < len(ids):
        keep = own & np.isin(filled, big)
        _, (ir, ic) = ndimage.distance_transform_edt(~keep, return_indices=True)
        filled = np.where(own, filled[ir, ic], -1).astype(np.int32)
    roofs = []
    for geom, v in shapes(filled, mask=own, transform=tr):
        if v < 0:
            continue
        poly = shape(geom).simplify(0.4, preserve_topology=True).intersection(fp)
        for g in getattr(poly, "geoms", [poly]):
            if isinstance(g, Polygon) and g.area >= 0.5:
                roofs.append((int(v), orient(g, 1.0)))
    inv = ~tr

    def roof_z(x, y):
        c, r = inv * (np.asarray(x), np.asarray(y))
        r = np.clip(np.floor(r).astype(int), 0, filled.shape[0] - 1)
        c = np.clip(np.floor(c).astype(int), 0, filled.shape[1] - 1)
        pid = filled[r, c]
        z = np.full(np.shape(x), np.nan)
        ok = pid >= 0
        if ok.any():
            P = planes.loc[pid[ok]]
            z[ok] = plane_z(P, np.asarray(x)[ok], np.asarray(y)[ok]).values
        return z
    return roofs, roof_z


def triangulate(poly: Polygon) -> np.ndarray:
    """(n, 3, 2) counter-clockwise triangles of a polygon (constrained Delaunay)."""
    tris = shapely.constrained_delaunay_triangles(poly)
    out = []
    for t in getattr(tris, "geoms", []):
        xy = np.asarray(t.exterior.coords)[:3]
        a = (xy[1, 0] - xy[0, 0]) * (xy[2, 1] - xy[0, 1]) - (xy[1, 1] - xy[0, 1]) * (xy[2, 0] - xy[0, 0])
        out.append(xy if a > 0 else xy[::-1])
    return np.asarray(out).reshape(-1, 3, 2)


def rdp_keep(s: np.ndarray, z: np.ndarray, tol: float) -> np.ndarray:
    """Indices kept by Ramer-Douglas-Peucker on the (distance, height) profile of one edge."""
    keep = np.zeros(len(s), bool)
    keep[[0, -1]] = True
    stack = [(0, len(s) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        zl = z[i] + (z[j] - z[i]) * (s[i + 1:j] - s[i]) / max(s[j] - s[i], 1e-9)
        k = int(np.argmax(np.abs(z[i + 1:j] - zl))) + i + 1
        if abs(z[k] - zl[k - i - 1]) > tol:
            keep[k] = True
            stack += [(i, k), (k, j)]
    return np.flatnonzero(keep)


def wall_segments(ring: np.ndarray, roof_z, centre, g0, step=1.0, tol=0.3):
    """Wall pieces along a footprint ring whose top follows the roof (sampled 0.3 m inside, simplified by RDP)."""
    A, B, ZA, ZB = [], [], [], []
    c = np.asarray(centre)
    for a, b in zip(ring[:-1], ring[1:]):
        L = np.hypot(*(b - a))
        if L < 1e-6:
            continue
        s = np.linspace(0, L, max(2, int(np.ceil(L / step)) + 1))
        p = a + (b - a) * (s / L)[:, None]
        inward = (c - p) / np.maximum(np.hypot(*(c - p).T)[:, None], 1e-6)
        z = roof_z(*(p + 0.3 * inward).T)
        z = np.where(np.isfinite(z), np.maximum(z, g0 + 1.0), g0 + 1.0)
        k = rdp_keep(s, z, tol)
        A.append(p[k[:-1]]); B.append(p[k[1:]]); ZA.append(z[k[:-1]]); ZB.append(z[k[1:]])
    if not A:
        return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros(0), np.zeros(0)
    return np.concatenate(A), np.concatenate(B), np.concatenate(ZA), np.concatenate(ZB)


# --------------------------------------------------------------------------- per chunk

def build_chunk(bld: gpd.GeoDataFrame, planes: pd.DataFrame, cells: pd.DataFrame, ground: dict, origin, res,
                plane_kwh: dict):
    """MeshBuffer (NAP z, ground per vertex) and CityJSON surfaces for one chunk's buildings."""
    x0, y1 = origin
    pl = planes.set_index("plane_id")
    buf, city_objs = MeshBuffer(), {}
    bx0, by0, bx1, by1 = bld.total_bounds
    c0, r0 = int((bx0 - x0) / res) - 2, int((y1 - by1) / res) - 2
    w, h = int((bx1 - bx0) / res) + 5, int((by1 - by0) / res) + 5
    tr = from_origin(x0 + c0 * res, y1 - r0 * res, res, res)
    lab = np.full((h, w), -1, np.int64)
    sub = cells[(cells.row >= r0) & (cells.row < r0 + h) & (cells.col >= c0) & (cells.col < c0 + w)]
    lab[sub.row.values - r0, sub.col.values - c0] = sub.plane_id.values
    bidx = rasterize(((g, i + 1) for i, g in enumerate(bld.geometry)), out_shape=(h, w), transform=tr, fill=0, dtype="int32")
    planes_of = pl.groupby("identificatie").groups
    for i, r in enumerate(bld.itertuples()):
        g0 = ground.get(r.identificatie, np.nan)
        if not np.isfinite(g0):
            continue
        # small window around the building
        minx, miny, maxx, maxy = r.geometry.bounds
        ca, ra = int((minx - tr.c) / res) - 2, int((tr.f - maxy) / res) - 2
        cb_, rb = int((maxx - tr.c) / res) + 3, int((tr.f - miny) / res) + 3
        ca, ra, cb_, rb = max(ca, 0), max(ra, 0), min(cb_, w), min(rb, h)
        wl, wb = lab[ra:rb, ca:cb_], bidx[ra:rb, ca:cb_]
        wtr = from_origin(tr.c + ca * res, tr.f - ra * res, res, res)
        own = wb == i + 1
        mine = np.isin(wl, np.asarray(planes_of.get(r.identificatie, [])))
        roofs, roof_z = building_surfaces(r.geometry, np.where(mine, wl, -1), own, wtr, pl, res)
        if not roofs:
            continue
        surfaces = []
        for pid, poly in roofs:
            p = pl.loc[pid]
            t = triangulate(poly)
            if not len(t):
                continue
            xy, inv = np.unique(np.round(t.reshape(-1, 2), 3), axis=0, return_inverse=True)
            z = np.maximum(plane_z(p, xy[:, 0], xy[:, 1]), g0 + 1.0)
            buf.add(np.c_[xy, z], inv.reshape(-1, 3), [p.nx, p.ny, p.nz], color_of(plane_kwh.get(pid, np.nan)), g0)
            rings = [np.asarray(poly.exterior.coords)] + [np.asarray(ii.coords) for ii in poly.interiors]
            surfaces.append(("RoofSurface", [np.c_[rg, np.maximum(plane_z(p, rg[:, 0], rg[:, 1]), g0 + 1.0)] for rg in rings],
                             {"plane_id": pid, "slope_deg": round(float(p.slope_deg), 1),
                              "aspect_deg": round(float(p.aspect_deg), 1),
                              "kwh_m2": None if not np.isfinite(plane_kwh.get(pid, np.nan)) else round(float(plane_kwh[pid]), 0)}))
        fp = orient(r.geometry if r.geometry.geom_type == "Polygon" else max(r.geometry.geoms, key=lambda q: q.area), 1.0)
        cx, cy = np.asarray(fp.centroid.coords)[0]
        for ring in [np.asarray(fp.exterior.coords)] + [np.asarray(ii.coords) for ii in fp.interiors]:
            a, b, za, zb = wall_segments(ring, roof_z, (cx, cy), g0)
            n = len(a)
            if not n:
                continue
            gz = np.full(n, g0)
            quads = np.stack([np.c_[a, gz], np.c_[b, gz], np.c_[b, zb], np.c_[a, za]], 1)  # (n, 4, 3)
            faces = (np.arange(n)[:, None, None] * 4 + np.array([[0, 1, 2], [0, 2, 3]])[None]).reshape(-1, 3)
            d = b - a
            nrm = np.repeat(np.c_[d[:, 1], -d[:, 0], np.zeros(n)] / np.maximum(np.hypot(*d.T), 1e-9)[:, None], 4, 0)
            buf.add_many(quads.reshape(-1, 3), faces, nrm, np.array(WALL_RGB, np.uint8), g0)
            surfaces += [("WallSurface", [np.vstack([q, q[:1]])], {}) for q in quads]
        surfaces.append(("GroundSurface", [np.c_[np.asarray(fp.exterior.coords)[::-1], np.full(len(fp.exterior.coords), g0)]], {}))
        city_objs[r.identificatie] = surfaces
    return buf, city_objs


class MeshBuffer:
    """Indexed triangle soup: vertices are shared within one flat surface only (flat shading, one normal each)."""

    def __init__(self):
        self.V, self.N, self.C, self.G, self.F, self.n = [], [], [], [], [], 0

    def add(self, verts, faces, normal, rgb, ground):
        """One flat surface: a single normal for all its vertices."""
        nrm = np.asarray(normal, float)
        nrm = nrm / max(np.linalg.norm(nrm), 1e-9)
        self.add_many(verts, faces, np.tile(nrm, (len(verts), 1)), rgb, ground)

    def add_many(self, verts, faces, normals, rgb, ground):
        """Several surfaces at once, normals given per vertex."""
        self.V.append(np.asarray(verts, float))
        self.N.append(np.asarray(normals, float))
        self.C.append(np.tile(np.asarray(rgb, np.uint8), (len(verts), 1)))
        self.G.append(np.full(len(verts), ground))
        self.F.append(np.asarray(faces) + self.n)
        self.n += len(verts)

    def arrays(self):
        if not self.V:
            return None
        return (np.concatenate(self.V), np.concatenate(self.N), np.concatenate(self.C),
                np.concatenate(self.G), np.concatenate(self.F).astype(np.uint32))


# --------------------------------------------------------------------------- glTF / 3D Tiles

def enu_frame(x, y):
    """Lon/lat of an RD point and the angle that rotates RD grid axes into true east/north."""
    lon, lat = TO_WGS.transform(x, y)
    lon1, lat1 = TO_WGS.transform(x, y + 100)
    dE = np.radians(lon1 - lon) * np.cos(np.radians(lat)) * 6378137.0
    dN = np.radians(lat1 - lat) * 6378137.0
    return lon, lat, np.arctan2(dE, dN)


def enu_to_ecef(lon, lat):
    lo, la = np.radians(lon), np.radians(lat)
    a, f = 6378137.0, 1 / 298.257223563
    e2 = f * (2 - f)
    N = a / np.sqrt(1 - e2 * np.sin(la) ** 2)
    t = np.array([N * np.cos(la) * np.cos(lo), N * np.cos(la) * np.sin(lo), N * (1 - e2) * np.sin(la)])
    e = np.array([-np.sin(lo), np.cos(lo), 0])
    n = np.array([-np.sin(la) * np.cos(lo), -np.sin(la) * np.sin(lo), np.cos(la)])
    u = np.array([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)])
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = e, n, u, t
    return m


def write_glb(path, v_enu: np.ndarray, n_enu: np.ndarray, rgb: np.ndarray, faces: np.ndarray):
    """Indexed triangles; ENU input (z up) is written glTF y-up as (E, U, -N)."""
    pos = np.c_[v_enu[:, 0], v_enu[:, 2], -v_enu[:, 1]].astype(np.float32)
    nor = np.c_[n_enu[:, 0], n_enu[:, 2], -n_enu[:, 1]].astype(np.float32)
    # glTF vertex colours are linear; the colour ramp is sRGB
    s = rgb.astype(np.float64) / 255
    lin = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    col = np.c_[np.round(lin * 255), np.full(len(pos), 255)].astype(np.uint8)
    idx = faces.astype(np.uint32).ravel()
    blobs = [pos.tobytes(), nor.tobytes(), col.tobytes(), idx.tobytes()]
    offs = np.cumsum([0] + [len(b) for b in blobs])
    gltf = {
        "asset": {"version": "2.0", "generator": "delft_twin"},
        "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
        "materials": [{"pbrMetallicRoughness": {"metallicFactor": 0.0, "roughnessFactor": 0.9}, "doubleSided": True}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "COLOR_0": 2}, "indices": 3, "material": 0}]}],
        "buffers": [{"byteLength": int(offs[-1])}],
        "bufferViews": [{"buffer": 0, "byteOffset": int(offs[i]), "byteLength": len(blobs[i]),
                         "target": 34963 if i == 3 else 34962} for i in range(4)],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": len(pos), "type": "VEC3",
             "min": pos.min(0).tolist(), "max": pos.max(0).tolist()},
            {"bufferView": 1, "componentType": 5126, "count": len(pos), "type": "VEC3"},
            {"bufferView": 2, "componentType": 5121, "normalized": True, "count": len(pos), "type": "VEC4"},
            {"bufferView": 3, "componentType": 5125, "count": len(idx), "type": "SCALAR"},
        ],
    }
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    bin_ = b"".join(blobs)
    bin_ += b"\0" * (-len(bin_) % 4)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(bin_), 0x004E4942) + bin_)


# --------------------------------------------------------------------------- CityJSON

def write_cityjson(path, objs: dict, attrs: dict):
    verts, index = [], {}

    def vid(p):
        k = (int(round(p[0] * 1000)), int(round(p[1] * 1000)), int(round(p[2] * 1000)))
        if k not in index:
            index[k] = len(verts)
            verts.append(list(k))
        return index[k]

    co = {}
    for bid, surfaces in objs.items():
        bounds, sem_s, sem_v = [], [], []
        for kind, rings, a in surfaces:
            bounds.append([[vid(p) for p in ring[:-1]] for ring in rings])
            sem_s.append({"type": kind, **{k: v for k, v in a.items() if v is not None}})
            sem_v.append(len(sem_s) - 1)
        co[f"NL.IMBAG.Pand.{bid}"] = {
            "type": "Building", "attributes": {"identificatie": bid, **attrs.get(bid, {})},
            "geometry": [{"type": "MultiSurface", "lod": "2.2", "boundaries": bounds,
                          "semantics": {"surfaces": sem_s, "values": sem_v}}]}
    v = np.asarray(verts, np.int64)
    mn = v.min(0)
    cj = {"type": "CityJSON", "version": "2.0",
          "transform": {"scale": [0.001, 0.001, 0.001], "translate": (mn / 1000).tolist()},
          "metadata": {"referenceSystem": "https://www.opengis.net/def/crs/EPSG/0/7415",
                       "title": "LiDAR energy digital twin of Delft (AHN6) - roof planes with solar attributes"},
          "CityObjects": co, "vertices": (v - mn).tolist()}
    path.write_text(json.dumps(cj, separators=(",", ":")))


# --------------------------------------------------------------------------- run

def run(ctx) -> dict:
    cfg, res = ctx.cfg, ctx.cfg["preprocess"]["raster_res"]
    ex = city.extent(ctx.tiles)
    origin = (ex[0] - cfg["shadow_buffer_m"], ex[3] + cfg["shadow_buffer_m"])
    b = ctx.buildings
    b = b[~b.incomplete & b.aoi.notna()].copy()
    # ground per building: median DTM inside the footprint
    from .change import dtm_on_grid
    dsm, _, cb = ctx.mosaics
    big = (cb.left, cb.bottom, cb.right, cb.top)
    dtm = dtm_on_grid(dsm.shape, big, res, ctx.tiles)
    lab = rasterize(((g, i + 1) for i, g in enumerate(b.geometry)), out_shape=dsm.shape,
                    transform=from_origin(cb.left, cb.top, res, res), fill=0, dtype="int32")
    m = (lab > 0) & np.isfinite(dtm)
    gm = pd.Series(dtm[m]).groupby(lab[m]).median()
    ground = dict(zip(b.identificatie, gm.reindex(np.arange(1, len(b) + 1)).values))
    del dtm, lab

    attrs = json.loads((WEB / "buildings.json").read_text())
    (WEB / "tiles").mkdir(parents=True, exist_ok=True)
    (WEB / "cityjson").mkdir(parents=True, exist_ok=True)
    children, objs_by_aoi, stats = [], {}, {}
    lon_all, lat_all = [], []
    for t in ctx.tiles:
        cells = pd.read_parquet(data.PROCESSED / t / "roof_cells_solar.parquet", columns=["row", "col", "plane_id", "kwh_m2"])
        planes = pd.read_parquet(data.PROCESSED / t / "roof_planes.parquet")
        kwh = cells.groupby("plane_id").kwh_m2.mean().to_dict()
        for aoi, g in b[b.tile == t].groupby("aoi"):
            buf, objs = build_chunk(g, planes, cells, ground, origin, res, kwh)
            arr = buf.arrays()
            if arr is None:
                continue
            V, Nr, C, G, F = arr
            objs_by_aoi.setdefault(aoi, {}).update(objs)
            # chunk frame: centre of the chunk; heights relative to each building's own ground
            gx, gy = g.union_all().centroid.coords[0]
            lon, lat, th = enu_frame(gx, gy)
            rot = lambda x, y: (x * np.cos(th) + y * np.sin(th), -x * np.sin(th) + y * np.cos(th))  # noqa: E731
            E, N = rot(V[:, 0] - gx, V[:, 1] - gy)
            enu = np.c_[E, N, V[:, 2] - G]
            nE, nN = rot(Nr[:, 0], Nr[:, 1])
            name = f"{aoi}_{t}.glb"
            write_glb(WEB / "tiles" / name, enu, np.c_[nE, nN, Nr[:, 2]], C, F)
            mn, mx = enu.min(0), enu.max(0)
            c, hlf = (mn + mx) / 2, (mx - mn) / 2 + 1
            children.append({"transform": enu_to_ecef(lon, lat).T.flatten().tolist(),
                             "boundingVolume": {"box": [*c, hlf[0], 0, 0, 0, hlf[1], 0, 0, 0, hlf[2]]},
                             "geometricError": 0, "content": {"uri": f"tiles/{name}"}})
            lon_all.append(lon); lat_all.append(lat)
            stats[name] = {"buildings": len(objs), "triangles": int(len(F)),
                           "mb": round((WEB / "tiles" / name).stat().st_size / 1e6, 2)}
    lo, la = np.radians(lon_all), np.radians(lat_all)
    pad = 0.0005
    tileset = {"asset": {"version": "1.1"}, "geometricError": 2000,
               "root": {"boundingVolume": {"region": [lo.min() - pad, la.min() - pad, lo.max() + pad, la.max() + pad, -10, 150]},
                        "geometricError": 500, "refine": "ADD", "children": children}}
    (WEB / "tileset.json").write_text(json.dumps(tileset, indent=1))
    for aoi, objs in objs_by_aoi.items():
        write_cityjson(WEB / "cityjson" / f"{aoi}.city.json", objs, attrs)
    stats["cityjson_mb"] = {p.name: round(p.stat().st_size / 1e6, 1) for p in (WEB / "cityjson").glob("*.json")}
    (city.CITY / "mesh_stats.json").write_text(json.dumps(stats, indent=1))
    return stats


if __name__ == "__main__":
    from .pipeline import Context
    print(json.dumps(run(Context(data.load_config())), indent=1))
