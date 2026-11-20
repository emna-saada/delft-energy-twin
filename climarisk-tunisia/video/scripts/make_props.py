"""Build video/public/props.json, the French voice-over (Piper TTS) and subtitles.

Every figure spoken or shown in the video is read from ../outputs/kpis.json (pipeline output).
Usage (from video/):  ../.venv/bin/python scripts/make_props.py
"""
from __future__ import annotations

import json
import math
import subprocess
import wave
from pathlib import Path

import pandas as pd

VIDEO = Path(__file__).resolve().parents[1]
ROOT = VIDEO.parent
PUB = VIDEO / "public"
FPS = 30
VOICE = VIDEO / "voice_model/fr_FR-siwis-medium.onnx"


def fr(x: float, d: int = 1) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def main() -> None:
    k = json.loads((ROOT / "outputs/kpis.json").read_text(encoding="utf-8"))
    P = k["periods"]
    labels = k["meta"]["period_labels"]
    sh0 = 100 * P["baseline"]["share_ead_high"]["med"]
    sh5 = 100 * P["ssp585_2050"]["share_ead_high"]["med"]
    el5 = P["ssp585_2050"]["el_add_tnd"]["med"] / 1e6
    bp5 = P["ssp585_2050"]["el_add_bp"]["med"]
    assets = pd.read_parquet(ROOT / "outputs/asset_results.parquet")
    sl = assets.drop_duplicates("sector").set_index("sector")["sector_label"].to_dict()
    top = sorted(k["by_sector"]["ssp585_2050"].items(), key=lambda kv: -kv[1]["el_add_bp_med"])[:2]
    top_txt = f"{sl[top[0][0]]} et {sl[top[1][0]].lower()}"

    scenes = [
        ("hook", 15, "Quand le climat change, le risque de crédit change aussi. Voici ClimaRisk Tunisie : "
                     "la carte des risques climatiques physiques d'un portefeuille de crédits."),
        ("origin", 25, "Inondations de Nabeul en 2018, sécheresses qui frappent les céréales, records de chaleur : "
                       "les actifs financés par les banques tunisiennes sont exposés. En novembre 2026, la Banque "
                       "Centrale de Tunisie a lancé une feuille de route 2026-2030 sur la finance verte et les risques "
                       "climatiques. Ce projet se place entre risque bancaire et changement climatique."),
        ("regulation", 25, "Le cadre s'est construit pas à pas : les principes du Comité de Bâle en 2022, la norme "
                           "IFRS S2 en 2023, les scénarios NGFS de phase cinq en 2024, les orientations de l'Autorité "
                           "bancaire européenne et le cadre volontaire de publication de Bâle en 2025, puis la feuille "
                           "de route de la BCT. L'outil prépare ces attentes, sans prétendre à une conformité."),
        ("method", 25, "Les données sont entièrement ouvertes : projections climatiques CMIP6 de la NASA, cartes "
                       "d'inondation Aqueduct, occupation du sol WorldCover et population WorldPop. Pour chaque crédit, "
                       "on croise aléa, exposition et vulnérabilité du secteur, puis on ajuste la probabilité de défaut "
                       "et la perte attendue. Le portefeuille de deux mille crédits est cent pour cent synthétique."),
        ("results", 45, f"Résultat : la part de l'encours située en zone d'aléa élevé passe de {fr(sh0)} pour cent "
                        f"aujourd'hui à {fr(sh5)} pour cent en 2050, dans le scénario SSP5 8,5. La perte attendue "
                        f"climatique additionnelle atteint {fr(el5)} millions de dinars, soit {fr(bp5, 0)} points de "
                        f"base de l'encours. {top_txt} sont les secteurs les plus touchés, et l'écart entre modèles "
                        f"climatiques reste important."),
        ("showcase", 30, "Le tableau de bord permet de choisir le scénario et l'horizon, d'explorer la carte des "
                         "gouvernorats, d'ouvrir la fiche de chaque crédit, puis d'exporter les tableaux et le "
                         "rapport PDF."),
        ("outro", 15, "Ces chiffres sont illustratifs, à calibrer sur des données bancaires réelles. ClimaRisk "
                      "Tunisie, un projet open source d'Emna Saada, en géoinformatique."),
    ]

    (PUB / "voice").mkdir(parents=True, exist_ok=True)
    out_scenes, srt, t0 = [], [], 0.0
    for i, (sid, target, text) in enumerate(scenes):
        wav = PUB / "voice" / f"{i:02d}_{sid}.wav"
        subprocess.run([str(ROOT / ".venv/bin/piper"), "-m", str(VOICE), "-f", str(wav),
                        "--length-scale", "1.0", "--sentence-silence", "0.25"], input=text.encode(), check=True,
                       capture_output=True)
        with wave.open(str(wav)) as w:
            dur = w.getnframes() / w.getframerate()
        scene_s = max(target, dur + 1.6)
        out_scenes.append({"id": sid, "text": text, "audio": f"voice/{wav.name}", "audioSeconds": dur,
                           "durationInFrames": math.ceil(scene_s * FPS)})
        # subtitles: split on sentence boundaries, distribute time by length
        parts = [s.strip() for s in text.replace(" : ", " : |").replace(". ", ".|").split("|") if s.strip()]
        total = sum(len(p) for p in parts)
        t = t0 + 0.6
        for p in parts:
            d = dur * len(p) / total
            srt.append((t, t + d, p))
            t += d
        t0 += scene_s

    def ts(x):
        h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int((s % 1) * 1000):03d}"

    (VIDEO / "out").mkdir(exist_ok=True)
    (VIDEO / "out/climarisk_demo.srt").write_text(
        "\n".join(f"{i + 1}\n{ts(a)} --> {ts(b)}\n{txt}\n" for i, (a, b, txt) in enumerate(srt)), encoding="utf-8")

    # Tunisia outline projected to a 600x1000 SVG box (equirectangular, cos(lat) scaling)
    gj = json.loads((ROOT / "data/raw/tun_adm1.geojson").read_text(encoding="utf-8"))
    lon0, lon1, lat0, lat1 = 7.4, 11.7, 30.2, 37.6
    kx = math.cos(math.radians(34))
    W, H = 600, 1000
    sx = W / ((lon1 - lon0) * kx)
    sy = H / (lat1 - lat0)
    s = min(sx, sy)

    def proj(lon, lat):
        return round((lon - lon0) * kx * s, 1), round((lat1 - lat) * s, 1)

    paths = []
    gov_el = k["by_governorate"]["ssp585_2050"]
    gov_heat = assets[assets.period == "ssp585_2050"].groupby("governorate")["heat"].mean().to_dict()
    for f in gj["features"]:
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        d = ""
        for poly in polys:
            ring = poly[0][::2] if len(poly[0]) > 400 else poly[0]
            pts = [proj(x, y) for x, y in ring]
            d += "M" + "L".join(f"{x},{y}" for x, y in pts) + "Z"
        name = f["properties"]["shapeName"]
        paths.append({"name": name, "d": d, "el_bp": gov_el.get(name, {}).get("el_add_bp_med", 0),
                      "heat": gov_heat.get(name, 0)})

    pts = []
    sample = assets[assets.period.isin(["baseline", "ssp585_2050"])].pivot_table(
        index=["loan_id", "lon", "lat", "ead_tnd"], columns="period", values="composite").reset_index()
    for r in sample.sample(900, random_state=1).itertuples():
        x, y = proj(r.lon, r.lat)
        pts.append({"x": x, "y": y, "r": round(2 + 7 * math.sqrt(r.ead_tnd / sample.ead_tnd.max()), 1),
                    "s0": round(r.baseline, 3), "s1": round(r.ssp585_2050, 3)})

    hm = k["heatmap_sector_hazard"]["ssp585_2050"]
    props = {
        "fps": FPS, "scenes": out_scenes, "svg": {"w": round((lon1 - lon0) * kx * s), "h": round((lat1 - lat0) * s),
                                                  "paths": paths, "points": pts},
        "kpi": {"share0": sh0, "share5": sh5, "share5_p10": 100 * P["ssp585_2050"]["share_ead_high"]["p10"],
                "share5_p90": 100 * P["ssp585_2050"]["share_ead_high"]["p90"], "el5": el5, "bp5": bp5,
                "el5_p10": P["ssp585_2050"]["el_add_tnd"]["p10"] / 1e6,
                "el5_p90": P["ssp585_2050"]["el_add_tnd"]["p90"] / 1e6,
                "n": k["meta"]["n_loans"], "ngov": k["meta"]["n_governorates"],
                "ead": k["meta"]["total_ead_tnd"] / 1e9,
                "hot0": k["hazard_means"]["baseline"]["hot35_days"],
                "hot5": k["hazard_means"]["ssp585_2050"]["hot35_days"],
                "pr5": k["hazard_means"]["ssp585_2050"]["prchange_pct"]},
        "periods": [{"key": p, "label": labels[p], "med": P[p]["el_add_tnd"]["med"] / 1e6,
                     "p10": P[p]["el_add_tnd"]["p10"] / 1e6, "p90": P[p]["el_add_tnd"]["p90"] / 1e6,
                     "share": 100 * P[p]["share_ead_high"]["med"]}
                    for p in ["baseline", "ssp245_2030", "ssp245_2050", "ssp585_2030", "ssp585_2050"]],
        "heatmap": {"rows": [sl[s] for s in hm], "cols": ["Chaleur", "Sécheresse", "Inondation", "Feux"],
                    "values": [[round(hm[s][h], 2) for h in ("heat", "drought", "flood", "fire")] for s in hm]},
        "disclaimer": k["meta"]["disclaimer"],
    }
    (PUB / "props.json").write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    total = sum(sc["durationInFrames"] for sc in out_scenes) / FPS
    print(f"props.json written · {len(out_scenes)} scenes · {total:.1f} s")
    for sc in out_scenes:
        print(f"  {sc['id']:<11} audio {sc['audioSeconds']:5.1f}s  scene {sc['durationInFrames'] / FPS:5.1f}s")


if __name__ == "__main__":
    main()
