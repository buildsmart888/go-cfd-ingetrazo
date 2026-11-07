"""Run external OpenFOAM with actionable Windows/WSL environment checks.

No automatic system installs, no subprocess shell=True, no Qt/scene access
from workers. Completed solver != validated CFD/design wind loads.
"""
from __future__ import annotations

from pathlib import Path
from threading import Event
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from typing import Callable

# OpenFOAM etc/bashrc may read/supply shell positional arguments as files.
# Sourcing with $1 still set to the bashrc path can re-source itself until
# bash crashes with SIGSEGV/exit 139. Copy the solver argv and CLEAR "$@"
# before sourcing. Keep arguments as a Bash array; no shell=True or eval.
_SOURCE_AND_EXEC = (
    'foamrc=$1; shift; go_cfd_argv=("$@"); set --; '
    '. "$foamrc"; exec "${go_cfd_argv[@]}"'
)
_SOURCE_AND_PROBE = (
    'foamrc=$1; set --; . "$foamrc" >/dev/null 2>&1; '
    'for tool in blockMesh snappyHexMesh checkMesh simpleFoam; do '
    'command -v "$tool" >/dev/null 2>&1 || exit 127; '
    'done; command -v blockMesh'
)

STAGES = (
    ("blockMesh", ()),
    ("snappyHexMesh", ("-overwrite",)),
    ("checkMesh", ()),
    ("simpleFoam", ()),
)


def _is_windows() -> bool:
    return sys.platform == "win32"


def _windows_path_to_wsl_argument(path: str) -> str:
    """Pass native drive paths to wslpath without shell-escaping backslashes.

    wsl.exe --exec skips the default Linux shell. Forward-slash Windows paths
    also prevent accidental Bash backslash consumption on WSL variants.
    The actual WSL mount root is resolved by wslpath, not hard-coded here.
    """
    value = str(path)
    if value.startswith(("\\\\", "//")):
        raise ValueError("Network/UNC case folders are not supported. Use C:/ or D:/.")
    if _is_windows() and not re.match(r"^[A-Za-z]:[\\/]", value):
        raise ValueError("CFD case folder must be an absolute Windows drive path.")
    return value.replace("\\", "/")


class RunCancelled(Exception):
    pass


