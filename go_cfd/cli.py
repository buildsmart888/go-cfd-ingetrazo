"""Independent W1 smoke workflow: make cube case, run solver, inspect forces."""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from .case_model import WindConfig
from .case_builder import build_case
from .geometry import cube_patch
from .results import load_force_history
from .runner import SolverRunner


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="GO CFD preliminary OpenFOAM cube runner")
    cmd = parser.add_subparsers(dest="command", required=True)
    demo = cmd.add_parser("demo-cube", help="Build OpenFOAM cube case; never overwrites")
    demo.add_argument("case_directory", type=Path)
    demo.add_argument("--speed-ms", required=True, type=float)
    demo.add_argument("--side-m", type=float, default=1.0)
    demo.add_argument("--direction-to-deg", type=float, default=0.0)
    demo.add_argument("--cell-m", type=float)
    run = cmd.add_parser("run", help="Run OpenFOAM commands externally")
    run.add_argument("case_directory", type=Path)
    run.add_argument("--backend", choices=("native", "wsl"), default="native")
    run.add_argument("--foam-bashrc", default="")
    read = cmd.add_parser("forces", help="Print last forces per patch")
    read.add_argument("case_directory", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "demo-cube":
            cfg = WindConfig(speed_ms=args.speed_ms,
                             direction_to_deg=args.direction_to_deg,
                             background_cell_m=args.cell_m)
            result = build_case(args.case_directory, (cube_patch(args.side_m),), cfg)
            print(json.dumps({"case": str(args.case_directory),
                              "status": result["status"],
                              "q_ref_pa": result["q_ref_pa"],
                              "warning": "Not for structural design"}, indent=2))
        elif args.command == "run":
            runner = SolverRunner(args.case_directory, backend=args.backend,
                                  foam_bashrc=args.foam_bashrc)
            result = runner.run(on_log=lambda line: print(line, flush=True),
                                on_stage=lambda s,i,n: print(f"[{i}/{n}] {s}", flush=True))
            print(result)
        else:
            records = load_force_history(args.case_directory)
            print(json.dumps({name: {"last_force_N": data[-1].force_total_N,
                                     "last_moment_Nm": data[-1].moment_total_Nm,
                                     "samples": len(data)}
                              for name, data in records.items() if data}, indent=2))
        return 0
    except (FileNotFoundError, ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
