"""Build the LinkedIn carousel (1080x1350 slides) from pipeline outputs.

Every figure on the slides is read from outputs/kpis.json. Images are the project's own maps,
charts, dashboard capture and video frame. Output: docs/linkedin/slides.html (rendered to PNG/PDF
by scripts/render_linkedin.js with Playwright).
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/linkedin"


def img(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def fr(x: float, d: int = 1) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def main(extra: dict[str, Path]) -> Path:
    k = json.loads((ROOT / "outputs/kpis.json").read_text(encoding="utf-8"))
    P, H = k["periods"], k["hazard_means"]
    s0 = 100 * P["baseline"]["share_ead_high"]["med"]
    s5 = 100 * P["ssp585_2050"]["share_ead_high"]["med"]
    s5lo, s5hi = (100 * P["ssp585_2050"]["share_ead_high"][q] for q in ("p10", "p90"))
    vt = P["ssp585_2050"]["el_add_vs_today_tnd"]["med"] / 1e6
    el5 = P["ssp585_2050"]["el_add_tnd"]["med"] / 1e6
    bp5 = P["ssp585_2050"]["el_add_bp"]["med"]
    hot0, hot5, pr5 = H["baseline"]["hot35_days"], H["ssp585_2050"]["hot35_days"], H["ssp585_2050"]["prchange_pct"]
    sec = sorted(k["by_sector"]["ssp585_2050"].items(), key=lambda kv: -kv[1]["el_add_bp_med"])
    labels = {"cereals": "Céréaliculture", "olives": "Oléiculture", "construction": "BTP", "citrus": "Agrumes",
              "chemicals": "Chimie & phosphates", "textile": "Textile", "tourism": "Tourisme côtier",
              "agrifood": "Agroalimentaire", "energy": "Énergie", "residential": "Immobilier résidentiel"}
    maps = ROOT / "outputs/maps"
    figs = ROOT / "outputs/figures"
    n = k["meta"]["n_loans"]
    ngov = k["meta"]["n_governorates"]
    sec_rows = "".join(
        f'<div class="srow"><span>{labels[s]}</span><i style="width:{min(100, v["el_add_bp_med"] / sec[0][1]["el_add_bp_med"] * 100):.0f}%"></i>'
        f'<b>{fr(v["el_add_bp_med"], 0)} pb</b></div>' for s, v in sec[:6])

    html = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>
:root {{ --ink:#0F2A33; --petrol:#0E5E6F; --sand:#F6F4EF; --muted:#5B6B70; --line:#E3E0D8; --amber:#D97706;
        --s245:#008C9E; --s585:#C2343F; --mist:#D5E6EA; }}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ background:#888; font-family:Inter, "Inter Display", sans-serif; }}
.slide {{ width:1080px; height:1350px; position:relative; overflow:hidden; background:var(--sand); color:var(--ink);
         padding:84px 80px 96px; display:flex; flex-direction:column; gap:36px; margin-bottom:20px; }}
.dark {{ background:radial-gradient(120% 90% at 85% 5%, #1A5563 0%, var(--ink) 55%, #0A1E25 100%); color:#fff; }}
.kick {{ font-size:22px; letter-spacing:.14em; text-transform:uppercase; font-weight:600; color:var(--amber); }}
h1 {{ font-family:"Inter Display", Inter, sans-serif; font-weight:800; font-size:92px; line-height:1.0; letter-spacing:-2px; }}
h2 {{ font-family:"Inter Display", Inter, sans-serif; font-weight:800; font-size:64px; line-height:1.05; letter-spacing:-1.2px; }}
.lead {{ font-size:34px; line-height:1.38; color:var(--muted); max-width:900px; }}
.dark .lead {{ color:var(--mist); }}
.foot {{ position:absolute; left:80px; right:80px; bottom:44px; display:flex; justify-content:space-between;
        font-size:20px; color:var(--muted); border-top:1px solid var(--line); padding-top:18px; }}
.dark .foot {{ color:#9FB8BE; border-color:rgba(255,255,255,.18); }}
.pager {{ font-variant-numeric:tabular-nums; }}
.card {{ background:#fff; border:1px solid var(--line); border-radius:24px; padding:36px 40px; }}
.figure {{ background:#fff; border:1px solid var(--line); border-radius:24px; padding:24px; display:flex; justify-content:center; align-items:center; }}
.figure img {{ max-width:100%; max-height:100%; display:block; }}
.num {{ font-family:"Inter Display", Inter; font-weight:800; font-variant-numeric:tabular-nums; letter-spacing:-2px; }}
.chip {{ display:inline-block; padding:8px 18px; border-radius:999px; font-size:22px; font-weight:600; border:1.5px solid currentColor; }}
.flow {{ display:grid; grid-template-columns:1fr; gap:22px; }}
.step {{ display:grid; grid-template-columns:96px 1fr; gap:28px; align-items:center; background:#fff; border:1px solid var(--line); border-radius:22px; padding:28px 32px; }}
.step b {{ font-size:36px; display:block; margin-bottom:6px; }}
.step p {{ font-size:25px; line-height:1.4; color:var(--muted); }}
.dot {{ width:96px; height:96px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:40px; font-weight:800; color:#fff; }}
.srow {{ display:grid; grid-template-columns:330px 1fr 120px; gap:20px; align-items:center; font-size:28px; padding:14px 0; border-bottom:1px solid var(--line); }}
.srow i {{ display:block; height:16px; border-radius:8px; background:var(--s585); }}
.srow b {{ text-align:right; font-variant-numeric:tabular-nums; }}
.warn {{ background:#FFF4E2; border:1.5px solid #F2C27A; color:#6B4A12; border-radius:18px; padding:20px 26px; font-size:24px; line-height:1.4; }}
ul.lim {{ list-style:none; display:grid; gap:30px; margin-top:12px; }}
ul.lim li {{ font-size:33px; line-height:1.38; padding-left:34px; position:relative; }}
ul.lim li:before {{ content:""; position:absolute; left:0; top:15px; width:14px; height:14px; border-radius:3px; background:var(--amber); }}
</style></head><body>

<section class="slide dark" id="s1">
  <div class="kick">Géoinformatique × risque de crédit</div>
  <h1>Quand le climat change, le risque de crédit change aussi.</h1>
  <p class="lead">ClimaRisk Tunisie relie chaque crédit d'un portefeuille à son exposition à la chaleur, à la sécheresse, aux inondations et aux feux, aujourd'hui, en 2030 et en 2050.</p>
  <div class="figure" style="flex:1;min-height:0;padding:18px"><img src="{img(maps / 'map_portfolio.png')}"></div>
  <div class="foot"><span>ClimaRisk Tunisie · portefeuille 100 % synthétique</span><span class="pager">1 / 7</span></div>
</section>

<section class="slide" id="s2">
  <div class="kick">La méthode</div>
  <h2>Des pixels satellites à la perte attendue, en quatre étapes</h2>
  <div class="flow">
    <div class="step"><div class="dot" style="background:var(--petrol)">1</div><div><b>Portefeuille</b><p>{n:,} crédits synthétiques géolocalisés dans les {ngov} gouvernorats, selon la population (WorldPop) et les terres cultivées (ESA WorldCover).</p></div></div>
    <div class="step"><div class="dot" style="background:#D1495B">2</div><div><b>Aléa</b><p>Jours &gt; 35 °C et sécheresse (5 modèles CMIP6, NASA), crue centennale (WRI Aqueduct), combustible végétal.</p></div></div>
    <div class="step"><div class="dot" style="background:#C98500">3</div><div><b>Vulnérabilité</b><p>Chaque secteur pondère les aléas : la céréaliculture craint la sécheresse, l'hôtellerie côtière l'inondation.</p></div></div>
    <div class="step"><div class="dot" style="background:var(--s585)">4</div><div><b>Crédit</b><p>PD′ = PD × (1 + β·score), LGD ajustée pour l'inondation, EL = PD′ × LGD′ × EAD, agrégée par secteur et gouvernorat.</p></div></div>
  </div>
  <div class="foot"><span>Données ouvertes · code MIT</span><span class="pager">2 / 7</span></div>
</section>

<section class="slide dark" id="s3">
  <div class="kick">Le résultat clé · SSP5-8.5 · 2050</div>
  <h2>La part de l'encours en zone d'aléa élevé est multipliée par {fr(s5 / s0, 0)}</h2>
  <div style="display:flex;align-items:baseline;gap:28px;white-space:nowrap">
    <span class="num" style="font-size:104px;color:#9FB8BE">{fr(s0)}&nbsp;%</span>
    <span style="font-size:72px;color:var(--amber)">→</span>
    <span class="num" style="font-size:168px;color:var(--amber)">{fr(s5)}&nbsp;%</span>
  </div>
  <p class="lead">Aujourd'hui → 2050. Intervalle entre modèles climatiques : {fr(s5lo)} à {fr(s5hi)} %.</p>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:28px">
    <div class="card" style="background:rgba(255,255,255,.07);border-color:rgba(255,255,255,.16);color:#fff"><div style="font-size:22px;color:#9FB8BE;letter-spacing:.06em;text-transform:uppercase;font-weight:600">Perte attendue en plus vs aujourd'hui</div><div class="num" style="font-size:58px;margin-top:10px;white-space:nowrap">+{fr(vt)}&nbsp;M&nbsp;TND</div></div>
    <div class="card" style="background:rgba(255,255,255,.07);border-color:rgba(255,255,255,.16);color:#fff"><div style="font-size:22px;color:#9FB8BE;letter-spacing:.06em;text-transform:uppercase;font-weight:600">EL climatique totale</div><div class="num" style="font-size:58px;margin-top:10px;white-space:nowrap">{fr(el5)}&nbsp;M&nbsp;TND</div><div style="font-size:22px;color:#9FB8BE;margin-top:6px">soit {fr(bp5, 0)} pb de l'encours</div></div>
  </div>
  <div class="warn" style="margin-top:auto;margin-bottom:24px;background:rgba(217,119,6,.14);border-color:rgba(217,119,6,.6);color:#FBD38D">Portefeuille 100 % synthétique : chiffres illustratifs, à calibrer sur des données bancaires réelles.</div>
  <div class="foot"><span>Médiane de 5 modèles CMIP6</span><span class="pager">3 / 7</span></div>
</section>

<section class="slide" id="s4">
  <div class="kick">Le moteur physique</div>
  <h2>De {fr(hot0, 0)} à {fr(hot5, 0)} jours par an au-dessus de 35 °C</h2>
  <p class="lead">Aux emplacements des crédits, SSP5-8.5, 2050. Les précipitations annuelles reculent de {fr(abs(pr5), 0)} % en médiane.</p>
  <div class="figure" style="flex:1;min-height:0"><img src="{img(maps / 'map_heat.png')}"></div>
  <div class="foot"><span>NASA NEX-GDDP-CMIP6 · 0,25°</span><span class="pager">4 / 7</span></div>
</section>

<section class="slide" id="s5">
  <div class="kick">Qui est touché</div>
  <h2>L'agriculture pluviale porte le choc</h2>
  <p class="lead">Perte attendue additionnelle en points de base de l'encours de chaque secteur, SSP5-8.5, 2050.</p>
  <div class="card" style="padding:16px 36px">{sec_rows}</div>
  <div class="figure" style="flex:1;min-height:0;padding:14px"><img src="{img(figs / 'heatmap.png')}"></div>
  <div class="foot"><span>Score moyen pondéré par l'exposition</span><span class="pager">5 / 7</span></div>
</section>

<section class="slide" id="s6">
  <div class="kick">L'outil</div>
  <h2>Un tableau de bord, un rapport, une vidéo</h2>
  <p class="lead">Choix du scénario et de l'horizon, carte des gouvernorats, fiche par crédit, matrice BCBS · NGFS · EBA · IFRS S2 · BCT, export CSV et rapport PDF.</p>
  <div class="figure" style="flex:1.25;min-height:0;padding:12px"><img src="{img(extra['dash'])}" style="border-radius:12px"></div>
  <div class="figure" style="flex:1;min-height:0;padding:12px;background:var(--ink);border-color:var(--ink)"><img src="{img(extra['video'])}" style="border-radius:10px"></div>
  <div class="foot"><span>Python · Streamlit · d3 · Remotion</span><span class="pager">6 / 7</span></div>
</section>

<section class="slide dark" id="s7">
  <div class="kick">Ce que je retiens</div>
  <h2>Un outil honnête vaut mieux qu'un chiffre précis</h2>
  <ul class="lim">
    <li>L'élasticité de la PD (β) pèse bien plus que l'incertitude climatique : c'est elle qu'il faut calibrer sur des défauts observés.</li>
    <li>Deux indicateurs de sécheresse peuvent désigner des régions opposées : le choix dépend de l'activité financée.</li>
    <li>La fonction de dommage PIB des scénarios NGFS Phase V repose sur un article rétracté : je ne l'utilise pas.</li>
    <li>Risque physique uniquement, résolution climatique de 25 km, portefeuille synthétique.</li>
  </ul>
  <p class="lead" style="margin-top:auto;color:#fff">Code, rapport méthodologique et vidéo de démonstration : lien en commentaire.</p>
  <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:28px"><span class="chip" style="color:var(--amber)">Python</span><span class="chip" style="color:#9FE3EA">CMIP6</span><span class="chip" style="color:#9FE3EA">NGFS</span><span class="chip" style="color:#9FE3EA">Géoinformatique</span><span class="chip" style="color:#9FE3EA">Risque de crédit</span></div>
  <div class="foot"><span>Emna Saada · géoinformatique, MSE (Université de la Manouba)</span><span class="pager">7 / 7</span></div>
</section>
</body></html>"""
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "slides.html"
    p.write_text(html, encoding="utf-8")
    return p


if __name__ == "__main__":
    import sys

    a = dict(arg.split("=", 1) for arg in sys.argv[1:])
    print(main({"dash": Path(a["dash"]), "video": Path(a["video"])}))
