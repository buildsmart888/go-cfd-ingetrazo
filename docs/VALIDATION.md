# Engineering Validation Gate (unpassed)

## Evidence levels

- `PASSED (OFFLINE)`: Python tests with deterministic data only.
- `NOT TESTED (HOST)`: IngeTrazo v0.6.0 GUI, file load and scene export not exercised.
- `NOT TESTED (SOLVER)`: No installed OpenFOAM v2606 executable run.
- `NOT TESTED (ENGINEERING)`: No published wind-tunnel comparisons, no mesh study.

## Required next-run experiments

1. **Host smoke:** clean IngeTrazo v0.6.0 plugin installation. Open dialog,
   select a cube, build case, Save/Reload `.igz`, check paths and undo integrity.
2. **Input geometry:** cube dimensions in metres, normals, shared edges,
   outward orientation and no duplicate internal faces.
3. **OpenFOAM syntax:** source OpenCFD v2606 environment; run `blockMesh`,
   `snappyHexMesh -overwrite`, `checkMesh`, `simpleFoam` using the generated case.
   Inspect full logs and boundary-field compatibility; record exact version.
4. **Domain sensitivity:** 5H/15H baseline is heuristic, not a validation.
   Confirm blockage ratio and domain extents with actual geometry.
5. **Mesh refinement:** at least 3 densities; compare force, moment, local Cp,
   convergence, residuals and grid metrics.
6. **Velocity/pressure physics:** ensure empty-domain flow profile is stable.
   Uniform inlet here is preliminary, not ABL.
7. **External benchmarks:** compare cube and cooling tower mean Cp and force
   histories against credible wind-tunnel measurements at equivalent Re.
8. **Pressure units:** verify incompressible pressure-to-Pa conversion, force
   object density settings, sign and reference values.
9. **Structural transfer:** future stage must conserve total F and M from CFD
   patches to structural shells/frames, with explicit tolerance and missing faces.
10. **Engineering review:** no use of mean Cp as peak design pressure; verify
    exposure, internal pressure, gust factors, applicable Thai standards.

## Explicit missing outputs

Cp contours/streamlines, load transfer, code loads, wind tunnel comparison,
and any certification are **NOT IMPLEMENTED / NOT TESTED**. Do not label these
as accepted or passed based solely on a green Python CI run.


## v0.2 preview boundary (2026-11-07)

Animated overlay paths are constructed around a bounding proxy. They are NOT
CFD-computed streamlines, flow speeds, pressures or force vectors. The overlay
is strictly non-mutating and holds a snapshot of the current selected bounds;
restart it after scene edits. Its offline tests cannot certify the installed
IngeTrazo v0.6.0 GUI or the actual fluid solver.
