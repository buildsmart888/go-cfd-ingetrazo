# GO CFD roadmap and verification gates

This is an experimental CFD-to-BIM project, **not a design-certified tool**.
Every item below requires its own independent evidence before being marked
ready for engineering use.

## W0 — Host and geometry

- [x] IngeTrazo v0.6.0 plugin with menus, toolbar and 4-tab dialog (host startup observed in user screenshots for v0.1)
- [x] Extract read-only selected Groups/Components in world-space, triangulate and screen topology
- [x] Generate case files without modifying original BIM elements
- [x] Detect geometry and parameter staleness (manual check)
- [x] Animated Wind Preview (**illustrative only**, v0.2)
- [ ] v0.2 Preview real-host screenshot and no-traceback QA
- [ ] Test Undo, selection and multi-document persistence across representative saved models

## W1 — OpenFOAM runtime

- [x] Generate a preliminary cube case and all relevant dictionaries (not solver-validated)
- [x] Native and WSL2 process orchestration; safe cancellation and logs
- [x] WSL/OpenFOAM preflight with useful diagnostics and no OS modifications
- [ ] Install/test actual pinned OpenFOAM-v2606 executable in WSL2
- [ ] blockMesh → snappyHexMesh → checkMesh → simpleFoam **real run**
- [ ] Document mesh QA, residuals, forces and momentum balance
- [ ] Resolve any runtime dictionary/mesh errors on real solver

## W2 — Fluid results rendering

- [ ] OpenFOAM velocity field U and pressure p reader (VTK/ParaView pipeline)
- [ ] Physical streamlines and particle advection **derived from solver field**
- [ ] Surface Cp pressure map with color legend, patch/face correspondence
- [ ] Distinguish steady visualization from transient animation
- [ ] Benchmark cube, roof, wall and sign geometry with verified reference data

## W3 — Structure integration

- [ ] Pressure-to-BIM facade/roof patch identity and coordinate mappings
- [ ] Conservative force/moment integration and structural distribution
- [ ] Validated GO Structural Analysis exchange with load combinations
- [ ] Model-change invalidation for computed CFD fields and structural exports

## W4 — CFD wind engineering

- [ ] Atmospheric boundary layer, terrain/roughness, code wind speed and direction sweeps
- [ ] Mesh independence, turbulence sensitivity and experimental validation
- [ ] Transient solver support for gusts / vortex shedding when justified
- [ ] Design-code checks and engineer review before any load may be used for design

### State of evidence (2026-11-07)

- Python offline: 28/28 PASSED including mock WSL and mock Qt overlay.
- Real v0.2 Qt GUI: NOT TESTED (PySide6 unavailable in execution environment).
- Real OpenFOAM: NOT TESTED (executables unavailable in execution environment).
- Latest GitHub Actions in prior push: failed before runner steps; investigate platform-side status separately from Python tests.
