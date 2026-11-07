# GO CFD - Wind and Structural Aerodynamics for IngeTrazo

**Development specification v0.1.0 (planning artifact)**  
Date: 2026-11-07  
Status: SPECIFICATION ONLY - no CFD solution has been computed or verified by this document.

## 1. Mission and design boundaries

Create an IngeTrazo extension to evaluate external wind around (a) low-rise houses, (b) industrial buildings / warehouses / steel roofs, (c) billboards and freestanding signs, (d) freestanding walls and fences, and (e) individual architectural/structural components. Provide CFD visualization and auditable pressure/force export for eventual structural use.

The extension UI is a controller and visualization bridge. **Do not implement an unvalidated toy CFD solver and call it engineering-grade.** Use a version-pinned external OpenFOAM installation for CFD. Experimental LBM/LES visualization may be a later, clearly labeled research mode.

A mean Cp field is not a design peak Cp field. External and internal pressure, gust effects, return period, directional effects, and local regulatory checks must be explicitly addressed before design loads can be approved.

## 2. Existing host capabilities - verify against actual installed build

- Upstream IngeTrazo plugin guide: https://github.com/ingelibre/ingetrazo/blob/main/docs/plugins.md
- Plugin package with module-level `setup(app)`; `app.add_panel`, menu actions, overlays; `app.document_data` for JSON-safe per-document data.
- IngeTrazo supports STL, OBJ, glTF/GLB export; identify its actual world-space face geometry and unit conventions.
- Read-only input may be collected from `scene.loose_mesh` and `scene.groups`; consult `formats/meshexport.py` for world-face traversal / component transforms.
- Never do heavy CFD, meshing, or file processing in the Qt UI thread; use a subprocess/worker and queued signals for UI updates.
- Any model writes must go through undoable scene commands (`SnapshotImport`, when appropriate). CFD overlays must not mutate structural geometry.
- The IngeTrazo 0.x plugin API can change. Pin and test the exact target version.

## 3. Architecture

```
IngeTrazo model (BIM + groups + components + local/global coordinate systems)
  -> Envelope selection / classification / simplification
  -> Geometry validation (closed solids; open sheets for billboard with prescribed thickness)
  -> Surface patch extraction (STL per patch + mapping manifest)
  -> Wind case builder (ABL profile, density, wind direction, domain, solver)
  -> OpenFOAM case generator and runner (local Linux / WSL2 / Docker / remote)
  -> Mesh checks + flow solver + convergence and force monitors
  -> Results importer (VTK/VTU/CSV + patch loads + mesh provenance)
  -> IngeTrazo CFD viewer (Cp, pressure, streamlines, slices, vectors)
  -> Structural load mapping (shell / equivalent line / nodal loads)
  -> GO Structural Analysis / CSV, JSON, PDF engineering report
```

Keep user scene geometry separate from CFD mesh and results. Large CFD cases live in an external project directory; the `.igz` file stores only small scenario metadata and result references/hashes.

## 4. Required model types

| Object | Critical aerodynamic geometry | Required outputs |
|---|---|---|
| House | roof pitches, eaves, parapets, wall openings | wall/roof pressure maps; uplift zones; net resultant forces |
| Industrial building | roof ridges, bays, openings, canopies | roof uplift; bay/purlin/rafter tributary loads; global forces |
| Billboard / sign | board thickness, size, height, supporting frame, porosity | normal/tangential loads, torsion, base overturning moment |
| Freestanding wall / fence | thickness, ends, top edges, gaps, porosity | panel/column loads, net pressure, base actions |
| Component | chosen facade panel, roof cladding, canopy, chimney | local pressure zone with patch-based export |

Treat a porous fence or perforated billboard using a validated porosity/permeability approach. Do not simply model it as a solid wall without notifying the user.

## 5. CFD operating modes

