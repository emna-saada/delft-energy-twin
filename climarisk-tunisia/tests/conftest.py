import numpy as np
import pandas as pd
import pytest

from climarisk.config import load_yaml
from climarisk.hazards import HAZARDS


@pytest.fixture
def assumptions():
    return load_yaml("assumptions.yaml")


@pytest.fixture
def tiny_results():
    """Tiny merged hazard + portfolio table (3 assets x 2 periods x 2 models)."""
    rng = np.random.default_rng(0)
    rows = []
    for p in ("baseline", "ssp585_2050"):
        for m in ("A", "B"):
            for i, sector in enumerate(["cereals", "tourism", "residential"]):
                scores = rng.uniform(0, 1, len(HAZARDS)) * (1.3 if p != "baseline" else 0.7)
                rows.append({"loan_id": f"SYN-{i}", "period": p, "model": m, "sector": sector,
                             "governorate": ["Béja", "Sousse", "Tunis"][i],
                             "ead_tnd": [1e5, 2e6, 3e5][i], "pd_base": 0.03, "lgd_base": 0.4,
                             "collateral": ["land", "real_estate", "real_estate"][i],
                             **dict(zip(HAZARDS, np.clip(scores, 0, 1)))})
    return pd.DataFrame(rows)
