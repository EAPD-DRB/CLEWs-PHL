#!/usr/bin/env python3
"""Create, generate, and solve a MUIO case run with CBC."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case")
    parser.add_argument("run")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument(
        "--activate-all",
        action="store_true",
        help="Activate the complete inherited scenario stack (the v10 PEP run).",
    )
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help="Regenerate and solve an existing run without changing its scenario stack.",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo / "API"))

    from Classes.Case.DataFileClass import DataFile

    data_file = DataFile(args.case)
    scenarios = []
    for item in data_file.genData["osy-scenarios"]:
        scenarios.append(
            {
                "ScenarioId": item["ScenarioId"],
                "Scenario": item["Scenario"],
                "Desc": item.get("Desc", ""),
                "Active": args.activate_all or item["ScenarioId"] == "SC_0",
            }
        )
    run_data = {
        "Case": args.run,
        "CaseId": args.case_id,
        "Desc": args.description,
        "Runtime": date.today().isoformat(),
        "Scenarios": scenarios,
    }
    if args.reuse_existing:
        run_path = repo / f"WebAPP/DataStorage/{args.case}/res/{args.run}"
        if not run_path.is_dir():
            raise RuntimeError(f"Existing run not found: {run_path}")
    else:
        created = data_file.createCaseRun(args.run, run_data)
        if created.get("status_code") != "success":
            raise RuntimeError(json.dumps(created, indent=2))
    data_file.generateDatafile(args.run)
    result = data_file.run("cbc", args.run)
    print(
        json.dumps(
            {
                "case": args.case,
                "run": args.run,
                "status": result.get("status_code"),
                "timer": result.get("timer"),
                "cbc": result.get("cbc_message", "")[-2000:],
                "glpk": result.get("glpk_message", "")[-2000:],
            },
            indent=2,
        )
    )
    if result.get("status_code") != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
