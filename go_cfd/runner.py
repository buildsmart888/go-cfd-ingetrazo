"""Execute an external OpenFOAM installation with logs, cancellation and state.

No subprocess shell=True and no Qt/scene access from worker threads.
"""
from __future__ import annotations

from pathlib import Path
from threading import Event
import json
import os
import shutil
import signal
import subprocess
import sys
from typing import Callable

STAGES = (
    ("blockMesh", ()),
    ("snappyHexMesh", ("-overwrite",)),
    ("checkMesh", ()),
    ("simpleFoam", ()),
)


class RunCancelled(Exception):
    pass


class SolverRunner:
    def __init__(self, case_dir: Path, *, backend: str = "native", foam_bashrc: str = ""):
        self.case_dir = Path(case_dir).resolve()
        self.backend = backend
        self.foam_bashrc = foam_bashrc.strip()
        self.cancel_event = Event()
        self.process = None

    def cancel(self):
        self.cancel_event.set()
        process = self.process
        if process is not None and process.poll() is None:
            self._stop(process)

    def _stop(self, process):
        if sys.platform != "win32":
            try:
                os.killpg(process.pid, signal.SIGTERM)
                return
            except ProcessLookupError:
                return
        process.terminate()

    def _commands(self, program: str, extra: tuple[str, ...]) -> list[str]:
        if self.backend == "native":
            if self.foam_bashrc:
                return ["bash", "-lc", '. "$1"; shift; exec "$@"', "bash",
                        self.foam_bashrc, program, "-case", str(self.case_dir), *extra]
            if not shutil.which(program):
                raise FileNotFoundError(f"{program} not on PATH; configure OpenFOAM environment")
            return [program, "-case", str(self.case_dir), *extra]
        if self.backend == "wsl":
            if os.name != "nt":
                raise RuntimeError("WSL backend requires Windows")
            if not shutil.which("wsl.exe"):
                raise FileNotFoundError("wsl.exe unavailable")
            result = subprocess.run(["wsl.exe", "--", "wslpath", "-a", str(self.case_dir)],
                                    check=True, capture_output=True, text=True, timeout=15)
            linux_case = result.stdout.strip()
            if not linux_case.startswith("/"):
                raise RuntimeError("Failed to convert Windows case directory to WSL path")
            if self.foam_bashrc:
                return ["wsl.exe", "--", "bash", "-lc", '. "$1"; shift; exec "$@"',
                        "bash", self.foam_bashrc, program, "-case", linux_case, *extra]
            return ["wsl.exe", "--", "bash", "-lc", 'exec "$@"',
                    "bash", program, "-case", linux_case, *extra]
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
        """Run to end, or raise. A completed solver is NOT a validated solution."""
        if not (self.case_dir / "go_cfd_manifest.json").exists():
            raise FileNotFoundError("Not a generated GO CFD case")
        logs = self.case_dir / "solver_logs"
        logs.mkdir(exist_ok=True)
        self._status("RUNNING")
        try:
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
                        start_new_session=(sys.platform != "win32"),
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