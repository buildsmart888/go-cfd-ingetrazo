"""Offline wind animation tests: NEVER a claim of CFD correctness."""
import math
import pytest

from go_cfd.wind_preview import build_preview_lines, point_at_fraction


def test_24_lines_with_3d_direction_and_finite_vertices():
    p = build_preview_lines((0, 0, 0), (4, 3, 2), 0, count=24)
    assert len(p.tracks) == 24
    assert len(p.tracks[0]) == 49
    assert all(len(v) == 3 and all(map(math.isfinite, v)) for t in p.tracks for v in t)
    assert all(t[-1][0] > t[0][0] for t in p.tracks)


def test_flow_to_90_is_positive_y_direction():
    p = build_preview_lines((0, 0, 0), (2, 2, 2), 90, count=8)
    assert all(t[-1][1] > t[0][1] for t in p.tracks)
    assert all(abs(t[-1][0] - t[0][0]) < 1e-8 for t in p.tracks)


def test_particle_fraction_wraps_and_interpolates():
    path = ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (4.0, 0.0, 0.0))
    assert point_at_fraction(path, 0.25) == (1.0, 0.0, 0.0)
    assert point_at_fraction(path, 1.25) == point_at_fraction(path, 0.25)


def test_invalid_preview_inputs_rejected():
    with pytest.raises(ValueError):
        build_preview_lines((0, 0, 0), (2, -1, 0), 0)
    with pytest.raises(ValueError):
        build_preview_lines((0, 0, 0), (1, 1, 1), float('nan'))
    with pytest.raises(ValueError):
        build_preview_lines((0, 0, 0), (1, 1, 1), 0, count=200)
    with pytest.raises(ValueError):
        point_at_fraction(((0, 0, 0),), .5)
