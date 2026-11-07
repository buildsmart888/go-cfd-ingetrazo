# GO CFD Engineering Roadmap

## W0 — Extension foundation
- [x] Repository created and initial commit
- [ ] Confirm clean installation of development package into IngeTrazo v0.6.0
- [ ] Verify toolbar, menu, dialog, selection, and project switching
- [ ] Capture app screenshot and traceback-free startup test

## W1 — Geometry and solver
- [ ] Validate cube STL orientation, watertightness, edge/manifold diagnostics
- [ ] Generate meshable OpenFOAM domain and surface names
- [ ] Run actual blockMesh, snappyHexMesh, checkMesh and simpleFoam
- [ ] Review residuals, continuity, and force output
- [ ] Conduct empty-domain and low-Re reference checks

## W2 — Building shapes
- [ ] House: gable and hip roofs, eaves and wall zones
- [ ] Factory: framing and cladding surfaces
- [ ] Sign boards, freestanding walls, porous walls
- [ ] Cooling towers and curved structures

## W3 — Structural coupling
- [ ] Map pressure patches to BIM identity (UID and face references)
- [ ] Preserve force and moment balance across mapping
- [ ] Export loads to GO Structural Analysis using explicit load cases
- [ ] Manage model hash and stale results

## W4 — Validated CFD and design
- [ ] Atmospheric boundary layer and terrain roughness
- [ ] Mesh independence and wind-direction sweeps
- [ ] Cp benchmarks and uncertainty / repeatability
- [ ] Peak/cladding pressures and code comparisons
- [ ] Engineering review: do not mark results design-ready before validation

## Status convention

PASSED = tested against stated evidence; FAILED = demonstrated defect;
NOT TESTED = no runtime evidence; NOT IMPLEMENTED = absent feature.
