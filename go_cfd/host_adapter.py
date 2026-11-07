"""Small, audited IngeTrazo 0.6.0 -> CFD bridge (read-only scene access)."""
from __future__ import annotations

from .constants import GEOMETRY_LIMIT_TRIANGLES
from .geometry import Patch, clean_name


def selected_groups(scene):
    """Only top-level, visible, selected Groups/Components are supported in W0."""
    selected = set(getattr(scene, "selection", ()))
    return [g for g in scene.groups if g in selected and scene.entity_visible(g)]


def source_patches_from_selection(scene) -> tuple[Patch, ...]:
    """Extract evaluated world triangles, respecting nested component transforms.

    Imports host-only modules lazily; this can be unit-tested without IngeTrazo.
    No model writes or BIM recompute. Use the host's own triangulation routine.
    """
    from core.group import world_mesh
    from formats.meshexport import export_triangles

    groups = selected_groups(scene)
    if not groups:
        raise ValueError("Select one or more visible solid Groups/Components first")
    patches = []
    total = 0
    for i, group in enumerate(groups, start=1):
        if getattr(group, "billboard", False):
            raise ValueError("Camera-facing image billboards are not physical CFD surfaces")
        mesh = world_mesh(group)
        tris = []
        for face in mesh.faces:
            for tri in export_triangles(face):
                tris.append(tuple((v.x(), v.y(), v.z()) for v in tri))
                total += 1
                if total > GEOMETRY_LIMIT_TRIANGLES:
                    raise ValueError("Too many triangles for W0; simplify/select a smaller envelope")
        if not tris:
            continue
        src = str(getattr(group, "uid", "") or f"group_index_{i}")
        # Truncate for OpenFOAM, include stable unique ordinal for collisions.
        patch_name = clean_name(f"surface_{i:03d}_{getattr(group, 'name', 'group')}")
        patches.append(Patch(patch_name, src, tuple(tris)))
    if not patches:
        raise ValueError("Selection has no usable 3D faces")
    return tuple(patches)