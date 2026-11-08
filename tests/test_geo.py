import pytest

from darkships.geo import KM_PER_NM, angle_diff_deg, haversine_km, haversine_nm


def test_one_degree_of_latitude_is_111_195_km():
    assert haversine_km(0, 0, 1, 0) == pytest.approx(111.195, abs=0.01)
    assert haversine_nm(0, 0, 1, 0) == pytest.approx(111.195 / KM_PER_NM, abs=0.01)


def test_identical_points_are_zero_apart():
    assert haversine_nm(29.3, -94.7, 29.3, -94.7) == 0


def test_angle_diff_wraps_around_north():
    assert angle_diff_deg(350, 10) == 20
