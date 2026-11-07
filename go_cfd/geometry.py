"""Host-independent CFD surface geometry: validation, hashing, ASCII STL.

All coordinates are metres. A patch is made from outward-oriented triangles.
This module never mutates an IngeTrazo scene or any source mesh.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import math
import re
import struct
from collections import Counter
from typing import Iterable

Vec3 = tuple[float, float, float]
Triangle = tuple[Vec3, Vec3, Vec3]


def vector_sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def dot(a: Vec3, b: Vec3) -> float:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def normal_area(t: Triangle) -> tuple[Vec3, float]:
    n = cross(vector_sub(t[1], t[0]), vector_sub(t[2], t[0]))
    d = math.sqrt(dot(n, n))
    return ((n[0]/d, n[1]/d, n[2]/d), d/2) if d > 1e-14 else ((0, 0, 0), 0.0)


def clean_name(value: str, *, maxlen: int = 48) -> str:
    """OpenFOAM patch name with safe ASCII characters and leading letter."""
    name = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")[:maxlen]
    return ("p_" + name) if not name or not name[0].isalpha() else name


@dataclass(frozen=True)
class Patch:
    name: str
    source_id: str
    triangles: tuple[Triangle, ...]

    def __post_init__(self):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", self.name):
            raise ValueError(f"Invalid CFD patch name: {self.name!r}")
        if not self.triangles:
            raise ValueError(f"Patch {self.name} is empty")
        for tri in self.triangles:
            if len(tri) != 3 or any(len(p) != 3 or not all(map(math.isfinite, p)) for p in tri):
                raise ValueError(f"Invalid triangle in patch {self.name}")


def rotate_to_wind(p: Vec3, bearing_deg: float) -> Vec3:
    """Rotate world XY by -bearing; incoming wind is +CFD X.

    Convention: bearing=0 means wind MOVES towards world +X, 90 towards +Y.
    It is not the meteorological 'wind FROM' compass direction.
    """
    a = math.radians(bearing_deg)
    c, s = math.cos(a), math.sin(a)
    return (c*p[0] + s*p[1], -s*p[0] + c*p[1], p[2])


def rotated_patch(patch: Patch, bearing_deg: float) -> Patch:
    return Patch(patch.name, patch.source_id, tuple(
        tuple(rotate_to_wind(v, bearing_deg) for v in t) for t in patch.triangles))


def bounds(patches: Iterable[Patch]) -> tuple[Vec3, Vec3]:
    coords = [p for patch in patches for tri in patch.triangles for p in tri]
    if not coords:
        raise ValueError("No CFD surface geometry supplied")
    return (tuple(min(p[i] for p in coords) for i in range(3)),
            tuple(max(p[i] for p in coords) for i in range(3)))


def geometry_hash(patches: Iterable[Patch]) -> str:
    """Stable hash of evaluated world triangles, before wind rotation."""
    digest = sha256()
    for patch in sorted(patches, key=lambda v: v.name):
        digest.update(patch.name.encode("utf-8"))
        digest.update(patch.source_id.encode("utf-8"))
        for tri in patch.triangles:
            for vertex in tri:
                digest.update(struct.pack("<3d", *vertex))
    return digest.hexdigest()


def _edge_key(a: Vec3, b: Vec3, digits: int = 7):
    """Quantize for tolerance-based edge matching; all units metres."""
    a = tuple(round(x, digits) for x in a)
    b = tuple(round(x, digits) for x in b)
    return tuple(sorted((a, b)))


def inspect_surface(patches: Iterable[Patch]) -> dict:
    """Preliminary closed-manifold, orientation and signed-volume screening.

    This is NOT a proof that surfaces do not self-intersect or enclose the
    intended CFD solid; external mesh QA remains required.
    """
    patches = tuple(patches)
    edges: Counter = Counter()
    directions: Counter = Counter()
    degenerate = 0
    count = 0
    signed_volume = 0.0
    origin = bounds(patches)[0] if patches else (0.0, 0.0, 0.0)
    for patch in patches:
        for tri in patch.triangles:
            count += 1
            if normal_area(tri)[1] < 1e-12:
                degenerate += 1
                continue
            a, b, c = tri
            av, bv, cv = (vector_sub(v, origin) for v in (a, b, c))
            signed_volume += dot(av, cross(bv, cv)) / 6.0
            for u, v in ((a, b), (b, c), (c, a)):
                edge = _edge_key(u, v)
                edges[edge] += 1
                # For each shared edge, adjacent outward triangles have
                # opposite directions. Count +1 against the sorted key.
                first = tuple(round(x, 7) for x in u)
                directions[edge] += 1 if first == edge[0] else -1
    open_edges = sum(1 for n in edges.values() if n == 1)
    nonmanifold_edges = sum(1 for n in edges.values() if n > 2)
    inconsistent_edges = sum(1 for edge, n in edges.items()
                             if n == 2 and directions[edge] != 0)
    closed = (count > 0 and degenerate == 0 and open_edges == 0 and
              nonmanifold_edges == 0 and inconsistent_edges == 0 and
              signed_volume > 1e-12)
    return {
        "triangles": count,
        "degenerate_triangles": degenerate,
        "open_edges": open_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "inconsistent_orientation_edges": inconsistent_edges,
        "signed_volume_m3": signed_volume,
        "edge_matching_precision_m": 1e-7,
        "watertight_candidate": closed,
        "warning": "Topology and volume screening do not exclude intersections or certify CFD readiness.",
    }


def write_ascii_stl(path: Path, patch: Patch) -> None:
    """ASCII STL avoids the .stl/.stlb binary format ambiguity in OpenFOAM."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii", newline="\n") as out:
        out.write(f"solid {patch.name}\n")
        for triangle in patch.triangles:
            n, area = normal_area(triangle)
            if area < 1e-12:
                raise ValueError(f"Degenerate triangle in {patch.name}")
            out.write(f"  facet normal {n[0]:.12g} {n[1]:.12g} {n[2]:.12g}\n")
            out.write("    outer loop\n")
            for p in triangle:
                out.write(f"      vertex {p[0]:.12g} {p[1]:.12g} {p[2]:.12g}\n")
            out.write("    endloop\n  endfacet\n")
        out.write(f"endsolid {patch.name}\n")


def cube_patch(side_m: float = 1.0, z0: float = 0.0) -> Patch:
    """Closed sample cube with outward triangle normals (benchmark GEOMETRY only)."""
    if not math.isfinite(side_m) or side_m <= 0:
        raise ValueError("Cube side must be positive")
    s = side_m
    v = [(0,0,z0), (s,0,z0), (s,s,z0), (0,s,z0),
         (0,0,z0+s), (s,0,z0+s), (s,s,z0+s), (0,s,z0+s)]
    quads = [(0,3,2,1), (4,5,6,7), (0,1,5,4),
             (3,7,6,2), (0,4,7,3), (1,2,6,5)]
    triangles = []
    for a, b, c, d in quads:
        triangles.extend(((v[a],v[b],v[c]), (v[a],v[c],v[d])))
    return Patch("cube", "EXAMPLE_CUBE", tuple(triangles))
