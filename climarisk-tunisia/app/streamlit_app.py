"""ClimaRisk Tunisie — Streamlit dashboard.

Run:  streamlit run app/streamlit_app.py   (after `make run`)
All figures come from outputs/ produced by the pipeline. Portfolio is 100 % synthetic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from climarisk import theme

OUT = ROOT / "outputs"
HAZ = ["heat", "drought", "flood", "fire"]
T = theme

st.set_page_config(page_title="ClimaRisk Tunisie", layout="wide",
                   initial_sidebar_state="expanded")

# --------------------------------------------------------------------------- style
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Fira+Sans:wght@300;400;500;600;700&display=swap');
:root {{ --ink:{T.INK}; --petrol:{T.PETROL}; --teal:{T.TEAL}; --sand:{T.SAND}; --muted:{T.MUTED};
        --border:{T.BORDER}; --amber:{T.AMBER}; }}
html, body, [class*="css"], .stMarkdown, .stText, p, li, label {{ font-family: 'Fira Sans', sans-serif; }}
.stApp {{ background: var(--sand); }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1400px; }}
h1, h2, h3, h4 {{ font-family: 'Fira Sans', sans-serif; color: var(--ink); letter-spacing: -0.01em; }}
section[data-testid="stSidebar"] {{ background: {T.INK}; }}
section[data-testid="stSidebar"] * {{ color: #E8EEF0 !important; }}
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] > div {{ background:#163A45; border-color:#2A5764; }}
.hero {{ background: linear-gradient(120deg, {T.INK} 0%, {T.PETROL} 55%, {T.TEAL} 100%); color: #fff;
        border-radius: 18px; padding: 26px 30px; margin-bottom: 18px; position: relative; overflow: hidden; }}
.hero:after {{ content:""; position:absolute; right:-60px; top:-60px; width:260px; height:260px; border-radius:50%;
        background: radial-gradient(circle, rgba(247,164,86,.55) 0%, rgba(247,164,86,0) 70%); }}
.hero h1 {{ color:#fff; font-size: 2.0rem; margin: 0 0 4px 0; font-weight: 700; }}
.hero p {{ color: #D5E6EA; margin: 0; font-size: 1.0rem; max-width: 820px; }}
.pill {{ display:inline-block; font-size:.72rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase;
        background: rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.25); padding:3px 10px;
        border-radius:999px; margin-right:6px; color:#fff; }}
.kpi {{ background: #fff; border: 1px solid var(--border); border-radius: 14px; padding: 16px 18px;
        box-shadow: 0 1px 2px rgba(15,42,51,.04); height: 100%; }}
.kpi .lab {{ color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; font-weight:600; }}
.kpi .val {{ font-family: 'Fira Code', monospace; font-size: 1.75rem; font-weight: 600; color: var(--ink);
        margin-top: 4px; font-variant-numeric: tabular-nums; }}
.kpi .sub {{ color: var(--muted); font-size: .82rem; margin-top: 2px; }}
.kpi.accent {{ border-top: 4px solid var(--amber); }}
.kpi.teal {{ border-top: 4px solid var(--teal); }}
.kpi.red {{ border-top: 4px solid #B8323B; }}
.kpi.ink {{ border-top: 4px solid var(--ink); }}
.note {{ background:#FFF8EB; border:1px solid #F5D9A8; border-radius:12px; padding:10px 14px; color:#6B4A12;
        font-size:.86rem; }}
.card {{ background:#fff; border:1px solid var(--border); border-radius:14px; padding:16px 18px; margin-bottom:12px; }}
.card h4 {{ margin:0 0 6px 0; font-size:1rem; }}
.tag {{ display:inline-block; font-size:.72rem; padding:2px 8px; border-radius:999px; background:#E6F2F3;
        color:{T.PETROL}; font-weight:600; margin: 2px 4px 2px 0; }}
.tag.warn {{ background:#FDEBD3; color:#8A4B07; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; background:#fff; padding:6px; border-radius:12px; border:1px solid var(--border); }}
.stTabs [data-baseweb="tab"] {{ height: 40px; border-radius: 8px; padding: 0 16px; font-weight:500; }}
.stTabs [aria-selected="true"] {{ background: {T.PETROL}; color: #fff !important; }}
.stTabs [aria-selected="true"] p {{ color:#fff !important; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display:none; }}
div[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- data
@st.cache_data
def load():
    if not (OUT / "kpis.json").exists():
        return None
    k = json.loads((OUT / "kpis.json").read_text(encoding="utf-8"))
    assets = pd.read_parquet(OUT / "asset_results.parquet")
    by_sector = pd.read_csv(OUT / "by_sector.csv")
    by_gov = pd.read_csv(OUT / "by_governorate.csv")
    by_period = pd.read_csv(OUT / "by_period.csv")
    sens = pd.read_csv(OUT / "sensitivity.csv")
    govs = json.loads((ROOT / "data/raw/tun_adm1.geojson").read_text(encoding="utf-8"))
    reg = yaml.safe_load((ROOT / "config/regulatory_matrix.yaml").read_text(encoding="utf-8"))
    assum = yaml.safe_load((ROOT / "config/assumptions.yaml").read_text(encoding="utf-8"))
    return k, assets, by_sector, by_gov, by_period, sens, govs, reg, assum


data = load()
if data is None:
    st.error("Aucune sortie trouvée. Lancez d'abord `make run` (pipeline) pour produire outputs/kpis.json.")
    st.stop()
K, A, BS, BG, BP, SENS, GOVS, REG, ASSUM = data
LABELS = K["meta"]["period_labels"]
SECTOR_LABELS = A.drop_duplicates("sector").set_index("sector")["sector_label"].to_dict()


def fmt_tnd(x: float) -> str:
    if abs(x) >= 1e9:
        return f"{x/1e9:,.2f} Md".replace(",", " ")
    if abs(x) >= 1e6:
        return f"{x/1e6:,.1f} M".replace(",", " ")
    if abs(x) >= 1e3:
        return f"{x/1e3:,.0f} k".replace(",", " ")
    return f"{x:,.0f}"


def plot_style(fig, h=380):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="white",
                      plot_bgcolor="white", font=dict(family="Fira Sans, sans-serif", color=T.INK, size=13),
                      title_font=dict(size=15), hoverlabel=dict(font_family="Fira Sans"),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_xaxes(gridcolor="#F0EEE8", zeroline=False)
    fig.update_yaxes(gridcolor="#F0EEE8", zeroline=False)
    return fig


# --------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### ClimaRisk Tunisie")
    st.caption("Risque climatique physique d'un portefeuille de crédits — démonstrateur géoinformatique")
    scen = st.radio("Scénario", ["ssp245", "ssp585"], horizontal=True,
                    format_func=lambda s: {"ssp245": "SSP2-4.5", "ssp585": "SSP5-8.5"}[s])
    hor = st.select_slider("Horizon", ["Aujourd'hui", "2030", "2050"], value="2050")
    period = "baseline" if hor == "Aujourd'hui" else f"{scen}_{hor}"
    sectors = st.multiselect("Secteurs", list(SECTOR_LABELS), default=list(SECTOR_LABELS),
                             format_func=SECTOR_LABELS.get)
    st.markdown("---")
    st.markdown(f"**Période affichée :** {LABELS[period]}")
    st.caption("Médiane de 5 modèles CMIP6 (NEX-GDDP) ; bande 10–90 % entre modèles.")
    st.markdown("---")
    st.caption("Portefeuille 100 % synthétique (loi organique n° 2004-63). Chiffres illustratifs, "
               "à calibrer sur des données bancaires réelles.")

sel = A[(A.period == period) & (A.sector.isin(sectors))]
P = K["periods"][period]

# --------------------------------------------------------------------------- header
st.markdown(f"""
<div class="hero">
  <span class="pill">Risque physique</span><span class="pill">CMIP6 · NGFS</span><span class="pill">Portefeuille synthétique</span>
  <h1>ClimaRisk Tunisie</h1>
  <p>Des pixels satellites et climatiques aux indicateurs de risque de crédit : exposition de
  {K['meta']['n_loans']:,} crédits répartis sur les {K['meta']['n_governorates']} gouvernorats à la chaleur extrême,
  la sécheresse, l'inondation et les feux de forêt — aujourd'hui, en 2030 et en 2050.</p>
