"""PDF methodology report (French) built from outputs/ with Jinja2 + WeasyPrint.

All figures quoted in the report are read from outputs/kpis.json (and the CSVs written by the
same pipeline run); nothing is typed by hand.
"""
from __future__ import annotations

import base64
import json
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from . import theme
from .config import project_root

HAZ = ["heat", "drought", "flood", "fire"]


FIG_DIR = None


def _fig_b64(fig, name: str | None = None) -> str:
    import io

    if name and FIG_DIR is not None:  # same figure reused on GitHub and in the LinkedIn visuals
        FIG_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(FIG_DIR / f"{name}.png", dpi=200, bbox_inches="tight", facecolor="white")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _img_b64(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def _style():
    theme.mpl_style()
    from matplotlib import font_manager

    names = {f.name for f in font_manager.fontManager.ttflist}
    if "Inter" in names:
        plt.rcParams["font.family"] = "Inter"


def charts(k: dict, out: Path) -> dict[str, str]:
    global FIG_DIR
    FIG_DIR = out / "figures"
    _style()
    labels = k["meta"]["period_labels"]
    res = {}

    # 1. EL additional by period with band
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    ps = theme.PERIOD_ORDER
    med = np.array([k["periods"][p]["el_add_tnd"]["med"] for p in ps]) / 1e6
    lo = np.array([k["periods"][p]["el_add_tnd"]["p10"] for p in ps]) / 1e6
    hi = np.array([k["periods"][p]["el_add_tnd"]["p90"] for p in ps]) / 1e6
    cols = [theme.SCENARIO_COLORS[p.split("_")[0]] for p in ps]
    ax.bar(range(5), med, color=cols, width=0.62)
    ax.errorbar(range(5), med, yerr=[med - lo, hi - med], fmt="none", ecolor=theme.INK, capsize=4, lw=1)
    for i, v in enumerate(med):
        ax.text(i, v + (hi[i] - med[i]) + 0.25, f"{v:.1f}", ha="center", fontsize=8.5, color=theme.INK)
    ax.set_xticks(range(5), [labels[p] for p in ps], fontsize=8.5)
    ax.set_ylabel("M TND")
    ax.set_title("EL climatique additionnelle (médiane et intervalle 10–90 % entre modèles)")
    res["el_period"] = _fig_b64(fig, "el_period")

    # 2. share EAD high
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    med = np.array([k["periods"][p]["share_ead_high"]["med"] for p in ps]) * 100
    lo = np.array([k["periods"][p]["share_ead_high"]["p10"] for p in ps]) * 100
    hi = np.array([k["periods"][p]["share_ead_high"]["p90"] for p in ps]) * 100
    ax.bar(range(5), med, color=cols, width=0.62, alpha=0.9)
    ax.errorbar(range(5), med, yerr=[med - lo, hi - med], fmt="none", ecolor=theme.INK, capsize=4, lw=1)
    ax.set_xticks(range(5), [labels[p] for p in ps], fontsize=8.5)
    for i, v in enumerate(med):
        ax.text(i, hi[i] + 1.2, f"{v:.1f} %".replace(".", ","), ha="center", fontsize=8.5, color=theme.INK)
    ax.set_ylabel("% de l'EAD")
    ax.set_title("Part de l'EAD en zone d'aléa élevé (médiane et intervalle 10–90 %)")
    res["share_high"] = _fig_b64(fig, "share_high")

    # 3. heatmap
    hm = pd.DataFrame(k["heatmap_sector_hazard"]["ssp585_2050"]).T[HAZ]
    pf = pd.read_parquet(out / "asset_results.parquet")
    sl = pf.drop_duplicates("sector").set_index("sector")["sector_label"]
    hm.index = hm.index.map(sl)
    hm = hm.loc[hm.sum(axis=1).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    im = ax.imshow(hm.values, cmap=theme.risk_cmap(), vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(4), [theme.HAZARD_LABELS[h] for h in HAZ], fontsize=8.5)
    ax.set_yticks(range(len(hm)), hm.index, fontsize=8.5)
    for i in range(hm.shape[0]):
        for j in range(4):
            v = hm.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if v > 0.55 else theme.INK)
    ax.spines[:].set_visible(False)
    fig.colorbar(im, ax=ax, fraction=0.04).outline.set_visible(False)
    ax.set_title("Score moyen d'aléa pondéré par l'EAD · SSP5-8.5 · 2050")
    res["heatmap"] = _fig_b64(fig, "heatmap")

    # 4. sensitivity
    s = pd.DataFrame(k["sensitivity"])
    s = s[s.label != "β × 1.0"]
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    c = [(theme.SCENARIO_COLORS["ssp585"] if v >= 0 else theme.SCENARIO_COLORS["ssp245"]) for v in s.delta_pct]
    ax.barh(s.label, s.delta_pct, color=c, height=0.62)
    for yi, v in enumerate(s.delta_pct):
        ax.text(v + (2 if v >= 0 else -2), yi, f"{v:+.0f} %".replace("-", "−"), va="center",
                ha="left" if v >= 0 else "right", fontsize=7.5, color=theme.MUTED)
    ax.set_xlim(-65, 115)
    ax.axvline(0, color=theme.INK, lw=0.8)
    ax.invert_yaxis()
    ax.set_xlabel("Variation de l'EL additionnelle (%)")
    ax.set_title("Sensibilité · SSP5-8.5 · 2050")
    res["sensitivity"] = _fig_b64(fig, "sensitivity")

    # 5. sector mix
    pfb = pf[pf.period == "baseline"]
    mix = pfb.groupby("sector_label")["ead_tnd"].sum().sort_values() / 1e6
    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    ax.barh(mix.index, mix.values, color=theme.PETROL)
    ax.set_xlabel("EAD (M TND)")
    ax.set_title("Répartition sectorielle de l'EAD synthétique")
    res["sector_mix"] = _fig_b64(fig, "sector_mix")

    # 6. physrisk comparison
    pc = out / "physrisk_comparison.csv"
    if pc.exists():
        d = pd.read_csv(pc)
        fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0))
        axes[0].scatter(d.ours_hot35_2050, d.physrisk_tas35_2050, s=5, color=theme.HAZARD_COLORS["heat"], alpha=0.5)
        axes[0].set_xlabel("ClimaRisk : jours Tmax > 35 °C")
        axes[0].set_ylabel("physrisk : jours Tmoy > 35 °C")
        axes[0].set_title("Chaleur · SSP5-8.5 2050 (ACCESS-CM2)", fontsize=9)
        axes[1].scatter(d.ours_drought_2050, d.physrisk_spei_months_2050, s=5,
                        color=theme.HAZARD_COLORS["drought"], alpha=0.5)
        axes[1].set_xlabel("ClimaRisk : score sécheresse")
        axes[1].set_ylabel("physrisk : mois SPEI-12 < −1,5")
        axes[1].set_title("Sécheresse · SSP5-8.5 2050", fontsize=9)
        fig.tight_layout()
        res["physrisk"] = _fig_b64(fig, "physrisk")
    return res


