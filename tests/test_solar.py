import numpy as np
import pytest

from delft_twin import data, solar


@pytest.fixture(scope="module")
def setup():
    cfg = data.load_config()
    tmy, _ = solar.pvgis_tmy(cfg["site"]["lat"], cfg["site"]["lon"], data.RAW / "pvgis_tmy.json")
    return cfg, tmy


def _run(cfg, tmy, dsm, rows, cols, z, nrm):
    out, svf, wx = solar.run_tile(np.array(rows), np.array(cols), np.array(z, float), np.array(nrm, float),
                                  dsm, dsm.copy(), 0.5, tmy, cfg)
    return out, svf, wx


def test_open_horizontal_plane_receives_ghi(setup):
    cfg, tmy = setup
    dsm = np.zeros((200, 200))
    out, svf, wx = _run(cfg, tmy, dsm, [100], [100], [0.0], [[0, 0, 1]])
    assert out[0, 2] == pytest.approx(wx["ghi_kwh"], rel=0.02)   # beam*sin(e) + DHI ~ GHI
    assert out[0, 0] == pytest.approx(out[0, 2], rel=1e-6)       # nothing obstructs
    assert svf[0] == pytest.approx(1.0, abs=0.01)


def test_wall_to_the_south_shades_cell(setup):
    cfg, tmy = setup
    dsm = np.zeros((200, 200))
    dsm[110:112, :] = 20.0          # 20 m wall, 5 m south of the cell
    out, svf, _ = _run(cfg, tmy, dsm, [100], [100], [0.0], [[0, 0, 1]])
    assert out[0, 0] < 0.6 * out[0, 2]
    assert svf[0] < 0.95


def test_north_facing_steep_roof_gets_less_than_south(setup):
    cfg, tmy = setup
    dsm = np.zeros((200, 200))
    t = np.radians(45)
    south, north = [0, -np.sin(t), np.cos(t)], [0, np.sin(t), np.cos(t)]
    out, _, _ = _run(cfg, tmy, dsm, [100, 100], [100, 100], [0.0, 0.0], [south, north])
    assert out[0, 0] > 1.5 * out[1, 0]
