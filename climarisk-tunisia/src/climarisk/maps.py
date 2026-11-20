"""Static PNG maps and charts (milestone 3 deliverable, reused by the PDF report)."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio

from . import theme
from .config import project_root
from .hazards import HAZARDS, climate
from .hazards.wildfire import fuel_grid
from .portfolio import load_governorates


def _frame(ax, govs):
    govs.boundary.plot(ax=ax, color="#ffffff", linewidth=0.6)
    govs.boundary.plot(ax=ax, color=theme.INK, linewidth=0.25, alpha=0.6)
    ax.set_xlim(7.4, 11.7)
    ax.set_ylim(30.2, 37.6)
    ax.set_axis_off()


def hazard_rasters(out: Path, govs: gpd.GeoDataFrame) -> list[Path]:
    """Four 'today' hazard maps + their 2050 SSP5-8.5 counterpart (ensemble median)."""
    theme.mpl_style()
    ds = climate.load_period_means()
    med = ds.median("model")
    cmap = theme.risk_cmap()
    paths = []
    mask = govs.union_all()

    def clip(da):
        lon, lat = np.meshgrid(da.lon, da.lat)
        from shapely import contains_xy
        inside = contains_xy(mask.buffer(0.15), lon, lat)
        return np.where(inside, da.values, np.nan)

    fields = {
        "heat": ("hot35", "Jours/an avec Tmax > 35 °C", 0, 150),
        "drought": ("cdd", "Jours secs consécutifs (max/an)", 0, 250),
    }
    for hz, (var, label, vmin, vmax) in fields.items():
        fig, axes = plt.subplots(1, 2, figsize=(7.2, 5.6))
        for ax, p, title in zip(axes, ["baseline", "ssp585_2050"], ["Référence 2010-2014", "SSP5-8.5 · 2050"]):
            da = med[var].sel(period=p)
            im = ax.pcolormesh(da.lon, da.lat, clip(da), cmap=cmap, vmin=vmin, vmax=vmax, shading="auto")
            _frame(ax, govs)
            ax.set_title(title, fontsize=10)
        cb = fig.colorbar(im, ax=axes, orientation="horizontal", fraction=0.04, pad=0.02)
        cb.set_label(label + " — médiane de 5 modèles CMIP6 (NEX-GDDP)", color=theme.MUTED, fontsize=8)
        cb.outline.set_visible(False)
        fig.suptitle(theme.HAZARD_LABELS[hz], x=0.02, ha="left", fontweight="bold", color=theme.INK)
        p_out = out / f"map_{hz}.png"
        fig.savefig(p_out)
        plt.close(fig)
        paths.append(p_out)

    # flood: Aqueduct RP100 riverine + coastal, baseline
    d = project_root() / "data/raw/flood"
    with rasterio.open(d / "inunriver_historical_000000000WATCH_1980.tif") as s:
        river = s.read(6)
        ext = rasterio.plot.plotting_extent(s) if hasattr(rasterio, "plot") else None
        tr = s.transform
    with rasterio.open(d / "inuncoast_historical_nosub_hist_0.tif") as s:
        coast = s.read(6)
    depth = np.maximum(river, coast)
    depth = np.where(depth > 0.02, depth, np.nan)
    extent = ext or (tr.c, tr.c + tr.a * depth.shape[1], tr.f + tr.e * depth.shape[0], tr.f)
    fig, ax = plt.subplots(figsize=(4.2, 5.6))
    govs.plot(ax=ax, color="#EEF2F3", edgecolor="none")
    im = ax.imshow(depth, extent=extent, cmap="Blues", vmin=0, vmax=2, interpolation="nearest")
    _frame(ax, govs)
    cb = fig.colorbar(im, ax=ax, orientation="horizontal", fraction=0.04, pad=0.02)
    cb.set_label("Profondeur d'eau, crue centennale (m) — WRI Aqueduct", color=theme.MUTED, fontsize=8)
    cb.outline.set_visible(False)
    ax.set_title(theme.HAZARD_LABELS["flood"] + " · référence")
    fig.savefig(out / "map_flood.png")
    plt.close(fig)
    paths.append(out / "map_flood.png")

    # fire fuel
    g, tr = fuel_grid()
    extent = (tr.c, tr.c + tr.a * g.shape[1], tr.f + tr.e * g.shape[0], tr.f)
    fig, ax = plt.subplots(figsize=(4.2, 5.6))
    govs.plot(ax=ax, color="#F3F1EC", edgecolor="none")
    im = ax.imshow(np.where(g > 0.05, g, np.nan), extent=extent, cmap="YlOrBr", vmin=0, vmax=0.8)
    _frame(ax, govs)
    cb = fig.colorbar(im, ax=ax, orientation="horizontal", fraction=0.04, pad=0.02)
    cb.set_label("Part de végétation combustible (rayon 2 km) — ESA WorldCover", color=theme.MUTED, fontsize=8)
    cb.outline.set_visible(False)
    ax.set_title(theme.HAZARD_LABELS["fire"] + " · combustible")
    fig.savefig(out / "map_fire.png")
    plt.close(fig)
    paths.append(out / "map_fire.png")
    return paths


def portfolio_maps(out: Path, govs: gpd.GeoDataFrame) -> list[Path]:
    theme.mpl_style()
    assets = pd.read_parquet(project_root() / "outputs/asset_results.parquet")
    paths = []
    fig, axes = plt.subplots(1, 3, figsize=(10, 5.4))
    for ax, p in zip(axes, ["baseline", "ssp245_2050", "ssp585_2050"]):
        g = assets[assets.period == p]
        govs.plot(ax=ax, color="#EDEAE3", edgecolor="white", linewidth=0.6)
        sc = ax.scatter(g.lon, g.lat, c=g.composite, cmap=theme.risk_cmap(), vmin=0, vmax=0.7,
                        s=4 + 30 * np.sqrt(g.ead_tnd / g.ead_tnd.max()), linewidths=0.2, edgecolors="white")
        _frame(ax, govs)
        ax.set_title({"baseline": "Aujourd'hui", "ssp245_2050": "SSP2-4.5 · 2050",
                      "ssp585_2050": "SSP5-8.5 · 2050"}[p], fontsize=10)
    cb = fig.colorbar(sc, ax=axes, orientation="horizontal", fraction=0.04, pad=0.02)
    cb.set_label("Score composite d'aléa physique (0-1), taille = EAD", color=theme.MUTED, fontsize=8)
    cb.outline.set_visible(False)
    fig.savefig(out / "map_portfolio.png")
    plt.close(fig)
    paths.append(out / "map_portfolio.png")

    # EL add by governorate (ssp585 2050)
    by_gov = pd.read_csv(project_root() / "outputs/by_governorate.csv")
    g = govs.merge(by_gov[by_gov.period == "ssp585_2050"], on="governorate")
    fig, ax = plt.subplots(figsize=(4.4, 5.6))
    g.plot(ax=ax, column="el_add_bp_med", cmap=theme.risk_cmap(), edgecolor="white", linewidth=0.6,
           legend=True, legend_kwds={"orientation": "horizontal", "fraction": 0.04, "pad": 0.02,
                                     "label": "EL climatique additionnelle (pb de l'EAD)"})
    _frame(ax, govs)
    ax.set_title("EL additionnelle · SSP5-8.5 · 2050")
    fig.savefig(out / "map_el_governorate.png")
    plt.close(fig)
    paths.append(out / "map_el_governorate.png")
    return paths


def render_all() -> list[Path]:
    out = project_root() / "outputs/maps"
    out.mkdir(parents=True, exist_ok=True)
    govs = load_governorates()
    paths = hazard_rasters(out, govs)
    if (project_root() / "outputs/asset_results.parquet").exists():
        paths += portfolio_maps(out, govs)
    for p in paths:
        print("map:", p)
    _ = HAZARDS
    return paths