TEMPLATE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<style>
@page { size: A4; margin: 18mm 17mm 18mm 17mm;
  @bottom-left { content: "ClimaRisk Tunisie · rapport méthodologique · portefeuille 100 % synthétique"; font: 7.5pt Inter, sans-serif; color: #5B6B70; }
  @bottom-right { content: counter(page) " / " counter(pages); font: 7.5pt Inter, sans-serif; color: #5B6B70; } }
@page :first { margin: 0; @bottom-left { content: none } @bottom-right { content: none } }
body { margin: 0; font-family: "Fira Sans", Inter, "DejaVu Sans", sans-serif; font-size: 9.6pt; line-height: 1.45; color: #0F2A33; }
h1 { font-size: 21pt; margin: 0 0 4mm 0; color: #0F2A33; letter-spacing: -.01em; }
h2 { font-size: 14.5pt; color: #0E5E6F; border-bottom: 2px solid #0E5E6F; padding-bottom: 1.5mm; margin: 0 0 4mm 0; page-break-before: always; }
h3 { font-size: 11pt; color: #0F2A33; margin: 5mm 0 2mm 0; }
p { margin: 0 0 2.6mm 0; text-align: justify; }
.cover { height: 296mm; page-break-after: always; overflow: hidden; background: linear-gradient(150deg, #0F2A33 0%, #0E5E6F 60%, #12808F 100%); color: #fff; padding: 60mm 22mm 0 22mm; box-sizing: border-box; position: relative; }
.cover .pill { display:inline-block; border:1px solid rgba(255,255,255,.4); border-radius: 99px; padding: 1mm 3.5mm; font-size: 8pt; letter-spacing: .08em; text-transform: uppercase; margin-right: 2mm; }
.cover h1 { color:#fff; font-size: 38pt; margin: 8mm 0 4mm 0; }
.cover .sub { font-size: 14pt; color: #D5E6EA; max-width: 150mm; line-height: 1.35; }
.cover .meta { position:absolute; bottom: 28mm; left: 22mm; right: 22mm; font-size: 9.5pt; color: #D5E6EA; border-top: 1px solid rgba(255,255,255,.3); padding-top: 4mm; }
.cover .sun { position:absolute; right: -40mm; top: -40mm; width: 160mm; height: 160mm; border-radius: 50%; background: radial-gradient(circle, rgba(247,164,86,.55) 0%, rgba(247,164,86,0) 70%); }
.kpis { display: flex; gap: 3mm; margin: 3mm 0 4mm 0; }
.kpi { flex: 1; border: 1px solid #E3E0D8; border-top: 3px solid #D97706; border-radius: 3mm; padding: 3mm; }
.kpi .l { font-size: 7.2pt; text-transform: uppercase; letter-spacing: .06em; color: #5B6B70; font-weight: 600; }
.kpi .v { font-family: "Fira Code", "JetBrains Mono", monospace; font-size: 15pt; font-weight: 600; margin-top: 1mm; }
.kpi .s { font-size: 7.5pt; color: #5B6B70; }
.note { background: #FFF8EB; border: 1px solid #F5D9A8; border-radius: 2.5mm; padding: 2.5mm 3.5mm; color: #6B4A12; font-size: 8.8pt; margin: 3mm 0; }
.box { background: #EEF5F6; border-left: 3px solid #0E5E6F; padding: 2.5mm 3.5mm; margin: 3mm 0; font-size: 9pt; }
table { width: 100%; border-collapse: collapse; font-size: 7.7pt; margin: 2mm 0 4mm 0; }
th { background: #0F2A33; color: #fff; text-align: left; padding: 1.6mm 2mm; font-weight: 600; }
td { border-bottom: 1px solid #E3E0D8; padding: 1.1mm 1.8mm; vertical-align: top; }
tr:nth-child(even) td { background: #FAF9F6; }
td.num, th.num { text-align: right; font-family: "JetBrains Mono", monospace; }
img { max-width: 100%; }
.two img { max-height: 95mm; width: auto; display: block; margin: 0 auto; }
.two { display: flex; gap: 4mm; align-items: flex-start; } .two > div { flex: 1; }
.formula { font-family: "JetBrains Mono", monospace; background: #F6F4EF; border: 1px solid #E3E0D8; border-radius: 2mm; padding: 3mm; font-size: 8.4pt; white-space: pre-wrap; }
.tag { display:inline-block; font-size: 7pt; padding: .4mm 2mm; border-radius: 99px; background: #E6F2F3; color: #0E5E6F; font-weight: 600; }
.tag.w { background: #FDEBD3; color: #8A4B07; }
.caption { font-size: 7.8pt; color: #5B6B70; margin-top: -1mm; margin-bottom: 3mm; }
ul { margin: 0 0 3mm 0; padding-left: 5mm; } li { margin-bottom: 1mm; }
</style></head><body>

<section class="cover"><div class="sun"></div>
<span class="pill">Rapport méthodologique</span><span class="pill">Risque physique</span><span class="pill">Version {{ version }}</span>
<h1>ClimaRisk Tunisie</h1>
<div class="sub">Risque climatique physique d'un portefeuille de crédits bancaires en Tunisie : scoring géospatial des aléas, scénarios CMIP6 / NGFS, agrégation au niveau du portefeuille.</div>
<div class="meta">Emna Saada — élève ingénieure en géoinformatique, MSE (Université de la Manouba)<br>
Généré le {{ today }} à partir de <code>outputs/kpis.json</code> · Portefeuille 100 % synthétique — résultats illustratifs, à calibrer sur des données bancaires réelles.</div>
</section>

<h2 style="page-break-before: avoid">1. Résumé exécutif</h2>
<p>Les banques tunisiennes financent des agriculteurs, des industriels, des promoteurs et des hôteliers dont les actifs sont exposés à la chaleur, à la sécheresse, aux inondations et aux incendies. ClimaRisk Tunisie est un démonstrateur open source qui relie chaque crédit d'un <b>portefeuille synthétique</b> de {{ n }} prêts à son exposition géographique à quatre aléas physiques, aujourd'hui et aux horizons 2030 et 2050, puis traduit cette exposition en ajustement illustratif de la probabilité de défaut (PD) et de la perte attendue (EL).</p>
<div class="kpis">
 <div class="kpi"><div class="l">EAD synthétique</div><div class="v">{{ ead_total }}</div><div class="s">{{ n }} crédits · {{ ngov }} gouvernorats</div></div>
 <div class="kpi"><div class="l">EAD en zone d'aléa élevé</div><div class="v">{{ sh_base }} → {{ sh_585 }}</div><div class="s">aujourd'hui → SSP5-8.5 2050 (bande {{ sh_585_band }})</div></div>
 <div class="kpi"><div class="l">EL additionnelle 2050</div><div class="v">{{ el_585 }}</div><div class="s">SSP5-8.5 · bande {{ el_585_band }} · dont {{ el_vs_today }} de plus qu'aujourd'hui</div></div>
 <div class="kpi"><div class="l">En points de base</div><div class="v">{{ bp_585 }}</div><div class="s">vs {{ bp_base }} aujourd'hui</div></div>
</div>
<ul>
<li><b>La chaleur progresse partout</b> : le nombre moyen de jours au-dessus de 35 °C aux emplacements des crédits passe de {{ hot_base }} à {{ hot_585 }} jours par an (SSP5-8.5, 2050 ; médiane de 5 modèles).</li>
<li><b>Le climat s'assèche</b> : la variation médiane des précipitations annuelles atteint {{ pr_585 }} % en 2050 sous SSP5-8.5 (par rapport à 2010-2014, mêmes modèles).</li>
<li><b>Les secteurs les plus touchés</b> en EL additionnelle (SSP5-8.5, 2050, en pb de leur EAD) : {{ top_sectors }}.</li>
<li><b>Les gouvernorats les plus touchés</b> (pb de l'EAD) : {{ top_govs }}.</li>
<li>L'<b>incertitude entre modèles</b> est substantielle (bandes 10–90 %) et les coefficients β, γ et la matrice de vulnérabilité sont des hypothèses : les montants servent à illustrer une méthode, pas à décrire une banque.</li>
</ul>
<div class="note"><b>Avertissement.</b> Le portefeuille est entièrement synthétique (loi organique n° 2004-63 relative à la protection des données personnelles). Aucun chiffre de ce rapport ne correspond à une banque tunisienne réelle.</div>

<h2>2. Contexte et origine du projet</h2>
<p>La supervision des risques climatiques se structure dans le monde depuis les principes du Comité de Bâle de juin 2022. En Tunisie, la Banque Centrale (BCT) a clôturé le 3 novembre 2026 un projet d'assistance technique financé par la KfW sur la gouvernance et la gestion des risques financiers liés au changement climatique, et lancé une feuille de route 2026-2030 organisée en quatre piliers, dont la gestion et la supervision des risques climatiques (source : presse tunisienne, à revérifier sur bct.gov.tn). Les banques manquent cependant d'un outil simple et reproductible reliant chaque crédit à son exposition géographique aux aléas.</p>
<p>Le projet se situe à l'intersection du risque bancaire et du changement climatique : il prolonge des compétences de géoinformatique (télédétection, Google Earth Engine, Python) vers la finance. En une phrase : <i>transformer des pixels satellites et climatiques en indicateurs de risque de crédit compréhensibles par une direction des risques</i>.</p>
<h3>Ce que fait l'outil</h3>
<ol>
<li>géolocalise chaque crédit d'un portefeuille synthétique réaliste (densité WorldPop, terres cultivées ESA WorldCover, littoral) ;</li>
<li>calcule un score d'aléa physique par actif (chaleur extrême, sécheresse, inondation, feux de forêt), aujourd'hui et sous SSP2-4.5 / SSP5-8.5 en 2030 et 2050 ;</li>
<li>combine aléa, exposition et vulnérabilité sectorielle, puis traduit le résultat en ΔPD, LGD et EL ;</li>
<li>agrège par secteur, gouvernorat et scénario, avec cartes, heatmap, top 20, tableau de bord et ce rapport.</li>
</ol>
<h3>Ce que l'outil ne fait pas</h3>
<p>Il ne traite ni le risque de transition, ni les effets de second ordre (chaînes de valeur, macroéconomie, assurance), et ne prétend à aucune conformité réglementaire : il prépare un dialogue entre direction des risques et superviseur.</p>

<h2>3. Cadre réglementaire et normatif</h2>
<p>Statut au 20 novembre 2026 ; chaque référence a été ouverte en ligne lorsque c'était possible (voir <code>docs/research_log.md</code>). Les mentions « sources secondaires » signalent un point à revérifier sur le texte officiel.</p>
<table><tr><th style="width:30%">Texte</th><th style="width:18%">Date</th><th>Exigence clé</th><th style="width:14%">Statut</th></tr>
{% for t in reg %}<tr><td><b>{{ t.title }}</b></td><td>{{ t.date }}</td><td>{{ t.requirement }}</td><td><span class="tag {{ 'w' if ('second' in t.status or 'revérif' in t.status or 'non' in t.status) else '' }}">{{ t.status }}</span></td></tr>{% endfor %}
</table>
<div class="box"><b>Point d'attention NGFS.</b> Le NGFS signale que la fonction de dommage PIB de la Phase V (variables « Kotz-Wenz », sorties NiGEM « physical/combined », scénarios REMIND-MAgPIE de dommages intégrés) repose sur Kotz et al. (2024), article rétracté de <i>Nature</i> (déclaration NGFS du 3 décembre 2025) ; les autres variables restent valides. ClimaRisk n'utilise donc pas la fonction de dommage PIB du NGFS : les scénarios NGFS servent de récit, les aléas proviennent directement des projections CMIP6.</div>

<h2>4. Données et méthode</h2>
<h3>4.1 Formule de base (logique GIEC : aléa × exposition × vulnérabilité)</h3>
<div class="formula">Score_h,s(i)  = normalisation 0–1 de l'indicateur d'aléa h à la localisation de l'actif i (bornes physiques fixes)
Composite_s(i) = Σ_h V[secteur(i), h] · Score_h,s(i) / Σ_h V[secteur(i), h]
PD_s(i)  = min(1, PD_base(i) · (1 + β_secteur · Composite_s(i)))
LGD_s(i) = min(1, LGD_base(i) · (1 + γ · Score_inondation,s(i)))     (garanties foncières et immobilières)
EL_s(i)  = PD_s(i) · LGD_s(i) · EAD(i)        EL additionnelle = EL_s − PD_base · LGD_base · EAD</div>
<p>PD_base est traitée comme « neutre climatiquement » (hypothèse illustrative) : l'ajustement existe donc aussi aujourd'hui, et l'évolution vers 2030 / 2050 se lit par différence.</p>
<h3>4.2 Indicateurs d'aléa (100 % données ouvertes et gratuites)</h3>
<table><tr><th>Aléa</th><th>Indicateur</th><th>Données</th><th>Normalisation</th></tr>
<tr><td>Chaleur extrême</td><td>Jours par an avec Tmax &gt; 35 °C</td><td>NASA NEX-GDDP-CMIP6, 0,25°, 5 modèles</td><td>0 → 120 jours</td></tr>
<tr><td>Sécheresse</td><td>Jours secs consécutifs (pr &lt; 1 mm) et variation des précipitations vs 2010-2014</td><td>NEX-GDDP-CMIP6 (pr)</td><td>CDD 30 → 200 j ; Δpr 0 → −30 %</td></tr>
<tr><td>Inondation</td><td>Profondeur d'eau, crue de période de retour 100 ans, max(fluviale, côtière)</td><td>WRI Aqueduct Floods v2 (≈1 km), via le Zarr public OS-Climate</td><td>0 → 2 m</td></tr>
<tr><td>Feux de forêt</td><td>Part de végétation combustible (rayon 2 km) × météo de feu (chaleur, sécheresse)</td><td>ESA WorldCover 2021 (≈320 m)</td><td>0 → 1</td></tr></table>
<p>Scénarios : référence 2010-2014 (run historique des mêmes modèles, ce qui neutralise une partie de leur biais), puis fenêtres de 3 ans centrées sur 2030 et 2050 sous SSP2-4.5 et SSP5-8.5. Pour l'inondation, Aqueduct fournit des projections CMIP5 (RCP4.5 / RCP8.5) utilisées comme proxy des SSP correspondants. Le modèle CMIP6 n° k est apparié au GCM Aqueduct n° k pour construire 5 réalisations, dont on tire médiane et intervalle 10–90 %.</p>
<h3>4.3 Portefeuille synthétique</h3>
<div class="two"><div>
<p>{{ n }} crédits répartis sur les {{ ngov }} gouvernorats ; dix secteurs inspirés de l'économie tunisienne (céréaliculture, oléiculture, agrumes, agroalimentaire, textile, tourisme côtier, immobilier résidentiel, BTP, chimie et phosphates, énergie). Les localisations suivent la population (WorldPop 2020), les terres cultivées (WorldCover) pour l'agriculture et une bande côtière de 3 km pour le tourisme ; aucun point n'est en mer (test automatisé). PD de base 1–8 % selon le secteur, LGD selon la garantie, maturité 1–20 ans, graine aléatoire fixe. Paramètres : <code>config/portfolio.yaml</code>.</p>
</div><div><img src="{{ charts.sector_mix }}"></div></div>

<h2>5. Cartes des aléas</h2>
<div class="two"><div><img src="{{ maps.heat }}"></div><div><img src="{{ maps.drought }}"></div></div>
<p class="caption">Médiane de 5 modèles CMIP6 (NEX-GDDP), 0,25°. La chaleur extrême progresse du sud vers le nord ; la sécheresse s'intensifie sur l'ensemble du territoire.</p>
<div class="two"><div><img src="{{ maps.flood }}"></div><div><img src="{{ maps.fire }}"></div></div>
<p class="caption">Gauche : profondeur d'eau de la crue centennale (WRI Aqueduct v2) — vallée de la Medjerda, Cap Bon et littoral. Droite : végétation combustible (ESA WorldCover) — forêts du Nord-Ouest (Kroumirie, Mogods) et dorsale.</p>

<h2>6. Résultats illustratifs</h2>
<img src="{{ charts.el_period }}">
<img src="{{ charts.share_high }}">
<table><tr><th>Période</th><th class="num">EAD en zone d'aléa élevé</th><th class="num">EL additionnelle (M TND)</th><th class="num">Bande 10–90 %</th><th class="num">pb de l'EAD</th></tr>
{% for r in period_rows %}<tr><td>{{ r.label }}</td><td class="num">{{ r.share }}</td><td class="num">{{ r.el }}</td><td class="num">{{ r.band }}</td><td class="num">{{ r.bp }}</td></tr>{% endfor %}
</table>

<h2>7. Analyse par secteur et par gouvernorat</h2>
<div class="two"><div><img src="{{ charts.heatmap }}"></div><div><img src="{{ maps.el_gov }}"></div></div>
<h3>Top 8 des expositions — EL additionnelle (SSP5-8.5, 2050)</h3>
<table><tr><th>Crédit</th><th>Secteur</th><th>Gouvernorat</th><th class="num">EAD (TND)</th><th class="num">Score</th><th class="num">EL add. (TND)</th></tr>
{% for r in top %}<tr><td>{{ r.loan_id }}</td><td>{{ r.sector_label }}</td><td>{{ r.governorate }}</td><td class="num">{{ "{:,.0f}".format(r.ead_tnd).replace(",", " ") }}</td><td class="num">{{ "%.2f"|format(r.composite) }}</td><td class="num">{{ "{:,.0f}".format(r.el_add).replace(",", " ") }}</td></tr>{% endfor %}
</table>

<h2>8. Sensibilité et validation</h2>
<div class="two"><div><img src="{{ charts.sensitivity }}"></div><div>
<p>L'EL additionnelle est proportionnelle à β : doubler β double l'ajustement de PD. Les poids de la matrice de vulnérabilité ont un effet plus modéré, car le score composite est une moyenne pondérée normalisée (une hausse de tous les poids d'un aléa déplace surtout la répartition entre aléas).</p>
<p>À titre de comparaison, la dispersion entre modèles climatiques (bande 10–90 %) va de {{ unc.model_lo }} à {{ unc.model_hi }} autour de la médiane, alors que faire varier β de ×0,5 à ×2 déplace l'EL additionnelle de {{ unc.beta_lo }} à {{ unc.beta_hi }}. L'hypothèse de crédit domine donc l'incertitude : c'est la calibration de β sur des défauts observés après des épisodes de sécheresse ou d'inondation qui la réduirait le plus.</p></div></div>
<h3>Comparaison avec OS-Climate physrisk</h3>
{% if charts.physrisk %}<img src="{{ charts.physrisk }}">{% endif %}
<p>Aux mêmes {{ n }} localisations, les indicateurs de chaleur de physrisk (jours de température <i>moyenne</i> journalière &gt; 35 °C, modèle ACCESS-CM2) sont très corrélés aux nôtres en rang (Spearman {{ pr.heat_spearman_base }} aujourd'hui, {{ pr.heat_spearman_2050 }} en 2050), mais beaucoup plus faibles en niveau ({{ pr.heat_mean_physrisk_2050 }} contre {{ pr.heat_mean_ours_2050 }} jours en 2050), car une moyenne journalière &gt; 35 °C est bien plus rare qu'un maximum &gt; 35 °C. Pour la sécheresse, les deux approches indiquent une aggravation pour {{ pr.worsen_ours }} des actifs (ClimaRisk) et {{ pr.worsen_physrisk }} (physrisk), mais leurs classements spatiaux divergent (Spearman {{ pr.drought_spearman_2050 }}) : l'indice SPEI de physrisk est <i>standardisé</i> par rapport au climat local et fait ressortir le nord, alors que notre indicateur (jours secs consécutifs) pénalise d'abord les zones arides du sud. Le choix de l'indicateur est donc structurant et doit être relié à la vulnérabilité réelle de chaque activité.</p>
<h3>Cohérence spatiale</h3>
<p>Les zones à forte profondeur de crue (vallée de la Medjerda, Cap Bon, plaines littorales de Nabeul) recoupent qualitativement les inondations historiques connues (Nabeul, septembre 2018 ; crues de la Medjerda). Une validation quantitative contre les surfaces brûlées MODIS (MCD64A1) et les précipitations CHIRPS est prévue via Earth Engine (niveau Community gratuit).</p>

<h2>9. Limites</h2>
<ul>
<li><b>Portefeuille synthétique</b> : répartitions sectorielles, PD et LGD sont des hypothèses illustratives, pas des statistiques BCT.</li>
<li><b>Résolution</b> : 0,25° (≈ 25 km) pour le climat — un actif hérite du climat de sa maille ; ≈ 1 km pour l'inondation, insuffisant pour le ruissellement urbain et les oueds secondaires.</li>
<li><b>Modèles climatiques</b> : 5 modèles CMIP6 et des fenêtres de 3 ans par horizon ; la variabilité interannuelle pèse lourd à l'horizon 2030 (par exemple une anomalie positive de précipitations en SSP2-4.5 2030). Une version étendue utiliserait 20 ans par horizon et davantage de modèles.</li>
<li><b>Aqueduct</b> repose sur des projections CMIP5 et une hydrologie globale ; les ouvrages de protection locaux ne sont pas représentés. La référence fluviale est forcée par les observations (WATCH) et les projections par des GCM : la comparaison aujourd'hui / futur n'est donc pas homogène (la baisse apparente du score d'inondation en 2050 en est probablement un artefact). L'appariement modèle CMIP6 n° k ↔ GCM Aqueduct n° k est arbitraire : la bande d'incertitude est un pseudo-ensemble.</li>
<li><b>Feux de forêt</b> : indicateur de combustible × météo, non calibré sur les surfaces brûlées observées.</li>
<li><b>Traduction crédit</b> : β, γ et la matrice de vulnérabilité ne sont pas estimés ; PD_base considérée climatiquement neutre.</li>
<li><b>Fonction de dommage NGFS</b> : fonction de dommage PIB non utilisée (Kotz et al., 2024, rétracté ; déclaration NGFS du 3 décembre 2025).</li>
<li><b>Périmètre</b> : risque physique uniquement ; pas de risque de transition ni d'effets de second ordre.</li>
</ul>
<h3>Usages possibles en Pilier 2 / ICAAP</h3>
<p>Dans l'esprit du guide BCE de 2020 et des orientations ABE sur les risques ESG, l'outil peut servir à : (i) une cartographie de matérialité des risques physiques par secteur et région ; (ii) des analyses de scénarios exploratoires pour l'ICAAP ; (iii) le suivi d'indicateurs d'exposition pour le comité des risques ; (iv) la préparation des futures attentes de la BCT au titre de sa feuille de route 2026-2030.</p>

<h2>10. Matrice de conformité</h2>
<table><tr><th style="width:28%">Texte</th><th>Modules ClimaRisk concernés</th><th style="width:15%">Couverture</th></tr>
{% for t in reg %}<tr><td><b>{{ t.title }}</b><br><span style="color:#5B6B70">{{ t.url }}</span></td><td><ul style="margin:0">{% for m in t.modules %}<li>{{ m }}</li>{% endfor %}</ul></td><td>{{ t.coverage }}</td></tr>{% endfor %}
</table>

<h2>Annexe A — Hypothèses</h2>
<table><tr><th>Secteur</th><th class="num">Chaleur</th><th class="num">Sécheresse</th><th class="num">Inondation</th><th class="num">Feux</th><th class="num">β</th></tr>
{% for s, v in vuln.items() %}<tr><td>{{ sector_labels[s] }}</td><td class="num">{{ v.heat }}</td><td class="num">{{ v.drought }}</td><td class="num">{{ v.flood }}</td><td class="num">{{ v.fire }}</td><td class="num">{{ beta.get(s, beta.default) }}</td></tr>{% endfor %}
</table>
<p>γ (LGD inondation) = {{ gamma }} · zone d'aléa élevé : un aléa matériel pour le secteur (vulnérabilité ≥ {{ mat }}) avec un score ≥ {{ thr }}. Toutes les valeurs sont des <b>hypothèses illustratives</b> documentées dans <code>config/assumptions.yaml</code>.</p>
<h3>Annexe B — Sources de données et licences</h3>
<table><tr><th>Jeu de données</th><th>Licence</th></tr>
<tr><td>NASA NEX-GDDP-CMIP6 (AWS Open Data)</td><td>CC0 (licence globale depuis septembre 2022)</td></tr>
<tr><td>WRI Aqueduct Floods v2 (via OS-Climate)</td><td>CC BY 4.0</td></tr>
<tr><td>ESA WorldCover 2021</td><td>CC BY 4.0</td></tr>
<tr><td>WorldPop 2020</td><td>CC BY 4.0</td></tr>
<tr><td>geoBoundaries (OpenStreetMap)</td><td>ODbL 1.0</td></tr>
<tr><td>Natural Earth</td><td>Domaine public</td></tr>
<tr><td>Voix Piper fr_FR-siwis-medium (vidéo)</td><td>Données SIWIS et Hi-Fi TTS, CC BY 4.0 ; logiciel piper-tts GPL-3.0 utilisé en ligne de commande</td></tr></table>
<p>Code sous licence MIT. Reproduction : <code>make install &amp;&amp; make data &amp;&amp; make demo</code>.</p>
</body></html>"""


def build_report(out_pdf: Path | None = None) -> Path:
    from jinja2 import Template
    from weasyprint import HTML

    root = project_root()
    out = root / "outputs"
    out_pdf = out_pdf or root / "docs/report.pdf"
    k = json.loads((out / "kpis.json").read_text(encoding="utf-8"))
    reg = yaml.safe_load((root / "config/regulatory_matrix.yaml").read_text(encoding="utf-8"))["texts"]
    a = yaml.safe_load((root / "config/assumptions.yaml").read_text(encoding="utf-8"))
    pr = json.loads((out / "physrisk_comparison.json").read_text()) if (out / "physrisk_comparison.json").exists() else {}
    worsen = {"worsen_ours": f"{100 * pr.get('share_assets_drought_worsening_ours', float('nan')):.0f} %",
              "worsen_physrisk": f"{100 * pr.get('share_assets_drought_worsening_physrisk', float('nan')):.0f} %"}
    pr = {kk: (f"{v:.2f}" if isinstance(v, float) and abs(v) < 10 else (f"{v:.0f}" if isinstance(v, float) else v))
          for kk, v in pr.items()} | worsen
    sens = pd.DataFrame(k["sensitivity"])
    beta = sens[sens.label.str.startswith("β")]
    e = k["periods"]["ssp585_2050"]["el_add_tnd"]

    def sp(x):
        return f"{x:+.0f} %".replace("-", "−")

    unc = {"model_lo": sp(100 * (e["p10"] / e["med"] - 1)), "model_hi": sp(100 * (e["p90"] / e["med"] - 1)),
           "beta_lo": sp(beta.delta_pct.min()), "beta_hi": sp(beta.delta_pct.max())}
    maps_dir = out / "maps"
    maps = {n: _img_b64(maps_dir / f"map_{f}.png") for n, f in
            [("heat", "heat"), ("drought", "drought"), ("flood", "flood"), ("fire", "fire"),
             ("portfolio", "portfolio"), ("el_gov", "el_governorate")]}
    P = k["periods"]
    labels = k["meta"]["period_labels"]

    def pct(x):
        return f"{100 * x:.1f} %".replace(".", ",")

    def mtnd(x):
        return f"{x / 1e6:.1f} M TND".replace(".", ",")

    sec = k["by_sector"]["ssp585_2050"]
    assets = pd.read_parquet(out / "asset_results.parquet")
    sl = assets.drop_duplicates("sector").set_index("sector")["sector_label"].to_dict()
    top_s = sorted(sec.items(), key=lambda kv: -kv[1]["el_add_bp_med"])[:3]
    gov = k["by_governorate"]["ssp585_2050"]
    top_g = sorted(gov.items(), key=lambda kv: -kv[1]["el_add_bp_med"])[:3]
    ctx = dict(
        version=k["meta"]["version"], today=date.today().strftime("%d/%m/%Y"),
        n=f"{k['meta']['n_loans']:,}".replace(",", " "), ngov=k["meta"]["n_governorates"],
        ead_total=f"{k['meta']['total_ead_tnd'] / 1e9:.1f} Md TND".replace(".", ","),
        sh_base=pct(P["baseline"]["share_ead_high"]["med"]), sh_585=pct(P["ssp585_2050"]["share_ead_high"]["med"]),
        sh_585_band=f"{pct(P['ssp585_2050']['share_ead_high']['p10'])} – {pct(P['ssp585_2050']['share_ead_high']['p90'])}",
        el_585=mtnd(P["ssp585_2050"]["el_add_tnd"]["med"]),
        el_vs_today=mtnd(P["ssp585_2050"]["el_add_vs_today_tnd"]["med"]),
        el_585_band=f"{mtnd(P['ssp585_2050']['el_add_tnd']['p10'])} – {mtnd(P['ssp585_2050']['el_add_tnd']['p90'])}",
        bp_585=f"{P['ssp585_2050']['el_add_bp']['med']:.1f} pb".replace(".", ","),
        bp_base=f"{P['baseline']['el_add_bp']['med']:.1f} pb".replace(".", ","),
        hot_base=f"{k['hazard_means']['baseline']['hot35_days']:.0f}",
        hot_585=f"{k['hazard_means']['ssp585_2050']['hot35_days']:.0f}",
        pr_585=f"{k['hazard_means']['ssp585_2050']['prchange_pct']:+.0f}".replace("-", "−"),
        top_sectors=", ".join(f"{sl[s]} ({v['el_add_bp_med']:.0f} pb)" for s, v in top_s),
        top_govs=", ".join(f"{g} ({v['el_add_bp_med']:.0f} pb)" for g, v in top_g),
        reg=reg, charts=charts(k, out), maps=maps, pr=pr,
        period_rows=[{"label": labels[p], "share": pct(P[p]["share_ead_high"]["med"]),
                      "el": f"{P[p]['el_add_tnd']['med'] / 1e6:.2f}".replace(".", ","),
                      "band": f"{P[p]['el_add_tnd']['p10'] / 1e6:.2f} – {P[p]['el_add_tnd']['p90'] / 1e6:.2f}".replace(".", ","),
                      "bp": f"{P[p]['el_add_bp']['med']:.1f}".replace(".", ",")} for p in theme.PERIOD_ORDER],
        top=k["top20_ssp585_2050"][:8], vuln=a["vulnerability"], beta=a["beta"], gamma=a["gamma_lgd_flood"],
        unc=unc, mat=a["materiality_min_vulnerability"], thr=a["high_hazard_threshold"], sector_labels=sl,
    )
    html = Template(TEMPLATE).render(**ctx)
    (out / "report.html").write_text(html, encoding="utf-8")
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html, base_url=str(root)).write_pdf(out_pdf)
    return out_pdf


if __name__ == "__main__":
    print(build_report())
