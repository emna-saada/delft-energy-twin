"""Publication figures in a plain journal style (serif type, no in-figure titles, captions in the text).

Each figure is written as vector PDF (for the LaTeX report) and PNG (for the website), in French
(outputs/paper/fr) and English (outputs/paper/en). All values come from outputs/ of the same run.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from matplotlib.colors import LinearSegmentedColormap
from rasterio.features import geometry_mask

from .config import project_root
from .hazards import climate
from .hazards.wildfire import fuel_grid
from .portfolio import load_governorates

INK, GREY, LIGHT = "#1a1a1a", "#6b6b6b", "#d9d9d9"
SCEN = {"baseline": "#9a9a9a", "ssp245": "#1f5f99", "ssp585": "#b23a2e"}
SEQ = LinearSegmentedColormap.from_list("oxblood", ["#f7efec", "#e3b9ad", "#c77a66", "#a1402f", "#6e1b13"])
HEAT = LinearSegmentedColormap.from_list("heat", ["#fbf4e6", "#f2d08a", "#e39a4d", "#c4502f", "#7e1f17"])
BLUE = LinearSegmentedColormap.from_list("water", ["#eaf1f8", "#9cc0df", "#3f7fb8", "#123f6e"])
FUEL = LinearSegmentedColormap.from_list("fuel", ["#f6f2df", "#cfd59a", "#8aa45a", "#3f6b2e", "#1d3d18"])
PERIODS = ["baseline", "ssp245_2030", "ssp245_2050", "ssp585_2030", "ssp585_2050"]

T = {
    "fr": {"today": "Climat actuel", "p": {"baseline": "Actuel", "ssp245_2030": "SSP2-4.5\n2030", "ssp245_2050": "SSP2-4.5\n2050",
                                           "ssp585_2030": "SSP5-8.5\n2030", "ssp585_2050": "SSP5-8.5\n2050"},
           "mtnd": "M TND", "pct_ead": "% de l'EAD", "ref": "Référence 2010–2014", "f2050": "SSP5-8.5, 2050",
           "hot": "Jours par an avec Tmax > 35 °C", "cdd": "Plus longue séquence sèche (jours)",
           "depth": "Profondeur d'eau, crue centennale (m)", "fuel": "Part de végétation combustible (rayon 2 km)",
           "bp": "EL additionnelle (pb de l'EAD)", "score": "Score composite d'aléa (0–1)",
           "today_s": "Aujourd'hui", "s245": "SSP2-4.5, 2050", "s585": "SSP5-8.5, 2050",
           "hz": ["Chaleur", "Sécheresse", "Inondation", "Feux"], "delta": "Variation de l'EL additionnelle (%)",
           "heat_ours": "ClimaRisk : jours Tmax > 35 °C", "heat_pr": "physrisk : jours Tmoy > 35 °C",
           "dr_ours": "ClimaRisk : score de sécheresse", "dr_pr": "physrisk : mois SPEI-12 < −1,5",
           "weight": "poids", "sect": "EL additionnelle (pb de l'EAD du secteur)", "dec": ","},
    "en": {"today": "Current climate", "p": {"baseline": "Current", "ssp245_2030": "SSP2-4.5\n2030", "ssp245_2050": "SSP2-4.5\n2050",
                                             "ssp585_2030": "SSP5-8.5\n2030", "ssp585_2050": "SSP5-8.5\n2050"},
           "mtnd": "M TND", "pct_ead": "% of EAD", "ref": "Reference 2010–2014", "f2050": "SSP5-8.5, 2050",
           "hot": "Days per year with Tmax > 35 °C", "cdd": "Longest dry spell (days)",
           "depth": "Water depth, 100-year flood (m)", "fuel": "Share of burnable vegetation (2 km radius)",
           "bp": "Extra expected loss (bp of EAD)", "score": "Composite hazard score (0–1)",
           "today_s": "Current climate", "s245": "SSP2-4.5, 2050", "s585": "SSP5-8.5, 2050",
           "hz": ["Heat", "Drought", "Flood", "Wildfire"], "delta": "Change in extra expected loss (%)",
           "heat_ours": "ClimaRisk: days Tmax > 35 °C", "heat_pr": "physrisk: days Tmean > 35 °C",
           "dr_ours": "ClimaRisk: drought score", "dr_pr": "physrisk: months SPEI-12 < −1.5",
           "weight": "weight", "sect": "Extra expected loss (bp of sector EAD)", "dec": "."},
}
SECTORS = {
    "fr": {"cereals": "Céréaliculture", "olives": "Oléiculture", "citrus": "Agrumes", "agrifood": "Agroalimentaire",
           "textile": "Textile", "tourism": "Tourisme côtier", "residential": "Immobilier résidentiel",
           "construction": "BTP", "chemicals": "Chimie et phosphates", "energy": "Énergie"},
    "en": {"cereals": "Cereals", "olives": "Olives", "citrus": "Citrus", "agrifood": "Agrifood", "textile": "Textile",
           "tourism": "Coastal tourism", "residential": "Housing", "construction": "Construction",
           "chemicals": "Chemicals and phosphates", "energy": "Energy"},
}


def style() -> None:
    mpl.rcParams.update({
        "font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"], "mathtext.fontset": "stix",
        "font.size": 9, "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
        "axes.edgecolor": INK, "axes.linewidth": 0.6, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 3, "ytick.major.size": 3,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
        "figure.dpi": 150, "savefig.dpi": 220, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
        "pdf.fonttype": 42, "legend.frameon": False,
    })


def num(x: float, d: int, lang: str) -> str:
    s = f"{x:.{d}f}"
    return s.replace(".", ",") if lang == "fr" else s


def save(fig, name: str, lang: str) -> None:
    d = project_root() / "outputs/paper" / lang
    d.mkdir(parents=True, exist_ok=True)
    fig.savefig(d / f"{name}.pdf")
    fig.savefig(d / f"{name}.png", facecolor="white")
    plt.close(fig)


def _frame(ax, govs, lw=0.35):
    govs.boundary.plot(ax=ax, color=INK, linewidth=lw)
    ax.set_xlim(7.45, 11.65)
    ax.set_ylim(30.2, 37.6)
    ax.set_aspect(1 / np.cos(np.deg2rad(34)))
    ax.set_axis_off()


def _cbar(fig, im, axes, label, ticks=None):
    cb = fig.colorbar(im, ax=axes, orientation="horizontal", fraction=0.035, pad=0.02, aspect=40, ticks=ticks)
    cb.set_label(label)
    cb.outline.set_linewidth(0.5)
    cb.ax.tick_params(width=0.5, length=2.5)
    return cb


def _clip(arr, transform, govs):
    out = geometry_mask([govs.union_all()], out_shape=arr.shape, transform=transform)
    return np.where(out, np.nan, arr)


def climate_maps(govs, lang):
    t = T[lang]
    med = climate.load_period_means().median("model")
    from shapely import contains_xy
    mask = govs.union_all()
    for name, var, label, vmax in (("fig_heat", "hot35", t["hot"], 150), ("fig_drought", "cdd", t["cdd"], 250)):
        fig, axes = plt.subplots(1, 2, figsize=(5.6, 4.6))
        for ax, p, ttl in zip(axes, ["baseline", "ssp585_2050"], [t["ref"], t["f2050"]]):
            da = med[var].sel(period=p)
            lon, lat = np.meshgrid(da.lon, da.lat)
            vals = np.where(contains_xy(mask.buffer(0.13), lon, lat), da.values, np.nan)
            im = ax.pcolormesh(da.lon, da.lat, vals, cmap=HEAT, vmin=0, vmax=vmax, shading="auto", rasterized=True)
            _frame(ax, govs)
            ax.text(0.5, 1.0, ttl, transform=ax.transAxes, ha="center", va="bottom", fontsize=9, style="italic")
        _cbar(fig, im, axes, label)
        save(fig, name, lang)


def flood_fire(govs, lang):
    t = T[lang]
    d = project_root() / "data/raw/flood"
    with rasterio.open(d / "inunriver_historical_000000000WATCH_1980.tif") as s:
        river, tr = s.read(6), s.transform
    with rasterio.open(d / "inuncoast_historical_nosub_hist_0.tif") as s:
        coast = s.read(6)
    depth = np.fmax(np.nan_to_num(river), np.nan_to_num(coast))
    depth = _clip(np.where(depth > 0.02, depth, np.nan), tr, govs)
    g, tf = fuel_grid()
    g = _clip(np.where(g > 0.05, g, np.nan), tf, govs)
    for name, arr, trf, cmap, vmax, label in (("fig_flood", depth, tr, BLUE, 1.5, t["depth"]),
                                              ("fig_fire", g, tf, FUEL, 0.8, t["fuel"])):
        fig, ax = plt.subplots(figsize=(3.0, 4.6))
        govs.plot(ax=ax, color="#f4f4f2", edgecolor="none")
        ext = (trf.c, trf.c + trf.a * arr.shape[1], trf.f + trf.e * arr.shape[0], trf.f)
        im = ax.imshow(arr, extent=ext, cmap=cmap, vmin=0, vmax=vmax, interpolation="nearest", zorder=2)
        _frame(ax, govs)
        labels = {"Tunis": (10.18, 36.88), "Medjerda": (9.25, 36.62), "Sousse": (10.64, 35.82)} if name == "fig_flood" else {}
        for lab, (x, y) in labels.items():
            ax.annotate(lab, (x, y), fontsize=7, style="italic", ha="center", zorder=3)
        _cbar(fig, im, ax, label)
        save(fig, name, lang)


def portfolio_maps(govs, assets, lang):
    t = T[lang]
    fig, axes = plt.subplots(1, 3, figsize=(6.3, 3.9))
    for ax, p, ttl in zip(axes, ["baseline", "ssp245_2050", "ssp585_2050"], [t["today_s"], t["s245"], t["s585"]]):
        a = assets[assets.period == p].sort_values("composite")
        govs.plot(ax=ax, color="#f4f4f2", edgecolor="none")
        sc = ax.scatter(a.lon, a.lat, c=a.composite, cmap=SEQ, vmin=0, vmax=0.65, s=1.5 + 16 * np.sqrt(a.ead_tnd / a.ead_tnd.max()),
                        linewidths=0, rasterized=True, zorder=2)
        _frame(ax, govs, 0.3)
        ax.text(0.5, 1.0, ttl, transform=ax.transAxes, ha="center", va="bottom", fontsize=9, style="italic")
    _cbar(fig, sc, axes, t["score"])
    save(fig, "fig_portfolio", lang)


def gov_map(govs, lang):
    t = T[lang]
    bg = pd.read_csv(project_root() / "outputs/by_governorate.csv")
    g = govs.merge(bg[bg.period == "ssp585_2050"], on="governorate")
    fig, ax = plt.subplots(figsize=(3.0, 4.6))
    g.plot(ax=ax, column="el_add_bp_med", cmap=SEQ, vmin=0, vmax=g.el_add_bp_med.max(), edgecolor="white", linewidth=0.5)
    _frame(ax, govs, 0.0)
    for _, r in g.nlargest(3, "el_add_bp_med").iterrows():
        c = r.geometry.representative_point()
        ax.annotate(r.governorate, (c.x, c.y), fontsize=6, ha="center", color="white" if r.el_add_bp_med > 40 else INK)
    sm = plt.cm.ScalarMappable(cmap=SEQ, norm=plt.Normalize(0, g.el_add_bp_med.max()))
    _cbar(fig, sm, ax, t["bp"])
    save(fig, "fig_gov", lang)


def scenario_charts(k, lang):
    t = T[lang]
    P = k["periods"]
    cols = [SCEN[p.split("_")[0]] for p in PERIODS]
    x = np.arange(5)
    for name, key, scale, ylab, d in (("fig_el", "el_add_tnd", 1e-6, t["mtnd"], 1), ("fig_share", "share_ead_high", 100, t["pct_ead"], 1)):
        med = np.array([P[p][key]["med"] for p in PERIODS]) * scale
        lo = np.array([P[p][key]["p10"] for p in PERIODS]) * scale
        hi = np.array([P[p][key]["p90"] for p in PERIODS]) * scale
        fig, ax = plt.subplots(figsize=(3.2, 2.4))
        ax.bar(x, med, width=0.6, color=cols, edgecolor="none")
        ax.errorbar(x, med, yerr=[med - lo, hi - med], fmt="none", ecolor=INK, elinewidth=0.7, capsize=2.5, capthick=0.7)
        for i, v in enumerate(med):
            ax.text(i, hi[i] + (hi.max() * 0.03), num(v, d, lang), ha="center", va="bottom", fontsize=7.5)
        ax.set_xticks(x, [t["p"][p] for p in PERIODS], fontsize=7.5)
        ax.set_ylabel(ylab)
        ax.set_ylim(0, hi.max() * 1.15)
        ax.tick_params(axis="x", length=0)
        if lang == "fr":
            ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))
        save(fig, name, lang)


def sector_charts(k, lang):
    t = T[lang]
    sl = SECTORS[lang]
    hm = pd.DataFrame(k["heatmap_sector_hazard"]["ssp585_2050"]).T[["heat", "drought", "flood", "fire"]]
    hm = hm.loc[hm.sum(axis=1).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    ax.imshow(hm.values, cmap=SEQ, vmin=0, vmax=0.8, aspect="auto")
    ax.set_xticks(range(4), t["hz"])
    ax.set_yticks(range(len(hm)), [sl[s] for s in hm.index])
    ax.tick_params(length=0)
    ax.xaxis.tick_top()
    for sp in ax.spines.values():
        sp.set_visible(False)
    for i in range(hm.shape[0]):
        for j in range(4):
            v = hm.values[i, j]
            ax.text(j, i, num(v, 2, lang), ha="center", va="center", fontsize=7, color="white" if v > 0.5 else INK)
    save(fig, "fig_heatmap", lang)

    bs = pd.read_csv(project_root() / "outputs/by_sector.csv")
    s = bs[bs.period == "ssp585_2050"].sort_values("el_add_bp_med")
    fig, ax = plt.subplots(figsize=(3.4, 2.9))
    ax.barh([sl[v] for v in s.sector], s.el_add_bp_med, color=SCEN["ssp585"], height=0.6)
    for i, v in enumerate(s.el_add_bp_med):
        ax.text(v + 1.2, i, num(v, 0, lang), va="center", fontsize=7.5)
    ax.set_xlabel(t["sect"])
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_xlim(0, s.el_add_bp_med.max() * 1.15)
    save(fig, "fig_sectors", lang)


def robustness(k, lang):
    t = T[lang]
    s = pd.DataFrame(k["sensitivity"])
    s = s[s.label != "β × 1.0"].copy()
    rep = {"poids": t["weight"], "chaleur": t["hz"][0].lower(), "sécheresse": t["hz"][1].lower(),
           "inondation": t["hz"][2].lower(), "feux": t["hz"][3].lower()}
    lab = s.label
    for a, b in rep.items():
        lab = lab.str.replace(a, b, regex=False)
    if lang == "fr":
        lab = lab.str.replace(r"(\d)\.(\d)", r"\1,\2", regex=True)
    fig, ax = plt.subplots(figsize=(3.4, 2.9))
    y = np.arange(len(s))[::-1]
    ax.barh(y, s.delta_pct, color=[SCEN["ssp585"] if v >= 0 else SCEN["ssp245"] for v in s.delta_pct], height=0.6)
    for yi, v in zip(y, s.delta_pct):
        ax.text(v + (2.5 if v >= 0 else -2.5), yi, (num(v, 0, lang) if v < 0 else "+" + num(v, 0, lang)).replace("-", "−"),
                va="center", ha="left" if v >= 0 else "right", fontsize=7)
    ax.set_yticks(y, lab)
    ax.axvline(0, color=INK, lw=0.6)
    ax.set_xlim(-75, 125)
    ax.set_xlabel(t["delta"])
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    save(fig, "fig_sensitivity", lang)

    pc = project_root() / "outputs/physrisk_comparison.csv"
    if pc.exists():
        d = pd.read_csv(pc)
        fig, axes = plt.subplots(1, 2, figsize=(5.8, 2.5))
        axes[0].scatter(d.ours_hot35_2050, d.physrisk_tas35_2050, s=3, color=SCEN["ssp585"], alpha=0.45, linewidths=0, rasterized=True)
        axes[0].set_xlabel(t["heat_ours"])
        axes[0].set_ylabel(t["heat_pr"])
        axes[1].scatter(d.ours_drought_2050, d.physrisk_spei_months_2050, s=3, color=SCEN["ssp245"], alpha=0.45, linewidths=0, rasterized=True)
        axes[1].set_xlabel(t["dr_ours"])
        axes[1].set_ylabel(t["dr_pr"])
        for ax, lab in zip(axes, ["(a)", "(b)"]):
            ax.text(-0.18, 1.02, lab, transform=ax.transAxes, fontsize=9)
        fig.tight_layout(w_pad=2.5)
        save(fig, "fig_physrisk", lang)


def render_all(langs=("fr", "en")) -> Path:
    style()
    root = project_root()
    govs = load_governorates()
    assets = pd.read_parquet(root / "outputs/asset_results.parquet")
    k = json.loads((root / "outputs/kpis.json").read_text(encoding="utf-8"))
    for lang in langs:
        climate_maps(govs, lang)
        flood_fire(govs, lang)
        portfolio_maps(govs, assets, lang)
        gov_map(govs, lang)
        scenario_charts(k, lang)
        sector_charts(k, lang)
        robustness(k, lang)
    return root / "outputs/paper"


if __name__ == "__main__":
    print(render_all())