1. **Preliminary / Explore**: low mesh resolution, steady RANS, interactive visualization; marked "PRELIMINARY - NOT FOR STRUCTURAL DESIGN".
2. **Engineering Candidate**: validated OpenFOAM case, atmospheric boundary layer (ABL), mesh sensitivity study, convergence/force checks, comparison to benchmarks, traceable data. Outputs remain pending engineer review.
3. **Advanced Research** (later): transient URANS/DES/LES or independently validated LBM-LES, gust/wake studies, time-series and peak/statistical analysis. Explicitly show compute cost and uncertainty.

Pin OpenFOAM distribution and version. Avoid assumptions that solver dictionaries are portable across all releases; use version-specific templates and automated case tests.

## 6. UI layout (five panels)

**A. Model:** Select CFD targets; exclude decorative details; classify roofs, walls, sign panels, porous surfaces and openings; inspect normals, watertightness, scale, coordinates, and BIM identity.

**B. Wind:** Local north, wind bearing in degrees, multi-direction schedule, reference height/speed, site exposure and ABL profile, air density, turbulence, analysis mode, external/internal pressure assumptions and design-standard context. Do not silently invent code wind speeds.

**C. Mesh & Solve:** Auto domain preview; meshing preset; quality warnings; solver choice; progress stages (geometry, domain, mesh, checkMesh, solve, postprocess); residuals and integrated-force history; pause/cancel when supported; logs and explicit failure reasons.

**D. Results:** Velocity contours, Cp and pressure contours, streamlines, plane slices (XY/XZ/YZ), normal force arrows, clipping, directional envelopes, roof uplift map, selectable patch / BIM entity, resultant force and moment per component, and side-by-side comparison across cases.

**E. Export:** Structural load cases, CSV/JSON/VTK, report PDF with screenshots, settings, mesh diagnostics, assumptions, validation outcome, force equilibrium, and result status. A sheet-composer integration may be added later without deleting or rewriting existing sheets.

Use a compact tab in IngeTrazo for controls and a larger nonmodal result viewer when complex 3D views are required. Avoid blocking UI or re-meshing on selection.

## 7. Geometry conversion and identity

- Export scene coordinates in meters. Record model origin and North angle, and verify global +X/+Y/+Z orientation.
- Traverse Group/Component placements and transforms; export evaluated world-space mesh rather than untransformed prototypes.
- Preserve unique `source_id` for each relevant wall, roof, board, fence panel, beam, etc. Keep `source_id -> CFD patch/triangle IDs` in a manifest.
- Generate dedicated CFD surface mesh without modifying the author's editable BIM model.
- Remove details below mesh fidelity, but protect controlling openings, edges, roof overhangs and clearances.
- Detect duplicate coplanar faces, inverted normals, non-manifold edges, disconnected islands, severe slivers, missing thickness/closure and collisions.
- Geometry hash + solver input hash + mesh hash are mandatory; changing model input marks a run STALE and blocks silent reuse of old pressures.

## 8. Computational domain and solver

- Provide configurable ABL inlet velocity and turbulence profiles, ground roughness, side/top, outlet and wall boundary conditions; verify horizontal homogeneity in an empty-domain test.
- Auto-size the domain from bounding-box height H and projected blockage. Use published AIJ/COST guidance as a starting point and permit engineering overrides; do not hardcode generic extents as universal truth.
- Use `blockMesh` + `snappyHexMesh`; check domain/mesh quality with `checkMesh`, patch assignment, near-surface mesh and refinement at leading edges, roof corners and wake regions.
- Start with steady incompressible turbulent RANS and appropriate turbulence-model comparisons; reserve unsteady LES for cases where steady prediction is inadequate.
- Monitor residuals, continuity, surface force/moment history and numerical stability; status must distinguish converged, failed, interrupted, or not verified.
- Use `forces` / `forceCoeffs` or equivalent version-verified OpenFOAM functions for pressure + viscous surface loads.

Documentation: https://doc.openfoam.com/2606/tools/pre-processing/mesh/generation/snappyhexmesh/ and https://doc.openfoam.com/2606/tools/post-processing/function-objects/forces/forces/

