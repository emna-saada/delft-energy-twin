"""Static figures for README / report (written to results/figures/)."""
from __future__ import annotations

import geopandas as gpd
import matplotlib
import numpy as np
import rasterio
from rasterio.enums import Resampling

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import city, data  # noqa: E402

FIG = data.ROOT / "results" / "figures"
BG = "#111"


def city_irradiation_map(step: int = 4):
    """Roof irradiation over all tiles (block-max downsampled for display) with AOI outlines."""
    with rasterio.open(city.CITY / "roof_irradiation_kwh_m2.tif") as s:
        h, w = s.height // step, s.width // step
        full = s.read(1, masked=True).filled(np.nan)[:h * step, :w * step]
        b = s.bounds
    with np.errstate(all="ignore"):
        blocks = full.reshape(h, step, w, step)
        irr = np.ma.masked_invalid(np.nanmax(np.where(np.isfinite(blocks), blocks, -np.inf), axis=(1, 3)))
    irr = np.ma.masked_less(irr, -1e30)
    with rasterio.open(city.CITY / "city_dsm.tif") as s:
        dsm = s.read(1, out_shape=(h, w), resampling=Resampling.average, masked=True)
    aois = gpd.read_file(data.CONFIGS / "aois.geojson")
    ext = (b.left, b.right, b.bottom, b.top)
    fig, ax = plt.subplots(figsize=(11, 12.5), facecolor=BG)
    ax.set_facecolor(BG)
    ax.imshow(np.clip(dsm.filled(0), -2, 30), cmap="gray", vmin=-2, vmax=45, extent=ext)
    im = ax.imshow(irr, cmap="inferno", vmin=200, vmax=1200, extent=ext)
    aois.boundary.plot(ax=ax, color="#4fd1c5", linewidth=1.6)
    for _, a in aois.iterrows():
        p = a.geometry.representative_point()
        ax.annotate(a.label, (p.x, p.y), color="#4fd1c5", fontsize=10, ha="center",
                    bbox=dict(fc=BG, ec="none", alpha=0.7))
    ax.set_axis_off()
    ax.set_title("Delft - annual roof irradiation from AHN6 (kWh/m²/yr), 14 tiles", color="w")
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.01)
    cb.ax.yaxis.set_tick_params(color="w")
    plt.setp(cb.ax.get_yticklabels(), color="w")
    FIG.mkdir(parents=True, exist_ok=True)
    out = FIG / "city_roof_irradiation.png"
    plt.tight_layout()
    plt.savefig(out, dpi=110, facecolor=BG)
    return out


AOIS = ["binnenstad", "campus", "voorhof"]
LABELS = {"binnenstad": "Binnenstad", "campus": "TU campus", "voorhof": "Voorhof"}
ACCENT = ["#f6ad55", "#4fd1c5", "#b794f4"]


def _style(ax, title):
    ax.set_facecolor(BG)
    ax.set_title(title, color="w", fontsize=11, loc="left")
    ax.tick_params(colors="#ccc")
    for s in ax.spines.values():
        s.set_color("#555")
    ax.yaxis.label.set_color("#ccc")
    ax.grid(axis="y", color="#333", lw=0.6)
    ax.set_axisbelow(True)