</div>
""".replace(",", " "), unsafe_allow_html=True)

tabs = st.tabs(["Accueil", "Carte", "Analyse", "Fiche crédit", "Reporting", "Réglementation", "Méthode & limites"])

# =========================================================================== Accueil
with tabs[0]:
    c = st.columns(4)
    el = P["el_add_tnd"]
    sh = P["share_ead_high"]
    cards = [
        ("ink", "EAD totale", fmt_tnd(K["meta"]["total_ead_tnd"]) + " TND", f"{K['meta']['n_loans']} crédits synthétiques"),
        ("accent", "EAD en zone d'aléa élevé", f"{100*sh['med']:.1f} %",
         f"bande {100*sh['p10']:.1f} – {100*sh['p90']:.1f} % · un aléa matériel ≥ {ASSUM['high_hazard_threshold']}"),
        ("red", "EL climatique additionnelle", fmt_tnd(el["med"]) + " TND",
         f"bande {fmt_tnd(el['p10'])} – {fmt_tnd(el['p90'])} TND"),
        ("teal", "Soit, en points de base", f"{P['el_add_bp']['med']:.1f} pb",
         f"de l'EAD · EL de base {fmt_tnd(K['meta']['el_base_tnd'])} TND"),
    ]
    for col, (cls, lab, val, sub) in zip(c, cards):
        col.markdown(f'<div class="kpi {cls}"><div class="lab">{lab}</div><div class="val">{val}</div>'
                     f'<div class="sub">{sub}</div></div>', unsafe_allow_html=True)
    st.write("")
    left, right = st.columns([1.25, 1])
    with left:
        order = theme.PERIOD_ORDER
        bp = BP.set_index("period").loc[order].reset_index()
        colors = [theme.SCENARIO_COLORS[p.split("_")[0]] for p in bp.period]
        fig = go.Figure(go.Bar(
            x=[LABELS[p] for p in bp.period], y=bp.el_add_med / 1e6, marker_color=colors,
            error_y=dict(type="data", symmetric=False, array=(bp.el_add_p90 - bp.el_add_med) / 1e6,
                         arrayminus=(bp.el_add_med - bp.el_add_p10) / 1e6, color=T.INK, thickness=1.2, width=6),
            hovertemplate="%{x}<br>EL additionnelle : %{y:.2f} M TND<extra></extra>"))
        fig.update_yaxes(title="M TND")
        st.plotly_chart(plot_style(fig.update_layout(title="EL climatique additionnelle par scénario (médiane, 10–90 %)")),
                        use_container_width=True)
    with right:
        s = BS[BS.period == period].copy()
        s["label"] = s.sector.map(SECTOR_LABELS)
        s = s.sort_values("el_add_med")
        fig = go.Figure(go.Bar(y=s.label, x=s.el_add_med / 1e6, orientation="h",
                               marker=dict(color=s.el_add_bp_med, colorscale=theme.RISK_SCALE,
                                           colorbar=dict(title="pb", thickness=10)),
                               hovertemplate="%{y}<br>%{x:.2f} M TND<extra></extra>"))
        fig.update_xaxes(title="M TND")
        st.plotly_chart(plot_style(fig.update_layout(title=f"EL additionnelle par secteur · {LABELS[period]}")),
                        use_container_width=True)
    st.markdown('<div class="note"><b>Lecture.</b> L\'EL additionnelle compare la perte attendue avec PD et LGD '
                'ajustées du score d\'aléa à la perte attendue de base. Le portefeuille est synthétique : ces montants '
                'illustrent la méthode, ils ne décrivent aucune banque tunisienne.</div>', unsafe_allow_html=True)

# =========================================================================== Carte
with tabs[1]:
    mcol, ccol = st.columns([3, 1])
    with ccol:
        layer_choice = st.radio("Colorer les crédits par", ["composite", *HAZ],
                                format_func=lambda h: "Score composite" if h == "composite" else theme.HAZARD_LABELS[h])
        show_gov = st.toggle("Gouvernorats colorés par EL additionnelle (pb)", value=True)
        size_by_ead = st.toggle("Taille proportionnelle à l'EAD", value=True)
        st.caption("Survolez un point pour voir le crédit. Fond de carte © CARTO / © OpenStreetMap.")
    pts = sel.copy()
    vals = pts[layer_choice].clip(0, 1).to_numpy()
    ramp = np.array([[int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)] for c in theme.RISK_SCALE])
    idx = vals * (len(ramp) - 1)
    lo = np.floor(idx).astype(int)
    hi = np.minimum(lo + 1, len(ramp) - 1)
    f = (idx - lo)[:, None]
    rgb = (ramp[lo] * (1 - f) + ramp[hi] * f).astype(int)
    pts["r"], pts["g"], pts["b"] = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    pts["radius"] = (600 + 4500 * np.sqrt(pts.ead_tnd / pts.ead_tnd.max())) if size_by_ead else 1200
    pts["score_txt"] = (pts[layer_choice] * 100).round(0).astype(int).astype(str)
    pts["ead_txt"] = pts.ead_tnd.map(fmt_tnd)
    layers = []
    if show_gov:
        g = BG[BG.period == period].set_index("governorate")["el_add_bp_med"]
        vmax = max(g.max(), 1e-9)
        gj = json.loads(json.dumps(GOVS))
        for feat in gj["features"]:
            name = feat["properties"]["shapeName"]
            v = float(g.get(name, 0)) / vmax
            j = min(int(v * (len(ramp) - 1)), len(ramp) - 1)
            feat["properties"]["fill"] = [*map(int, ramp[j]), 110]
            feat["properties"]["el_bp"] = f"{g.get(name, 0):.1f}"
        layers.append(pdk.Layer("GeoJsonLayer", gj, stroked=True, filled=True, get_fill_color="properties.fill",
                                get_line_color=[255, 255, 255, 220], line_width_min_pixels=1, pickable=False))
    layers.append(pdk.Layer("ScatterplotLayer", pts, get_position="[lon, lat]", get_radius="radius",
                            get_fill_color="[r, g, b, 225]", get_line_color=[15, 42, 51, 160],
                            line_width_min_pixels=0.5, stroked=True, pickable=True))
    with mcol:
        st.pydeck_chart(pdk.Deck(
            layers=layers, map_style="light",
            initial_view_state=pdk.ViewState(latitude=34.0, longitude=9.6, zoom=5.6, pitch=0),
            tooltip={"html": "<b>{loan_id}</b> · {sector_label}<br/>{governorate}<br/>EAD {ead_txt} TND<br/>"
                             "Score : {score_txt}/100", "style": {"fontFamily": "Fira Sans", "fontSize": "12px"}}),
            use_container_width=True, height=640)

# =========================================================================== Analyse
with tabs[2]:
    hm = pd.DataFrame(K["heatmap_sector_hazard"][period]).T[HAZ]
    hm.index = hm.index.map(SECTOR_LABELS)
    hm.columns = [theme.HAZARD_LABELS[h] for h in HAZ]
    l, r = st.columns([1.1, 1])
    with l:
        fig = px.imshow(hm.round(2), text_auto=".2f", aspect="auto", zmin=0, zmax=1,
                        color_continuous_scale=theme.RISK_SCALE)
        fig.update_traces(hovertemplate="%{y} · %{x}<br>Score moyen pondéré EAD : %{z:.2f}<extra></extra>")
        st.plotly_chart(plot_style(fig.update_layout(title=f"Heatmap secteur × aléa · {LABELS[period]}",
                                                     coloraxis_colorbar=dict(title="score", thickness=10)), 460),
                        use_container_width=True)
    with r:
        g = BG[BG.period == period].sort_values("el_add_bp_med", ascending=True).tail(24)
        fig = go.Figure(go.Bar(y=g.governorate, x=g.el_add_bp_med, orientation="h",
                               error_x=dict(type="data", symmetric=False, array=g.el_add_bp_p90 - g.el_add_bp_med,
                                            arrayminus=g.el_add_bp_med - g.el_add_bp_p10, color="#9AA7AA", thickness=1),
                               marker_color=T.PETROL, hovertemplate="%{y} : %{x:.1f} pb<extra></extra>"))
        st.plotly_chart(plot_style(fig.update_layout(title="EL additionnelle par gouvernorat (pb de l'EAD)"), 460),
                        use_container_width=True)
    l, r = st.columns(2)
    with l:
        rows = []
        for sc in ("ssp245", "ssp585"):
            for p in ("baseline", f"{sc}_2030", f"{sc}_2050"):
                row = BP[BP.period == p].iloc[0]
                rows.append({"scénario": {"ssp245": "SSP2-4.5", "ssp585": "SSP5-8.5"}[sc],
                             "horizon": {"baseline": "Aujourd'hui"}.get(p, p[-4:]),
                             "med": row.el_add_med / 1e6, "p10": row.el_add_p10 / 1e6, "p90": row.el_add_p90 / 1e6})
        d = pd.DataFrame(rows)
        fig = go.Figure()
        for sc, col in (("SSP2-4.5", T.TEAL), ("SSP5-8.5", "#B8323B")):
            q = d[d["scénario"] == sc]
            fig.add_trace(go.Scatter(x=list(q.horizon) + list(q.horizon[::-1]), y=list(q.p90) + list(q.p10[::-1]),
                                     fill="toself", fillcolor=col, opacity=0.15, line=dict(width=0),
                                     hoverinfo="skip", showlegend=False))
            fig.add_trace(go.Scatter(x=q.horizon, y=q.med, mode="lines+markers", name=sc,
                                     line=dict(color=col, width=3), marker=dict(size=9)))
        fig.update_yaxes(title="M TND")
        st.plotly_chart(plot_style(fig.update_layout(title="Aujourd'hui → 2030 → 2050 (médiane et bande 10–90 %)")),
                        use_container_width=True)
    with r:
        s = SENS.copy()
        fig = go.Figure(go.Bar(y=s.label, x=s.delta_pct, orientation="h",
                               marker_color=np.where(s.delta_pct >= 0, "#B8323B", T.TEAL),
                               hovertemplate="%{y} : %{x:+.1f} %<extra></extra>"))
        fig.update_xaxes(title="variation de l'EL additionnelle (%) · SSP5-8.5 2050")
        st.plotly_chart(plot_style(fig.update_layout(title="Analyse de sensibilité (β et poids des aléas)")),
                        use_container_width=True)
    st.markdown("##### Top 20 des expositions — EL additionnelle")
    top = sel.nlargest(20, "el_add")[["loan_id", "sector_label", "governorate", "ead_tnd", "composite",
                                      *HAZ, "pd_base", "pd_climate", "el_add"]]
    st.dataframe(top.rename(columns={"sector_label": "secteur", "ead_tnd": "EAD (TND)", "el_add": "EL add. (TND)",
                                     "pd_base": "PD base", "pd_climate": "PD climat"}),
                 hide_index=True, use_container_width=True,
                 column_config={"composite": st.column_config.ProgressColumn("score", min_value=0, max_value=1, format="%.2f"),
                                "EAD (TND)": st.column_config.NumberColumn(format="%.0f"),
                                "EL add. (TND)": st.column_config.NumberColumn(format="%.0f"),
                                "PD base": st.column_config.NumberColumn(format="%.3f"),
                                "PD climat": st.column_config.NumberColumn(format="%.3f")})

# =========================================================================== Fiche crédit
with tabs[3]:
    default = sel.nlargest(1, "el_add").loan_id.iloc[0] if len(sel) else A.loan_id.iloc[0]
    ids = sorted(A.loan_id.unique())
    lid = st.selectbox("Crédit", ids, index=ids.index(default))
    one = A[A.loan_id == lid].set_index("period").loc[theme.PERIOD_ORDER]
    info = one.iloc[0]
    c = st.columns(4)
    for col, (lab, val) in zip(c, [("Secteur", info.sector_label), ("Gouvernorat", info.governorate),
                                   ("EAD", fmt_tnd(info.ead_tnd) + " TND"), ("Garantie · maturité",
                                   f"{info.collateral} · {info.maturity_years} ans")]):
        col.markdown(f'<div class="kpi teal"><div class="lab">{lab}</div><div class="val" style="font-size:1.2rem">{val}</div></div>',
                     unsafe_allow_html=True)
    st.write("")
    l, r = st.columns([1.2, 1])
    with l:
        fig = go.Figure()
        for h in HAZ:
            fig.add_trace(go.Bar(name=theme.HAZARD_LABELS[h], x=[LABELS[p] for p in one.index], y=one[h],
                                 marker_color=theme.HAZARD_COLORS[h]))
        fig.add_trace(go.Scatter(name="Composite", x=[LABELS[p] for p in one.index], y=one.composite,
                                 mode="lines+markers", line=dict(color=T.INK, width=3)))
        fig.update_yaxes(range=[0, 1], title="score 0-1")
        st.plotly_chart(plot_style(fig.update_layout(barmode="group", title="Scores d'aléa par période")), use_container_width=True)
    with r:
        p0 = one.loc[period]
        st.markdown(f"""<div class="card"><h4>Effet sur la PD · {LABELS[period]}</h4>
        <p style="font-family:'Fira Code';font-size:1.3rem;margin:4px 0">{100*p0.pd_base:.2f} % → <b>{100*p0.pd_climate:.2f} %</b></p>
        <p style="color:{T.MUTED};margin:0">LGD {100*p0.lgd_base:.0f} % → {100*p0.lgd_climate:.0f} % ·
        EL {fmt_tnd(p0.el_base)} → {fmt_tnd(p0.el_climate)} TND</p></div>""", unsafe_allow_html=True)
        beta = ASSUM["beta"].get(info.sector, ASSUM["beta"]["default"])
        V = ASSUM["vulnerability"][info.sector]
        st.markdown(f"""<div class="card"><h4>Hypothèses appliquées</h4>
        <span class="tag">β secteur = {beta}</span><span class="tag">γ LGD inondation = {ASSUM['gamma_lgd_flood']}</span>
        <span class="tag">seuil aléa élevé = {ASSUM['high_hazard_threshold']}</span><br/>
        Vulnérabilité : {' · '.join(f"{theme.HAZARD_LABELS[h]} {V[h]}" for h in HAZ)}<br/>
        <span class="tag warn">hypothèses illustratives — config/assumptions.yaml</span></div>""", unsafe_allow_html=True)
        st.markdown(f"""<div class="card"><h4>Indicateurs physiques (médiane modèles)</h4>
        Jours &gt; 35 °C : <b>{p0.hot35:.0f}</b> /an · Jours secs consécutifs : <b>{p0.cdd:.0f}</b> ·
        Δ précipitations : <b>{p0.prchange:+.1f} %</b><br/>Profondeur crue 100 ans : <b>{p0.flood_depth_m:.2f} m</b> ·
        Végétation combustible : <b>{100*p0.fuel:.0f} %</b></div>""", unsafe_allow_html=True)

# =========================================================================== Reporting
with tabs[4]:
    st.markdown("#### Tableaux d'exposition aux risques physiques — inspirés du cadre volontaire BCBS (juin 2025)")
    st.caption("Format illustratif : le cadre BCBS d597 est volontaire et son adoption laissée à chaque juridiction.")
    t = sel.copy()
    t["bande"] = pd.cut(t.composite, [-0.01, 0.25, 0.5, 0.75, 1.0], labels=["faible", "modéré", "élevé", "très élevé"])
    tab1 = t.pivot_table(index="sector_label", columns="bande", values="ead_tnd", aggfunc="sum",
                         observed=False, fill_value=0) / 1e6
    tab1["Total (M TND)"] = tab1.sum(1)
    st.markdown("**EAD par secteur et niveau d'aléa physique composite (M TND)**")
    st.dataframe(tab1.round(1), use_container_width=True)
    dom = t[HAZ].idxmax(axis=1).map(theme.HAZARD_LABELS)
    tab2 = t.assign(aléa_dominant=dom).pivot_table(index="governorate", columns="aléa_dominant", values="ead_tnd",
                                                    aggfunc="sum", fill_value=0) / 1e6
    st.markdown("**EAD par gouvernorat et aléa dominant (M TND)**")
    st.dataframe(tab2.round(1), use_container_width=True)
    c1, c2, c3 = st.columns(3)
    c1.download_button("Exporter les crédits (CSV)", sel.to_csv(index=False).encode("utf-8"),
                       f"climarisk_{period}.csv", "text/csv", use_container_width=True)
    c2.download_button("Exporter le tableau secteur (CSV)", tab1.to_csv().encode("utf-8"),
                       f"climarisk_secteur_{period}.csv", "text/csv", use_container_width=True)
    pdf = ROOT / "docs/report.pdf"
    if pdf.exists():
        c3.download_button("Rapport PDF", pdf.read_bytes(), "ClimaRisk_Tunisie_rapport.pdf", "application/pdf",
                           use_container_width=True)
    else:
        c3.info("Rapport PDF : lancer `make report`.")

# =========================================================================== Réglementation
with tabs[5]:
    st.markdown("#### Matrice de conformité — ce que l'outil couvre")
    st.markdown('<div class="note">L\'outil <b>prépare</b> les banques aux attentes climatiques ; il ne prétend '
                'à aucune conformité réglementaire. Statut des sources vérifié le 20/11/2026 (docs/research_log.md).</div>',
                unsafe_allow_html=True)
    st.write("")
    cols = st.columns(2)
    for i, tx in enumerate(REG["texts"]):
        warn = "warn" if ("secondaire" in tx["status"] or "revérifier" in tx["status"] or "non" in tx["status"]) else ""
        mods = "".join(f"<li>{m}</li>" for m in tx["modules"])
        cols[i % 2].markdown(f"""<div class="card"><h4><a href="{tx['url']}" target="_blank" style="color:{T.PETROL};text-decoration:none">{tx['title']}</a></h4>
        <span class="tag">{tx['date']}</span><span class="tag {warn}">{tx['status']}</span><span class="tag">couverture : {tx['coverage']}</span>
        <p style="margin:8px 0 4px 0">{tx['requirement']}</p><ul style="margin:0;color:{T.MUTED}">{mods}</ul></div>""",
                             unsafe_allow_html=True)

# =========================================================================== Méthode
with tabs[6]:
    l, r = st.columns([1.2, 1])
    with l:
        st.markdown("""
