"""Export pipeline outputs as small JSON tables ({rows, meta}) for the online results dashboard.

Reads only outputs/ written by `make run` (synthetic portfolio) and data/raw/tun_adm1.geojson.
Writes outputs/dashboard/*.json. Every file carries this script's own text in `meta`.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DST = OUT / "dashboard"
CODE = Path(__file__).read_text(encoding="utf-8")
LABELS = {"baseline": "Today", "ssp245_2030": "SSP2-4.5 · 2030", "ssp245_2050": "SSP2-4.5 · 2050",
          "ssp585_2030": "SSP5-8.5 · 2030", "ssp585_2050": "SSP5-8.5 · 2050"}
SCEN = {"baseline": "Today", "ssp245_2030": "SSP2-4.5", "ssp245_2050": "SSP2-4.5",
        "ssp585_2030": "SSP5-8.5", "ssp585_2050": "SSP5-8.5"}
HOR = {"baseline": "Today", "ssp245_2030": "2030", "ssp245_2050": "2050", "ssp585_2030": "2030", "ssp585_2050": "2050"}


def write(name: str, rows: list[dict], inputs: str) -> None:
    meta = [{"label": "export_dashboard_data.py", "value": CODE, "type": "code", "lang": "python"},
            {"label": "Input", "value": inputs},
            {"label": "Portfolio", "value": "100 % synthetic (2,000 loans) — illustrative figures"}]
    DST.mkdir(parents=True, exist_ok=True)
    (DST / f"{name}.json").write_text(json.dumps({"rows": rows, "meta": meta}, ensure_ascii=False), encoding="utf-8")
    print(f"{name}: {len(rows)} rows")


def main() -> None:
    k = json.loads((OUT / "kpis.json").read_text(encoding="utf-8"))
    assets = pd.read_parquet(OUT / "asset_results.parquet")
    sl = assets.drop_duplicates("sector").set_index("sector")["sector_label"].to_dict()
    sector_en = {"cereals": "Cereals", "olives": "Olives", "citrus": "Citrus", "agrifood": "Agrifood",
                 "textile": "Textile", "tourism": "Coastal tourism", "residential": "Housing",
                 "construction": "Construction", "chemicals": "Chemicals & phosphates", "energy": "Energy"}

    rows = []
    for p, d in k["periods"].items():
        hm = k["hazard_means"][p]
        rows.append({"period": p, "label": LABELS[p], "scenario": SCEN[p], "horizon": HOR[p],
                     "share_high_med": round(100 * d["share_ead_high"]["med"], 3),
                     "share_high_p10": round(100 * d["share_ead_high"]["p10"], 3),
                     "share_high_p90": round(100 * d["share_ead_high"]["p90"], 3),
                     "el_add_m_med": round(d["el_add_tnd"]["med"] / 1e6, 3),
                     "el_add_m_p10": round(d["el_add_tnd"]["p10"] / 1e6, 3),
                     "el_add_m_p90": round(d["el_add_tnd"]["p90"] / 1e6, 3),
                     "el_add_bp_med": round(d["el_add_bp"]["med"], 2),
                     "el_vs_today_m_med": round(d["el_add_vs_today_tnd"]["med"] / 1e6, 3),
                     "el_vs_today_m_p10": round(d["el_add_vs_today_tnd"]["p10"] / 1e6, 3),
                     "el_vs_today_m_p90": round(d["el_add_vs_today_tnd"]["p90"] / 1e6, 3),
                     "hot35_days": round(hm["hot35_days"], 1), "cdd_days": round(hm["cdd_days"], 1),
                     "prchange_pct": round(hm["prchange_pct"], 1)})
    write("scenarios", rows, "outputs/kpis.json → periods, hazard_means")

    write("portfolio", [{"n_loans": k["meta"]["n_loans"], "n_governorates": k["meta"]["n_governorates"],
                         "total_ead_bn": round(k["meta"]["total_ead_tnd"] / 1e9, 3),
                         "el_base_m": round(k["meta"]["el_base_tnd"] / 1e6, 3),
                         "cmip6_models": len(k["meta"]["cmip6_models"])}], "outputs/kpis.json → meta")

    bs = pd.read_csv(OUT / "by_sector.csv")
    write("sectors", [{"period": r.period, "sector": sector_en[r.sector], "el_add_bp": round(r.el_add_bp_med, 1),
                       "el_add_m": round(r.el_add_med / 1e6, 3), "share_high": round(100 * r.share_ead_high_med, 1)}
                      for r in bs.itertuples()], "outputs/by_sector.csv")

    bg = pd.read_csv(OUT / "by_governorate.csv")
    write("governorates", [{"period": r.period, "governorate": r.governorate, "el_add_bp": round(r.el_add_bp_med, 1),
                            "el_add_bp_p10": round(r.el_add_bp_p10, 1), "el_add_bp_p90": round(r.el_add_bp_p90, 1),
                            "share_high": round(100 * r.share_ead_high_med, 1)} for r in bg.itertuples()],
          "outputs/by_governorate.csv")

    hm_rows = []
    for p, secs in k["heatmap_sector_hazard"].items():
        for s, hz in secs.items():
            for h, v in hz.items():
                hm_rows.append({"period": p, "sector": sector_en[s], "hazard": h, "score": round(v, 3)})
    write("heatmap", hm_rows, "outputs/kpis.json → heatmap_sector_hazard (EAD-weighted mean score)")

    fr2en = {"β": "β"}
    sens = [{"test": s["label"].replace("poids ", "weight ").replace("chaleur", "heat").replace("sécheresse", "drought")
             .replace("inondation", "flood").replace("feux", "fire"), "delta_pct": round(s["delta_pct"], 1),
             "el_add_m": round(s["el_add"] / 1e6, 3)} for s in k["sensitivity"]]
    _ = fr2en
    write("sensitivity", sens, "outputs/kpis.json → sensitivity (SSP5-8.5 · 2050)")

    top = [{"loan": t["loan_id"], "sector": sector_en[[s for s, lab in sl.items() if lab == t["sector_label"]][0]],
            "governorate": t["governorate"], "ead_m": round(t["ead_tnd"] / 1e6, 3),
            "score": round(t["composite"], 3), "el_add_k": round(t["el_add"] / 1e3, 1)}
           for t in k["top20_ssp585_2050"]]
    write("top_exposures", top, "outputs/kpis.json → top20_ssp585_2050")

    pr = json.loads((OUT / "physrisk_comparison.json").read_text())
    write("physrisk", [
        {"indicator": "Heat — rank correlation today", "value": round(pr["heat_spearman_base"], 2)},
        {"indicator": "Heat — rank correlation 2050", "value": round(pr["heat_spearman_2050"], 2)},
        {"indicator": "Drought — rank correlation 2050", "value": round(pr["drought_spearman_2050"], 2)},
    ], "outputs/physrisk_comparison.json")

    g = gpd.read_file(ROOT / "data/raw/tun_adm1.geojson")[["shapeName", "geometry"]]
    from shapely.geometry.polygon import orient
    # d3-geo expects clockwise exterior rings (spherical convention), unlike RFC 7946
    g["geometry"] = g.geometry.simplify(0.01, preserve_topology=True).apply(
        lambda geom: orient(geom, sign=-1.0) if geom.geom_type == "Polygon"
        else type(geom)([orient(p, sign=-1.0) for p in geom.geoms]))
    gj = json.loads(g.rename(columns={"shapeName": "governorate"}).to_json(drop_id=True))
    for f in gj["features"]:
        f["geometry"]["coordinates"] = json.loads(json.dumps(f["geometry"]["coordinates"]),
                                                  parse_float=lambda x: round(float(x), 3))
    (DST / "tunisia_adm1.geojson.json").write_text(json.dumps(gj), encoding="utf-8")
    print("geojson", (DST / "tunisia_adm1.geojson.json").stat().st_size, "bytes")


if __name__ == "__main__":
    main()
