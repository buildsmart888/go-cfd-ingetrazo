"""Genuine field-data tests using synthetic fixtures ONLY for validation.

Fixtures are never shipped as a fake completed CFD simulation.
"""
import json
from pathlib import Path
import numpy as np
import pytest

vtk = pytest.importorskip("vtk")
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

from go_cfd.postprocessing import find_latest_vtk, export_case_vtk
from go_cfd.vtk_results import (load_cfd_results, CFDFieldError, read_volume,
    with_speed, with_pressure_pa, with_cp, horizontal_slice, streamlines, read_boundary)


def make_vtu(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    image = vtk.vtkImageData()
    image.SetDimensions(8, 7, 6)
    image.SetSpacing(.5, .5, .5)
    n = image.GetNumberOfPoints()
    coords = np.array([image.GetPoint(i) for i in range(n)])
    u = numpy_to_vtk(np.column_stack([np.full(n, 10.), np.zeros(n), np.zeros(n)]), deep=True)
    u.SetName("U")
    image.GetPointData().AddArray(u)
    p = numpy_to_vtk(coords[:, 0] * 2, deep=True)
    p.SetName("p")
    image.GetPointData().AddArray(p)
    convert = vtk.vtkAppendFilter()
    convert.AddInputData(image)
    convert.Update()
    writer = vtk.vtkXMLUnstructuredGridWriter()
    path = directory / "internal.vtu"
    writer.SetFileName(str(path))
    writer.SetInputData(convert.GetOutput())
    assert writer.Write() == 1
    return path


def make_boundary(directory: Path, label="surface_001"):
    directory.mkdir(parents=True, exist_ok=True)
    square = vtk.vtkPlaneSource()
    square.SetOrigin(1, 1, 0)
    square.SetPoint1(2, 1, 0)
    square.SetPoint2(1, 2, 0)
    square.Update()
    mesh = square.GetOutput()
    scalar = numpy_to_vtk(np.full(mesh.GetNumberOfPoints(), -5.0), deep=True)
    scalar.SetName("p")
    mesh.GetPointData().AddArray(scalar)
    writer = vtk.vtkXMLPolyDataWriter()
    path = directory / (label + ".vtp")
    writer.SetFileName(str(path))
    writer.SetInputData(mesh)
    assert writer.Write() == 1
    return path


def sample_case(tmp_path, status="SOLVER_COMPLETED_UNVERIFIED"):
    case = tmp_path / "cube"
    case.mkdir()
    (case / "go_cfd_manifest.json").write_text(json.dumps({
        "case_fingerprint": "f1", "go_cfd_version": "0.2.3-dev", "status": status,
        "scenario": {"density_kgm3": 1.225, "speed_ms": 20.0, "ground_z_m": 0.0},
    }))
    make_vtu(case / "VTK" / "cube_100")
    make_boundary(case / "VTK" / "cube_100" / "boundary")
    return case


def test_discovery_prefers_numeric_latest_time(tmp_path):
    case = sample_case(tmp_path)
    make_vtu(case / "VTK" / "cube_25")  # newer mtime, earlier physical time
    files = find_latest_vtk(case)
    assert files.volume_file.parent.name == "cube_100"
    assert len(files.boundary_files) == 1
    assert files.boundary_files[0].stem == "surface_001"


def test_real_vtk_field_transforms(tmp_path):
    case = sample_case(tmp_path)
    loaded = load_cfd_results(case)
    assert loaded.is_solver_completed
    vol = read_volume(loaded.files.volume_file)
    speed = vtk_to_numpy(with_speed(vol).GetPointData().GetArray("Velocity_m_s"))
    assert np.allclose(speed, 10.0)
    press = vtk_to_numpy(with_pressure_pa(vol, 1.225).GetPointData().GetArray("Pressure_Pa"))
    assert np.isclose(press.max(), 3.5 * 2 * 1.225)
    cp = vtk_to_numpy(with_cp(vol, 20).GetPointData().GetArray("Cp"))
    assert np.isclose(cp.max(), 2 * (3.5 * 2) / 400)
    section = horizontal_slice(vol, 1.25)
    assert section.GetNumberOfCells() > 0
    lines = streamlines(vol, seed_count=16)
    assert lines.GetNumberOfLines() > 0
    assert lines.GetPointData().GetArray("Velocity_m_s") is not None
    surf = read_boundary(loaded.files.boundary_files[0])
    cp_surf = vtk_to_numpy(with_cp(surf, 20).GetPointData().GetArray("Cp"))
    assert np.allclose(cp_surf, -0.025)


def test_empty_and_missing_fields_are_rejected(tmp_path):
    case = sample_case(tmp_path)
    (case / "VTK" / "cube_100" / "internal.vtu").unlink()
    with pytest.raises(FileNotFoundError, match="internal.vtu"):
        find_latest_vtk(case)


def test_stale_vtk_provenance_is_refused(tmp_path):
    case = sample_case(tmp_path)
    (case / "go_cfd_vtk_export.json").write_text(json.dumps({"source_case_fingerprint":"old"}))
    with pytest.raises(CFDFieldError, match="STALE"):
        load_cfd_results(case)


def test_export_refuses_unfinished_solver(tmp_path):
    case = sample_case(tmp_path, status="FAILED")
    class FakeRunner:
        case_dir = case
        def preflight(self):
            raise AssertionError("must not invoke OpenFOAM after solver failed")
    with pytest.raises(RuntimeError, match="requires all four"):
        export_case_vtk(case, FakeRunner())


def test_kinematic_pressure_and_cp_require_positive_references(tmp_path):
    case = sample_case(tmp_path)
    vol = read_volume(find_latest_vtk(case).volume_file)
    with pytest.raises(ValueError, match="density"):
        with_pressure_pa(vol, 0)
    with pytest.raises(ValueError, match="speed"):
        with_cp(vol, 0)
    with pytest.raises(ValueError, match="seed"):
        streamlines(vol, seed_count=1)


def test_export_writes_provenance_for_existing_real_vtk_only(tmp_path, monkeypatch):
    case = sample_case(tmp_path)
    from types import SimpleNamespace
    calls = []
    class FakeRunner:
        case_dir = case.resolve()
        def preflight(self):
            return "mock-openfoam-available"
        def _commands(self, program, args):
            calls.append((program, args))
            return ["fake-foamToVTK", *args]
    class FakeProcess:
        stdout = iter(["Writing internal.vtu\n", "Writing boundary files\n"])
        def wait(self):
            return 0
    def fake_popen(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeProcess()
    monkeypatch.setattr("go_cfd.postprocessing.subprocess.Popen", fake_popen)
    log = []
    result = export_case_vtk(case, FakeRunner(), on_log=log.append)
    assert result.volume_file.is_file()
    assert calls[0] == ("foamToVTK", ("-latestTime", "-fields", "(U p)"))
    assert "Writing internal.vtu" in log
    data = json.loads((case / "go_cfd_vtk_export.json").read_text())
    assert data["validation"] == "NOT_TESTED"
    assert data["source_case_fingerprint"] == "f1"
    assert data["steady_state"] is True
    assert "NOT VALIDATED" not in data.get("source_solver_state", "")
    assert (case / "solver_logs" / "05_foamToVTK.log").is_file()


def test_export_fails_without_generated_vtk(tmp_path, monkeypatch):
    case = sample_case(tmp_path)
    for path in (case / "VTK").rglob("*.*"):
        path.unlink()
    class FakeRunner:
        case_dir = case.resolve()
        def preflight(self):
            return "mock"
        def _commands(self, program, args):
            return ["foamToVTK", *args]
    from types import SimpleNamespace
    monkeypatch.setattr("go_cfd.postprocessing.subprocess.Popen", lambda *_a, **_kw:
                        SimpleNamespace(stdout=iter(["No fields\n"]), wait=lambda: 0))
    with pytest.raises(FileNotFoundError, match="internal.vtu"):
        export_case_vtk(case, FakeRunner())
    assert not (case / "go_cfd_vtk_export.json").exists()
