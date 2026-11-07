import pytest
from go_cfd.results import parse_force_line
from go_cfd.runner import SolverRunner
from go_cfd.case_builder import build_case
from go_cfd.case_model import WindConfig
from go_cfd.geometry import cube_patch
import json


def test_force_line_with_pressure_and_viscous():
    row = '10 ((1 2 3) (4 5 6) (0 0 0)) ((7 8 9) (10 11 12) (0 0 0))'
    item = parse_force_line(row)
    assert item.time == 10
    assert item.force_total_N == (5,7,9)
    assert item.moment_total_Nm == (17,19,21)
    assert parse_force_line('# comment') is None
    with pytest.raises(ValueError):
        parse_force_line('12 invalid')


def test_solver_missing_is_reported_not_approved(tmp_path, monkeypatch):
    case = tmp_path / 'c'
    build_case(case, (cube_patch(),), WindConfig(speed_ms=15))
    monkeypatch.setattr('go_cfd.runner.shutil.which', lambda _: None)
    runner = SolverRunner(case)
    with pytest.raises(FileNotFoundError, match='not on PATH'):
        runner.run()
    manifest = json.loads((case / 'go_cfd_manifest.json').read_text())
    assert manifest['status'] == 'FAILED'
    assert manifest['validation'] == 'NOT_TESTED'
    assert manifest['design_use'] is False


def test_pipeline_orchestration_with_fake_executables(tmp_path, monkeypatch):
    """This tests launch/status only, NOT a real OpenFOAM solution."""
    import os
    import sys
    from go_cfd.runner import STAGES
    if sys.platform == 'win32':
        pytest.skip('POSIX mock command test')
    fake_dir = tmp_path / 'bin'
    fake_dir.mkdir()
    for command, _ in STAGES:
        script = fake_dir / command
        script.write_text('#!/bin/sh\necho fake-openfoam-stage\nexit 0\n')
        script.chmod(0o755)
    monkeypatch.setenv('PATH', str(fake_dir) + os.pathsep + os.environ.get('PATH',''))
    case = tmp_path / 'c'
    build_case(case, (cube_patch(),), WindConfig(speed_ms=15))
    names = []
    runner = SolverRunner(case)
    assert runner.run(on_stage=lambda stage, i, n: names.append(stage)) == 'SOLVER_COMPLETED_UNVERIFIED'
    assert names == [s for s, _ in STAGES]
    assert (case / 'solver_logs' / '04_simpleFoam.log').exists()
    result = json.loads((case / 'go_cfd_manifest.json').read_text())
    assert result['status'] == 'SOLVER_COMPLETED_UNVERIFIED'
    assert result['validation'] == 'NOT_TESTED'