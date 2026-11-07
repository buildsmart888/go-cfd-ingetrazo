# GO CFD v0.3.0-dev — Real CFD Results Viewer (W2 prototype)

## What is implemented

- `foamToVTK -latestTime -fields '(U p)'` after all four OpenFOAM solver stages COMPLETE.
- Read OpenFOAM v2606 XML export: `VTK/<case>_<time>/internal.vtu` plus `boundary/*.vtp`.
- A separate **interactive, embedded-in-IngeTrazo Qt 3D VTK viewer window** (not yet overlaying the native modelling viewport).
- Velocity streamlines from the computed vector field `U`, colored by |U| m/s.
- Moving particles *along a steady computed vector field*. Motion is illustrative advection; it does NOT indicate simulated gust timing.
- Horizontal velocity and pressure slices (change height `Z` in metres).
- Pressure on ground or selected building boundary patches, in Pa.
- Surface Cp with gauge reference: `Cp = 2 * (p_kinematic - 0) / U_ref^2`.
- PNG image export with permanent **UNVERIFIED** window title and results labels.
- Optional VTK dependency; the extension still loads without it.

## Quick test on Windows + Ubuntu WSL2

1. Confirm `GO CFD v0.3.0-dev` appears in the extension window after installing this source package and restarting IngeTrazo.
2. Build a sample cube from a `20 m/s` wind case, keep `Case root folder` free of spaces (e.g. `C:\GO_CFD_Cases`).
3. Select `Windows WSL2`, check OpenFOAM v2606 environment, and press `Run OpenFOAM`.
4. Confirm that **all** `blockMesh`, `snappyHexMesh`, `checkMesh`, `simpleFoam` stages completed. If any stage fails, fix its log before exporting. This release does NOT repair existing failing OpenFOAM dictionaries or meshes.
5. In the `4 Results` tab click `Export CFD fields (foamToVTK)` (the extension attempts this automatically after successful solver completion).
6. Confirm an actual `VTK/.../internal.vtu` is present. Then click `Open 3D CFD Results Viewer`.
7. Choose `Velocity streamlines`, `Velocity slice`, `Pressure slice`, `Surface pressure`, `Surface Cp`. Use `Z` for horizontal sections, `Seeds` for streamlines, and `Ground` or a building patch for pressure surfaces.

If the viewer says `No real VTK results`, CFD post-processing has NOT produced usable data. It intentionally does not fabricate CFD values.

## Installing optional VTK in IngeTrazo

The VTK 3D viewer requires the `vtk` Python package and uses **the host's existing PySide6**. It is not included in the small plugin ZIP. Installing a separate Windows Python's `vtk` package will **not** make it available inside a frozen IngeTrazo executable.

To check the Python interpreter IngeTrazo is running, open its Python Console and execute:

```python
import sys
print(sys.executable)
import importlib.util
print(importlib.util.find_spec('vtk'))
```

- If it runs from a normal Python interpreter with writable packages, use the corresponding interpreter to install `vtk>=9.3,<10`. Reuse the host PySide6; do not overwrite its Qt binding.
- If IngeTrazo is a frozen Windows EXE with no straightforward installation mechanism, use **ParaView** to open the `.vtm` output until the runtime includes VTK. The GO CFD extension remains functional without VTK.
- If graphical rendering fails due to GPU/Qt/VTK incompatibility, use ParaView for large jobs. Do not copy random DLLs into the program directory.

## Files and provenance

- `solver_logs/05_foamToVTK.log` records the OpenFOAM post-process command output.
- `go_cfd_vtk_export.json` records the original case fingerprint, selected VTK volume path, and UNVERIFIED status.
- Actual computed fields remain in per-case `VTK` directories; they are never copied into BIM solids or used as design loads.
- Models are exported rotated such that the solver wind is aligned to CFD `+X`. This 3D viewer currently displays the **CFD coordinate frame**. Transforming the data back into the IngeTrazo native viewport is planned, not included.

## Engineering cautions / next steps

OpenFOAM `simpleFoam` is **steady-state RANS**, not LES or a transient CFD simulation. The `p` scalar is kinematic pressure (m²/s²) and is multiplied by `rho [kg/m³]` to display Pa; the outlet reference pressure in the W1 case is zero gauge. `Cp` is nondimensional and requires a valid reference speed and pressure.

CFD fields remain **UNVERIFIED** until the mesh passes engineering QA, physical ABL boundaries are implemented and verified, grid-independence and convergence are documented, and pressure and loads are checked against valid benchmarks and code requirements. **Never use these visualizations directly to approve structural design loads.**

## Test evidence

Local unit tests include synthetic VTK fixtures (known `U`, `p`) to validate numerical conversion and streamline/slice pipelines. Synthetic fixture outputs are test-only, never shipped as purported results from OpenFOAM. UI integration and live WSL OpenFOAM runs are **NOT TESTED** in the test container.
