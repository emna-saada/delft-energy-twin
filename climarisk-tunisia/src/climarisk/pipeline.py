"""End-to-end pipeline: portfolio -> hazards -> credit -> outputs/ (parquet + kpis.json)."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from . import __version__
from .config import load_yaml, project_root
from .credit import aggregate, apply_credit, ensemble_summary, high_hazard_flag, sensitivity
from .hazards import HAZARDS, asset_hazards
from .portfolio import generate_portfolio

PERIOD_LABELS = {
    "baseline": "Aujourd'hui",
    "ssp245_2030": "SSP2-4.5 · 2030",
    "ssp245_2050": "SSP2-4.5 · 2050",
    "ssp585_2030": "SSP5-8.5 · 2030",
    "ssp585_2050": "SSP5-8.5 · 2050",
}
PORTFOLIO_COLS = ["loan_id", "sector", "sector_label", "governorate", "lon", "lat", "ead_tnd",
                  "pd_base", "lgd_base", "maturity_years", "collateral"]


def run(out_dir: Path | None = None, portfolio: gpd.GeoDataFrame | None = None, **hazard_kwargs) -> dict:
    out_dir = out_dir or project_root() / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    a = load_yaml("assumptions.yaml")

    pf = portfolio if portfolio is not None else generate_portfolio()
    pf.to_parquet(out_dir / "portfolio.parquet")
    hz = asset_hazards(pf, assumptions=a, **hazard_kwargs)
    df = hz.merge(pd.DataFrame(pf[PORTFOLIO_COLS]), on="loan_id", how="left")
    res = apply_credit(df, a)

    # asset-level ensemble median (dashboard / maps)
    num = ["hot35", "hot40", "cdd", "prchange", "flood_depth_m", "fuel", *HAZARDS, "composite",
           "pd_climate", "lgd_climate", "el_base", "el_climate", "el_add"]
    assets = res.groupby(["loan_id", "period"])[num].median().reset_index()
    assets = assets.merge(pd.DataFrame(pf[PORTFOLIO_COLS]), on="loan_id")
    assets["high_hazard"] = high_hazard_flag(assets, a)
    assets.to_parquet(out_dir / "asset_results.parquet")

    by_period = ensemble_summary(res, ["period"])
    by_sector = ensemble_summary(res, ["period", "sector"])
    by_gov = ensemble_summary(res, ["period", "governorate"])
    agg_med = aggregate(assets.assign(model="median"), ["period"])
    sens = sensitivity(df, a)
    for name, t in {"by_period": by_period, "by_sector": by_sector, "by_governorate": by_gov,
                    "sensitivity": sens}.items():
        t.to_csv(out_dir / f"{name}.csv", index=False)

    # heatmap sector x hazard: EAD-weighted mean score (ensemble median)
    heat = {}
    for p, g in assets.groupby("period"):
        w = g["ead_tnd"]
        heat[p] = {s: {h: float(np.average(gs[h], weights=gs["ead_tnd"])) for h in HAZARDS}
                   for s, gs in g.groupby("sector")}
        _ = w

    total_ead = float(pf["ead_tnd"].sum())
    kpis = {
        "meta": {
            "generated": date.today().isoformat(), "version": __version__,
            "disclaimer": "Portefeuille 100 % synthétique — chiffres illustratifs, à calibrer sur des données bancaires réelles.",
            "n_loans": len(pf), "n_governorates": int(pf["governorate"].nunique()),
            "total_ead_tnd": total_ead, "cmip6_models": sorted(res["model"].unique().tolist()),
            "period_labels": PERIOD_LABELS,
            "el_base_tnd": float(assets.loc[assets.period == "baseline", "el_base"].sum()),
        },
        "periods": {
            r.period: {
                "share_ead_high": {"med": r.share_ead_high_med, "p10": r.share_ead_high_p10, "p90": r.share_ead_high_p90},
                "el_add_tnd": {"med": r.el_add_med, "p10": r.el_add_p10, "p90": r.el_add_p90},
                "el_add_bp": {"med": r.el_add_bp_med, "p10": r.el_add_bp_p10, "p90": r.el_add_bp_p90},
                "el_climate_tnd": {"med": r.el_climate_med},
            } for r in by_period.itertuples()
        },
        "hazard_means": {
            p: {"hot35_days": float(g["hot35"].mean()), "cdd_days": float(g["cdd"].mean()),
                "prchange_pct": float(g["prchange"].mean()),
                "flood_exposed_share": float((g["flood_depth_m"] > 0).mean()),
                **{h: float(np.average(g[h], weights=g["ead_tnd"])) for h in HAZARDS}}
            for p, g in assets.groupby("period")
        },
        "by_sector": {
            p: {r.sector: {"el_add_med": r.el_add_med, "share_ead_high_med": r.share_ead_high_med,
                           "el_add_bp_med": r.el_add_bp_med}
                for r in g.itertuples()} for p, g in by_sector.groupby("period")
        },
        "by_governorate": {
            p: {r.governorate: {"el_add_med": r.el_add_med, "share_ead_high_med": r.share_ead_high_med,
                                "el_add_bp_med": r.el_add_bp_med}
                for r in g.itertuples()} for p, g in by_gov.groupby("period")
        },
        "heatmap_sector_hazard": heat,
        "top20_ssp585_2050": assets[assets.period == "ssp585_2050"].nlargest(20, "el_add")[
            ["loan_id", "sector_label", "governorate", "ead_tnd", "composite", "el_add"]].to_dict("records"),
        "sensitivity": sens[["label", "el_add", "delta_pct"]].to_dict("records"),
        "check_total_ead_conserved": bool(np.isclose(agg_med.groupby("period")["ead"].sum().iloc[0], total_ead)),
    }
    with open(out_dir / "kpis.json", "w", encoding="utf-8") as f:
        json.dump(kpis, f, ensure_ascii=False, indent=2, default=float)
    return kpis


if __name__ == "__main__":
    k = run()
    print(json.dumps(k["periods"], indent=1, default=float))
