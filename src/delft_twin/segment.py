"""Roof plane segmentation per BAG footprint.

1. Assign building points to footprints (rasterised inner-buffered BAG polygons).
2. kNN normals + curvature by local PCA (neighbours restricted to the same building).
3. Region growing (numba): seeds in order of increasing curvature; a neighbour joins
   if its normal is within `normal_angle_deg` of the region normal and it lies within
   `dist_threshold` of the region plane.
4. Least-squares refit per plane -> slope, aspect, area, fit RMSE.
5. Planes steeper than `max_roof_slope_deg` are treated as walls and dropped.
6. Obstacles: building points > `obstacle_height` above the plane they sit on.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from numba import njit
from rasterio.features import rasterize
from rasterio.transform import from_origin
from scipy.spatial import cKDTree

LABEL_RES = 0.25


def assign_footprints(x, y, foot: gpd.GeoDataFrame, inner_buffer: float, bounds) -> np.ndarray:
    """Building index (row of `foot`) for each point, -1 outside every footprint."""
    x0, y0, x1, y1 = bounds
    nx, ny = int((x1 - x0) / LABEL_RES), int((y1 - y0) / LABEL_RES)
    tr = from_origin(x0, y1, LABEL_RES, LABEL_RES)
    shapes = ((g, i) for i, g in enumerate(foot.geometry.buffer(-inner_buffer)) if not g.is_empty)
    lab = rasterize(shapes, out_shape=(ny, nx), transform=tr, fill=-1, dtype="int32")
    col = np.clip(((x - x0) / LABEL_RES).astype(np.int64), 0, nx - 1)
    row = np.clip(((y1 - y) / LABEL_RES).astype(np.int64), 0, ny - 1)
    return lab[row, col]


def knn_normals(xyz: np.ndarray, bid: np.ndarray, k: int):
    """Neighbour table (-1 where neighbour belongs to another building), normals, curvature."""
    tree = cKDTree(xyz)
    _, nb = tree.query(xyz, k=k + 1, workers=-1)
    nb = nb[:, 1:]
    nb[bid[nb] != bid[:, None]] = -1
    normals, curv = _pca(xyz, nb)
    return nb, normals, curv


@njit(cache=True)
def _pca(xyz, nb):
    n, k = nb.shape
    normals = np.zeros((n, 3))
    curv = np.full(n, 1.0)
    for i in range(n):
        idx = [i]
        for j in range(k):
            if nb[i, j] >= 0:
                idx.append(nb[i, j])
        if len(idx) < 4:
            continue
        p = np.empty((len(idx), 3))
        for a in range(len(idx)):
            p[a] = xyz[idx[a]]
        c = p - p.sum(axis=0) / len(idx)
        w, v = np.linalg.eigh(c.T @ c)
        nrm = v[:, 0]
        if nrm[2] < 0:
            nrm = -nrm
        normals[i] = nrm
        s = w.sum()
        curv[i] = w[0] / s if s > 0 else 1.0
    return normals, curv


@njit(cache=True)
def _region_grow(xyz, nb, normals, curv, cos_tol, dist_tol, min_pts):
    n, k = nb.shape
    label = np.full(n, -1, np.int64)
    order = np.argsort(curv)
    stack = np.empty(n, np.int64)
    members = np.empty(n, np.int64)
    nxt = 0
    for s in order:
        if label[s] != -1 or curv[s] > 0.05:
            continue
        label[s] = nxt
        rn = normals[s].copy()
        sn = normals[s].copy()
        sp = xyz[s].copy()
        cnt = 1
        top = 0
        stack[top] = s
        top += 1
        nm = 0
        members[nm] = s
        nm += 1
        while top > 0:
            top -= 1
            i = stack[top]
            for j in range(k):
                q = nb[i, j]
                if q < 0 or label[q] != -1:
                    continue
                if abs(normals[q, 0] * rn[0] + normals[q, 1] * rn[1] + normals[q, 2] * rn[2]) < cos_tol:
                    continue
                c0, c1, c2 = sp[0] / cnt, sp[1] / cnt, sp[2] / cnt
                d = (xyz[q, 0] - c0) * rn[0] + (xyz[q, 1] - c1) * rn[1] + (xyz[q, 2] - c2) * rn[2]
                if abs(d) > dist_tol:
                    continue
                label[q] = nxt
                stack[top] = q
                top += 1
                members[nm] = q
                nm += 1
                sn += normals[q]
                sp += xyz[q]
                cnt += 1
                rn = sn / np.sqrt((sn * sn).sum())
        if cnt < min_pts:
            for a in range(nm):
                label[members[a]] = -2  # too small: never reused as seed or member
        else:
            nxt += 1
    for i in range(n):
        if label[i] == -2:
            label[i] = -1
    return label


def fit_plane(p: np.ndarray):
    c = p.mean(axis=0)
    _, _, vt = np.linalg.svd(p - c, full_matrices=False)
    nrm = vt[2] if vt[2, 2] >= 0 else -vt[2]
    rmse = float(np.sqrt(np.mean(((p - c) @ nrm) ** 2)))
    return c, nrm, rmse


def plane_attributes(p: np.ndarray, cell: float = 0.5) -> dict:
    c, nrm, rmse = fit_plane(p)
    slope = float(np.degrees(np.arccos(np.clip(nrm[2], -1, 1))))
    aspect = float((np.degrees(np.arctan2(nrm[0], nrm[1])) + 360) % 360)  # 0 = N, 90 = E
    cells = np.unique(np.floor(p[:, :2] / cell).astype(np.int64), axis=0)
    area_2d = len(cells) * cell * cell
    return {"cx": c[0], "cy": c[1], "cz": c[2], "nx": nrm[0], "ny": nrm[1], "nz": nrm[2],
            "slope_deg": slope, "aspect_deg": aspect, "fit_rmse": rmse,
            "area_2d_m2": area_2d, "area_3d_m2": area_2d / max(np.cos(np.radians(slope)), 0.2),
            "n_pts": len(p), "z_min": float(p[:, 2].min()), "z_max": float(p[:, 2].max())}


def segment_buildings(pts: dict, foot: gpd.GeoDataFrame, bounds, cfg: dict):
    """Return (planes DataFrame, per-point arrays: building index, plane id, obstacle flag)."""
    sc = cfg["segmentation"]
    bid = assign_footprints(pts["x"], pts["y"], foot, sc["footprint_inner_buffer"], bounds)
    keep = bid >= 0
    xyz = np.column_stack([pts["x"][keep], pts["y"][keep], pts["z"][keep]])
    b = bid[keep]
    origin = xyz.min(axis=0)
    xyz_l = xyz - origin  # local coords keep PCA numerically clean

    nb, normals, curv = knn_normals(xyz_l, b, sc["knn"])
    label = _region_grow(xyz_l, nb, normals, curv, np.cos(np.radians(sc["normal_angle_deg"])),
                         sc["dist_threshold"], sc["min_points"])

    rows = []
    order = np.argsort(label, kind="stable")
    lab_sorted = label[order]
    starts = np.searchsorted(lab_sorted, np.arange(label.max() + 2))
    for pid in range(label.max() + 1):
        idx = order[starts[pid]:starts[pid + 1]]
        a = plane_attributes(xyz[idx])
        a.update({"plane_id": pid, "bag_idx": int(b[idx[0]])})
        rows.append(a)
    planes = pd.DataFrame(rows)
    # near-vertical planes are facade / parapet / courtyard-wall points inside the footprint
    walls = planes.plane_id[planes.slope_deg > sc["max_roof_slope_deg"]].values
    label[np.isin(label, walls)] = -1
    planes = planes[planes.slope_deg <= sc["max_roof_slope_deg"]].reset_index(drop=True)
    planes["roof_type"] = np.where(planes.slope_deg < sc["flat_slope_deg"], "flat", "pitched")
    planes["identificatie"] = foot["identificatie"].values[planes.bag_idx]

    # obstacles: unassigned points that rise above the plane below them (same building)
    obstacle = np.zeros(len(b), bool)
    un = np.flatnonzero(label < 0)
    if len(un) and len(planes):
        tree = cKDTree(xyz_l[label >= 0][:, :2])
        assigned = np.flatnonzero(label >= 0)
        _, j = tree.query(xyz_l[un, :2], k=1, workers=-1)
        near = assigned[j]
        same = b[near] == b[un]
        pl = planes.set_index("plane_id").loc[label[near]]
        h = ((xyz[un, 0] - pl.cx.values) * pl.nx.values + (xyz[un, 1] - pl.cy.values) * pl.ny.values
             + (xyz[un, 2] - pl.cz.values) * pl.nz.values)
        obstacle[un] = same & (h > sc["obstacle_height"])

    per_point = {"keep": keep, "bag_idx": b, "plane_id": label, "obstacle": obstacle}
    return planes, per_point
