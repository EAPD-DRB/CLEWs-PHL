#!/usr/bin/env python3
"""Generate, solve and export the safeguarded Philippines v17 base case."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import types
from datetime import date
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
DEFAULT_MUIOGO = PACKAGE.parents[1] / "MUIOGO"
DEFAULT_CASE = "Philippines_v17"
DEFAULT_RUN = "LAND_SAFEGUARDS_CENTRAL_COMPLETE"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--muiogo", type=Path, default=DEFAULT_MUIOGO)
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--run", default=DEFAULT_RUN)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    muiogo = args.muiogo.resolve()
    storage = muiogo / "WebAPP" / "DataStorage"
    case = storage / args.case
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
            "CaseId": f"CS_{args.case}_{args.run}",
            "Desc": "Full-chain validation of Philippines v17 land-transition safeguards",
            "Runtime": date.today().isoformat(),
            "Scenarios": scenarios,
        },
    )
    if response.get("status_code") != "success":
        raise RuntimeError(json.dumps(response, indent=2))

    timings: dict[str, float] = {}
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
        [
            str(glpsol), "--check", "-m", str(model_file),
            "-d", str(run / "data_processed.txt"), "--wlp", str(run / "lp.lp"),
        ],
        cwd=model.glpkFolder.resolve() if model.glpsol_is_bundled else None,
        capture_output=True,
        text=True,
        timeout=120,
    )
    timings["glpsol_check_and_lp"] = time.monotonic() - started
    if checked.returncode != 0:
        raise RuntimeError((checked.stdout + "\n" + checked.stderr)[-12000:])

    started = time.monotonic()
    solved = subprocess.run(
        [str(cbc), str(run / "lp.lp"), "solve", "-printing", "all", "-solu", str(run / "results.txt")],
        cwd=model.cbcFolder.resolve() if model.cbc_is_bundled else None,
        capture_output=True,
        text=True,
        timeout=args.timeout,
    )
    timings["cbc_solve"] = time.monotonic() - started
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
    timings["total"] = sum(timings.values())
    print(json.dumps({"status": status, "case": str(case), "run": args.run, "timings_seconds": timings}, indent=2))


if __name__ == "__main__":
    main()