## 9. Pressure and structural-load conversion

Define the velocity reference and pressure coefficients explicitly:

```
q_ref = 0.5 * rho * U_ref^2
Cp = (p_surface - p_ref) / q_ref
p_net = p_external - p_internal
face_force = - p_net * area * outward_unit_normal
F_total = sum(face_force + optional_viscous_force)
M_about_O = sum(cross(face_centroid - O, face_force + optional_viscous_force))
```

Check OpenFOAM pressure units: in some incompressible solver configurations, the solved `p` is kinematic pressure and must be multiplied by density to obtain Pa. Preserve pressure sign conventions explicitly.

For structural load mapping, offer shell face pressure, equivalent frame line load (tributary polygon), and nodal forces. Check conservation of global forces and moments before enabling structural export; include a reconciliation table and unmatched surfaces. Do not distribute a roof panel's load to multiple support systems by accident.

Report separate **CFD mean response**, **CFD unsteady statistics (if available)** and **code-based design wind loads**. Do not directly substitute CFD mean Cp for a code's peak/gust factors, nor apply gust multipliers twice. A structural design load requires a documented and validated procedure approved by the responsible engineer.

## 10. Thai standards and regulatory track

- Check applicability of Thailand's 2023 (BE 2566) ministerial structural regulation, section 17, as amended.
- Support DPT 1311-50 (wind loads and building response), including the appropriate reference velocity/exposure, design method, cladding versus MWFRS, internal pressure and dynamic effects.
- Keep standards calculation independent of CFD estimates and identify each source, version, and clause in the final report.
- Do not generalize a building rule to signs or freestanding walls without checking their object-specific requirements.
- Require engineer review and external verification before labeling results "FOR DESIGN".

References: https://www.bsa.or.th/LAW1/MO-STRUCTURE-2566.html ; https://downloads.yotathai.com/doc/dpt-1311-50-wind-load

## 11. Data schema (proposed)

```
scenario: {
  schema_version: 1,
  project_id: "...", case_id: "WIND_000",
  source_model_hash: "...", source_geometry_ids: ["..."],
  wind: {bearing_deg: 0, reference_height_m: 10, reference_speed_ms: null,
         air_density_kgm3: 1.225, terrain_exposure: "user-selected",
         inlet_profile: "ABL", turbulence_model: "version-verified"},
  geometry: {stl_files: [], patch_map: "surface_map.json"},
  solver: {name: "OpenFOAM", distribution: "pinned", version: "pinned"},
  result: {status: "NOT_RUN", validated: false, stale: false,
           directory: "...", summary_file: "..."}
}
```

Fields for code-related speed and terrain must be user-provided or obtained through a separately validated standards module; null must trigger input validation rather than silent defaults.

## 12. Repository layout

```
go-cfd-ingetrazo/
  README.md
  CHANGELOG.md
  docs/
    ENGINEERING_METHOD.md
    CFD_VALIDATION.md
    USER_GUIDE.md
  go_cfd/
    __init__.py            # setup(app), menus, panel wiring
    constants.py
    ui.py                  # Qt controls, log + progress
    host_adapter.py        # IngeTrazo API boundary
    geometry_export.py
    geometry_checks.py
    cfd_case.py            # schema + validation
    mesh_builder.py        # OpenFOAM dictionaries
    runner.py              # isolated worker / subprocess
    results_import.py      # pressure, velocity, VTK
    viewer.py              # overlays / widgets
    pressure_map.py        # spatial mapping to BIM geometry
    structural_export.py   # force/moment conservation
    report.py
  solver_templates/
    <pinned_openfoam_version>/
  examples/
    cube/
    gable_house/
    industrial_roof/
    signboard/
    freestanding_wall/
    cooling_tower_benchmark/
  tests/
    test_plugin_smoke.py
    test_geometry.py
    test_wind_inputs.py
    test_pressure_units.py
    test_patch_mapping.py
    test_force_balance.py
    test_stale_results.py
    test_openfoam_case.py
    test_validation_benchmarks.py
  install_windows.cmd
```

