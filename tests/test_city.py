import numpy as np
from shapely.geometry import box

from delft_twin import city
from delft_twin.pipeline import roof_cells


def test_roof_cells_takes_highest_plane_and_flags_obstacles():
    # two points in the same 0.5 m cell (plane 0 low, plane 1 high), one in the next cell
    pts = {"x": np.array([0.1, 0.2, 0.7]), "y": np.array([9.9, 9.8, 9.9]), "z": np.array([1.0, 5.0, 2.0])}
    labels = {"plane_id": np.array([0, 1, 0]), "obstacle": np.array([False, False, True])}
    rows, cols, pids, obst = roof_cells(pts, labels, origin=(0.0, 10.0), res=0.5, ncols=20)
    assert list(zip(rows, cols, pids)) == [(0, 0, 1), (0, 1, 0)]
    assert obst.tolist() == [False, True]


def test_roof_cells_unlabelled_points_never_form_cells():
    pts = {"x": np.array([0.1]), "y": np.array([9.9]), "z": np.array([3.0])}
    labels = {"plane_id": np.array([-1]), "obstacle": np.array([False])}
    rows, _, _, _ = roof_cells(pts, labels, origin=(0.0, 10.0), res=0.5, ncols=20)
    assert rows.size == 0


def test_tile_box_and_extent():
    assert city.tile_box("84000_447000").equals(box(84000, 447000, 85000, 448000))
    assert city.extent(["84000_447000", "85000_446000"]) == (84000, 446000, 86000, 448000)
