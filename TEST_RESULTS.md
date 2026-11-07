# GO CFD - Test results (2026-11-07)

## Offline Python tests: PASSED (18/18)

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

## Status by system

| System | Status | Evidence |
|---|---|---|
| Python source syntax | PASSED | `python -m compileall -q go_cfd` |
| Offline math, geometry, case generation | PASSED | pytest, 18 tests |
| IngeTrazo v0.6.0 installed-host integration | NOT TESTED | No installed GUI in runner |
| Qt UI smoke / screenshot | NOT TESTED | PySide6 unavailable in runner |
| OpenFOAM v2606 mesh / solver | NOT TESTED | `blockMesh`, `snappyHexMesh`, `simpleFoam` unavailable |
| WSL2 backend | NOT TESTED | Windows / WSL unavailable in runner |
| Cp map / contours | NOT IMPLEMENTED | Future stage |
| ABL / domain / mesh independence | NOT IMPLEMENTED / NOT TESTED | Validation gate |
| Engineering design loads | NOT IMPLEMENTED | Not for structural design |

**A synthetic fake executable test checks orchestration only, not CFD physics.**