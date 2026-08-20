#!/usr/bin/env python3
"""Run the one authorized CBC optimization and export v21 results."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import types
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--muiogo", type=Path, required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--run", default="POWER_ALLOCATION_V21_BASE")
    parser.add_argument("--timeout", type=int, default=1000)
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()
    muiogo = args.muiogo.resolve()
    case = muiogo / "WebAPP" / "DataStorage" / args.case
    run = case / "res" / args.run
    lp, results = run / "lp.lp", run / "results.txt"
    if not lp.is_file() or results.exists():
        raise AssertionError({"lp_exists": lp.is_file(), "results_exists": results.exists()})

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *unused_args, **unused_kwargs: None
    sys.modules.setdefault("dotenv", dotenv_stub)
    sys.path.insert(0, str(muiogo / "API"))
    from Classes.Case.DataFileClass import DataFile
    from Classes.Case.OsemosysClass import Osemosys
    model = DataFile(args.case)
    cbc = Osemosys._find_solver_binary(model.cbcFolder.resolve(), "cbc", recursive=False)
    if cbc is None:
        raise RuntimeError("CBC unavailable")

    started_total = time.monotonic()
    started = time.monotonic()
    command = [str(cbc), str(lp), "solve", "-printing", "all", "-solu", str(results)]
    try:
        solved = subprocess.run(
            command,
            cwd=model.cbcFolder.resolve() if model.cbc_is_bundled else None,
            capture_output=True, text=True, timeout=args.timeout,
        )
    except subprocess.TimeoutExpired as error:
        solve_seconds = time.monotonic() - started
        stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else (error.stdout or "")
        stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else (error.stderr or "")
        (run / "cbc.log").write_text(stdout + "\n" + stderr, encoding="utf-8")
        record = {
            "optimizer_runs": 1, "status": "timed_out", "timeout_seconds": args.timeout,
            "case": str(case), "run": str(run), "timings_seconds": {"cbc_solve": solve_seconds},
            "purpose": "Validate the corrected v21 off-grid replacement and power-allocation candidate",
            "sensitivity_runs": 0, "artifacts": {"lp": str(lp), "cbc_log": str(run / "cbc.log")},
        }
        args.record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(record, indent=2))
        raise SystemExit(124)
    solve_seconds = time.monotonic() - started
    (run / "cbc.log").write_text(solved.stdout + "\n" + solved.stderr, encoding="utf-8")
    if solved.returncode != 0 or not results.is_file():
        raise RuntimeError((solved.stdout + solved.stderr)[-12000:])
    status = results.read_text(encoding="utf-8").splitlines()[0]
    if not status.startswith("Optimal"):
        raise RuntimeError(status)
    started = time.monotonic()
    model.generateCSVfromCBC(run / "data.txt", results, run)
    csv_seconds = time.monotonic() - started
    started = time.monotonic()
    model.generateResultsViewer(args.run)
    viewer_seconds = time.monotonic() - started
    record = {
        "optimizer_runs": 1,
        "purpose": "Validate the one combined v21 off-grid, crop-residue biomass, and hydro-envelope candidate",
        "why_deterministic_checks_were_insufficient": "The technology allocation and coupled perfect-foresight response require optimization",
        "additional_optimizer_runs": 0, "sensitivity_runs": 0,
        "status": status, "case": str(case), "run": str(run),
        "timings_seconds": {"cbc_solve": solve_seconds, "csv_export": csv_seconds,
                            "viewer_export": viewer_seconds, "total": time.monotonic() - started_total},
        "artifacts": {"lp": str(lp), "results": str(results), "cbc_log": str(run / "cbc.log"),
                      "csv": str(run / "csv")},
    }
    args.record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
