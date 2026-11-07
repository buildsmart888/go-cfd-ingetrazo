"""Traceable CFD wind scenario and domain settings (stdlib only)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from .geometry import Patch, bounds
from .constants import VERSION, TARGET_OPENFOAM, TEMPLATE_VERSION
from .loads import reference_pressure_pa


@dataclass(frozen=True)
class WindConfig:
    speed_ms: float
    direction_to_deg: float = 0.0
    density_kgm3: float = 1.225
    reference_height_m: float = 10.0
    turbulence_intensity: float = 0.10
    viscosity_m2s: float = 1.5e-5
    ground_z_m: float = 0.0
    background_cell_m: float | None = None
    iterations: int = 500
    # This first milestone uses UNIFORM inlet, not a validated ABL.
    profile: str = "uniform_preliminary"

    def validate(self) -> None:
        for label, value in asdict(self).items():
            if value is not None and isinstance(value, (int, float)) and not math.isfinite(value):
                raise ValueError(f"{label} must be finite")
        reference_pressure_pa(self.density_kgm3, self.speed_ms)
        if not 0 <= self.direction_to_deg < 360:
            raise ValueError("direction_to_deg must be between 0 and 360")
        if not 0 < self.turbulence_intensity < 1:
            raise ValueError("turbulence_intensity must be within (0,1)")
        if not self.viscosity_m2s > 0:
            raise ValueError("Viscosity must be positive")
        if not self.reference_height_m > 0:
            raise ValueError("Reference height must be positive")
        if self.background_cell_m is not None and not self.background_cell_m > 0:
            raise ValueError("Background cell size must be positive")
        if not isinstance(self.iterations, int) or self.iterations < 50:
            raise ValueError("Iterations must be an integer >= 50")
        if self.profile != "uniform_preliminary":
            raise ValueError("Only preliminary uniform inflow is implemented in v0.1")


@dataclass(frozen=True)
class Domain:
    minimum: tuple[float, float, float]
    maximum: tuple[float, float, float]
    cells: tuple[int, int, int]
    location_in_mesh: tuple[float, float, float]
    scale_H_m: float


def make_domain(patches: tuple[Patch, ...], cfg: WindConfig) -> Domain:
    """Initial wind-tunnel proportions (NOT validated for every object)."""
    cfg.validate()
    mn, mx = bounds(patches)
    if mn[2] < cfg.ground_z_m - 1e-6:
        raise ValueError("Model extends below configured ground z")
    H = max(mx[2] - cfg.ground_z_m, mx[2] - mn[2], 0.1)
    minp = (mn[0] - 5*H, mn[1] - 5*H, cfg.ground_z_m)
    maxp = (mx[0] + 15*H, mx[1] + 5*H, mx[2] + 5*H)
    h = cfg.background_cell_m if cfg.background_cell_m is not None else H/2.5
    cells = tuple(max(4, math.ceil((maxp[i] - minp[i]) / h)) for i in range(3))
    cells_total = cells[0] * cells[1] * cells[2]
    if cells_total > 2_000_000:
        raise ValueError("Background mesh >2M cells; increase cell size")
    keep = (mn[0] - 2.5*H, mn[1] - 2.0*H, cfg.ground_z_m + 0.5*H)
    return Domain(minp, maxp, cells, keep, H)


def case_fingerprint(cfg: WindConfig, source_geometry_hash: str) -> str:
    payload = json.dumps({"wind": asdict(cfg), "source_geometry_hash": source_geometry_hash,
                          "code_version": VERSION, "solver_target": TARGET_OPENFOAM,
                          "template_version": TEMPLATE_VERSION},
                         sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def is_stale(manifest: dict, cfg: WindConfig, source_geometry_hash: str) -> bool:
    return manifest.get("case_fingerprint") != case_fingerprint(cfg, source_geometry_hash)