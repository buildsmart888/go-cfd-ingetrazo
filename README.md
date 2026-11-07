# GO CFD — Wind & Structural Aerodynamics for IngeTrazo

> **PRELIMINARY SOFTWARE — NOT FOR STRUCTURAL DESIGN.** This repository is
> an early implementation, not a validated CFD wind-engineering product.

**Version:** `0.3.0-dev` · **Target IngeTrazo:** `v0.6.0` · **Target OpenFOAM:**
OpenCFD `v2606` (template target, **not yet solver-tested**).

GO CFD connects selected 3D envelope Groups/Components in IngeTrazo to
OpenFOAM steady incompressible RANS (`simpleFoam`), using `blockMesh` and
`snappyHexMesh`. Source BIM geometry is read-only; CFD jobs live in separate
case directories.

## NEW v0.3.0-dev: real OpenFOAM 3D Results Viewer (W2 prototype)

After a genuine **completed** `blockMesh -> snappyHexMesh -> checkMesh -> simpleFoam`
case (status remains `SOLVER_COMPLETED_UNVERIFIED`), GO CFD can run `foamToVTK`
to export the computed `U` and `p` fields. The `4 Results` tab now offers:

- **Export CFD fields (foamToVTK)** — writes actual `VTK/.../internal.vtu`,
  boundary `*.vtp`, `solver_logs/05_foamToVTK.log` and a provenance record.
- **Open 3D CFD Results Viewer** — interactive native VTK/Qt window within
  IngeTrazo; computed velocity streamlines, horizontal U and pressure slices,
  pressure or Cp colors on building surfaces and ground; moving particles on
  *steady* velocity paths; export PNG.
- **No fake CFD data** — missing/partial exports raise clear errors. The older
  Wind Preview is still a separate, explicitly illustrative overlay.

Viewer requires optional `vtk>=9.3,<10` **in the same Python interpreter that
runs IngeTrazo**. It is intentionally not bundled in the plugin ZIP. If the
IngeTrazo Windows EXE has no VTK bindings, open the generated `.vtm` file in
ParaView instead. See [CFD Viewer setup, limitations, and validation](docs/REAL_CFD_VIEWER.md).

**Currently verified:** offline VTK field math/slices/streamline pipelines and
Qt-free integration tests. **NOT VERIFIED:** running the real viewer on the
user's IngeTrazo v0.6.0 build, or completing a live OpenFOAM cube mesh/solve.
The viewer shows the **wind-aligned CFD coordinate frame**, not yet a result
mesh back-transformed into the IngeTrazo native viewport. These fields are
**NOT STRUCTURAL DESIGN WIND LOADS**.

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
- **NEW v0.2:** animated, non-CFD viewport wind preview in IngeTrazo (moving
  schematic paths/particles, line density, direction and animation speed).
  This is a model-scale illustration only, independent of OpenFOAM.
- **NEW v0.2:** Windows defaults to WSL2; environment check diagnoses distro
  startup, OpenFOAM availability and Windows/WSL path mapping before solving.
- Pytest unit tests; CI workflow (live solver/in-app QA separate).

## v0.2.3-dev: OpenFOAM rejects inherited IngeTrazo working directory

After the OpenFOAM v2606 banner, a native exception such as:

```
fileName::stripInvalid() called for invalid fileName /mnt/c/ProgramFiles/IngeTrazo
```

is consistent with WSL inheriting a Windows working directory under
`C:/Program Files/IngeTrazo`. This directory is not the CFD case.

The WSL launcher now uses `wsl.exe --cd / --exec` for all preflight and
solver stages. Windows also starts solver subprocesses from the CFD case
folder instead of inheriting the IngeTrazo installation directory.

**How to test:** close IngeTrazo, install the latest source bundle, restart,
choose `C:/GO_CFD_Cases` (avoid spaces), build a new sample cube case, run
`Check WSL / OpenFOAM environment` and then `Run OpenFOAM`.

Independent PowerShell check:

```powershell
wsl -d Ubuntu --cd / --exec bash -lc 'pwd'
# Expect /
```

This patch does not change CFD physics or certify solver output.

## OpenFOAM launch fix (v0.2.2-dev)

After WSL and OpenFOAM were detected, `blockMesh` could exit 139 even on a
valid Cube case. The launcher was sourcing OpenFOAM `etc/bashrc` while the
script arguments were still present. Some OpenFOAM versions interpret these
arguments as files to source, which can recursively source `etc/bashrc`
until a segmentation fault. v0.2.2 captures the intended solver command,
clears `$@` using `set --`, then sources the bashrc and executes the saved
command. Explicit WSL bashrc preflight uses the same protection.

If the error persists, check `solver_logs/01_blockMesh.log`, test
`blockMesh -help` in Ubuntu and compare native Linux filesystem vs `/mnt/c`.
This is a process launch fix, not CFD validation.

### WSL path fix (v0.2.1)

For Windows drive-backed case folders, the runner now passes a forward-slash
Windows path through `wsl.exe --exec wslpath -u -a`, avoiding shell removal of
backslashes. This fixes the preflight failure displaying
`wslpath: C:Users...` for case folders stored under `C:\Users\...`.
The fix does **not** install OpenFOAM or repair open/non-manifold BIM geometry.

From PowerShell you may verify case paths independently:

```powershell
wsl -d Ubuntu --exec wslpath -u -a 'C:/Users/g_np2/Documents/GO_CFD_Cases'
wsl -d Ubuntu --exec ls -ld /mnt/c/Users/g_np2/Documents/GO_CFD_Cases
```

## Not implemented / not verified

- **A successful complete live OpenFOAM mesh/solve is not yet confirmed.** Templates
  must be adapted and validated against the exact installed solver version.
- No atmospheric boundary layer (ABL), roughness model or empty-domain test.
- Initial computed Cp contours and velocity streamlines are available in an
  optional native VTK Qt viewer, but NOT validated or yet on the host viewport.
  **Animated Wind Preview is illustrative, not a real CFD animation.**
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
6. To see moving wind without OpenFOAM: **GO CFD > 2 Wind > Start Wind Preview**;
   the dialog hides so you see the animated overlay on the 3D viewport.
7. For actual CFD: OpenFOAM is **not bundled**. Install separately and use
   **Check WSL / OpenFOAM environment** before running.
8. See [Animated Wind Preview & Windows setup](docs/ANIMATION_AND_WSL.md).

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
- `go_cfd/runner.py` — external OpenFOAM stages, preflight and logs.
- `go_cfd/wind_preview.py` — Qt-free schematic stream tracks (NOT CFD).
- `go_cfd/preview_overlay.py` — QPainter animation on the live viewport.
- `go_cfd/loads.py`, `results.py` — engineering units, force processing.
- `go_cfd/postprocessing.py` — authentic foamToVTK export and provenance.
- `go_cfd/vtk_results.py` — real VTK fields, U/p/Cp, slices and traces.
- `go_cfd/vtk_viewer.py` — optional 3D Qt/VTK results dialog (requires vtk).
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
