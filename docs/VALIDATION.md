# Validation requirements

## Non-negotiable release gate

This project is experimental and does not currently generate certified design wind loads.

1. **Geometry:** watertight triangulated solid, consistent outward normals, correct units in metres, no self-intersections or zero-area triangles.
2. **Solver:** run on an actual pinned OpenFOAM distribution; checkMesh must report valid mesh; residual and mass-balance criteria documented.
3. **Boundary conditions:** inlet, outlet, ground and top/sides must be physically appropriate to the case. Atmospheric boundary layer is required for realistic external building wind engineering.
4. **Sensitivity:** multiple mesh refinements and numerical-scheme sensitivity evaluated.
5. **Benchmark:** compare Cp, forces and moments with recognized experiments or validated reference results.
6. **Load mapping:** integrated pressure traction must equal mapped structural forces/moments within declared tolerances.
7. **Wind standards:** CFD cannot silently replace site wind climate, peak factors, internal pressure, local roof zones or mandatory code requirements.
8. **Staleness:** change to source geometry, wind setup, solver version or mesh settings invalidates downstream results.
9. **Units:** incompressible OpenFOAM `p` is kinematic pressure; multiply by fluid density to obtain Pa. Record pressure reference.

## Test status (2026-11-07)

- Offline Python unit tests for complete local source archive: PASSED 17/17
- Host integration IngeTrazo v0.6.0: NOT TESTED
- Qt GUI offscreen testing: NOT TESTED
- Live OpenFOAM checkMesh and flow: NOT TESTED
- Cp contours / ABL / design loads: NOT IMPLEMENTED

No wind-load results are presented as validated.
