# GO CFD - Test results (2026-11-07)

## Offline Python tests: PASSED (28/28)

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
| Offline math, geometry, case generation | PASSED | pytest, 28 tests |
| IngeTrazo v0.6.0 installed-host v0.1 | USER SCREENSHOT | Menu/toolbar/dialog visible in user's screenshot; solver blocked |
| IngeTrazo v0.6.0 installed-host v0.2 | NOT TESTED | New animation UI not yet tried on Windows |
| Qt GUI (real pixels) / screenshot | NOT TESTED | PySide6 unavailable in runner; fake QPainter test passed |
| OpenFOAM v2606 mesh / solver | NOT TESTED | `blockMesh`, `snappyHexMesh`, `simpleFoam` unavailable |
| WSL2 backend | MOCKED PASS / LIVE NOT TESTED | Simulated failure and success paths; actual Windows WSL unavailable |
| Cp map / contours | NOT IMPLEMENTED | Future stage |
| ABL / domain / mesh independence | NOT IMPLEMENTED / NOT TESTED | Validation gate |
| Engineering design loads | NOT IMPLEMENTED | Not for structural design |

**A synthetic fake executable test checks orchestration only, not CFD physics.**

## GitHub Actions CI (2026-11-07)

- Full-source run [42347581868](https://github.com/buildsmart888/go-cfd-ingetrazo/actions/runs/42347581868) returned **FAILURE**.
- Job metadata contains **zero steps** and `runner_id=0`; no job log was available. The job appears to have failed before a runner executed any Python test. Check the Actions run page for GitHub-side runner, billing, or policy messages.
- Local `python -m pytest -q`: **28/28 PASSED**. This is independent of GitHub Actions.
- GitHub-hosted CI remains **FAILED / needs investigation** until an actual job runs.