def summary_panels():
    """Tree sensitivity, AHN5->AHN6 change, and PV value before/after the end of net metering."""
    import json
    import pandas as pd
    sens = pd.read_csv(city.CITY / "tree_sensitivity.csv")
    chg = json.loads((city.CITY / "change_stats.json").read_text())["building_change_by_aoi"]
    pv = json.loads((city.CITY / "pv_summary.json").read_text())["by_aoi"]
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.8), facecolor=BG)
    x = np.arange(len(AOIS))

    order = ["sparse", "base", "dense", "opaque", "crown+1m", "crown+2m"]
    ax = axs[0]
    for i, a in enumerate(AOIS):
        s = sens[sens.aoi == a].set_index("scenario").reindex(order)
        ax.plot(order, 100 * s.share_bldg_tree_loss_gt10pct, "o-", color=ACCENT[i], label=LABELS[a])
    _style(ax, "Buildings losing >10 % of roof sun to trees")
    ax.set_ylabel("% of buildings")
    ax.tick_params(axis="x", rotation=30)
    ax.legend(facecolor=BG, labelcolor="w", edgecolor="#555", fontsize=9)

    ax = axs[1]
    kinds = [("new_since_2023", "new"), ("raised_or_extended", "raised / extended"), ("lowered", "lowered")]
    w = 0.26
    for j, (k, lab) in enumerate(kinds):
        ax.bar(x + (j - 1) * w, [chg[a].get(k, 0) for a in AOIS], w, color=["#68d391", "#f6ad55", "#fc8181"][j], label=lab)
    ax.set_xticks(x, [LABELS[a] for a in AOIS])
    _style(ax, "Buildings changed, AHN5 (2023) → AHN6 (2025/26)")
    ax.set_ylabel("buildings")
    ax.legend(facecolor=BG, labelcolor="w", edgecolor="#555", fontsize=9)

    ax = axs[2]
    vals = [("value_2026_meur", "2026 net metering", "#90cdf4"), ("value_2027_meur", "2027 rules", "#fc8181"),
            ("value_2027_battery_meur", "2027 + 5 kWh battery/dwelling", "#68d391")]
    for j, (k, lab, col) in enumerate(vals):
        ax.bar(x + (j - 1) * w, [pv[a][k] for a in AOIS], w, color=col, label=lab)
    ax.set_xticks(x, [LABELS[a] for a in AOIS])
    _style(ax, "Annual value of rooftop PV on homes")
    ax.set_ylabel("million EUR / yr")
    ax.legend(facecolor=BG, labelcolor="w", edgecolor="#555", fontsize=9)
    plt.tight_layout()
    out = FIG / "summary_trees_change_value.png"
    plt.savefig(out, dpi=110, facecolor=BG)
    return out


def heritage_map(tile: str = "84000_447000", window=(84350, 447250, 84750, 447650)):
    """Usable PV cells by heritage category around the Markt, with detected front facades."""
    import pandas as pd
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    cfg = data.load_config()
    res = cfg["preprocess"]["raster_res"]
    ex = city.extent(city.tile_ids(cfg))
    x0, y1 = ex[0] - cfg["shadow_buffer_m"], ex[3] + cfg["shadow_buffer_m"]
    u = pd.read_parquet(data.PROCESSED / tile / "pv_usable_cells.parquet")
    u["x"], u["y"] = x0 + (u.col + 0.5) * res, y1 - (u.row + 0.5) * res
    wx0, wy0, wx1, wy1 = window
    u = u[(u.x >= wx0) & (u.x < wx1) & (u.y >= wy0) & (u.y < wy1)]
    w, h = int((wx1 - wx0) / res), int((wy1 - wy0) / res)
    img = np.full((h, w), np.nan)
    code = {"permitted": 0, "permit_required": 1, "not_permitted": 2}
    img[((wy1 - u.y) / res).astype(int), ((u.x - wx0) / res).astype(int)] = u.heritage.map(code).values
    with rasterio.open(city.CITY / "city_dsm.tif") as s:
        win = rasterio.windows.from_bounds(wx0, wy0, wx1, wy1, s.transform)
        dsm = s.read(1, window=win, masked=True)
    fronts = gpd.read_file(city.CITY / "heritage_front_facades.gpkg", bbox=window)
    fig, ax = plt.subplots(figsize=(9, 9), facecolor=BG)
    ax.set_facecolor(BG)
    ext = (wx0, wx1, wy0, wy1)
    ax.imshow(np.clip(dsm.filled(0), -2, 30), cmap="gray", vmin=-2, vmax=45, extent=ext)
    ax.imshow(img, cmap=ListedColormap(["#68d391", "#f6ad55", "#fc8181"]), vmin=0, vmax=2, extent=ext, interpolation="nearest")
    fronts.plot(ax=ax, color="#4fd1c5", linewidth=1.2)
    ax.set_xlim(wx0, wx1); ax.set_ylim(wy0, wy1); ax.set_axis_off()
    ax.set_title("Indicative heritage filter around the Markt (usable PV cells)", color="w", loc="left")
    ax.legend(handles=[Patch(color="#68d391", label="permitted"), Patch(color="#f6ad55", label="permit required (rijksmonument)"),
                       Patch(color="#fc8181", label="not permitted (front-facing / < 4 m from front)"),
                       Patch(color="#4fd1c5", label="detected front facade")],
              loc="lower left", facecolor=BG, labelcolor="w", edgecolor="#555", fontsize=9)
    out = FIG / "heritage_markt.png"
    plt.tight_layout()
    plt.savefig(out, dpi=110, facecolor=BG)
    return out


if __name__ == "__main__":
    print(city_irradiation_map())
    print(summary_panels())
    print(heritage_map())
