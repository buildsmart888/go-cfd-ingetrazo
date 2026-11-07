"""Regression: IngeTrazo runs from Program Files but OpenFOAM must not."""
from __future__ import annotations
from types import SimpleNamespace

import pytest

from go_cfd.case_builder import build_case
from go_cfd.case_model import WindConfig
from go_cfd.geometry import cube_patch
from go_cfd.runner import SolverRunner, STAGES, _wsl_exec


def test_wsl_exec_root_is_explicit():
    assert _wsl_exec("bash", "-lc", "pwd") == [
        "wsl.exe", "--cd", "/", "--exec", "bash", "-lc", "pwd"
    ]


def test_every_wsl_preflight_command_sets_safe_linux_cwd(monkeypatch, tmp_path):
    monkeypatch.setattr("go_cfd.runner._is_windows", lambda: True)
    monkeypatch.setattr("go_cfd.runner.shutil.which", lambda _: "wsl.exe")
    seen = []

    def fake_capture(argv, **kwargs):
        seen.append(argv)
        if "wslpath" in argv:
            return SimpleNamespace(stdout="/mnt/c/GO_CFD_Cases/cube\n", stderr="", returncode=0)
        if "GO_CFD_WSL_READY" in str(argv):
            return SimpleNamespace(stdout="GO_CFD_WSL_READY", stderr="", returncode=0)
        return SimpleNamespace(stdout="PATH:/usr/bin/blockMesh", stderr="", returncode=0)

    monkeypatch.setattr("go_cfd.runner.SolverRunner._capture", staticmethod(fake_capture))
    runner = SolverRunner(tmp_path, backend="wsl")
    runner.case_dir = r"C:\GO_CFD_Cases\cube"
    runner.preflight()
    assert len(seen) == 3
    assert all(cmd[:4] == ["wsl.exe", "--cd", "/", "--exec"] for cmd in seen)
    assert all(
        runner._commands(prog, args)[:4] == ["wsl.exe", "--cd", "/", "--exec"]
        for prog, args in STAGES
    )


def test_preflight_blocks_whitespace_in_openfoam_case_path(monkeypatch, tmp_path):
    monkeypatch.setattr("go_cfd.runner._is_windows", lambda: True)
    monkeypatch.setattr("go_cfd.runner.shutil.which", lambda _: "wsl.exe")

    def fake_capture(argv, **kwargs):
        if "wslpath" in argv:
            return SimpleNamespace(stdout="/mnt/c/Some Folder/cube\n", stderr="", returncode=0)
        return SimpleNamespace(stdout="GO_CFD_WSL_READY", stderr="", returncode=0)

    monkeypatch.setattr("go_cfd.runner.SolverRunner._capture", staticmethod(fake_capture))
    runner = SolverRunner(tmp_path, backend="wsl")
    runner.case_dir = r"C:\Some Folder\cube"
    with pytest.raises(ValueError, match="contains whitespace"):
        runner.preflight()


def test_launch_from_windows_app_uses_case_as_process_cwd(monkeypatch, tmp_path):
    monkeypatch.setattr("go_cfd.runner._is_windows", lambda: True)
    case = tmp_path / "case"
    build_case(case, (cube_patch(),), WindConfig(speed_ms=20))
    runner = SolverRunner(case, backend="wsl", foam_bashrc="/opt/openfoam/etc/bashrc")
    runner._wsl_case = "/mnt/c/GO_CFD_Cases/cube"
    runner.preflight = lambda: "fake ready"
    observed = []

    class FakeProcess:
        def __init__(self):
            self.stdout = iter(["mock solver output\n"])
        def wait(self):
            return 0
        def poll(self):
            return None

    def fake_popen(cmd, **kwargs):
        observed.append((cmd, kwargs))
        return FakeProcess()

    monkeypatch.setattr("go_cfd.runner.subprocess.Popen", fake_popen)
    assert runner.run() == "SOLVER_COMPLETED_UNVERIFIED"
    assert len(observed) == len(STAGES)
    assert all(item[0][:4] == ["wsl.exe", "--cd", "/", "--exec"] for item in observed)
    assert all(item[1]["cwd"] == str(case) for item in observed)
