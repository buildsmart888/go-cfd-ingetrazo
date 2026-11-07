"""Read OpenFOAM force function-object files; no design certification."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import math

_FLOAT = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


@dataclass(frozen=True)
class ForcePoint:
    time: float
    force_pressure_N: tuple[float, float, float]
    force_viscous_N: tuple[float, float, float]
    moment_pressure_Nm: tuple[float, float, float]
    moment_viscous_Nm: tuple[float, float, float]

    @property
    def force_total_N(self):
        return tuple(a+b for a,b in zip(self.force_pressure_N, self.force_viscous_N))

    @property
    def moment_total_Nm(self):
        return tuple(a+b for a,b in zip(self.moment_pressure_Nm, self.moment_viscous_Nm))


def parse_force_line(line: str) -> ForcePoint | None:
    """Expect OpenFOAM 'time (Fp Fv Fpor) (Mp Mv Mpor)' layout."""
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    nums = [float(x) for x in _FLOAT.findall(s)]
    if len(nums) != 19 or not all(map(math.isfinite, nums)):
        raise ValueError(f"Unsupported forces.dat row ({len(nums)} fields): {s[:120]}")
    return ForcePoint(nums[0], tuple(nums[1:4]), tuple(nums[4:7]),
                      tuple(nums[10:13]), tuple(nums[13:16]))


def load_force_history(case_dir: Path) -> dict[str, list[ForcePoint]]:
    """Read latest time folder per named patch. Force values are physical N/Nm."""
    root = Path(case_dir) / "postProcessing"
    history = {}
    if not root.exists():
        return history
    for func_dir in sorted(root.glob("forces_*/")):
        matches = list(func_dir.glob("*/forces.dat"))
        if not matches:
            continue
        datafile = max(matches, key=lambda p: float(p.parent.name) if _isfloat(p.parent.name) else -1)
        history[func_dir.name[len("forces_"):]] = [
            point for line in datafile.read_text(encoding="utf-8", errors="replace").splitlines()
            if (point := parse_force_line(line)) is not None]
    return history


def _isfloat(s: str) -> bool:
    try:
        return math.isfinite(float(s))
    except (ValueError, TypeError):
        return False