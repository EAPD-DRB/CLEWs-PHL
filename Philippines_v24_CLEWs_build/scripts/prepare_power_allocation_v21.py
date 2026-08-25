#!/usr/bin/env python3
"""Generate, preprocess, and matrix-check the disposable v21 candidate."""

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
    parser.add_argument("--run", default="POWER_ALLOCATION_V21_BASE")
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()
    muiogo = args.muiogo.resolve()
    case = muiogo / "WebAPP" / "DataStorage" / args.case
    run = case / "res" / args.run
    model_file = muiogo / "WebAPP" / "SOLVERs" / "model.v.5.4.txt"
    if run.exists():
        raise FileExistsError(run)

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *unused_args, **unused_kwargs: None
    sys.modules.setdefault("dotenv", dotenv_stub)
    sys.path.insert(0, str(muiogo / "API"))
    from Classes.Case.DataFileClass import DataFile
    from Classes.Case.OsemosysClass import Osemosys

    model = DataFile(args.case)
    scenarios = [{"ScenarioId": item["ScenarioId"], "Scenario": item["Scenario"],
                  "Desc": item.get("Desc", ""), "Active": item["Scenario"] == "BASE"}
                 for item in model.genData["osy-scenarios"]]
    response = model.createCaseRun(args.run, {
        "Case": args.run, "CaseId": f"CS_{args.run}",
        "Desc": "Single disposable validation optimization for Philippines v21 power allocation",
        "Runtime": date.today().isoformat(), "Scenarios": scenarios,
    })
    if response.get("status_code") != "success":
        raise RuntimeError(json.dumps(response, indent=2))

    timings = {}
    started = time.monotonic()
    model.generateDatafile(args.run)
    timings["generate_datafile"] = time.monotonic() - started
    started = time.monotonic()
    model.preprocessData(run / "data.txt", run / "data_processed.txt")
    timings["preprocess_data"] = time.monotonic() - started
    glpsol = Osemosys._find_solver_binary(model.glpkFolder.resolve(), "glpsol", recursive=False)
    cbc = Osemosys._find_solver_binary(model.cbcFolder.resolve(), "cbc", recursive=False)
    if glpsol is None or cbc is None:
        raise RuntimeError("GLPK or CBC unavailable")
    started = time.monotonic()
    checked = subprocess.run(
        [str(glpsol), "--check", "-m", str(model_file), "-d", str(run / "data_processed.txt"),
         "--wlp", str(run / "lp.lp")],
        cwd=model.glpkFolder.resolve() if model.glpsol_is_bundled else None,
        capture_output=True, text=True, timeout=300,
    )
    timings["glpsol_check_and_lp"] = time.monotonic() - started
    (run / "glpsol_check.log").write_text(checked.stdout + "\n" + checked.stderr, encoding="utf-8")
    if checked.returncode != 0:
        raise RuntimeError((checked.stdout + checked.stderr)[-12000:])
    record = {
        "optimizer_runs": 0, "status": "matrix_check_passed", "case": str(case), "run": str(run),
        "timings_seconds": timings, "cbc_binary": str(cbc),
        "artifacts": {"data": str(run / "data.txt"), "processed_data": str(run / "data_processed.txt"),
                      "lp": str(run / "lp.lp"), "glpsol_log": str(run / "glpsol_check.log")},
    }
    args.record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
