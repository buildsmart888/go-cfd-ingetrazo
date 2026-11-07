# GO CFD — Wind & Structural Aerodynamics for IngeTrazo

> **PRELIMINARY SOFTWARE — NOT FOR STRUCTURAL DESIGN.** This repository is
> an early implementation, not a validated CFD wind-engineering product.

**Version:** `0.1.0-dev` · **Target IngeTrazo:** `v0.6.0` · **Target OpenFOAM:**
OpenCFD `v2606` (template target, **not yet solver-tested**).

GO CFD connects selected 3D envelope Groups/Components in IngeTrazo to
OpenFOAM steady incompressible RANS (`simpleFoam`), using `blockMesh` and
`snappyHexMesh`. Source BIM geometry is read-only; CFD jobs live in separate
case directories.

## What works in this development baseline

- `Extensions -> GO CFD -> Open GO CFD Wind Lab...` and a toolbar action.
- Select Groups/Components; convert world-space faces to patch-preserving STL.
- Check for degenerate faces, unmatched edges and non-manifold edges.
- Specify wind *flow-to* angle, speed, density and background cell size.
- Write a preliminary, uniform-inflow OpenFOAM case to a **new** folder.
- Build a closed 1 x 1 x 1 m cube case without IngeTrazo.
- Launch local Linux OpenFOAM or WSL2 processes, record logs, cancel.
- Read the latest forces.dat by patch, inspect force/moment units.
- Geometry and parameter fingerprints, explicit result freshness check.
- Pytest unit tests; CI workflow (live solver/in-app QA separate).

## Not implemented / not verified

- **No successful live OpenFOAM mesh/solve has been executed yet.** Templates
  must be adapted and validated against the exact installed solver version.
- No atmospheric boundary layer (ABL), roughness model or empty-domain test.
- No Cp-contour viewer, VTK importer, post-processed velocity streamlines.
- No mesh-independence study, convergence classification, benchmark validation.
- No cladding peak pressures, internal pressure, gust or terrain code checks.
- No automated line/nodal load transfer into GO Structural Analysis.
- No fluid-structure interaction or validated LES.
- No safety/design certification. Solver success remains `UNVERIFIED`.

## Install IngeTrazo extension (Windows)

1. Download and extract this repository.
2. Close IngeTrazo v0.6.0.
3. Run `install_windows.cmd` (backs up an older `go_cfd` plugin).
4. Restart IngeTrazo; choose **Extensions -> GO CFD**.
5. Select a *closed external building envelope*, not structural framing mixed
   with walls, then create a case. You can also build the sample cube.
6. OpenFOAM is **not bundled**. Install separately and configure PATH or WSL.

Manual alternative: copy the single `go_cfd` package into
`%APPDATA%\ingetrazo\plugins\go_cfd` on Windows. On Linux:
`~/.local/share/ingetrazo/plugins/go_cfd`.

## Command-line test without IngeTrazo

From the repository root with Python 3.12+:

```bash
python -m pip install -e '.[test]'
python -m pytest
python -m go_cfd.cli demo-cube ./local_cases/cube_01 --speed-ms 20
# If you have OpenCFD v2606 installed and environment sourced:
python -m go_cfd.cli run ./local_cases/cube_01 --backend native
python -m go_cfd.cli forces ./local_cases/cube_01
```

The `demo-cube` command creates input dictionaries but does not run the solver.
No aerodynamic force values are supplied or invented by this project.

## Coordinate conventions

- All source and CFD geometry units are **metres**.
- World frame: IngeTrazo X/Y/Z, with +Z up.
- `direction_to_deg=0` means air **moves to +world-X**, 90 towards +world-Y.
  This is **not** meteorological wind-from bearing.
- Before exporting STL, model XY is rotated by `-direction_to_deg` to make
  incoming air flow along +CFD-X.
- OpenFOAM incompressible `p` is kinematic pressure (m2/s2); multiply by air
  density for Pa. `Cp=(p_surface-p_ref)/(0.5*rho*U_ref^2)`.
- Positive net pressure acts **into** a surface; suction acts outward.

## Project layout

- `go_cfd/__init__.py` — IngeTrazo plugin API setup.
- `go_cfd/ui.py` — Qt UI + asynchronous solver worker.
- `go_cfd/host_adapter.py` — world-space selected BIM geometry.
- `go_cfd/geometry.py` — STL, surface diagnostics, traceability.
- `go_cfd/case_model.py`, `case_builder.py` — CFD scenario and dictionaries.
- `go_cfd/runner.py` — external OpenFOAM stages and logs.
- `go_cfd/loads.py`, `results.py` — engineering units, force processing.
- `docs/` — development plan, validation matrix, safety boundaries.
- `tests/` — offline pure-Python tests.

## Source repository and development updates

The complete, inspectable Python implementation and offline unit tests are
maintained at [buildsmart888/go-cfd-ingetrazo](https://github.com/buildsmart888/go-cfd-ingetrazo).
The ZIP download includes a package-shaped plugin and independent Python CLI.
If making changes from a source ZIP on Windows, `publish_github.ps1` can stage
and push changes through an authenticated `git clone`, without rewriting Git
history or creating an unrelated root commit. Review any changes before push.


## Provenance and safety

Input geometry is hashed. A new case may never overwrite existing solver
results. Any model/settings change invalidates previous input signatures; use
**Check if model changed** prior to interpreting results. Changes in turbulence
model, domain or solver version also warrant a rerun even if the source geometry
matches. The quick edge-count check is not a full watertightness/intersection
certificate. Model-only testing, live IngeTrazo testing, actual CFD solver
runs, and independent engineering validation are separately tracked.

License: GPL-3.0-or-later. OpenFOAM and IngeTrazo retain their own licenses.
