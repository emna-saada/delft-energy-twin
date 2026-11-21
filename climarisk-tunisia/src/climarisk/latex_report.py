"""Typeset the methodology report (French) with LaTeX from outputs/kpis.json.

Template: report/climarisk.tex.j2 (Jinja2 with LaTeX-safe delimiters \\VAR{...} and \\BLOCK{...}).
Figures: outputs/paper/fr/*.pdf from climarisk.paperfigs. Output: docs/report.pdf.
Requires pdflatex (TeX Live: latex-base, latex-recommended, latex-extra, fonts-recommended, lang-french).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

from .config import project_root

MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
          "novembre", "décembre"]
SECT = {"cereals": "Céréaliculture", "olives": "Oléiculture", "citrus": "Agrumes", "agrifood": "Agroalimentaire",
        "textile": "Textile", "tourism": "Tourisme côtier", "residential": "Immobilier résidentiel",
        "construction": "BTP", "chemicals": "Chimie et phosphates", "energy": "Énergie"}
REG_USE = {
    "BCBS-2022": "Intégration au risque de crédit, données et analyse de scénarios.",
    "BCBS-P3-2025": "Tableaux d'exposition aux risques physiques par secteur et gouvernorat.",
    "NGFS-V": "Cadre narratif ; correspondance avec SSP2-4.5 et SSP5-8.5. Fonction de dommage PIB non utilisée.",
    "EBA-ESG-2025": "Horizons court, moyen et long terme ; analyse de sensibilité.",
    "ECB-2020": "Usages possibles dans le Pilier 2 et l'ICAAP.",
    "IFRS-S2": "Indicateurs d'exposition ; risque physique uniquement.",
    "BCT-91-24": "Agrégation par secteur et gouvernorat (concentration). Texte à revérifier.",
    "BCT-2018-06": "Contexte prudentiel. Ratios non cités.",
    "BCT-ROADMAP": "Positionnement de l'outil ; source : presse tunisienne.",
    "LOI-2004-63": "Portefeuille entièrement synthétique.",
}
SHORT = {
    "BCBS-2022": "BCBS, principes pour la gestion des risques climatiques",
    "BCBS-P3-2025": "BCBS, cadre volontaire de publication",
    "NGFS-V": "NGFS, scénarios de long terme, phase V",
    "EBA-ESG-2025": "EBA, orientations sur les risques ESG",
    "ECB-2020": "BCE, guide sur les risques climatiques",
    "IFRS-S2": "ISSB, IFRS S2",
    "BCT-91-24": "BCT, circulaire n\\textsuperscript{o}~91-24",
    "BCT-2018-06": "BCT, circulaire n\\textsuperscript{o}~2018-06",
    "BCT-ROADMAP": "BCT, feuille de route 2026--2030",
    "LOI-2004-63": "Loi organique n\\textsuperscript{o}~2004-63",
}
SHORT_DATE = {
    "BCBS-2022": "juin 2022", "BCBS-P3-2025": "juin 2025", "NGFS-V": "nov. 2024", "EBA-ESG-2025": "janv. 2025",
    "ECB-2020": "nov. 2020", "IFRS-S2": "juin 2023", "BCT-91-24": "1991, modifiée", "BCT-2018-06": "juin 2018",
    "BCT-ROADMAP": "nov. 2026", "LOI-2004-63": "juill. 2004",
}


def fr(x: float, d: int = 1) -> str:
    s = f"{x:,.{d}f}".replace(",", "\\,").replace(".", "{,}")
    return s


def signed(x: float, d: int = 1) -> str:
    return ("+" if x > 0 else "$-$" if x < 0 else "") + fr(abs(x), d)


def context() -> dict:
    root = project_root()
    k = json.loads((root / "outputs/kpis.json").read_text(encoding="utf-8"))
    a = yaml.safe_load((root / "config/assumptions.yaml").read_text(encoding="utf-8"))
    reg = yaml.safe_load((root / "config/regulatory_matrix.yaml").read_text(encoding="utf-8"))["texts"]
    P, H = k["periods"], k["hazard_means"]
    labels = {"baseline": "Climat actuel (2010--2014)", "ssp245_2030": "SSP2-4.5, 2030", "ssp245_2050": "SSP2-4.5, 2050",
              "ssp585_2030": "SSP5-8.5, 2030", "ssp585_2050": "SSP5-8.5, 2050"}
    rows = []
    for p, label in labels.items():
        d = P[p]
        sh = fr(100 * d["share_ead_high"]["med"])
        if p != "baseline":
            sh += f" [{fr(100 * d['share_ead_high']['p10'])}--{fr(100 * d['share_ead_high']['p90'])}]"
        rows.append({"label": label, "share": sh,
                     "el": f"{fr(d['el_add_tnd']['med'] / 1e6)} [{fr(d['el_add_tnd']['p10'] / 1e6)}--{fr(d['el_add_tnd']['p90'] / 1e6)}]",
                     "bp": fr(d["el_add_bp"]["med"]),
                     "vt": "--" if p == "baseline" else signed(d["el_add_vs_today_tnd"]["med"] / 1e6)})
    sec = k["by_sector"]["ssp585_2050"]
    gov = sorted(k["by_governorate"]["ssp585_2050"].items(), key=lambda kv: -kv[1]["el_add_bp_med"])[:5]
    govs = ", ".join(f"{g} ({fr(v['el_add_bp_med'], 0)}~pb)" for g, v in gov[:-1]) + f" et {gov[-1][0]} ({fr(gov[-1][1]['el_add_bp_med'], 0)}~pb)"
    sens = pd.DataFrame(k["sensitivity"])
    beta = sens[sens.label.str.startswith("β")]
    w = sens[~sens.label.str.startswith("β")]
    e = P["ssp585_2050"]["el_add_tnd"]
    pr = json.loads((root / "outputs/physrisk_comparison.json").read_text())
    today = date.today()
    return {
        "figdir": str(root / "outputs/paper/fr"),
        "date": f"{MONTHS[today.month - 1]} {today.year}".upper(),
        "n": f"{k['meta']['n_loans']:,}".replace(",", "\\,"), "ngov": k["meta"]["n_governorates"],
        "ead": fr(k["meta"]["total_ead_tnd"] / 1e9, 0),
        "sh0": fr(100 * P["baseline"]["share_ead_high"]["med"]), "sh5": fr(100 * P["ssp585_2050"]["share_ead_high"]["med"]),
        "sh5lo": fr(100 * P["ssp585_2050"]["share_ead_high"]["p10"]), "sh5hi": fr(100 * P["ssp585_2050"]["share_ead_high"]["p90"]),
        "el5": fr(e["med"] / 1e6), "bp5": fr(P["ssp585_2050"]["el_add_bp"]["med"]),
        "vt5": fr(P["ssp585_2050"]["el_add_vs_today_tnd"]["med"] / 1e6),
        "hot0": fr(H["baseline"]["hot35_days"], 0), "hot5": fr(H["ssp585_2050"]["hot35_days"], 0),
        "cdd0": fr(H["baseline"]["cdd_days"], 0), "cdd5": fr(H["ssp585_2050"]["cdd_days"], 0),
        "pr5": fr(abs(H["ssp585_2050"]["prchange_pct"]), 0),
        "sec1": fr(sec["cereals"]["el_add_bp_med"], 0), "sec2": fr(sec["olives"]["el_add_bp_med"], 0),
        "secres": fr(sec["residential"]["el_add_bp_med"], 0), "govs": govs,
        "bmin": signed(beta.delta_pct.min(), 0), "bmax": signed(beta.delta_pct.max(), 0),
        "mlo": signed(100 * (e["p10"] / e["med"] - 1), 0), "mhi": signed(100 * (e["p90"] / e["med"] - 1), 0),
        "wmax": fr(w.delta_pct.abs().max() + 0.5, 0),
        "rho_h0": fr(pr["heat_spearman_base"], 2), "rho_h5": fr(pr["heat_spearman_2050"], 2),
        "rho_d5": signed(pr["drought_spearman_2050"], 2),
        "rows": rows,
        "reg": [{"title": SHORT[t["id"]], "date": SHORT_DATE[t["id"]], "use": REG_USE[t["id"]]} for t in reg],
        "vuln": [{"name": SECT[s], **{h: fr(v[h], 1) for h in ("heat", "drought", "flood", "fire")},
                  "beta": fr(a["beta"].get(s, a["beta"]["default"]), 1)} for s, v in a["vulnerability"].items()],
        "gamma": fr(a["gamma_lgd_flood"], 1), "thr": fr(a["high_hazard_threshold"], 1),
        "mat": fr(a["materiality_min_vulnerability"], 1),
    }


def build_report(out_pdf: Path | None = None) -> Path:
    from jinja2 import Environment, FileSystemLoader

    from .paperfigs import render_all

    root = project_root()
    out_pdf = out_pdf or root / "docs/report.pdf"
    render_all(("fr",))
    env = Environment(loader=FileSystemLoader(str(root / "report")), block_start_string=r"\BLOCK{", block_end_string="}",
                      variable_start_string=r"\VAR{", variable_end_string="}", comment_start_string=r"\#{",
                      comment_end_string="}", trim_blocks=True, autoescape=False)
    tex = env.get_template("climarisk.tex.j2").render(**context())
    (root / "report/climarisk.tex").write_text(tex, encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        for _ in range(2):  # second pass resolves cross-references
            r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory", tmp,
                                str(root / "report/climarisk.tex")], check=False, capture_output=True, text=True)
            if r.returncode != 0:
                log = Path(tmp, "climarisk.log").read_text(errors="ignore")
                raise RuntimeError("pdflatex failed:\n" + log[-3000:])
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(tmp, "climarisk.pdf"), out_pdf)
    return out_pdf


if __name__ == "__main__":
    print(build_report())
