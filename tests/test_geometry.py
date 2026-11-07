import math
import pytest
from go_cfd.geometry import (
    Patch, bounds, cube_patch, geometry_hash, inspect_surface, rotate_to_wind,
    rotated_patch, clean_name, normal_area,
)


def test_cube_closed_and_outward():
    p = cube_patch()
    report = inspect_surface((p,))
    assert report["triangles"] == 12
    assert report["watertight_candidate"] is True
    assert sum(normal_area(t)[1] for t in p.triangles) == pytest.approx(6)
    assert bounds((p,)) == ((0, 0, 0), (1, 1, 1))


def test_open_surface_rejected():
    p = Patch("wall", "a", (((0,0,0), (1,0,0), (0,1,0)),))
    report = inspect_surface((p,))
    assert report["open_edges"] == 3
    assert report["watertight_candidate"] is False


def test_direction_and_hash():
    a = cube_patch()
    b = rotated_patch(a, 90)
    assert rotate_to_wind((0, 1, 0), 90) == pytest.approx((1, 0, 0), abs=1e-12)
    assert geometry_hash((a,)) != geometry_hash((b,))
    assert geometry_hash((a,)) == geometry_hash((cube_patch(),))


def test_patch_name_sanitized():
    assert clean_name("โกดัง & Roof #1") == "Roof_1"
    assert clean_name("123") == "p_123"
    with pytest.raises(ValueError):
        Patch("../bad", "id", cube_patch().triangles)
