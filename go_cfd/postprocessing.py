"""Export authentic OpenFOAM fields for VTK visualization (no Qt dependency).

The exporter never creates synthetic results and never sets design-validation flags.
One steady simpleFoam time is exported, NOT an unsteady animation sequence.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from datetime import datetime, timezone
import json
import subprocess

from .runner import SolverRunner, _is_windows


@dataclass(frozen=True)
class ExportResult:
    case_dir: Path
    volume_file: Path
    boundary_files: tuple[Path, ...]
    time_label: str


def _time_from_name(name: str) -> float:
    import re
    match = re.search(r"_([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)$", name)
    if not match:
        return -1.0
    try:
        return float(match.group(1))
    except ValueError:
        return -1.0


def _within(path: Path, root: Path) -> bool:
    return path.is_relative_to(root)


def find_latest_vtk(case_dir: Path) -> ExportResult:
    """Discover foamToVTK XML output; prefer latest simulation time, not mtime.

    OpenFOAM v2606 typically writes VTK/<case>_<time>/internal.vtu and
    VTK/<case>_<time>/boundary/<patch>.vtp, plus a top-level .vtm index.
    """
    case = Path(case_dir).resolve()
    if not (case / "go_cfd_manifest.json").is_file():
        raise FileNotFoundError("Not a GO CFD case; go_cfd_manifest.json missing")
    vtk_root = (case / "VTK").resolve()
    if not vtk_root.is_dir() or not _within(vtk_root, case):
        raise FileNotFoundError("No real VTK results. Run OpenFOAM, then Export CFD fields (foamToVTK).")
    candidates = [p for p in vtk_root.rglob("internal.vtu") if p.is_file() and _within(p.resolve(), vtk_root)]
    # Legacy and occasional direct-export datasets are also accepted.
    if not candidates:
        candidates = [p for p in vtk_root.glob("*.vtu") if p.is_file() and _within(p.resolve(), vtk_root)]
    if not candidates:
        raise FileNotFoundError("OpenFOAM VTK internal.vtu is missing. Check 05_foamToVTK.log.")
    # A file written by a later export does not imply a later CFD time.
    volume = max(candidates, key=lambda p: (_time_from_name(p.parent.name), p.stat().st_mtime_ns, str(p)))
    parent = volume.parent
    boundary_dir = parent / "boundary"
    boundaries = tuple(sorted(p for p in boundary_dir.glob("*.vtp")
                              if p.is_file() and _within(p.resolve(), vtk_root))) if boundary_dir.is_dir() else ()
    label = parent.name
    return ExportResult(case, volume, boundaries, label)


def _write_json_atomic(path: Path, obj: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def export_case_vtk(case_dir: Path, runner: SolverRunner, *,
                    on_log: Callable[[str], None] | None = None) -> ExportResult:
    """Run real foamToVTK on a completed, preliminary solver case.

    In particular, a generated case or a FAILED solver is not exported as a
    fictional computed field. It is intentionally never marked validated.
    """
    case = Path(case_dir).resolve()
    manifest_path = case / "go_cfd_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("Build a GO CFD case before post-processing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "SOLVER_COMPLETED_UNVERIFIED":
        raise RuntimeError(
            "CFD field export requires all four solver stages to complete. "
            f"Current state: {manifest.get('status', 'UNKNOWN')}."
        )
    if case != runner.case_dir:
        raise ValueError("Post-processing runner must reference the same case directory")
    logs = case / "solver_logs"
    logs.mkdir(exist_ok=True)
    info = runner.preflight()
    if on_log:
        on_log("ENVIRONMENT: " + info)
    command = runner._commands("foamToVTK", ("-latestTime", "-fields", "(U p)"))
    logpath = logs / "05_foamToVTK.log"
    with logpath.open("w", encoding="utf-8") as log:
        log.write("# foamToVTK -latestTime -fields '(U p)'\n")
        log.flush()
        proc = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", bufsize=1,
            cwd=str(case), start_new_session=(not _is_windows()),
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            log.write(line)
            if on_log:
                on_log(line.rstrip())
        exit_code = proc.wait()
    if exit_code:
        raise RuntimeError(f"foamToVTK exited with code {exit_code}; inspect {logpath}")
    result = find_latest_vtk(case)
    _write_json_atomic(case / "go_cfd_vtk_export.json", {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_case_fingerprint": manifest.get("case_fingerprint"),
        "source_solver_state": manifest["status"],
        "validation": "NOT_TESTED",
        "design_use": False,
        "volume_file": str(result.volume_file.relative_to(case)),
        "boundary_files": [str(p.relative_to(case)) for p in result.boundary_files],
        "time_label": result.time_label,
        "steady_state": True,
        "note": "Unverified steady RANS field; not an unsteady/gust simulation or design load.",
    })
    return result
