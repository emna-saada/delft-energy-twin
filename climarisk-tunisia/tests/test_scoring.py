import numpy as np

from climarisk.hazards import scoring


def test_linear_score_bounds_and_monotone():
    x = np.linspace(-50, 300, 200)
    s = scoring.linear_score(x, 0, 120)
    assert s.min() >= 0 and s.max() <= 1
    assert np.all(np.diff(s) >= 0)


def test_decreasing_bounds_for_precipitation_change():
    s = scoring.linear_score(np.array([10, 0, -15, -30, -60]), 0, -30)
    assert list(s) == [0, 0, 0.5, 1, 1]


def test_scores_monotone_in_intensity(assumptions):
    days = np.arange(0, 200)
    assert np.all(np.diff(scoring.heat_score(days, assumptions)) >= 0)
    depth = np.linspace(0, 5, 50)
    assert np.all(np.diff(scoring.flood_score(depth, assumptions)) >= 0)
    cdd = np.linspace(0, 300, 50)
    d = scoring.drought_score(cdd, np.zeros_like(cdd), assumptions)
    assert np.all(np.diff(d) >= 0)


def test_fire_needs_fuel(assumptions):
    assert scoring.fire_score(np.zeros(3), np.ones(3), np.ones(3), assumptions).max() == 0
    f = scoring.fire_score(np.ones(3), np.array([0, 0.5, 1]), np.array([0, 0.5, 1]), assumptions)
    assert np.all(np.diff(f) > 0) and f.max() <= 1


def test_nan_is_treated_as_no_hazard():
    assert scoring.linear_score(np.array([np.nan]), 0, 1)[0] == 0
