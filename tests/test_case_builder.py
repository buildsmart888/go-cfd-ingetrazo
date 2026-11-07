import json
from pathlib import Path
import pytest
from go_cfd.case_model import WindConfig, case_fingerprint, is_stale
from go_cfd.case_builder import build_case, make_case_files
from go_cfd.geometry import Patch, cube_patch, geometry_hash


def test_wind_inputs_required():
    for speed in (0.0, -1.0, float('nan')):
        with pytest.raises(ValueError):
            WindConfig(speed_ms=speed).validate()
    with pytest.raises(ValueError):
        WindConfig(speed_ms=20, direction_to_deg=360).validate()
    with pytest.raises(ValueError):
        WindConfig(speed_ms=20, profile='ABL').validate()


def test_case_generation_and_manifest(tmp_path):
    cfg = WindConfig(speed_ms=20)
    patch = cube_patch()
    manifest = build_case(tmp_path / 'case', (patch,), cfg)
    case = tmp_path / 'case'
    assert manifest['q_ref_pa'] == pytest.approx(245)
    assert manifest['status'] == 'NOT_RUN'
    assert manifest['design_use'] is False
    assert (case / 'constant' / 'triSurface' / 'cube.stl').exists()
    assert (case / 'system' / 'snappyHexMeshDict').exists()
    assert 'forces_cube' in (case / 'system' / 'controlDict').read_text()
    assert 'inlet' in (case / '0' / 'U').read_text()
    assert (case / 'go_cfd_manifest.json').exists()
    assert json.loads((case / 'go_cfd_manifest.json').read_text())['case_fingerprint'] == case_fingerprint(cfg, geometry_hash((patch,)))
    with pytest.raises(FileExistsError):
        build_case(case, (patch,), cfg)


def test_stale_on_changed_wind_or_geometry(tmp_path):
    cfg = WindConfig(speed_ms=20)
    patch = cube_patch()
    manifest = build_case(tmp_path / 'case', (patch,), cfg)
    assert not is_stale(manifest, cfg, geometry_hash((patch,)))
    assert is_stale(manifest, WindConfig(speed_ms=25), geometry_hash((patch,)))
    assert is_stale(manifest, cfg, geometry_hash((cube_patch(side_m=2),)))


def test_nonwatertight_rejected():
    patch = Patch('open', 'id', (((0,0,0),(0,1,0),(0,0,1)),))
    with pytest.raises(ValueError, match='screening failed'):
        make_case_files((patch,), WindConfig(speed_ms=10))
