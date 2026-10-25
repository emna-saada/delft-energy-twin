"""Tree-shading sensitivity: crown transmissivity and crown extent.

AHN6 over Delft was flown in Dec 2025 / Jan 2026 (leaf-off), so crowns are under-sampled.
Scenarios vary the seasonal transmissivity (tau) and grow crowns by a grey dilation of the
vegetation surface (a simple proxy for leaf-on crown extent). Everything else is the base model.
"""
from __future__ import annotations

import copy
import json
import time

import numpy as np
import pandas as pd
from scipy import ndimage

from . import city, data, solar

SCENARIOS = {
    #  name: (tau leaf-on, tau leaf-off, crown dilation m)
    "base": (0.3, 0.7, 0.0),
    "opaque": (0.0, 0.0, 0.0),
    "dense": (0.1, 0.5, 0.0),
    "sparse": (0.5, 0.9, 0.0),
    "crown+1m": (0.3, 0.7, 1.0),
    "crown+2m": (0.3, 0.7, 2.0),
}


def dilate_crowns(dsm: np.ndarray, dsm_noveg: np.ndarray, metres: float, res: float) -> np.ndarray:
    """DSM with the tree surface grown by `metres` (max filter); buildings and terrain unchanged elsewhere."""
    if metres <= 0:
        return dsm
    veg = np.where(np.isfinite(dsm) & (dsm != dsm_noveg), dsm, -np.inf).astype(np.float32)
    k = int(round(metres / res))
    fp = np.hypot(*np.mgrid[-k:k + 1, -k:k + 1]) <= k
    grown = ndimage.grey_dilation(veg, footprint=fp)
    return np.where(grown > np.nan_to_num(dsm, nan=-np.inf), grown, dsm).astype(np.float32)


def run(ctx, cell_inputs_fn) -> pd.DataFrame:
    cfg, res = ctx.cfg, ctx.cfg["preprocess"]["raster_res"]
    dsm, dsm_nv, _ = ctx.mosaics
    weather, _ = solar.pvgis_tmy(cfg["site"]["lat"], cfg["site"]["lon"], data.RAW / "pvgis_tmy.json")
    b = ctx.buildings.set_index("identificatie")
    in_aoi = set(b.index[b.aoi.notna()])
    cells, ids = {}, {}
    for t in ctx.tiles:  # study-area buildings only: they are what the sensitivity is reported for
        c = cell_inputs_fn(ctx, t)
        i = c["planes"].identificatie.reindex(c["pids"]).values
        keep = pd.Series(i).isin(in_aoi).values  # hash-based; np.isin on object arrays is quadratic
        if keep.any():
            cells[t] = {k: c[k][keep] for k in ("rows", "cols", "z", "nrm")}
            ids[t] = i[keep]
    rows = []
    for name, (t_on, t_off, grow) in SCENARIOS.items():
        t0 = time.time()
        sc = copy.deepcopy(cfg)
        sc["solar"]["tree_tau_leaf_on"], sc["solar"]["tree_tau_leaf_off"] = t_on, t_off
        surf = dilate_crowns(dsm, dsm_nv, grow, res)
        per_bld = []
        for t, c in cells.items():
            irr, _, _ = solar.run_tile(c["rows"], c["cols"], c["z"], c["nrm"], surf, dsm_nv, res, weather, sc)
            per_bld.append(pd.DataFrame({"identificatie": ids[t], "full": irr[:, 0], "notrees": irr[:, 1]})
                           .groupby("identificatie").sum())
        g = pd.concat(per_bld)
        g["aoi"] = b.aoi.reindex(g.index).values
        g["tree_loss"] = 1 - g.full / g.notrees
        for aoi, ga in list(g.groupby("aoi")) + [("all", g)]:
            rows.append({"scenario": name, "tau_on": t_on, "tau_off": t_off, "crown_dilation_m": grow, "aoi": aoi,
                         "roof_irradiation_gwh": float(ga.full.sum() * res * res / 1e6),
                         "tree_loss": float(1 - ga.full.sum() / ga.notrees.sum()),
                         "share_bldg_tree_loss_gt10pct": float((ga.tree_loss > 0.10).mean()),
                         "share_bldg_tree_loss_gt25pct": float((ga.tree_loss > 0.25).mean())})
        print(name, f"{time.time() - t0:.0f}s", flush=True)
    df = pd.DataFrame(rows)
    out = city.CITY / "tree_sensitivity.csv"
    df.to_csv(out, index=False)
    return df


if __name__ == "__main__":
    from .pipeline import Context, cell_inputs
    ctx = Context(data.load_config())
    df = run(ctx, cell_inputs)
    piv = df.pivot_table(index="scenario", columns="aoi", values="tree_loss").reindex(list(SCENARIOS))
    print((100 * piv).round(2).to_string())
    (city.CITY / "tree_sensitivity_summary.json").write_text(json.dumps((100 * piv).round(3).to_dict(), indent=2))
