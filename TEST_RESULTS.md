# GO CFD - Test results (2026-11-07)

## Offline Python tests: PASSED (37/37)

Command: `python -m pytest -q`

Coverage includes:
- Closed cube geometry, area, rotation and geometry hashing
- Open surface rejection and patch name validation
- Dynamic reference pressure, kinematic pressure conversion, pressure integration
- Force/moment transfer balance arithmetic
- Wind configuration, generated OpenFOAM dictionary/manifest content, overwrite guard
- Input fingerprint / stale result detection
- Force-file parsing
- Plugin entry point registration with test doubles (including Qt-free setup)
- Selected Group export adapter with mocked host modules
- Missing solver handling and fake subprocess-stage orchestration
- v0.2 illustrative track shape/direction and animated particle interpolation
- v0.2 fake Qt QPainter overlay lifecycle, restart and multi-tab registration
- v0.2 mocked Windows WSL startup, failed distro launch (4294967295),
  path conversion, OpenFOAM discovery and native PATH error

## Status by system

| System | Status | Evidence |
|---|---|---|
| Python source syntax | PASSED | `python -m compileall -q go_cfd` |
| Offline math, geometry, case generation | PASSED | pytest, 37 tests |
| IngeTrazo v0.6.0 installed-host v0.1 | USER SCREENSHOT | Menu/toolbar/dialog visible in user's screenshot; solver blocked |
| IngeTrazo v0.6.0 installed-host v0.2 | USER SCREENSHOT | Wind Preview visible; solver UI and environment checks used |
| Qt GUI (real pixels) / screenshot | USER SCREENSHOT | Wind Preview displayed in host. Real automated GUI test remains NOT TESTED |
| OpenFOAM v2606 mesh / solver | USER TEST: FAILED AT blockMesh (1) | v0.2.2 started blockMesh and displayed version banner, then OpenFOAM rejected inherited Program Files path |
| WSL2 backend | USER LIVE: PARTIAL PASS | WSL boot, wslpath and OpenFOAM presence confirmed; blockMesh fileName failure in v0.2.2 |
| Cp map / contours | NOT IMPLEMENTED | Future stage |
| ABL / domain / mesh independence | NOT IMPLEMENTED / NOT TESTED | Validation gate |
| Engineering design loads | NOT IMPLEMENTED | Not for structural design |

**A synthetic fake executable test checks orchestration only, not CFD physics.**

## GitHub Actions CI (2026-11-07)

- Full-source run [42347581868](https://github.com/buildsmart888/go-cfd-ingetrazo/actions/runs/42347581868) returned **FAILURE**.
- Job metadata contains **zero steps** and `runner_id=0`; no job log was available. The job appears to have failed before a runner executed any Python test. Check the Actions run page for GitHub-side runner, billing, or policy messages.
- Local `python -m pytest -q`: **37/37 PASSED**. This is independent of GitHub Actions.
- GitHub-hosted CI remains **FAILED / needs investigation** until an actual job runs.

## v0.2.2-dev: blockMesh exit 139 investigation

The user's live WSL2/OpenFOAM v2606 output showed `ENV CHECK OK` but
`blockMesh exited with code 139` before the mesh stage finished. Source review
found the solver launcher sourcing `etc/bashrc` with positional parameters
that included its own path. Some OpenFOAM bashrc files interpret positional
arguments as files to source, causing recursive sourcing and Bash SIGSEGV.

The launcher now isolates the arguments with a Bash array and clears
`$@` before sourcing. Added three regression tests, including two actual
Bash subprocess tests. The existing suite passes **37/37 offline tests**.

**Live v0.2.2-dev WSL/OpenFOAM run: NOT TESTED YET.** Results are not design-ready.

## v0.2.3-dev: Invalid OpenFOAM working directory (2026-11-07)

Observed from user's actual IngeTrazo v0.2.2-dev log:

```
Exec : blockMesh -case /mnt/c/Users/g_np2/Documents/GO_CFD_Cases/cube_20261107_160644
fileName::stripInvalid() called for invalid fileName /mnt/c/ProgramFiles/IngeTrazo
RUN STOPPED: blockMesh exited with code 1
```

This points at the inherited IngeTrazo install cwd containing `Program Files`,
**not** the cube case path. The WSL launcher now enforces a Linux cwd of `/`
using `wsl.exe --cd / --exec`; Windows solver subprocesses also explicitly
start from the CFD case directory. The launcher validates that the case path
contains no whitespace before opening the solver.

Regression tests cover every WSL preflight command and solver stage, the
Windows `cwd` argument, and paths with whitespace. Offline Python tests:
**37/37 PASSED**. `python -m compileall -q go_cfd`: PASSED.

**v0.2.3 live WSL/OpenFOAM run: NOT TESTED YET.** The actual cube solution,
meshing stages, flow fields and engineering load validation are NOT VERIFIED.
