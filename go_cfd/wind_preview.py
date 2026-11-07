"""Lightweight *illustrative* wind paths for a responsive BIM viewport preview.

This is NOT a CFD solver or a pressure/velocity field. Trajectories are simple
curves bent around a bounding proxy; they must never be interpreted as results.
Pure Python, independent of IngeTrazo, Qt and OpenFOAM.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

Vec3 = tuple[float, float, float]


@dataclass(frozen=True)
class PreviewLines:
    """Precomputed world-space tracks for the paint overlay."""

    tracks: tuple[tuple[Vec3, ...], ...]
    bounds_min: Vec3
    bounds_max: Vec3
    direction_to_deg: float


def _check_bounds(lo: Vec3, hi: Vec3) -> None:
    if len(lo) != 3 or len(hi) != 3:
        raise ValueError("Preview bounds must be 3D")
    if not all(math.isfinite(v) for v in (*lo, *hi)):
        raise ValueError("Preview bounds must be finite")
    if any(hi[i] < lo[i] for i in range(3)):
        raise ValueError("Preview maximum must not be below minimum")


def build_preview_lines(
    lo: Vec3, hi: Vec3, direction_to_deg: float, *,
    count: int = 24, samples: int = 49,
) -> PreviewLines:
    """Return reproducible 3D illustration tracks around a model's AABB.

    The function uses a smooth, deliberately schematic lateral displacement
    near a bounding proxy. No flow equations or pressure coefficients are used.
    The air-flow angle is *to* world +X=0deg, +Y=90deg.
    """
    _check_bounds(lo, hi)
    if not math.isfinite(direction_to_deg):
        raise ValueError("Direction must be finite")
    if not 0 <= direction_to_deg < 360:
        raise ValueError("Direction must be [0, 360)")
    if not 4 <= count <= 120:
        raise ValueError("Track count must be in [4, 120]")
    if not 10 <= samples <= 300:
        raise ValueError("Samples must be in [10, 300]")

    cx, cy, cz = tuple((lo[i] + hi[i]) / 2 for i in range(3))
    dims = tuple(hi[i] - lo[i] for i in range(3))
    size = max(dims[0], dims[1], dims[2], 0.5)
    radius = size * 0.7
    r_clear = radius * 1.22
    theta = math.radians(direction_to_deg)
    dx, dy = math.cos(theta), math.sin(theta)
    px, py = -dy, dx

    rows = max(2, round(math.sqrt(count / 1.6)))
    cols = math.ceil(count / rows)
    z_lo = lo[2] + 0.12 * max(dims[2], 0.2)
    z_hi = hi[2] + 0.4 * max(dims[2], 0.2)
    if z_hi <= z_lo:
        z_hi = z_lo + size
    tracks: list[tuple[Vec3, ...]] = []
    for index in range(count):
        row, col = divmod(index, cols)
        row_norm = row / (rows - 1) if rows > 1 else 0.5
        col_norm = col / (cols - 1) if cols > 1 else 0.5
        lateral = (-1.7 + 3.4 * col_norm) * radius
        vertical = z_lo + (z_hi - z_lo) * row_norm - cz
        # Deliberately approximate visual deflection, NOT a stream function.
        cross_radius = max(math.hypot(lateral, vertical), size * 0.01)
        bend = max(0.0, r_clear - cross_radius)
        points: list[Vec3] = []
        for j in range(samples):
            s = (-4.5 + 11.0 * j / (samples - 1)) * radius
            envelope = math.exp(-((s / (2.1 * radius)) ** 4))
            outward = bend * envelope
            yl = lateral * (1.0 + outward / cross_radius)
            zl = vertical * (1.0 + outward / cross_radius)
            points.append((cx + s*dx + yl*px,
                           cy + s*dy + yl*py, cz + zl))
        tracks.append(tuple(points))
    return PreviewLines(tuple(tracks), lo, hi, direction_to_deg)


def point_at_fraction(track: tuple[Vec3, ...], fraction: float) -> Vec3:
    """Interpolate particle position on a precomputed track; fraction wraps."""
    if len(track) < 2:
        raise ValueError("A wind track needs at least two points")
    if not math.isfinite(fraction):
        raise ValueError("Particle position must be finite")
    t = (fraction % 1.0) * (len(track) - 1)
    i = min(int(t), len(track) - 2)
    f = t - i
    a, b = track[i], track[i+1]
    return tuple(a[k] + (b[k]-a[k])*f for k in range(3))
