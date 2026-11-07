# GO CFD — Wind & Structural Aerodynamics for IngeTrazo

**Development preview: v0.1.0-dev | Target: IngeTrazo v0.6.0 | OpenFOAM: OpenCFD v2606**

> This is an early engineering prototype. **NOT FOR STRUCTURAL DESIGN.** A successful CFD solver run does not validate design loads.

## Project goals

- Export selected BIM envelope Groups/Components from IngeTrazo as triangulated, world-space STL.
- Diagnose open/non-manifold/degenerate surfaces before meshing.
- Define CFD wind speed and direction, density, and computational domain.
- Build OpenFOAM steady incompressible RANS cases (blockMesh, snappyHexMesh, simpleFoam).
- Read simulation logs and surface-force outputs, with explicit UNVERIFIED / STALE results.
- Later: Cp contours and streamlines, ABL, mesh-independence validation, local and global design pressures and load transfer to GO Structural Analysis.

## Current implementation and availability

The **complete development source archive** was provided separately in this ChatGPT conversation, along with an IngeTrazo plugin ZIP. The initial GitHub upload is being staged. The repository may not yet contain every source file from that archive.

Full source download is available in the earlier conversation attachment named `GO_CFD_IngeTrazo_Source_v0.1.0-dev.zip`.

### Install from full source archive

1. Extract the provided source archive.
2. Close IngeTrazo v0.6.0.
3. Run `install_windows.cmd` from the extracted archive, or copy its `go_cfd` directory to `%APPDATA%\ingetrazo\plugins\go_cfd`.
4. Restart IngeTrazo; open Extensions > GO CFD.
5. Install and configure OpenFOAM separately. It is not bundled.

### Offline tests from full source archive

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python -m go_cfd.cli demo-cube ./local_cases/cube_01 --speed-ms 20
```

The baseline's offline tests passed 17/17 on 2026-11-07. Installed IngeTrazo GUI and real OpenFOAM solver runs remain **NOT TESTED**.

## Source integration / development

IngeTrazo's extension loader discovers package directories under `%APPDATA%\ingetrazo\plugins`; package-level `setup(app)` is the host entry point. Keep Qt and IngeTrazo imports inside GUI/host modules so numerical modules are independently testable.

### Validation gate

Before using pressures for structural analysis, require watertight geometry, appropriate flow domain and ABL boundary conditions, mesh and time-step convergence as applicable, reference benchmark comparisons, pressure integration checks, and code-specific design factors.

**Developer:** GO Engineering / buildsmart888