class SolverRunner:
    def __init__(self, case_dir: Path, *, backend: str = "native", foam_bashrc: str = ""):
        self.case_dir = Path(case_dir).resolve()
        self.backend = backend
        self.foam_bashrc = foam_bashrc.strip()
        self.cancel_event = Event()
        self.process = None
        self._wsl_case = None
        self._resolved_bashrc = self.foam_bashrc

    def cancel(self):
        self.cancel_event.set()
        process = self.process
        if process is not None and process.poll() is None:
            self._stop(process)

    def _stop(self, process):
        if not _is_windows():
            try:
                os.killpg(process.pid, signal.SIGTERM)
                return
            except ProcessLookupError:
                return
        process.terminate()

    @staticmethod
    def _capture(argv: list[str], *, timeout: int = 25):
        try:
            return subprocess.run(argv, capture_output=True, text=True,
                                  errors="replace", timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "WSL/OpenFOAM environment check timed out. Open Ubuntu once, "
                "then run 'wsl --status' and 'wsl -l -v' in PowerShell."
            ) from exc
        except OSError as exc:
            raise RuntimeError(f"Could not start environment check: {exc}") from exc

    def preflight(self) -> str:
        """Check actual runtime before Stage 1; never claim a solver ran."""
        if self.backend == "native":
            if not self.foam_bashrc and not shutil.which("blockMesh"):
                hint = (" On Windows select 'Windows WSL2' after installing "
                        "WSL Ubuntu and OpenFOAM." if _is_windows() else "")
                raise FileNotFoundError(
                    "blockMesh not on PATH; configure OpenFOAM environment." + hint)
            if self.foam_bashrc and not shutil.which("bash"):
                raise FileNotFoundError("bash not on PATH; use Windows WSL2 or a Linux host")
            if not self.foam_bashrc:
                missing = [name for name, _ in STAGES if not shutil.which(name)]
                if missing:
                    raise FileNotFoundError(
                        f"OpenFOAM programs missing on PATH: {', '.join(missing)}")
            return "Native backend selected; OpenFOAM command availability checked."

        if self.backend != "wsl":
            raise ValueError("backend must be native or wsl")
        if not _is_windows():
            raise RuntimeError("WSL2 backend requires Windows")
        if not shutil.which("wsl.exe"):
            raise FileNotFoundError(
                "WSL executable missing. Open PowerShell as Administrator, "
                "run 'wsl --list --online', then install a listed Ubuntu distribution.")

        # Check Ubuntu startup BEFORE attempting wslpath so 4294967295
        # becomes a useful diagnostic rather than an opaque CalledProcessError.
        boot = self._capture(["wsl.exe", "--exec", "bash", "-lc",
                              'printf "GO_CFD_WSL_READY"'])
        if boot.returncode or "GO_CFD_WSL_READY" not in boot.stdout:
            detail = (boot.stderr or boot.stdout or "").strip()[-320:]
            raise RuntimeError(
                f"WSL could not launch Ubuntu (exit {boot.returncode}). "
                "In PowerShell run: wsl --status; wsl --list --verbose. "
                "If no Ubuntu WSL2 distro is installed, use an Administrator "
                "PowerShell: wsl --list --online, install a listed Ubuntu, "
                "then launch it once to create a Linux account. "
                f"Details: {detail}")

        # Windows backslashes were stripped by the default WSL shell on some
        # machines (C:\Users\... became C:Users...). --exec and forward
        # slashes bypass shell interpretation and let wslpath detect mounts.
        convert = self._capture(["wsl.exe", "--exec", "wslpath", "-u", "-a",
                                 _windows_path_to_wsl_argument(str(self.case_dir))])
        linux_case = convert.stdout.strip()
        if convert.returncode or not linux_case.startswith("/"):
            raise RuntimeError(
                "WSL started but could not translate the Windows case folder. "
                "Use an existing local drive-backed case folder (e.g. C:/Users/.../Documents/GO_CFD_Cases). "
                + (convert.stderr or convert.stdout or "")[-250:])
        self._wsl_case = linux_case

        if self.foam_bashrc:
            # User-specified absolute Linux bashrc, never interpolated into shell.
            if not self.foam_bashrc.startswith("/"):
                raise ValueError("OpenFOAM bashrc must be an absolute Linux path")
            probe = self._capture([
                "wsl.exe", "--exec", "bash", "-lc",
                _SOURCE_AND_PROBE, "bash", self.foam_bashrc])
            if probe.returncode:
                raise RuntimeError(
                    "Ubuntu starts, but OpenFOAM blockMesh was not found using "
                    f"bashrc {self.foam_bashrc!r}. Check that file inside Ubuntu "
                    "or install OpenFOAM matching this case's solver version.")
            self._resolved_bashrc = self.foam_bashrc
        else:
            # Check PATH first; auto-source common WSL package locations.
            shell_probe = r'''all_tools() {
  for tool in blockMesh snappyHexMesh checkMesh simpleFoam; do
    command -v "$tool" >/dev/null 2>&1 || return 1
  done
}
if all_tools; then
  printf 'PATH:%s' "$(command -v blockMesh)"; exit 0
fi
for f in /opt/openfoam*/etc/bashrc /usr/lib/openfoam/*/etc/bashrc; do
  if [ -f "$f" ]; then
    set --
    . "$f" >/dev/null 2>&1
    if all_tools; then
      printf 'BASHRC:%s' "$f"; exit 0
    fi
  fi
done
exit 127'''
            probe = self._capture(["wsl.exe", "--exec", "bash", "-lc", shell_probe])
            if probe.returncode:
                raise FileNotFoundError(
                    "WSL Ubuntu is working but OpenFOAM 'blockMesh' was not "
                    "found. Install OpenFOAM inside Ubuntu (not just on Windows), "
                    "or enter its Linux bashrc path such as "
                    "/opt/openfoam2606/etc/bashrc. Open Ubuntu and check: "
                    "command -v blockMesh")
            text = probe.stdout.strip()
            self._resolved_bashrc = text.split("BASHRC:", 1)[-1] if "BASHRC:" in text else ""
        return (f"WSL2 Ubuntu reachable; OpenFOAM blockMesh located. "
                f"Case: {linux_case}. "
                f"Bashrc: {self._resolved_bashrc or 'environment PATH'}")

    def _commands(self, program: str, extra: tuple[str, ...]) -> list[str]:
        if self.backend == "native":
            if self.foam_bashrc:
                return ["bash", "-lc", _SOURCE_AND_EXEC, "bash",
                        self.foam_bashrc, program, "-case", str(self.case_dir), *extra]
            if not shutil.which(program):
                raise FileNotFoundError(f"{program} not on PATH; configure OpenFOAM environment")
            return [program, "-case", str(self.case_dir), *extra]
        if self.backend == "wsl":
            if not self._wsl_case:
                self.preflight()
            if self._resolved_bashrc:
                return ["wsl.exe", "--exec", "bash", "-lc", _SOURCE_AND_EXEC,
                        "bash", self._resolved_bashrc, program, "-case", self._wsl_case, *extra]
            return ["wsl.exe", "--exec", "bash", "-lc", 'exec "$@"',
                    "bash", program, "-case", self._wsl_case, *extra]
        raise ValueError("backend must be native or wsl")

    def _status(self, status: str, *, reason: str | None = None):
        manifest = self.case_dir / "go_cfd_manifest.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["status"] = status
        data["validation"] = "NOT_TESTED"
        if reason:
            data["run_message"] = reason
        tmp = manifest.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(manifest)

    def run(self, on_log: Callable[[str], None] | None = None,
            on_stage: Callable[[str, int, int], None] | None = None):
        """Run solver stages, or raise. 'Completed' is NOT 'validated'."""
        if not (self.case_dir / "go_cfd_manifest.json").exists():
            raise FileNotFoundError("Not a generated GO CFD case")
        logs = self.case_dir / "solver_logs"
        logs.mkdir(exist_ok=True)
        self._status("RUNNING")
        try:
            check = self.preflight()
            if on_log:
                on_log("ENVIRONMENT: " + check)
            for number, (program, args) in enumerate(STAGES, start=1):
                if self.cancel_event.is_set():
                    raise RunCancelled("Cancelled before " + program)
                if on_stage:
                    on_stage(program, number, len(STAGES))
                cmd = self._commands(program, args)
                with (logs / f"{number:02d}_{program}.log").open("w", encoding="utf-8") as log:
                    log.write("# Stage: " + program + "\n")
                    log.flush()
                    self.process = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, errors="replace", bufsize=1,
                        start_new_session=(not _is_windows()),
                    )
                    assert self.process.stdout is not None
                    for line in self.process.stdout:
                        log.write(line)
                        if on_log:
                            on_log(line.rstrip())
                        if self.cancel_event.is_set():
                            self._stop(self.process)
                            raise RunCancelled("Cancelled during " + program)
                    code = self.process.wait()
                    self.process = None
                    if code != 0:
                        if code in (139, -11):
                            raise RuntimeError(
                                f"{program} crashed (SIGSEGV / exit 139). "
                                f"See {logs / f'{number:02d}_{program}.log'}; "
                                "OpenFOAM startup or its native libraries failed. "
                                "Verify blockMesh -help inside Ubuntu."
                            )
                        raise RuntimeError(f"{program} exited with code {code}; inspect solver_logs")
            self._status("SOLVER_COMPLETED_UNVERIFIED", reason="Mesh and convergence QA not completed")
            return "SOLVER_COMPLETED_UNVERIFIED"
        except RunCancelled as exc:
            self._status("CANCELLED", reason=str(exc))
            raise
        except Exception as exc:
            self._status("FAILED", reason=str(exc))
            raise
        finally:
            self.process = None