Package only the plugin folder for a community ZIP. The CFD solver, large meshes and case archives are external dependencies, not embedded in the community package.

## 13. Acceptance plan and verification

### W0 - Plugin + scenario workflow
- [ ] Load plugin in a clean IngeTrazo user profile; no traceback.
- [ ] Menu/panel appears, the dialog opens, settings persist per document.
- [ ] Select surfaces, inspect scene geometry, export a patch-preserving, dimensionally correct STL/manifest.
- [ ] Progress/cancellation works, no GUI freeze, New/Open/Undo behaviors remain intact.
- [ ] No unintended BIM/model/sheet changes.

### W1 - First real CFD result: simple cube
- [ ] Version-pinned OpenFOAM found and tested; case builds without manual file editing.
- [ ] `checkMesh` passes documented quality checks.
- [ ] Solver produces demonstrably converged flow / integrated force histories.
- [ ] Cp pressure plot and integrated forces are reproducible.
- [ ] Compare Cp and force trends with published cube benchmarks; record deviations.
- [ ] Three mesh densities + domain sensitivity; no unverified PASS shortcut.

### W2 - Five engineering objects
- [ ] House: pitched roof / eaves / ridge separation.
- [ ] Warehouse: wall + roof pressure zones and uplift.
- [ ] Signboard: front/back pressure and overturning moment.
- [ ] Freestanding wall: end/top effects, isolated/porous case.
- [ ] Cooling tower: Cp versus circumferential angle and height; compare against experimental curve and published geometry/flow definition.
- [ ] Force and moment conservation from CFD faces to structural loads.

### W3 - Structural and report integration
- [ ] Directional wind cases + envelopes (with sound peak/design methodology).
- [ ] External/internal pressure methodology documented.
- [ ] Export model-mapped cases to GO Structural Analysis; no silent doubling of loads.
- [ ] PDF case report and artifacts with complete traceability.
- [ ] Source-model edits mark all affected CFD results STALE.

### W4 - Advanced CFD and validation
- [ ] Transient flows, appropriate turbulence model and gust statistics.
- [ ] Additional benchmarks with wind-tunnel results.
- [ ] Performance benchmarks on different hardware.
- [ ] Third-party engineering review / qualification boundaries defined.

The AIJ guidelines emphasize comparison against wind-tunnel/field data and mesh/domain choice; use this guidance for validation planning, not as a blanket certification: https://www.sciencedirect.com/science/article/pii/S0167610508000445

## 14. Implementation priority and exclusions

**First release target:** functional cube and pitched-roof results using a real OpenFOAM backend, plus a working UI and results import. It is not yet a design-approval tool.

**Exclude from the first release:** fully validated building code design load generation, general-purpose unsteady LES for every model, complex fluid-structure interaction, live GPU fluid simulation in IngeTrazo viewport, automatic porosity inference from arbitrary CAD materials, and stamping engineering reports as approved.

Do not publish a community catalog release until the plugin has been tested on its declared IngeTrazo version and the exact ZIP passes install/verification checks.

## 15. Ready-to-use Codex task

Inspect `https://github.com/ingelibre/ingetrazo/blob/main/docs/plugins.md` and working bundled reference plugins, then scaffold the public repository `go-cfd-ingetrazo` according to this specification. Preserve the host's plugin API and use a module-level `setup(app)`. Implement only W0 and the W1 cube pipeline first. Build a true external OpenFOAM case runner that does not freeze Qt, and record case version, provenance, errors, residuals and results. No fabricated CFD output or claimed engineering validity. Add runnable geometry, math and plugin smoke tests. Report PASS / FAIL / NOT TESTED for source tests, actual OpenFOAM cases, and actual installed-host tests separately. Do not claim host compatibility or numerical validation unless performed.
