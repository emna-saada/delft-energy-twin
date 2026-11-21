"""Credit translation: climate-adjusted PD, LGD, expected loss and aggregations.

PD_s  = min(1, PD_base * (1 + beta_sector * Score_s))
LGD_s = min(1, LGD_base * (1 + gamma * flood_score))      (land / real-estate collateral only)
EL_s  = PD_s * LGD_s * EAD
Additional climate EL = EL_s - PD_base * LGD_base * EAD

PD_base is treated as climate-neutral (illustrative assumption): the uplift therefore
also exists "today". Increments vs today are reported separately (``vs_today``).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import load_yaml
from .vulnerability import composite_score


def beta_for(sectors: pd.Series, a: dict, multiplier: float = 1.0) -> np.ndarray:
    b = a["beta"]
    return sectors.map(lambda s: b.get(s, b["default"])).to_numpy(dtype=float) * multiplier


def apply_credit(df: pd.DataFrame, assumptions: dict | None = None,
                 beta_multiplier: float = 1.0) -> pd.DataFrame:
    """``df`` = hazard table merged with portfolio columns (sector, ead_tnd, pd_base, lgd_base, collateral)."""
    a = assumptions or load_yaml("assumptions.yaml")
    out = df.copy()
    out["composite"] = composite_score(out, a)
    beta = beta_for(out["sector"], a, beta_multiplier)
    out["pd_climate"] = np.minimum(1.0, out["pd_base"] * (1 + beta * out["composite"]))
    lgd_sensitive = out["collateral"].isin(["real_estate", "land"]).to_numpy()
    uplift = np.where(lgd_sensitive, a["gamma_lgd_flood"] * out["flood"], 0.0)
    out["lgd_climate"] = np.minimum(1.0, out["lgd_base"] * (1 + uplift))
    out["el_base"] = out["pd_base"] * out["lgd_base"] * out["ead_tnd"]
    out["el_climate"] = out["pd_climate"] * out["lgd_climate"] * out["ead_tnd"]
    out["el_add"] = out["el_climate"] - out["el_base"]
    out["high_hazard"] = high_hazard_flag(out, a)
    return out


def high_hazard_flag(df: pd.DataFrame, a: dict) -> pd.Series:
    """An exposure is in a high-hazard zone when at least one hazard that is material for its
    sector (vulnerability >= materiality threshold) scores above the high-hazard threshold."""
    from .hazards import HAZARDS
    from .vulnerability import vulnerability_matrix

    V = vulnerability_matrix(a).loc[df["sector"]].to_numpy()
    material = V >= a["materiality_min_vulnerability"]
    s = df[list(HAZARDS)].to_numpy()
    return pd.Series(((s >= a["high_hazard_threshold"]) & material).any(axis=1), index=df.index)


def aggregate(res: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Sum EAD / EL over groups; EAD is conserved (sum over groups == total)."""
    g = res.assign(ead_high=res["ead_tnd"] * res["high_hazard"]).groupby(by, observed=True)
    agg = g.agg(n=("loan_id", "size"), ead=("ead_tnd", "sum"), ead_high=("ead_high", "sum"),
                el_base=("el_base", "sum"), el_climate=("el_climate", "sum"), el_add=("el_add", "sum"),
                composite=("composite", "mean"))
    agg["share_ead_high"] = agg["ead_high"] / agg["ead"]
    agg["el_add_bp"] = 1e4 * agg["el_add"] / agg["ead"]
    return agg.reset_index()


def ensemble_summary(res: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Per-model aggregates -> median and 10-90 % band across climate models."""
    per_model = aggregate(res, by + ["model"])
    q = per_model.groupby(by)[["el_add", "el_climate", "share_ead_high", "el_add_bp"]]
    med = q.median().add_suffix("_med")
    lo = q.quantile(0.1).add_suffix("_p10")
    hi = q.quantile(0.9).add_suffix("_p90")
    return pd.concat([med, lo, hi], axis=1).reset_index()


def sensitivity(df: pd.DataFrame, assumptions: dict | None = None, period: str = "ssp585_2050") -> pd.DataFrame:
    """Sensitivity of total additional EL (ensemble median) to beta and to hazard weights."""
    import copy

    a = assumptions or load_yaml("assumptions.yaml")
    sub = df[df["period"] == period]
    rows = []

    def total(res):
        return res.groupby("model")["el_add"].sum().median()

    base = total(apply_credit(sub, a))
    for m in a["sensitivity"]["beta_multipliers"]:
        rows.append({"test": "beta", "label": f"β × {m}", "value": m,
                     "el_add": total(apply_credit(sub, a, m))})
    pert = a["sensitivity"]["weight_perturbation"]
    from .hazards import HAZARDS
    FR = {"heat": "chaleur", "drought": "sécheresse", "flood": "inondation", "fire": "feux"}
    for h in HAZARDS:
        for sign in (-1, 1):
            a2 = copy.deepcopy(a)
            for s in a2["vulnerability"]:
                a2["vulnerability"][s][h] = max(0.0, a2["vulnerability"][s][h] * (1 + sign * pert))
            rows.append({"test": "weight", "label": f"poids {FR[h]} {'+' if sign > 0 else '−'}{int(pert*100)} %",
                         "value": sign * pert, "el_add": total(apply_credit(sub, a2))})
    out = pd.DataFrame(rows)
    out["delta_pct"] = 100 * (out["el_add"] / base - 1)
    out["base"] = base
    return out


def vs_today(res: pd.DataFrame) -> pd.DataFrame:
    """Additional EL relative to today's climate, per period: median and 10-90 % across models
    (each model's future EL minus the same model's baseline EL)."""
    tot = res.groupby(["period", "model"])["el_add"].sum().unstack("period")
    delta = tot.sub(tot["baseline"], axis=0)
    out = pd.DataFrame({"med": delta.median(), "p10": delta.quantile(0.1), "p90": delta.quantile(0.9)})
    return out.rename_axis("period").reset_index()