#### Méthode — expliquée pour un comité des risques
**1. Aléa.** Pour chaque crédit, on mesure quatre aléas physiques à sa localisation :
- *Chaleur extrême* — jours par an avec Tmax > 35 °C (NASA NEX-GDDP-CMIP6, 5 modèles) ;
- *Sécheresse* — jours secs consécutifs et variation des précipitations par rapport à 2010-2014 ;
- *Inondation* — profondeur d'eau d'une crue centennale, fluviale ou côtière (WRI Aqueduct) ;
- *Feux de forêt* — végétation combustible dans un rayon de 2 km (ESA WorldCover) × météo de feu.

Chaque indicateur est ramené à un score 0-1 par des bornes physiques fixes (comparables entre scénarios).

**2. Exposition × vulnérabilité.** Le score composite pondère les aléas par la sensibilité du secteur
(la céréaliculture pluviale craint d'abord la sécheresse, l'hôtellerie côtière l'inondation).

**3. Traduction crédit.**
""")
        st.latex(r"PD_{s} = \min\left(1,\ PD_{base}\,(1 + \beta_{secteur}\,Score_{s})\right)")
        st.latex(r"LGD_{s} = \min\left(1,\ LGD\,(1 + \gamma\,Score^{inond}_{s})\right),\qquad EL_{s} = PD_{s}\,LGD_{s}\,EAD")
        st.markdown("""
**4. Agrégation** par secteur, gouvernorat et scénario ; incertitude = dispersion entre modèles climatiques
(médiane et intervalle 10–90 %).
""")
    with r:
        st.markdown("""<div class="card"><h4>Limites à garder en tête</h4><ul>
<li>Portefeuille <b>100 % synthétique</b> : chiffres illustratifs.</li>
<li>Résolution : 0,25° (~25 km) pour le climat, ~1 km pour l'inondation, ~320 m pour la végétation.</li>
<li>Biais des modèles climatiques ; 5 modèles seulement, 3 années par horizon.</li>
<li>Aqueduct utilise des projections CMIP5 (RCP4.5/8.5) servant de proxy aux SSP.</li>
<li>β, γ et la matrice de vulnérabilité sont des hypothèses à calibrer sur des défauts observés.</li>
<li>La fonction de dommage physique NGFS Phase V (Kotz et al., 2024) a été rétractée : elle n'est pas utilisée.</li>
<li>Pas de risque de transition, pas d'effets de second ordre (chaînes d'approvisionnement, macroéconomie).</li>
</ul></div>""", unsafe_allow_html=True)
        st.markdown("""<div class="card"><h4>Sources de données ouvertes</h4>
<span class="tag">NASA NEX-GDDP-CMIP6</span><span class="tag">WRI Aqueduct Floods</span><span class="tag">ESA WorldCover</span>
<span class="tag">WorldPop</span><span class="tag">geoBoundaries</span><span class="tag">Natural Earth</span>
<span class="tag">OS-Climate physrisk</span><p style="margin-top:8px;color:#5B6B70">Licences détaillées : docs/LICENSES_DATA.md</p></div>""",
                    unsafe_allow_html=True)

st.markdown(f"<p style='text-align:center;color:{T.MUTED};font-size:.8rem;margin-top:24px'>ClimaRisk Tunisie · "
            "Emna Saada — géoinformatique, MSE (Université de la Manouba) · code MIT · données ouvertes</p>",
            unsafe_allow_html=True)
