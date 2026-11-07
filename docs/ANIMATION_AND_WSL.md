# Animated Wind Preview & OpenFOAM setup (IngeTrazo 0.6.0 / Windows 11)

## What actually animates in v0.2.0-dev

GO CFD has TWO separate modes. They must not be confused:

1. **Animated Wind Preview** (implemented): moving teal paths and amber particles in the IngeTrazo viewport, using a schematic bounding-box deflection. No solver and no physics-based pressure. A persistent viewport label says `SNAPSHOT / ILLUSTRATION - NOT CFD OR DESIGN LOADS`. Use for demonstrating wind **direction** only, not detailed wake, suction or pressure.
2. **True CFD animation** (NOT IMPLEMENTED in IngeTrazo): a converged OpenFOAM velocity field must first be computed, then sampled and advected to generate animated streamlines. The W1 `simpleFoam` case is steady state: an animated particle following its converged field represents *visualization of steady flow*, not transient fluctuations. Real unsteady gusts/vortex shedding require a time-accurate solver, time steps, solver/mesh validation and a later visualization pipeline.

### Try Preview now, without OpenFOAM

1. In IngeTrazo, select one or more existing 3D Groups or Components. They may be imperfect/open surfaces for *Preview*, but not for CFD meshing.
2. Open `Extensions > GO CFD > Animated Wind Preview Settings...` (or GO CFD toolbar > `2 Wind`).
3. Set reference velocity greater than zero (for example `20 m/s`), wind direction **TO** (`0°` means +X, `90°` means +Y), and animation speed / line count.
4. Press **Start Wind Preview (hide dialog)**. The dialog hides, and the world-space wind animation is drawn **over** the existing IngeTrazo model. Orbit/pan as normal.
5. Stop using `Extensions > GO CFD > Stop Animated Wind Preview` (or the toolbar `Stop Wind` action).
6. If you edit or move the model, **restart** Preview to recalculate its bounding geometry. It is a snapshot, not automatically rebuilt.

No geometry, BIM metadata, BOQ or solver result is modified by Preview.

## Why your current solver won't start

These are independent failures:

- `open_edges: 1` and `nonmanifold_edges: 7` for 38 triangles: the selected **combined** external envelope is not watertight. Inspect the two groups separately; remove overlapping/double faces, seal holes and consider a clean *external-only* envelope. Do not auto-union structural members into the CFD solid without checking intersections. The sample Cube (`12 triangles`, `watertight_candidate: true`) only passed preliminary topology checks, **not CFD validation**.
- `blockMesh not on PATH`: the **Native** backend on Windows cannot locate the OpenFOAM utilities. In the updated UI, Windows defaults to WSL2.
- WSL error code `4294967295`: WSL failed to initialize or launch the requested Linux command, *before* an OpenFOAM case was solved. The code alone does not prove why; check the distribution and Windows virtualization state.

## Windows 11 WSL2 diagnosis

Open Windows PowerShell (not the IngeTrazo Python console):

```powershell
wsl --status
wsl --list --verbose
```

If a working Ubuntu WSL2 distribution exists, you should see `VERSION 2` in the list. Start Ubuntu once and finish its first-run account setup:

```powershell
wsl -d Ubuntu
```

The distribution name may differ, e.g. `Ubuntu-22.04`. **Only if no WSL/Ubuntu is installed**, open PowerShell *as Administrator*:

```powershell
wsl --install -d Ubuntu-22.04
```

Restart Windows if prompted; open the new Ubuntu terminal and create its Linux user. For WSL repair, consult the official Microsoft WSL documentation and consider `wsl --update` plus checking firmware virtualization; avoid assuming the error code uniquely identifies the cause.

Then install a version-compatible **OpenFOAM** *inside Ubuntu*, following the official OpenFOAM-v2606 package/installation documentation for that Ubuntu version. Verify inside the Linux shell:

```bash
command -v blockMesh
command -v snappyHexMesh
command -v checkMesh
command -v simpleFoam
```

If you have installed OpenFOAM but the commands are unavailable in new shells, source its `etc/bashrc` (replace with your **real installed path**):

```bash
source /opt/openfoam2606/etc/bashrc
command -v blockMesh
```

In GO CFD: choose **Windows WSL2**, optionally set the absolute Linux `bashrc` path, then click **Check WSL / OpenFOAM environment** *before* pressing **Run OpenFOAM**. The extension checks distro startup, Windows-to-Linux case path conversion and availability of blockMesh. It will NOT install OS components automatically.

Official references:
- Microsoft WSL: https://learn.microsoft.com/windows/wsl/install
- OpenFOAM OpenCFD v2606: https://www.openfoam.com/current-release
- OpenFOAM v2606 docs: https://doc.openfoam.com/2606/quickstart/

## True CFD results: what is still needed

- W1: real runtime proof for blockMesh → snappyHexMesh → checkMesh → simpleFoam on a pinned OpenFOAM build and validated exterior geometry.
- W2: extract the computed `U` and `p` fields (e.g. ParaView/VTK), map wind-oriented coordinates back to IngeTrazo, calculate physically correct reference pressure and Cp, and render streamlines / surface maps with a legend.
- W3: for *physical time-dependent flow*, support a time-accurate transient solver with a measured time base and frame-by-frame velocity datasets. Keep time-averaged and instantaneous pressure separate.
- Independent mesh convergence, proper atmospheric boundary layer, solver convergence, experimental benchmark and code load criteria remain required for structural design.

**DO NOT use Preview geometry, colors or motion as evidence of wind loads or structural safety.**

## v0.2.1 WSL path-conversion fix

The Windows user's log `wslpath: C:Usersg_np2Documents...` indicates that
backslashes in a Windows case path were consumed before `wslpath` saw them.
The runner now uses `wsl.exe --exec wslpath -u -a` with a forward-slash path
`C:/Users/...` so the default Linux shell cannot remove separators. This fix
is independent of whether OpenFOAM has been installed inside Ubuntu.

In PowerShell, verify the *existing* case directory:

```powershell
$case = 'C:/Users/g_np2/Documents/GO_CFD_Cases/cube_20261107_133927'
Test-Path $case
wsl -d Ubuntu --exec wslpath -u -a $case
```

If the command returns an absolute `/mnt/c/...` path, Windows/WSL path
conversion is working. If it still fails, verify the WSL drive mount with
`wsl -d Ubuntu --exec ls -ld /mnt/c/Users/g_np2/Documents/GO_CFD_Cases`.
If `Test-Path` is false, regenerate the sample cube case before running.

Separately, `open_edges` and `nonmanifold_edges` on Group 3 mean its surface
is not closed or includes topologically conflicting faces. Do not suppress
watertight screening. Build/select a separate closed **exterior-only** shell
before attempting a mesh on a real building.

## v0.2.2: blockMesh exit 139 after environment readiness

The previous launcher sourced OpenFOAM etc/bashrc with positional arguments
still set, potentially causing recursive self-sourcing and Bash SIGSEGV (139).
The patched launcher saves the argv array, clears positional arguments with
`set --` before sourcing, and executes the preserved solver arguments.
This applies to WSL and native Linux launchers and explicit bashrc preflight.

If a crash remains, inspect `solver_logs/01_blockMesh.log`. Test `blockMesh -help`
in Ubuntu; success there but failure on a GO CFD case needs inspection of the
case dictionary or mount. No structural design results are validated by this fix.
