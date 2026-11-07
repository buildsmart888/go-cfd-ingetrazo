# Integration and architecture notes

**Verified upstream source:**
- IngeTrazo `core/version.py`: 0.6.0 (main as inspected 2026-11-07).
- `docs/plugins.md`: package plugin `setup(app)`, user plugins directory,
  `add_menu`, `add_menu_action`, `document_data` + `set_document_data`.
- `core/group.py`: `world_mesh(group)` handles instance nested placements.
- `formats/meshexport.py`: `export_triangles(face)` ignores sliver triangles.
- Model mutation commands require `core.history.SnapshotImport` or equivalent;
  GO CFD does not create/edit model geometry in W0.

**Object metadata:** group `uid` -> safe per-patch OpenFOAM ID in JSON manifest.
Source is untouched. Stored `.igz` extension data is only a reference to an
external case directory and its source geometry hash; OpenFOAM fields are not
embedded into the `.igz` model.

**Limitations to fix:**
- Validate nested component transforms in the installed IngeTrazo app.
- Improve mesh checks with oriented-manifold/intersection test; edge-count alone
  is insufficient for outward orientation and complex connected geometry.
- Geometry extraction on GUI thread, capped at 300k triangles; large models
  need a non-blocking snapshot extraction design.
- WSL2 subprocess and OpenCFD-v2606 case dictionaries require live testing.
- Auto freshness on model change currently requires explicit user verification.
- Physical model includes only uniform RANS, not an atmospheric boundary layer.
- Force object output parsing version-specific; recheck with actual solver run.

**Future architecture:** BIM patch classifier, zone-to-structural mapping,
VTK/VTU readback, Qt/VTK viewer or viewport shader overlay, multi-angle
batch cases, ABL and terrain selection, unsteady LES mode with clear cost,
benchmark database and full forensic engineering report.