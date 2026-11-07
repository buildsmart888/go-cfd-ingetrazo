import pytest
from go_cfd.geometry import cube_patch
from go_cfd.loads import (
    Wrench, integrate_pressure, mapped_load_balance,
    kinematic_to_pa, pressure_coefficient, reference_pressure_pa,
)


def test_reference_pressure_and_units():
    assert reference_pressure_pa(1.225, 20) == pytest.approx(245.0)
    assert kinematic_to_pa(100, 1.225) == pytest.approx(122.5)
    assert pressure_coefficient(300, 55, 245) == pytest.approx(1)
    with pytest.raises(ValueError):
        reference_pressure_pa(1.225, 0)


def test_closed_cube_uniform_pressure_net_zero():
    triangles = cube_patch().triangles
    total = integrate_pressure(triangles, (10.0,) * len(triangles))
    assert total.force_N == pytest.approx((0,0,0), abs=1e-9)
    assert total.moment_Nm == pytest.approx((0,0,0), abs=1e-9)
    assert total.pressure_area_m2 == pytest.approx(6)


def test_windward_pressure_pushes_x():
    triangles = cube_patch().triangles
    # The last-but-one cube face is -X in the reference cube factory.
    pressures = (0.0,)*8 + (100.0, 100.0) + (0.0,)*2
    total = integrate_pressure(triangles, pressures)
    assert total.force_N == pytest.approx((100,0,0))
    assert total.moment_Nm == pytest.approx((0,50,-50))


def test_mapped_balance_check():
    a = Wrench((10,0,0),(0,5,0),1)
    assert mapped_load_balance(a, a)["passed"]
    assert not mapped_load_balance(a, Wrench((8,0,0),(0,5,0),1))["passed"]
