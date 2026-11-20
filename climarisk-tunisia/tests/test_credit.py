import numpy as np
import pandas as pd

from climarisk.credit import aggregate, apply_credit, ensemble_summary, sensitivity
from climarisk.vulnerability import composite_score


def test_composite_in_unit_interval(tiny_results, assumptions):
    c = composite_score(tiny_results, assumptions)
    assert ((c >= 0) & (c <= 1)).all()


def test_pd_and_lgd_stay_in_unit_interval(tiny_results, assumptions):
    extreme = tiny_results.assign(pd_base=0.9, lgd_base=0.95, heat=1, drought=1, flood=1, fire=1)
    res = apply_credit(extreme, assumptions, beta_multiplier=5)
    assert res["pd_climate"].between(0, 1).all()
    assert res["lgd_climate"].between(0, 1).all()


def test_pd_uplift_monotone_in_hazard(tiny_results, assumptions):
    low = apply_credit(tiny_results.assign(heat=0.1, drought=0.1, flood=0.1, fire=0.1), assumptions)
    high = apply_credit(tiny_results.assign(heat=0.9, drought=0.9, flood=0.9, fire=0.9), assumptions)
    assert (high["pd_climate"].to_numpy() >= low["pd_climate"].to_numpy()).all()
    assert (high["el_add"].to_numpy() >= low["el_add"].to_numpy()).all()


def test_zero_hazard_means_zero_additional_loss(tiny_results, assumptions):
    res = apply_credit(tiny_results.assign(heat=0, drought=0, flood=0, fire=0), assumptions)
    assert np.allclose(res["el_add"], 0)


def test_aggregation_conserves_ead(tiny_results, assumptions):
    res = apply_credit(tiny_results, assumptions)
    one = res[(res.period == "baseline") & (res.model == "A")]
    total = one["ead_tnd"].sum()
    for by in (["sector"], ["governorate"], ["sector", "governorate"]):
        assert np.isclose(aggregate(one, by)["ead"].sum(), total)
    assert np.isclose(aggregate(one, ["sector"])["el_add"].sum(), one["el_add"].sum())


def test_ensemble_band_is_ordered(tiny_results, assumptions):
    res = apply_credit(tiny_results, assumptions)
    s = ensemble_summary(res, ["period"])
    assert (s["el_add_p10"] <= s["el_add_med"] + 1e-9).all()
    assert (s["el_add_med"] <= s["el_add_p90"] + 1e-9).all()


def test_sensitivity_beta_is_monotone(tiny_results, assumptions):
    sens = sensitivity(tiny_results, assumptions, period="ssp585_2050")
    b = sens[sens.test == "beta"].sort_values("value")
    assert (np.diff(b["el_add"].to_numpy()) >= 0).all()
    assert isinstance(sens, pd.DataFrame)
