#!/usr/bin/env python3
"""Verify source and generated-model identity after Philippines v20 promotion."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import types
from datetime import date
from pathlib import Path


SOURCE_FILES = [
    "R.json", "RE.json", "RS.json", "RT.json", "RTSM.json", "RYC.json", "RYCTs.json",
    "RYCn.json", "RYDtb.json", "RYE.json", "RYS.json", "RYSeDt.json", "RYT.json",
    "RYTC.json", "RYTCM.json", "RYTCn.json", "RYTEM.json", "RYTM.json", "RYTTs.json",
    "RYTs.json", "genData.json",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--muiogo", type=Path, required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--live", required=True)
    parser.add_argument("--candidate-run", required=True)
    parser.add_argument("--live-run", default="POWER_CALIBRATION_V20_PROMOTION_CHECK")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.muiogo.resolve()
    storage = repo / "WebAPP" / "DataStorage"
    candidate, live = storage / args.candidate, storage / args.live
    for name in SOURCE_FILES:
        assert digest(candidate / name) == digest(live / name), name

    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *unused_args, **unused_kwargs: None
    sys.modules.setdefault("dotenv", dotenv_stub)
    sys.path.insert(0, str(repo / "API"))
    from Classes.Case.DataFileClass import DataFile
    from Classes.Case.OsemosysClass import Osemosys

    model = DataFile(args.live)
    run = live / "res" / args.live_run
    if run.exists():
        raise FileExistsError(run)
    scenarios = [{
        "ScenarioId": item["ScenarioId"], "Scenario": item["Scenario"],
        "Desc": item.get("Desc", ""), "Active": item["Scenario"] == "BASE",
    } for item in model.genData["osy-scenarios"]]
    response = model.createCaseRun(args.live_run, {
        "Case": args.live_run, "CaseId": f"CS_{args.live_run}",
        "Desc": "Generation and matrix identity check only; no optimizer",
        "Runtime": date.today().isoformat(), "Scenarios": scenarios,
    })
    assert response.get("status_code") == "success", response
    model.generateDatafile(args.live_run)
    model.preprocessData(run / "data.txt", run / "data_processed.txt")

    candidate_run = candidate / "res" / args.candidate_run
    candidate_data, live_data = candidate_run / "data.txt", run / "data.txt"
    assert candidate_data.read_bytes() == live_data.read_bytes()

    glpsol = Osemosys._find_solver_binary(model.glpkFolder.resolve(), "glpsol", recursive=False)
    assert glpsol is not None
    checked = subprocess.run(
        [str(glpsol), "--check", "-m", str(repo / "WebAPP" / "SOLVERs" / "model.v.5.4.txt"),
         "-d", str(run / "data_processed.txt"), "--wlp", str(run / "lp.lp")],
        cwd=model.glpkFolder.resolve() if model.glpsol_is_bundled else None,
        capture_output=True, text=True, timeout=240,
    )
    (run / "glpsol_check.log").write_text(checked.stdout + "\n" + checked.stderr, encoding="utf-8")
    assert checked.returncode == 0, checked.stderr[-4000:]
    expected = {
        "Number of rows               =   809933",
        "Number of columns            =   901586",
        "Number of non-zeros (matrix) = 13080959",
    }
    assert expected.issubset(set(checked.stdout.splitlines()))
    record = {
        "schema": "philippines-v20-power-promotion-identity-v1",
        "status": "passed",
        "source_files_byte_identical": len(SOURCE_FILES),
        "candidate_data_sha256": digest(candidate_data),
        "live_data_sha256": digest(live_data),
        "matrix": {"rows": 809933, "columns": 901586, "nonzeros": 13080959},
        "optimizer_runs": 0,
        "reason_no_live_solve": "promoted source and generated data.txt are byte-identical to the solved accepted candidate",
    }
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
