"""Real VTK field extraction and visualization pipelines (without Qt imports).

Reads foamToVTK's internal.vtu / boundary *.vtp. Uses native VTK as an
optional dependency and raises precise errors if a field is absent; no
synthetic wind velocity, pressure or Cp is invented by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math

from .postprocessing import ExportResult, find_latest_vtk

MAX_VTK_FILE_BYTES = 750 * 1024 * 1024  # protect an interactive GUI from very large jobs


class CFDFieldError(RuntimeError):
    pass


def _vtk():
    try:
        import vtk
    except ImportError as exc:
        raise CFDFieldError(
            "VTK is not installed in IngeTrazo's Python environment. "
            "Install the optional vtk package in the SAME Python interpreter as IngeTrazo, "
            "or open the VTK files with ParaView instead."
        ) from exc
    return vtk


def _vtk_file(path: Path, reader_name: str):
    vtk = _vtk()
    path = Path(path)
    if not path.is_file():
        raise CFDFieldError(f"VTK data file not found: {path}")
    if path.stat().st_size > MAX_VTK_FILE_BYTES:
        raise CFDFieldError(
            f"Dataset {path.name} exceeds the interactive 750 MB file limit; "
            "use ParaView or decimate/export a smaller dataset."
        )
    reader = getattr(vtk, reader_name)()
    reader.SetFileName(str(path))
    reader.Update()
    data = reader.GetOutput()
    if data is None or data.GetNumberOfCells() == 0:
        raise CFDFieldError(f"Empty or unreadable VTK dataset: {path}")
    return data


def read_volume(path: Path):
    """Return field-bearing VTK volume data, cell arrays interpolated to points."""
    vtk = _vtk()
    volume = _vtk_file(path, "vtkXMLUnstructuredGridReader")
    c2p = vtk.vtkCellDataToPointData()
    c2p.SetInputData(volume)
    c2p.PassCellDataOn()
    c2p.Update()
    result = vtk.vtkUnstructuredGrid()
    result.ShallowCopy(c2p.GetOutput())
    u = result.GetPointData().GetArray("U")
    p = result.GetPointData().GetArray("p")
    if u is None or u.GetNumberOfComponents() != 3:
        raise CFDFieldError("VTK volume has no 3-component velocity U. Export fields (U p).")
    if p is None or p.GetNumberOfComponents() != 1:
        raise CFDFieldError("VTK volume has no scalar kinematic pressure p. Export fields (U p).")
    return result


def read_boundary(path: Path):
    vtk = _vtk()
    data = _vtk_file(path, "vtkXMLPolyDataReader")
    c2p = vtk.vtkCellDataToPointData()
    c2p.SetInputData(data)
    c2p.PassCellDataOn()
    c2p.Update()
    result = vtk.vtkPolyData()
    result.ShallowCopy(c2p.GetOutput())
    if result.GetPointData().GetArray("p") is None:
        raise CFDFieldError(f"Surface {path.name} does not have OpenFOAM pressure p")
    return result


def _derived_field(dataset, *, expression: str, array_name: str,
                   vector_names: tuple[str, ...] = (), scalar_names: tuple[str, ...] = ()):
    vtk = _vtk()
    calc = vtk.vtkArrayCalculator()
    calc.SetInputData(dataset)
    calc.SetAttributeTypeToPointData()
    for name in vector_names:
        calc.AddVectorArrayName(name)
    for name in scalar_names:
        calc.AddScalarArrayName(name)
    calc.SetResultArrayName(array_name)
    calc.SetFunction(expression)
    calc.Update()
    out = calc.GetOutput().NewInstance()
    out.ShallowCopy(calc.GetOutput())
    if out.GetPointData().GetArray(array_name) is None:
        raise CFDFieldError(f"Unable to derive {array_name} from CFD dataset")
    return out


def with_speed(volume):
    return _derived_field(volume, expression="mag(U)", array_name="Velocity_m_s",
                          vector_names=("U",))


def with_pressure_pa(dataset, density_kgm3: float):
    if not math.isfinite(density_kgm3) or density_kgm3 <= 0:
        raise ValueError("Positive air density is required to convert kinematic p to Pa")
    return _derived_field(dataset, expression=f"p*{density_kgm3:.12g}",
                          array_name="Pressure_Pa", scalar_names=("p",))


def with_cp(dataset, speed_ms: float, *, p_ref_kinematic: float = 0.0):
    if not math.isfinite(speed_ms) or speed_ms <= 0:
        raise ValueError("Positive reference speed is required for Cp")
    if not math.isfinite(p_ref_kinematic):
        raise ValueError("Reference pressure must be finite")
    # Incompressible OpenFOAM p has units m^2/s^2; rho cancels from Cp.
    return _derived_field(dataset,
                          expression=f"2*(p-({p_ref_kinematic:.12g}))/{(speed_ms*speed_ms):.12g}",
                          array_name="Cp", scalar_names=("p",))


def horizontal_slice(volume, elevation_m: float):
    vtk = _vtk()
    bounds = volume.GetBounds()
    if not math.isfinite(elevation_m) or not (bounds[4] <= elevation_m <= bounds[5]):
        raise ValueError(f"Slice elevation must be between {bounds[4]:.3f} and {bounds[5]:.3f} m")
    plane = vtk.vtkPlane()
    plane.SetOrigin(0.0, 0.0, elevation_m)
    plane.SetNormal(0.0, 0.0, 1.0)
    cutter = vtk.vtkCutter()
    cutter.SetInputData(volume)
    cutter.SetCutFunction(plane)
    cutter.Update()
    result = vtk.vtkPolyData()
    result.ShallowCopy(cutter.GetOutput())
    if result.GetNumberOfCells() == 0:
        raise CFDFieldError("Requested horizontal slice contains no cells")
    return result


def streamlines(volume, *, seed_count: int = 80, max_length_factor: float = 1.5):
    """Trace steady velocity U, seeding a rectangular plane near domain inlet."""
    vtk = _vtk()
    if not 4 <= seed_count <= 300:
        raise ValueError("Streamline seed count must be 4..300")
    u = volume.GetPointData().GetArray("U")
    if u is None or u.GetNumberOfComponents() != 3:
        raise CFDFieldError("Volume velocity U is not available")
    b = volume.GetBounds()
    dx, dy, dz = b[1]-b[0], b[3]-b[2], b[5]-b[4]
    source = vtk.vtkPlaneSource()
    # CFD world is aligned to +X by the GO CFD case exporter.
    x = b[0] + 0.02 * dx
    source.SetOrigin(x, b[2]+0.06*dy, b[4]+0.06*dz)
    source.SetPoint1(x, b[3]-0.06*dy, b[4]+0.06*dz)
    source.SetPoint2(x, b[2]+0.06*dy, b[5]-0.06*dz)
    source.SetXResolution(max(2, int(math.sqrt(seed_count*1.5))))
    source.SetYResolution(max(2, int(math.sqrt(seed_count/1.5))))
    source.Update()
    tracer = vtk.vtkStreamTracer()
    tracer.SetInputData(volume)
    tracer.SetSourceConnection(source.GetOutputPort())
    tracer.SetIntegrator(vtk.vtkRungeKutta4())
    tracer.SetIntegrationDirectionToForward()
    tracer.SetMaximumPropagation(dx * max_length_factor)
    tracer.SetInitialIntegrationStep(max(min(dx,dy,dz)/80.0, 0.001))
    tracer.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, "U")
    tracer.Update()
    output = vtk.vtkPolyData()
    output.ShallowCopy(tracer.GetOutput())
    if output.GetNumberOfLines() < 1:
        raise CFDFieldError("No streamlines crossed the inlet seed plane. Check U and flow direction.")
    # Tracer normally carries U as point field. Magnitudes remain solver-derived.
    return with_speed(output)


@dataclass(frozen=True)
class LoadedCFD:
    files: ExportResult
    volume: object
    boundary_paths: tuple[Path, ...]
    density_kgm3: float
    reference_speed_ms: float
    ground_z_m: float
    is_solver_completed: bool
    source_version: str


def load_cfd_results(case_dir: Path) -> LoadedCFD:
    files = find_latest_vtk(case_dir)
    manifest = json.loads((files.case_dir / "go_cfd_manifest.json").read_text(encoding="utf-8"))
    scenario = manifest.get("scenario") or {}
    density = float(scenario.get("density_kgm3", 0))
    speed = float(scenario.get("speed_ms", 0))
    ground = float(scenario.get("ground_z_m", 0))
    if not math.isfinite(ground) or density <= 0 or speed <= 0:
        raise CFDFieldError("Invalid CFD manifest wind speed, density or ground level")
    # If source inputs changed, a previous VTK export must not silently be current.
    provenance_file = files.case_dir / "go_cfd_vtk_export.json"
    if provenance_file.is_file():
        provenance = json.loads(provenance_file.read_text(encoding="utf-8"))
        if provenance.get("source_case_fingerprint") != manifest.get("case_fingerprint"):
            raise CFDFieldError("VTK export is STALE: CFD case fingerprint changed")
    volume = read_volume(files.volume_file)
    return LoadedCFD(files, volume, files.boundary_files, density, speed, ground,
                     manifest.get("status") == "SOLVER_COMPLETED_UNVERIFIED",
                     manifest.get("go_cfd_version", "unknown"))
