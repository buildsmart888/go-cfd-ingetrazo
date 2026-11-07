"""Regression checks for OpenFOAM bashrc sourced with stale positional args.

The bug reproduced by some v2606 shells caused recursive re-sourcing,
ending in SIGSEGV (139) instead of running blockMesh. Tests use a harmless
fake bashrc: no OpenFOAM or WSL is required.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest

from go_cfd.runner import SolverRunner, _SOURCE_AND_EXEC, _SOURCE_AND_PROBE


@pytest.mark.skipif(shutil.which("bash") is None, reason="Bash not installed")
def test_source_bashrc_sees_zero_parameters_and_executes_original_argv(tmp_path: Path):
    """The source file must NOT see its own filename in $1."""
    count_log = tmp_path / "source-parameter-count.txt"
    foamrc = tmp_path / "etc bashrc"
    foamrc.write_text(
        'printf "%s" "$#" > "$GO_CFD_ARG_COUNT"\n'
        '[ "$#" -eq 0 ] || return 70\n'
        'export GO_CFD_ENV_VAR=READY\n', encoding="utf-8")
    tool = tmp_path / "fake blockMesh"
    tool.write_text(
        '#!/bin/sh\n'
        'printf "env=%s\\n" "$GO_CFD_ENV_VAR"\n'
        'printf "argc=%s\\n" "$#"\n'
        'printf "arg=%s\\n" "$@"\n', encoding="utf-8")
    tool.chmod(0o755)
    runner = SolverRunner(tmp_path, backend="native", foam_bashrc=str(foamrc))
    cmd = runner._commands(str(tool), ("hello world",))
    assert cmd[2] == _SOURCE_AND_EXEC
    env = os.environ.copy()
    env["GO_CFD_ARG_COUNT"] = str(count_log)
    completed = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)
    assert completed.returncode == 0, completed.stderr
    assert count_log.read_text(encoding="utf-8") == "0"
    assert "env=READY" in completed.stdout
    assert "argc=3" in completed.stdout
    assert f"arg={tmp_path}" in completed.stdout
    assert "arg=hello world" in completed.stdout


@pytest.mark.skipif(shutil.which("bash") is None, reason="Bash not installed")
def test_explicit_bashrc_preflight_clears_parameters(tmp_path: Path):
    foamrc = tmp_path / "foam-bashrc"
    foamrc.write_text('''[ "$#" -eq 0 ] || return 72
for tool in blockMesh snappyHexMesh checkMesh simpleFoam; do
  eval "$tool() { :; }"
done
''', encoding="utf-8")
    completed = subprocess.run(["bash", "-lc", _SOURCE_AND_PROBE, "bash", str(foamrc)],
                               capture_output=True, text=True, timeout=10)
    assert completed.returncode == 0, completed.stderr
    assert "blockMesh" in completed.stdout


def test_wsl_launcher_preserves_source_clear_and_case_args(tmp_path: Path):
    runner = SolverRunner(tmp_path, backend="wsl", foam_bashrc="/usr/lib/openfoam/openfoam2606/etc/bashrc")
    runner._wsl_case = "/mnt/c/GO_CFD_Cases/cube_1"
    cmd = runner._commands("blockMesh", ())
    assert cmd[:6] == ["wsl.exe", "--cd", "/", "--exec", "bash", "-lc"]
    assert cmd[6] == _SOURCE_AND_EXEC
    assert "set --" in cmd[6]
    assert cmd[-3:] == ["blockMesh", "-case", "/mnt/c/GO_CFD_Cases/cube_1"]
    assert cmd[8] == "/usr/lib/openfoam/openfoam2606/etc/bashrc"
