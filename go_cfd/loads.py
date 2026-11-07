"""Pressure-to-force calculations and postprocessing unit conversions."""
from __future__ import annotations

from dataclasses import dataclass
import math
from .geometry import Triangle, Vec3, cross, normal_area, vector_sub


@dataclass(frozen=True)
class Wrench:
    force_N: Vec3
    moment_Nm: Vec3
    pressure_area_m2: float


def _add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])


def reference_pressure_pa(density_kgm3: float, speed_ms: float) -> float:
    if not math.isfinite(density_kgm3) or density_kgm3 <= 0:
        raise ValueError("Air density must be positive")
    if not math.isfinite(speed_ms) or speed_ms <= 0:
        raise ValueError("Reference wind speed must be positive")
    return 0.5 * density_kgm3 * speed_ms * speed_ms


def kinematic_to_pa(kinematic_p_m2s2: float, density_kgm3: float) -> float:
    """In incompressible OpenFOAM, p is often kinematic pressure (m2/s2)."""
    if density_kgm3 <= 0:
        raise ValueError("Air density must be positive")
    return kinematic_p_m2s2 * density_kgm3


def pressure_coefficient(p_surface_pa: float, p_reference_pa: float, q_ref_pa: float) -> float:
    if not math.isfinite(q_ref_pa) or q_ref_pa <= 0:
        raise ValueError("Reference dynamic pressure must be positive")
    return (p_surface_pa - p_reference_pa) / q_ref_pa


def integrate_pressure(
    triangles: tuple[Triangle, ...],
    net_pressures_pa: tuple[float, ...],
    origin_m: Vec3 = (0.0, 0.0, 0.0),
) -> Wrench:
    """Positive net pressure PUSHES IN: force = -pressure*area*outward_normal."""
    if len(triangles) != len(net_pressures_pa):
        raise ValueError("Need one net surface pressure per triangle")
    force = (0.0, 0.0, 0.0)
    moment = (0.0, 0.0, 0.0)
    area_sum = 0.0
    for triangle, pressure in zip(triangles, net_pressures_pa):
        if not math.isfinite(pressure):
            raise ValueError("Pressure must be finite")
        n, area = normal_area(triangle)
        if area < 1e-12:
            raise ValueError("Cannot integrate degenerate triangle")
        face_force = tuple(-pressure * area * x for x in n)
        centre = tuple(sum(v[i] for v in triangle)/3 for i in range(3))
        lever = vector_sub(centre, origin_m)
        force = _add(force, face_force)
        moment = _add(moment, cross(lever, face_force))
        area_sum += area
    return Wrench(force, moment, area_sum)


def mapped_load_balance(reference: Wrench, mapped: Wrench, *,
                        tol_force_N: float = 1e-4, tol_moment_Nm: float = 1e-4) -> dict:
    df = tuple(a-b for a,b in zip(reference.force_N, mapped.force_N))
    dm = tuple(a-b for a,b in zip(reference.moment_Nm, mapped.moment_Nm))
    f_error = math.sqrt(sum(x*x for x in df))
    m_error = math.sqrt(sum(x*x for x in dm))
    return {"force_residual_N": f_error, "moment_residual_Nm": m_error,
            "passed": f_error <= tol_force_N and m_error <= tol_moment_Nm}
