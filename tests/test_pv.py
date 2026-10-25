import numpy as np
import pandas as pd

from delft_twin.pv import battery_dispatch, fill_holes, profile_key, usable_cells

RES = 0.5


def _cells(n, plane_id=0, col0=0, obstacle_at=None, hole_at=None):
    rows, cols = np.divmod(np.arange(n * n), n)
    df = pd.DataFrame({"row": rows, "col": cols + col0, "plane_id": plane_id, "obstacle": False, "kwh_m2": 900.0})
    if obstacle_at is not None:
        df.loc[(df.row == obstacle_at[0]) & (df.col == obstacle_at[1] + col0), "obstacle"] = True
    if hole_at is not None:
        df = df[~((df.row == hole_at[0]) & (df.col == hole_at[1] + col0))]
    return df


def _plane(pid, normal=(0, 0, 1), z=10.0):
    n = np.array(normal, float) / np.linalg.norm(normal)
    return {"plane_id": pid, "nx": n[0], "ny": n[1], "nz": n[2], "cx": 1.0, "cy": 9.0, "cz": z}


def _usable(cells, planes):
    return usable_cells(cells, pd.DataFrame(planes), origin=(0.0, 10.0), res=RES, setback=1)


def test_outline_gets_no_extra_setback():
    # roof cells already start 0.5 m inside the footprint (segmentation inner buffer)
    u = _usable(_cells(5), [_plane(0)])
    assert len(u) == 25 and u.field.nunique() == 1


def test_setback_around_obstacle():
    u = _usable(_cells(7, obstacle_at=(3, 3)), [_plane(0)])
    assert len(u) == 49 - 9                     # obstacle and its 0.5 m ring


def test_coplanar_fragments_are_not_edges():
    c = pd.concat([_cells(4, 0), _cells(4, 1, col0=4)])
    u = _usable(c, [_plane(0), _plane(1)])     # two flat fragments at the same height
    assert len(u) == 32 and u.field.nunique() == 1


def test_step_between_planes_is_an_edge():
    c = pd.concat([_cells(4, 0), _cells(4, 1, col0=4)])
    u = _usable(c, [_plane(0, z=10.0), _plane(1, z=11.0)])  # 1 m step
    assert len(u) == 32 - 8 and u.field.nunique() == 2      # one column lost on each side of the step


def test_interior_hole_is_filled_not_an_edge():
    u = _usable(_cells(5, hole_at=(2, 2)), [_plane(0)])
    assert len(u) == 25                         # same as without the hole
    assert u.kwh_m2.isna().sum() == 1           # filled cell carries no irradiance of its own


def test_fill_holes_needs_majority():
    lab = np.full((3, 3), 7)
    lab[1, 1] = -1
    assert fill_holes(lab, np.zeros((3, 3), bool))[1, 1] == 7


def test_battery_conserves_energy():
    rng = np.random.default_rng(0)
    prod = rng.uniform(0, 3, (48, 5))
    dem = rng.uniform(0, 2, (48, 5))
    imp, exp = battery_dispatch(prod, dem, cap=np.full(5, 5.0), power=np.full(5, 2.5), eff=0.9)
    covered = dem.sum(0) - imp.sum(0)
    assert np.all(covered + exp.sum(0) <= prod.sum(0) + 1e-9)        # losses only take energy away
    assert np.all(covered >= np.minimum(prod, dem).sum(0) - 1e-9)    # battery never lowers self-consumption
    assert np.all((imp >= 0) & (exp >= 0))


def test_profile_key_bins():
    assert profile_key(True, 2.0, 123.0) == "EW"
    assert profile_key(False, 41.0, 187.0) == (40, 180)
    assert profile_key(False, 44.0, 355.0) == (45, 0)
