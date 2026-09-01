#!/usr/bin/env python3
"""Generate and concurrently solve the three Philippines vIS2 policy scenarios."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import subprocess
import time
from pathlib import Path

import philippines_vis2_agriculture_spatial as vis2


TIMEOUT = 900
SCENARIOS = {
    "COAL_PHASEOUT": "COAL_PHASEOUT_VIS2_AGRICULTURE_SPATIAL_R3_900S",
    "RE": "RE_VIS2_AGRICULTURE_SPATIAL_R3_900S",
    "EV": "EV_VIS2_AGRICULTURE_SPATIAL_R3_900S",
}
VIS15_RUNS = {
    "COAL_PHASEOUT": "COAL_PHASEOUT_VIS15_WATER_BOUNDARY",
    "RE": "RE_VIS15_WATER_BOUNDARY",
    "EV": "EV_VIS15_WATER_BOUNDARY",
}


def _write(path: Path, value: object) -> None:
    vis2.write(path, value)


def _lp_land_zero_gate(lp_path: Path, land_names: set[str]) -> dict:
    zero_rows = set()
    nonzero_rows = []
    pending = None
    with lp_path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            label = re.match(
                r"\s*NCC1_TotalAnnualMaxNewCapacityConstraint\(RE1,(LNDAGRPHLC\d{2}_(?:LUZ|VIS|MIN|OFF)),(\d{4})\):",
                line,
            )
            if label and label.group(1) in land_names:
                pending = (label.group(1), label.group(2))
                continue
            if pending:
                bound = re.match(
                    r"\s*\+ NewCapacity\(RE1,([^,]+),(\d{4})\) <= ([-+0-9.eE]+)\s*$",
                    line,
                )
                if bound and (bound.group(1), bound.group(2)) == pending:
                    value = float(bound.group(3))
                    if value == 0:
                        zero_rows.add(pending)
                    else:
                        nonzero_rows.append((*pending, value))
                pending = None
    expected = {(name, year) for name in land_names for year in vis2.YEARS}
    return {
        "passed": zero_rows == expected and not nonzero_rows,
        "zero_row_count": len(zero_rows),
        "expected_row_count": len(expected),
        "nonzero_rows": nonzero_rows,
    }


def generate() -> None:
    if vis2.read(vis2.TARGET / "documentation/vis2_preflight.json")["status"] != "passed":
        raise RuntimeError("vIS2 source preflight has not passed")
    df = vis2.datafile()
    available = {row["Scenario"]: row for row in df.genData["osy-scenarios"]}
    land_names = {
        row["Tech"] for row in df.genData["osy-tech"]
        if re.fullmatch(r"LNDAGRPHLC\d{2}_(LUZ|VIS|MIN|OFF)", row["Tech"])
    }
    reports = {}
    for scenario, run_name in SCENARIOS.items():
        run = vis2.TARGET / "res" / run_name
        if run.exists():
            raise FileExistsError(f"refusing to replace existing run: {run}")
        scenario_rows = [
            {"ScenarioId": row["ScenarioId"], "Scenario": row["Scenario"],
             "Desc": row.get("Desc", ""), "Active": row["Scenario"] in {"BASE", scenario}}
            for row in df.genData["osy-scenarios"]
        ]
        created = df.createCaseRun(run_name, {
            "Case": run_name,
            "CaseId": f"CS_PHL_VIS2_AGRICULTURE_SPATIAL_R3_{scenario}",
            "Desc": f"Philippines vIS2 agriculture spatial {scenario}",
            "Runtime": str(vis2.date.today()),
            "Scenarios": scenario_rows,
        })
        if created.get("status_code") != "success":
            raise RuntimeError(created)
        started = time.monotonic()
        df.generateDatafile(run_name)
        df.preprocessData(run / "data.txt", run / "data_processed.txt")
        glpsol = vis2.v15.Osemosys._find_solver_binary(df.glpkFolder.resolve(), "glpsol", recursive=False)
        checked = subprocess.run(
            [str(glpsol), "--check", "-m", str(vis2.MODEL), "-d", str(run / "data_processed.txt"),
             "--wlp", str(run / "lp.lp")],
            cwd=df.glpkFolder.resolve() if df.glpsol_is_bundled else None,
            capture_output=True, text=True, timeout=300,
        )
        log = checked.stdout + "\n" + checked.stderr
        (run / "glpsol_check.log").write_text(log, encoding="utf-8")
        processed = (run / "data_processed.txt").read_text(encoding="utf-8")
        modes_ok = True
        for name in land_names:
            match = re.search(rf"^set MODEperTECHNOLOGY\[{re.escape(name)}\]:=\s*(.*?)\s*;$", processed, re.M)
            modes_ok &= bool(match) and set(map(int, match.group(1).split())) == set(vis2.ACTIVE_LAND_MODES)
        zero_gate = _lp_land_zero_gate(run / "lp.lp", land_names)
        passed = (checked.returncode == 0 and "Model has been successfully generated" in log
                  and len(land_names) == 29 and modes_ok and zero_gate["passed"])
        report = {
            "scenario": scenario,
            "scenario_id": available[scenario]["ScenarioId"],
            "active_scenarios": ["BASE", scenario],
            "status": "passed" if passed else "failed",
            "optimizer_runs": 0,
            "generation_check_seconds": time.monotonic() - started,
            "matrix_dimensions": vis2.v15._v14.matrix_metrics(log),
            "generated_land_mode_sets_exact": modes_ok,
            "land_new_capacity_fixed_zero_in_lp": zero_gate,
        }
        _write(run / "generation_matrix_report.json", report)
        reports[scenario] = report
        if not passed:
            raise RuntimeError(json.dumps(report, indent=2))
    _write(vis2.TARGET / "documentation/vis2_policy_generation_900s.json", reports)
    print(json.dumps(reports, indent=2))


def _solve_one(scenario: str, run_name: str) -> dict:
    run = vis2.TARGET / "res" / run_name
    gate = vis2.read(run / "generation_matrix_report.json")
    if gate["status"] != "passed" or gate["optimizer_runs"] != 0:
        raise RuntimeError(f"unclean generation gate for {scenario}")
    df = vis2.datafile()
    cbc = vis2.v15.Osemosys._find_solver_binary(df.cbcFolder.resolve(), "cbc", recursive=False)
    log_path = run / "cbc.log"
    started = time.monotonic()
    timed_out = False
    with log_path.open("w", encoding="utf-8", buffering=1) as log_stream:
        process = subprocess.Popen(
            [str(cbc), str(run / "lp.lp"), "solve", "-printing", "all", "-solu", str(run / "results.txt")],
            cwd=df.cbcFolder.resolve() if df.cbc_is_bundled else None,
            stdout=log_stream, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        try:
            returncode = process.wait(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
            returncode = process.returncode
    elapsed = time.monotonic() - started
    log = log_path.read_text(encoding="utf-8")
    diagnostics = vis2.cbc_diagnostics(log)
    if timed_out:
        status = "timed_out"
        objective = None
    elif returncode != 0 or not (run / "results.txt").is_file():
        status = f"solver_error_returncode_{returncode}"
        objective = None
    else:
        status = (run / "results.txt").read_text(encoding="utf-8").splitlines()[0]
        match = re.search(r"objective value\s+([-+0-9.eE]+)", status)
        objective = float(match.group(1)) if match else None
    baseline = vis2.read(vis2.SOURCE / "res" / VIS15_RUNS[scenario] / "optimization_record.json")
    report = {
        "scenario": scenario, "run": run_name, "status": status, "optimizer_runs": 1,
        "timeout_seconds": TIMEOUT, "solve_seconds": elapsed, "objective": objective,
        "returncode": returncode, "vIS15_objective": baseline.get("objective"),
        "vIS15_solve_seconds": baseline.get("solve_seconds"),
        "objective_change": objective - baseline["objective"] if objective is not None and baseline.get("objective") is not None else None,
        "objective_change_percent": 100 * (objective / baseline["objective"] - 1) if objective is not None and baseline.get("objective") is not None else None,
        **diagnostics,
    }
    _write(run / "optimization_record.json", report)
    return report


def solve() -> None:
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_solve_one, scenario, run): scenario for scenario, run in SCENARIOS.items()}
        reports = {futures[future]: future.result() for future in concurrent.futures.as_completed(futures)}
    df = vis2.datafile()
    for scenario in SCENARIOS:
        report = reports[scenario]
        if report["status"].startswith("Optimal"):
            run = vis2.TARGET / "res" / report["run"]
            df.generateCSVfromCBC(run / "data.txt", run / "results.txt", run)
    ordered = {scenario: reports[scenario] for scenario in SCENARIOS}
    _write(vis2.TARGET / "documentation/vis2_policy_validation_900s.json", ordered)
    print(json.dumps(ordered, indent=2))


def finalize() -> None:
    """Finalize already-completed CBC artifacts without launching an optimizer."""
    reports = {}
    df = vis2.datafile()
    for scenario, run_name in SCENARIOS.items():
        run = vis2.TARGET / "res" / run_name
        log = (run / "cbc.log").read_text(encoding="utf-8")
        if not (run / "results.txt").is_file():
            raise RuntimeError(f"missing completed results for {scenario}")
        status = (run / "results.txt").read_text(encoding="utf-8").splitlines()[0]
        objective_match = re.search(r"objective value\s+([-+0-9.eE]+)", status)
        objective = float(objective_match.group(1)) if objective_match else None
        wall_match = re.search(r"Total time \(CPU seconds\):\s+[-+0-9.eE]+\s+\(Wallclock seconds\):\s+([-+0-9.eE]+)", log)
        elapsed = float(wall_match.group(1)) if wall_match else None
        baseline = vis2.read(vis2.SOURCE / "res" / VIS15_RUNS[scenario] / "optimization_record.json")
        report = {
            "scenario": scenario, "run": run_name, "status": status, "optimizer_runs": 1,
            "timeout_seconds": TIMEOUT, "solve_seconds": elapsed, "objective": objective,
            "returncode": 0, "vIS15_objective": baseline.get("objective"),
            "vIS15_solve_seconds": baseline.get("solve_seconds"),
            "objective_change": objective - baseline["objective"] if objective is not None and baseline.get("objective") is not None else None,
            "objective_change_percent": 100 * (objective / baseline["objective"] - 1) if objective is not None and baseline.get("objective") is not None else None,
            **vis2.cbc_diagnostics(log),
            "finalized_from_existing_artifacts_without_optimizer": True,
        }
        _write(run / "optimization_record.json", report)
        reports[scenario] = report
        if status.startswith("Optimal"):
            df.generateCSVfromCBC(run / "data.txt", run / "results.txt", run)
    ordered = {scenario: reports[scenario] for scenario in SCENARIOS}
    _write(vis2.TARGET / "documentation/vis2_policy_validation_900s.json", ordered)
    print(json.dumps(ordered, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("generate", "solve", "finalize"))
    args = parser.parse_args()
    if args.phase == "generate":
        generate()
    elif args.phase == "solve":
        solve()
    else:
        finalize()


if __name__ == "__main__":
    main()
