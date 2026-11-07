"""Pure offline diagnostics: no Windows WSL and no real CFD required."""
from types import SimpleNamespace
import pytest

from go_cfd.runner import SolverRunner


def _result(out="", err="", code=0):
    return SimpleNamespace(stdout=out, stderr=err, returncode=code)


def test_wsl_unavailable_startup_reports_diagnostic(monkeypatch, tmp_path):
    monkeypatch.setattr("go_cfd.runner._is_windows", lambda: True)
    monkeypatch.setattr("go_cfd.runner.shutil.which", lambda _: "C:/Windows/System32/wsl.exe")
    seen = []

    def fake_run(args, **_):
        seen.append(args)
        return _result(err="WSL HCS failure", code=4294967295)

    monkeypatch.setattr("go_cfd.runner.subprocess.run", fake_run)
    runner = SolverRunner(tmp_path, backend="wsl")
    with pytest.raises(RuntimeError, match="wsl --status"):
        runner.preflight()
    assert len(seen) == 1
    assert "wslpath" not in str(seen[0])


def test_wsl_not_installed_help(monkeypatch, tmp_path):
    monkeypatch.setattr("go_cfd.runner._is_windows", lambda: True)
    monkeypatch.setattr("go_cfd.runner.shutil.which", lambda _: None)
    with pytest.raises(FileNotFoundError, match="wsl --list --online"):
        SolverRunner(tmp_path, backend="wsl").preflight()


def test_wsl_starts_but_openfoam_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("go_cfd.runner._is_windows", lambda: True)
    monkeypatch.setattr("go_cfd.runner.shutil.which", lambda _: "wsl.exe")
    calls = []

    def fake_run(args, **_):
        calls.append(args)
        if "wslpath" in args:
            return _result(out="/mnt/c/Users/test/Documents/GO_CFD_Cases\n")
        if "GO_CFD_WSL_READY" in str(args):
            return _result(out="GO_CFD_WSL_READY")
        return _result(code=127)

    monkeypatch.setattr("go_cfd.runner.subprocess.run", fake_run)
    r = SolverRunner(tmp_path, backend="wsl")
    r.case_dir = r"C:\Users\test\Documents\GO_CFD_Cases"
    with pytest.raises(FileNotFoundError, match="not found"):
        r.preflight()
    assert len(calls) == 3


def test_wsl_autodetects_bashrc_and_reuses_path(monkeypatch, tmp_path):
    monkeypatch.setattr("go_cfd.runner._is_windows", lambda: True)
    monkeypatch.setattr("go_cfd.runner.shutil.which", lambda _: "wsl.exe")

    def fake_run(args, **_):
        if "wslpath" in args:
            return _result(out="/mnt/c/Users/test/CFD/case\n")
        if "GO_CFD_WSL_READY" in str(args):
            return _result(out="GO_CFD_WSL_READY")
        return _result(out="BASHRC:/opt/openfoam2606/etc/bashrc")

    monkeypatch.setattr("go_cfd.runner.subprocess.run", fake_run)
    r = SolverRunner(tmp_path, backend="wsl")
    r.case_dir = r"C:\Users\test\CFD\case"
    assert "OpenFOAM blockMesh located" in r.preflight()
    cmd = r._commands("checkMesh", ())
    assert cmd[0] == "wsl.exe"
    assert "/opt/openfoam2606/etc/bashrc" in cmd
    assert "/mnt/c/Users/test/CFD/case" in cmd


def test_native_windows_actionable_error(monkeypatch, tmp_path):
    monkeypatch.setattr("go_cfd.runner._is_windows", lambda: True)
    monkeypatch.setattr("go_cfd.runner.shutil.which", lambda _: None)
    with pytest.raises(FileNotFoundError, match="select 'Windows WSL2'"):
        SolverRunner(tmp_path, backend="native").preflight()


def test_wsl_drive_paths_preserve_slashes(monkeypatch):
    from go_cfd.runner import _windows_path_to_wsl_argument
    monkeypatch.setattr("go_cfd.runner._is_windows", lambda: True)
    native = r"C:\Users\g_np2\Documents\GO CFD Cases\cube"
    assert _windows_path_to_wsl_argument(native) == (
        "C:/Users/g_np2/Documents/GO CFD Cases/cube"
    )
    with pytest.raises(ValueError, match="UNC"):
        _windows_path_to_wsl_argument(r"\\server\share\case")


def test_wsl_exec_does_not_strip_path_separators(monkeypatch, tmp_path):
    monkeypatch.setattr("go_cfd.runner._is_windows", lambda: True)
    monkeypatch.setattr("go_cfd.runner.shutil.which", lambda _: "wsl.exe")
    commands = []

    def fake_run(args, **kwargs):
        commands.append(args)
        if "GO_CFD_WSL_READY" in str(args):
            return _result(out="GO_CFD_WSL_READY")
        if "wslpath" in args:
            return _result(out="/mnt/c/Users/g_np2/Documents/GO CFD Cases/cube\n")
        return _result(out="PATH:/usr/bin/blockMesh")

    monkeypatch.setattr("go_cfd.runner.subprocess.run", fake_run)
    runner = SolverRunner(tmp_path, backend="wsl")
    runner.case_dir = r"C:\Users\g_np2\Documents\GO CFD Cases\cube"
    assert "OpenFOAM blockMesh located" in runner.preflight()
    assert commands[1] == [
        "wsl.exe", "--exec", "wslpath", "-u", "-a",
        "C:/Users/g_np2/Documents/GO CFD Cases/cube",
    ]
    assert runner._commands("blockMesh", ())[0:2] == ["wsl.exe", "--exec"]
