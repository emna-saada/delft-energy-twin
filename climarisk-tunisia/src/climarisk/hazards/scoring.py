"""Normalisation of hazard indicators to 0-1 scores with fixed, documented bounds."""
from __future__ import annotations

import numpy as np


def linear_score(x, low: float, high: float):
    """Monotone 0-1 score; works for decreasing bounds (high < low) too."""
    x = np.asarray(x, dtype="float64")
    s = (x - low) / (high - low)
    return np.clip(np.nan_to_num(s, nan=0.0), 0.0, 1.0)


def heat_score(hot35_days, a: dict):
    b = a["hazard_normalisation"]["heat_days_35"]
    return linear_score(hot35_days, b["low"], b["high"])


def drought_score(cdd, prchange, a: dict):
    n = a["hazard_normalisation"]
    w = a["drought_weights"]
    s_cdd = linear_score(cdd, n["drought_cdd"]["low"], n["drought_cdd"]["high"])
    s_pr = linear_score(prchange, n["drought_prchange"]["low"], n["drought_prchange"]["high"])
    return (w["cdd"] * s_cdd + w["prchange"] * s_pr) / (w["cdd"] + w["prchange"])


def flood_score(depth_m, a: dict):
    b = a["hazard_normalisation"]["flood_depth_m"]
    return linear_score(depth_m, b["low"], b["high"])


def fire_score(fuel_fraction, heat_s, drought_s, a: dict):
    """Fire needs fuel: score = fuel * (w_fuel + w_weather * weather), weather = mean(heat, drought)."""
    w = a["fire_weights"]
    weather = 0.5 * (np.asarray(heat_s) + np.asarray(drought_s))
    fuel = np.clip(np.asarray(fuel_fraction, dtype="float64"), 0, 1)
    return np.clip(fuel * (w["fuel"] + w["weather"] * weather) / (w["fuel"] + w["weather"]), 0, 1)
