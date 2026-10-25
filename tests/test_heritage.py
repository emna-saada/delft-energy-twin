import geopandas as gpd
from shapely.geometry import box

from delft_twin.heritage import front_edges


def _scene():
    # street along the south (y < 0); a private 3 m front strip; two terraced houses (party wall at x = 6);
    # a rear annex that faces the houses across a yard but not the street
    street = gpd.GeoDataFrame(geometry=[box(-20, -10, 30, -3)], crs="EPSG:28992")
    houses = gpd.GeoDataFrame({"identificatie": ["A", "B", "C"], "in_protected_view": True},
                              geometry=[box(0, 0, 6, 10), box(6, 0, 12, 10), box(0, 20, 12, 26)], crs="EPSG:28992")
    return houses, street


def test_front_found_behind_private_strip():
    houses, street = _scene()
    fr = front_edges(houses, street)
    a = fr[fr.identificatie == "A"]
    assert a.length.sum() >= 5.5                       # the 6 m street facade of house A
    assert (a.geometry.centroid.y.abs() < 0.01).all()  # ... and only that facade (y = 0)


def test_party_wall_and_rear_annex_are_not_fronts():
    houses, street = _scene()
    fr = front_edges(houses, street)
    on_party_wall = fr.geometry.centroid.x.sub(6).abs() < 0.01
    assert not (on_party_wall & (fr.geometry.length > 0)).any()
    assert "C" not in set(fr.identificatie)            # its view to the street is blocked by A and B
