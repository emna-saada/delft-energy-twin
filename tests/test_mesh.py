import json
import struct

import numpy as np
from shapely.geometry import Polygon, box

from delft_twin import mesh


def test_triangulate_covers_polygon_counter_clockwise():
    poly = Polygon([(0, 0), (10, 0), (10, 4), (6, 4), (6, 8), (0, 8)])  # L-shape
    t = mesh.triangulate(poly)
    area = 0.5 * np.abs(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])).sum()
    signed = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    assert np.isclose(area, poly.area) and (signed > 0).all()


def test_rdp_keeps_gable_peak_and_drops_flat_points():
    s = np.linspace(0, 6, 7)
    flat = mesh.rdp_keep(s, np.full(7, 9.0), 0.3)
    gable = mesh.rdp_keep(s, np.array([9, 10, 11, 12, 11, 10, 9.0]), 0.3)
    assert flat.tolist() == [0, 6]
    assert gable.tolist() == [0, 3, 6]


def test_wall_segments_follow_roof_and_ground():
    ring = np.asarray(box(0, 0, 6, 10).exterior.coords)
    roof = lambda x, y: 10 + np.minimum(np.asarray(x), 6 - np.asarray(x))  # ridge along x = 3  # noqa: E731
    a, b, za, zb = mesh.wall_segments(ring, roof, (3, 5), g0=0.0)
    assert len(a) <= 8                                      # 4 edges, gable ends split once at the ridge
    assert np.isclose(max(za.max(), zb.max()), 13, atol=0.35)


def test_color_of_scalar_and_nan():
    assert mesh.color_of(np.nan).tolist() == list(mesh.WALL_RGB)
    assert mesh.color_of([200.0, 1200.0]).shape == (2, 3)


def test_glb_roundtrip(tmp_path):
    v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
    n = np.tile([0, 0, 1.0], (4, 1))
    f = np.array([[0, 1, 2], [0, 2, 3]])
    p = tmp_path / "t.glb"
    mesh.write_glb(p, v, n, np.full((4, 3), 128, np.uint8), f)
    b = p.read_bytes()
    magic, ver, length = struct.unpack("<III", b[:12])
    jl = struct.unpack("<I", b[12:16])[0]
    js = json.loads(b[20:20 + jl])
    assert magic == 0x46546C67 and ver == 2 and length == len(b)
    assert js["accessors"][0]["count"] == 4 and js["accessors"][3]["count"] == 6
    # y-up: ENU (E, N, U) -> glTF (E, U, -N)
    assert js["accessors"][0]["max"] == [1.0, 1.0, 0.0] and js["accessors"][0]["min"] == [0.0, 0.0, -1.0]


def test_enu_to_ecef_is_orthonormal():
    m = mesh.enu_to_ecef(4.36, 52.01)
    r = m[:3, :3]
    assert np.allclose(r.T @ r, np.eye(3), atol=1e-12)
    assert np.isclose(np.linalg.norm(m[:3, 3]), 6364.9e3, rtol=1e-3)
