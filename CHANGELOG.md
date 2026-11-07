# Changelog

## 0.2.0-dev (2026-11-07)

- Added animated Wind Preview overlay with 3D wind paths, moving particles,
  density / direction / animation controls; model snapshot is never modified.
- Added menu and toolbar actions to reopen/stop preview; supports switching project tabs.
- Preview works with imperfect geometry but is prominently labelled NON-CFD.
- Improved per-patch surface screening diagnostics and repair guidance.
- Default to WSL2 backend on Windows; added asynchronous environment check UI.
- Preflight WSL startup before wslpath (handles opaque exit 4294967295),
  auto-detects common OpenFOAM bashrc paths, and checks blockMesh availability.
- Added pure-Python preview math, fake Qt overlay lifecycle and mocked WSL tests.
- Installed-host v0.2 GUI and real OpenFOAM physics are still NOT TESTED.

## 0.1.0-dev (2026-11-07)

- Added IngeTrazo v0.6.0 menu, toolbar and non-modal CFD laboratory UI.
- Added read-only selected Group/Component world-mesh extraction.
- Added closed-surface screening, surface hashes, and per-patch ASCII STL.
- Added preliminary OpenCFD-v2606 case dictionary writer and sample cube generator.
- Added OpenFOAM subprocess runner with logs, cancellation and explicit unverified status.
- Added pressure unit helpers, force integration, balance test, forces.dat parsing.
- Added pure Python automated tests and GitHub Actions workflow.
- **No live OpenFOAM solver run or installed IngeTrazo UI test has been performed.**
