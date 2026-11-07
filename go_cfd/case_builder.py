"""OpenFOAM OpenCFD-v2606 steady RANS case writer: preliminary case only.

Generated dictionaries follow the OpenCFD line (v2606) and are subject to
live OpenFOAM syntax/mesh/solver QA before any engineering use.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json
import math

from .case_model import WindConfig, case_fingerprint, make_domain
from .constants import TARGET_OPENFOAM, VERSION, TEMPLATE_VERSION
from .geometry import Patch, geometry_hash, inspect_surface, rotated_patch, write_ascii_stl
from .loads import reference_pressure_pa

HEADER = '''/*--------------------------------*- C++ -*----------------------------------*\\
| GO CFD OpenFOAM case | PRELIMINARY / NOT FOR STRUCTURAL DESIGN             |
\\*---------------------------------------------------------------------------*/
'''


def _dict(class_name: str, name: str, text: str, *, location: str | None = None) -> str:
    loc = f'    location    "{location}";\n' if location else ""
    return (HEADER + "FoamFile\n{\n    version     2.0;\n    format      ascii;\n"
            + f"    class       {class_name};\n{loc}    object      {name};\n}}\n\n"
            + text.rstrip() + "\n")


def _vector(v) -> str:
    return "(" + " ".join(f"{float(x):.10g}" for x in v) + ")"


def _block_mesh(domain) -> str:
    lo, hi = domain.minimum, domain.maximum
    verts = [(lo[0],lo[1],lo[2]),(hi[0],lo[1],lo[2]),
             (hi[0],hi[1],lo[2]),(lo[0],hi[1],lo[2]),
             (lo[0],lo[1],hi[2]),(hi[0],lo[1],hi[2]),
             (hi[0],hi[1],hi[2]),(lo[0],hi[1],hi[2])]
    return _dict("dictionary", "blockMeshDict", f'''
scale 1;
vertices
(
{chr(10).join('    '+_vector(p) for p in verts)}
);
blocks (hex (0 1 2 3 4 5 6 7) {_vector(domain.cells)} simpleGrading (1 1 1));
edges ();
boundary
(
    inlet  {{ type patch; faces ((0 4 7 3)); }}
    outlet {{ type patch; faces ((1 2 6 5)); }}
    ground {{ type wall;  faces ((0 3 2 1)); }}
    top    {{ type symmetryPlane; faces ((4 5 6 7)); }}
    sideMin {{ type symmetryPlane; faces ((0 1 5 4)); }}
    sideMax {{ type symmetryPlane; faces ((3 7 6 2)); }}
);
mergePatchPairs ();
''')


def _snappy(domain, patches) -> str:
    geometry = "\n".join(f'    {p.name}.stl {{ type triSurfaceMesh; name {p.name}; }}'
                         for p in patches)
    surfaces = "\n".join(f'        {p.name} {{ level (2 3); patchInfo {{ type wall; }} }}'
                          for p in patches)
    return _dict("dictionary", "snappyHexMeshDict", f'''
castellatedMesh true;
snap            true;
addLayers       false;
mergeTolerance  1e-6;
geometry
{{
{geometry}
}}
castellatedMeshControls
{{
    maxLocalCells  1500000;
    maxGlobalCells 3500000;
    minRefinementCells 0;
    maxLoadUnbalance 0.10;
    nCellsBetweenLevels 3;
    features ();
    refinementSurfaces
    {{
{surfaces}
    }}
    resolveFeatureAngle 30;
    refinementRegions {{ }}
    locationInMesh {_vector(domain.location_in_mesh)};
    allowFreeStandingZoneFaces true;
}}
snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 30;
    nRelaxIter 5;
    nFeatureSnapIter 10;
    implicitFeatureSnap false;
    explicitFeatureSnap false;
    multiRegionFeatureSnap false;
}}
addLayersControls
{{
    relativeSizes true;
    layers {{ }}
    expansionRatio 1.0;
    finalLayerThickness 0.3;
    minThickness 0.1;
    nGrow 0;
    featureAngle 60;
    nRelaxIter 3;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedianAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
}}
meshQualityControls
{{
    maxNonOrtho 65;
    maxBoundarySkewness 20;
    maxInternalSkewness 4;
    maxConcave 80;
    minVol 1e-13;
    minTetQuality -1e30;
    minArea -1;
    minTwist 0.02;
    minDeterminant 0.001;
    minFaceWeight 0.02;
    minVolRatio 0.01;
    minTriangleTwist -1;
    nSmoothScale 4;
    errorReduction 0.75;
}}
''')


def _control(cfg, patches, origin) -> str:
    funcs = "\n".join(f'''
    forces_{p.name}
    {{
        type forces;
        libs ("libforces.so");
        patches ({p.name});
        p p;
        U U;
        rho rhoInf;
        rhoInf {cfg.density_kgm3:.10g};
        CofR {_vector(origin)};
        writeControl timeStep;
        writeInterval 25;
    }}''' for p in patches)
    return _dict("dictionary", "controlDict", f'''
application simpleFoam;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime {cfg.iterations};
deltaT 1;
writeControl timeStep;
writeInterval 100;
purgeWrite 2;
writeFormat ascii;
writePrecision 8;
runTimeModifiable true;
functions
{{
{funcs}
}}
''')


def _fv_schemes() -> str:
    return _dict("dictionary", "fvSchemes", '''
ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; grad(U) cellLimited Gauss linear 1; }
divSchemes
{
    default none;
    div(phi,U) bounded Gauss linearUpwind grad(U);
    div(phi,k) bounded Gauss upwind;
    div(phi,epsilon) bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist { method meshWave; }
''')


def _fv_solution() -> str:
    return _dict("dictionary", "fvSolution", '''
solvers
{
    p
    {
        solver GAMG;
        tolerance 1e-7;
        relTol 0.05;
        smoother GaussSeidel;
    }
    "(U|k|epsilon)"
    {
        solver smoothSolver;
        smoother symGaussSeidel;
        tolerance 1e-7;
        relTol 0.1;
    }
}
SIMPLE
{
    nNonOrthogonalCorrectors 1;
    consistent yes;
    residualControl
    {
        p 1e-4;
        U 1e-5;
        "(k|epsilon)" 1e-5;
    }
}
relaxationFactors
{
    fields { p 0.3; }
    equations { U 0.7; k 0.7; epsilon 0.7; }
}
''')


def _field(name: str, dimensions: str, init: str, inlet: str,
           outlet: str, wall: str, patches: tuple[Patch, ...]) -> str:
    surfaces = "\n".join(f"    {p.name} {{ {wall} }}" for p in patches)
    return _dict("volVectorField" if name == "U" else "volScalarField",
                 name, f'''
dimensions {dimensions};
internalField uniform {init};
boundaryField
{{
    inlet {{ {inlet} }}
    outlet {{ {outlet} }}
    ground {{ {wall} }}
    top {{ type symmetryPlane; }}
    sideMin {{ type symmetryPlane; }}
    sideMax {{ type symmetryPlane; }}
{surfaces}
}}
''', location="0")


def _fields(cfg, patches, H):
    U = f"({cfg.speed_ms:.10g} 0 0)"
    k = max(1e-10, 1.5 * (cfg.speed_ms * cfg.turbulence_intensity)**2)
    length = 0.07 * max(H, 0.1)
    epsilon = max(1e-10, (0.09**0.75) * (k**1.5) / length)
    return {
        "0/U": _field("U", "[0 1 -1 0 0 0 0]", U,
                      f"type fixedValue; value uniform {U};",
                      f"type inletOutlet; inletValue uniform {U}; value uniform {U};",
                      "type noSlip;", patches),
        "0/p": _field("p", "[0 2 -2 0 0 0 0]", "0",
                      "type zeroGradient;", "type fixedValue; value uniform 0;",
                      "type zeroGradient;", patches),
        "0/k": _field("k", "[0 2 -2 0 0 0 0]", f"{k:.10g}",
                      f"type fixedValue; value uniform {k:.10g};",
                      f"type inletOutlet; inletValue uniform {k:.10g}; value uniform {k:.10g};",
                      f"type kqRWallFunction; value uniform {k:.10g};", patches),
        "0/epsilon": _field("epsilon", "[0 2 -3 0 0 0 0]", f"{epsilon:.10g}",
                      f"type fixedValue; value uniform {epsilon:.10g};",
                      f"type inletOutlet; inletValue uniform {epsilon:.10g}; value uniform {epsilon:.10g};",
                      f"type epsilonWallFunction; value uniform {epsilon:.10g};", patches),
        "0/nut": _field("nut", "[0 2 -1 0 0 0 0]", "0",
                        "type calculated; value uniform 0;",
                        "type calculated; value uniform 0;",
                        "type nutkWallFunction; value uniform 0;", patches),
    }


def make_case_files(patches: tuple[Patch, ...], cfg: WindConfig) -> tuple[dict, dict[str, str]]:
    """Render case to dictionary of file paths and contents without writing."""
    cfg.validate()
    if len({p.name for p in patches}) != len(patches):
        raise ValueError("CFD patch names must be unique")
    if not inspect_surface(patches)["watertight_candidate"]:
        raise ValueError("Surface screening failed. Close gaps/fix duplicates before meshing")
    rotated = tuple(rotated_patch(p, cfg.direction_to_deg) for p in patches)
    domain = make_domain(rotated, cfg)
    files = {
        "system/blockMeshDict": _block_mesh(domain),
        "system/snappyHexMeshDict": _snappy(domain, rotated),
        "system/controlDict": _control(cfg, rotated, (0.0, 0.0, cfg.ground_z_m)),
        "system/fvSchemes": _fv_schemes(),
        "system/fvSolution": _fv_solution(),
        "constant/transportProperties": _dict("dictionary", "transportProperties", f'''
transportModel Newtonian;
nu [0 2 -1 0 0 0 0] {cfg.viscosity_m2s:.10g};
'''),
        "constant/turbulenceProperties": _dict("dictionary", "turbulenceProperties", '''
simulationType RAS;
RAS { RASModel kEpsilon; turbulence on; printCoeffs on; }
'''),
    }
    files.update(_fields(cfg, rotated, domain.scale_H_m))
    provenance = {
        "go_cfd_version": VERSION,
        "openfoam_target": TARGET_OPENFOAM,
        "template_version": TEMPLATE_VERSION,
        "moment_reference_point_cfd_m": [0.0, 0.0, cfg.ground_z_m],
        "status": "NOT_RUN",
        "validation": "NOT_TESTED",
        "design_use": False,
        "inlet_profile": "UNIFORM - not atmospheric boundary layer",
        "source_geometry_hash": geometry_hash(patches),
        "case_fingerprint": case_fingerprint(cfg, geometry_hash(patches)),
        "scenario": asdict(cfg),
        "domain": asdict(domain),
        "q_ref_pa": reference_pressure_pa(cfg.density_kgm3, cfg.speed_ms),
        "patches": [{"patch": p.name, "source_id": p.source_id,
                     "triangles": len(p.triangles), "stl": p.name + ".stl"} for p in patches],
        "wind_transform": "world XY rotated -direction_to_deg; +CFD X inflow",
        "warnings": ["Exploratory steady RANS only", "No ABL profile", "No mesh/convergence/benchmark certification", "No design wind loads"],
    }
    return provenance, files


def build_case(destination: Path, patches: tuple[Patch, ...], cfg: WindConfig) -> dict:
    """Create a new case in an EMPTY directory; never replace existing results."""
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Refusing to overwrite existing case: {destination}")
    provenance, files = make_case_files(patches, cfg)
    destination.mkdir(parents=True, exist_ok=True)
    rotated = tuple(rotated_patch(p, cfg.direction_to_deg) for p in patches)
    for p in rotated:
        write_ascii_stl(destination / "constant" / "triSurface" / f"{p.name}.stl", p)
    for path, text in files.items():
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    (destination / "go_cfd_manifest.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return provenance
