## v0.3.0-dev — 2026-11-07

- Added W2 real CFD results export with `foamToVTK -latestTime -fields '(U p)'`.
- Added explicit post-process provenance, real volume/boundary VTK discovery,
  and refusal to export fields from a solver run that did not complete.
- Added optional native VTK 3D Qt viewer for velocity streamlines, vertical
  particle advection along steady streamlines, horizontal U and p slices,
  pressure on ground/buildings, and surface Cp. Export viewer image as PNG.
- Converted kinematic OpenFOAM p to physical Pa via `p * rho`; reference Cp
  uses `2*(p - p_ref_kinematic)/U_ref^2` with outlet p_ref=0 for this case.
- Added automatic export after a completed solver worker, Qt-free fallback,
  CLI `export-vtk` and `vtk-info`, VTK fixture regression tests and safety limits.
- Offline pytest suite: 45/45 PASSED; live VTK Qt host and CFD solver: NOT TESTED.
- Results remain UNVERIFIED; viewer is a separate IngeTrazo 3D window,
  NOT a native-viewport overlay or an engineering-approved wind-load module.

# Changelog

## 0.2.3-dev (2026-11-07)

- Fixed OpenFOAM's fatal `fileName::stripInvalid()` after running from IngeTrazo installed under `C:/Program Files`.
- All Windows WSL preflight and solver subprocesses now use `wsl.exe --cd / --exec` so Linux starts from a whitespace-free cwd.
- WSL solver launch also sets the Windows subprocess cwd to the generated CFD case folder.
- Reject CFD case paths containing whitespace early (suggest `C:/GO_CFD_Cases`).
- Added tests for WSL working directory, case path whitespace and subprocess cwd.
- Still requires a real OpenFOAM runtime and engineering QA; no design-load validity is claimed.

## 0.2.2-dev (2026-11-07)

- Fix SIGSEGV/exit 139 caused by sourcing OpenFOAM etc/bashrc with positional arguments still present.
- Clear positional parameters before sourcing in native and WSL solver launchers and explicit bashrc preflight.
- Add runtime Bash integration regression tests and SIGSEGV error hint.
- Live OpenFOAM runtime still requires user verification and case validation.

## 0.2.1-dev (2026-11-07)

- Fixed Windows/WSL case-path conversion: use direct `wsl.exe --exec wslpath`
  and normalize `C:\\Users\\...` to `C:/Users/...` before crossing into Linux.
- All WSL process launches now use `--exec` to avoid the default shell
  silently consuming Windows path separators.
- Added regression tests for drive paths, spaces, and UNC path rejection.
- Still requires an installed OpenFOAM solver and a valid closed external
  CFD envelope; this patch does not change fluid physics or mesh QA.

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
