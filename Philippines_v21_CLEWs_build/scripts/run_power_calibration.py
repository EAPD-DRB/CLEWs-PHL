#!/usr/bin/env python3
"""Generate, matrix-check, solve, and export the disposable v20 power candidate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import types
from datetime import date
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--muiogo", type=Path, required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--run", default="POWER_CALIBRATION_V20_BASE")
    parser.add_argument("--timeout", type=int, default=1000)
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()

    muiogo = args.muiogo.resolve()
    case = muiogo / "WebAPP" / "DataStorage" / args.case
    run = case / "res" / args.run
    model_file = muiogo / "WebAPP" / "SOLVERs" / "model.v.5.4.txt"
    if not case.is_dir():
        raise FileNotFoundError(case)
    if run.exists():
        raise FileExistsError(f"refusing to replace existing run: {run}")

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *unused_args, **unused_kwargs: None
    sys.modules.setdefault("dotenv", dotenv_stub)
    sys.path.insert(0, str(muiogo / "API"))
    from Classes.Case.DataFileClass import DataFile
    from Classes.Case.OsemosysClass import Osemosys

    model = DataFile(args.case)
    scenarios = [
        {
            "ScenarioId": item["ScenarioId"],
            "Scenario": item["Scenario"],
            "Desc": item.get("Desc", ""),
            "Active": item["Scenario"] == "BASE",
        }
        for item in model.genData["osy-scenarios"]
    ]
    response = model.createCaseRun(
        args.run,
        {
            "Case": args.run,
            "CaseId": f"CS_{args.run}",
            "Desc": "Single disposable validation optimization for Philippines v20 power calibration",
            "Runtime": date.today().isoformat(),
            "Scenarios": scenarios,
        },
    )
    if response.get("status_code") != "success":
        raise RuntimeError(json.dumps(response, indent=2))

    timings: dict[str, float] = {}
    started_total = time.monotonic()
    started = time.monotonic()
    model.generateDatafile(args.run)
    timings["generate_datafile"] = time.monotonic() - started
    started = time.monotonic()
    model.preprocessData(run / "data.txt", run / "data_processed.txt")
    timings["preprocess_data"] = time.monotonic() - started

    glpsol = Osemosys._find_solver_binary(model.glpkFolder.resolve(), "glpsol", recursive=False)
    cbc = Osemosys._find_solver_binary(model.cbcFolder.resolve(), "cbc", recursive=False)
    if glpsol is None or cbc is None:
        raise RuntimeError("GLPK or CBC solver is unavailable")
    model.deleteCaseResultsJSON(args.run)

    started = time.monotonic()
    checked = subprocess.run(
        [str(glpsol), "--check", "-m", str(model_file), "-d", str(run / "data_processed.txt"),
         "--wlp", str(run / "lp.lp")],
        cwd=model.glpkFolder.resolve() if model.glpsol_is_bundled else None,
        capture_output=True, text=True, timeout=240,
    )
    timings["glpsol_check_and_lp"] = time.monotonic() - started
    (run / "glpsol_check.log").write_text(checked.stdout + "\n" + checked.stderr, encoding="utf-8")
    if checked.returncode != 0:
        raise RuntimeError((checked.stdout + "\n" + checked.stderr)[-12000:])

    started = time.monotonic()
    solved = subprocess.run(
        [str(cbc), str(run / "lp.lp"), "solve", "-printing", "all", "-solu", str(run / "results.txt")],
        cwd=model.cbcFolder.resolve() if model.cbc_is_bundled else None,
        capture_output=True, text=True, timeout=args.timeout,
    )
    timings["cbc_solve"] = time.monotonic() - started
    (run / "cbc.log").write_text(solved.stdout + "\n" + solved.stderr, encoding="utf-8")
    if solved.returncode != 0 or not (run / "results.txt").is_file():
        raise RuntimeError((solved.stdout + "\n" + solved.stderr)[-12000:])
    status = (run / "results.txt").read_text(encoding="utf-8").splitlines()[0]
    if not status.startswith("Optimal"):
        raise RuntimeError(status)

    started = time.monotonic()
    model.generateCSVfromCBC(run / "data.txt", run / "results.txt", run)
    timings["csv_export"] = time.monotonic() - started
    started = time.monotonic()
    model.generateResultsViewer(args.run)
    timings["viewer_export"] = time.monotonic() - started
    timings["total"] = time.monotonic() - started_total

    record = {
        "optimizer_runs": 1,
        "purpose": "Validate the one combined dependable-capacity and Malampaya take-or-pay candidate",
        "why_deterministic_checks_were_insufficient": "Dispatch and coupled perfect-foresight effects require optimization",
        "sensitivity_runs": 0,
        "status": status,
        "case": str(case),
        "run": str(run),
        "timings_seconds": timings,
        "artifacts": {
            "data": str(run / "data.txt"),
            "processed_data": str(run / "data_processed.txt"),
            "lp": str(run / "lp.lp"),
            "results": str(run / "results.txt"),
            "cbc_log": str(run / "cbc.log"),
            "csv": str(run / "csv"),
        },
    }
    args.record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
