#!/usr/bin/env python3
"""Generate, solve, and document the three vIS1.5 policy scenarios."""

from __future__ import annotations

import concurrent.futures
import json
import re
import subprocess
import time
from pathlib import Path

import philippines_vis15_water_boundary as v15


SCENARIOS = {
    "COAL_PHASEOUT": {"run": "COAL_PHASEOUT_VIS15_WATER_BOUNDARY", "timeout": 421, "anchor": 280.5446129999982},
    "RE": {"run": "RE_VIS15_WATER_BOUNDARY", "timeout": 421, "anchor": 280.5729726660029},
    "EV": {"run": "EV_VIS15_WATER_BOUNDARY", "timeout": 460, "anchor": 306.5874035829984},
}


def generate() -> None:
    df = v15.datafile()
    available = {row["Scenario"]: row for row in df.genData["osy-scenarios"]}
    reports = {}
    for scenario, spec in SCENARIOS.items():
        run = v15.TARGET / "res" / spec["run"]
        if run.exists():
            raise FileExistsError(f"refusing to replace existing run {run}")
        metadata = []
        for row in df.genData["osy-scenarios"]:
            metadata.append({"ScenarioId": row["ScenarioId"], "Scenario": row["Scenario"],
                             "Desc": row.get("Desc", ""), "Active": row["Scenario"] in {"BASE", scenario}})
        created = df.createCaseRun(spec["run"], {
            "Case": spec["run"], "CaseId": f"CS_PHL_VIS15_WATER_BOUNDARY_{scenario}",
            "Desc": f"Philippines vIS1.5 water-cost boundary {scenario}",
            "Runtime": str(v15.date.today()), "Scenarios": metadata,
        })
        if created.get("status_code") != "success":
            raise RuntimeError(json.dumps(created, indent=2))
        started = time.monotonic()
        df.generateDatafile(spec["run"])
        df.preprocessData(run / "data.txt", run / "data_processed.txt")
        glpsol = v15.Osemosys._find_solver_binary(df.glpkFolder.resolve(), "glpsol", recursive=False)
        checked = subprocess.run([str(glpsol), "--check", "-m", str(v15.MODEL),
                                  "-d", str(run / "data_processed.txt"), "--wlp", str(run / "lp.lp")],
                                 cwd=df.glpkFolder.resolve() if df.glpsol_is_bundled else None,
                                 capture_output=True, text=True, timeout=300)
        log = checked.stdout + "\n" + checked.stderr
        (run / "glpsol_check.log").write_text(log, encoding="utf-8")
        ok = checked.returncode == 0 and "Model has been successfully generated" in log
        reports[scenario] = {"scenario_id": available[scenario]["ScenarioId"], "status": "passed" if ok else "failed",
                             "generation_check_seconds": time.monotonic() - started,
                             "matrix_dimensions": v15._v14.matrix_metrics(log), "optimizer_runs": 0}
        v15.write_json(run / "generation_matrix_report.json", reports[scenario])
        if not ok:
            raise RuntimeError(f"{scenario} generation/matrix check failed")
    v15.write_json(v15.TARGET / "documentation" / "vis15_policy_generation.json", reports)
    print(json.dumps(reports, indent=2))


def _solve_one(scenario: str, spec: dict) -> dict:
    run = v15.TARGET / "res" / spec["run"]
    df = v15.datafile()
    cbc = v15.Osemosys._find_solver_binary(df.cbcFolder.resolve(), "cbc", recursive=False)
    command = [str(cbc), str(run / "lp.lp"), "solve", "-printing", "all", "-solu", str(run / "results.txt")]
    started = time.monotonic()
    try:
        completed = subprocess.run(command, cwd=df.cbcFolder.resolve() if df.cbc_is_bundled else None,
                                   capture_output=True, text=True, timeout=spec["timeout"])
        elapsed = time.monotonic() - started
        log = completed.stdout + "\n" + completed.stderr
        status = (run / "results.txt").read_text(encoding="utf-8").splitlines()[0] if (run / "results.txt").is_file() else "no result"
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - started
        out = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        log, status = out + "\n" + err, "timed_out"
        completed = None
    (run / "cbc.log").write_text(log, encoding="utf-8")
    match = re.search(r"objective value\s+([-+0-9.eE]+)", status)
    report = {"scenario": scenario, "status": status, "optimizer_runs": 1,
              "timeout_seconds": spec["timeout"], "runtime_anchor_seconds": spec["anchor"],
              "headroom_factor": spec["timeout"] / spec["anchor"], "solve_seconds": elapsed,
              "objective": float(match.group(1)) if match else None,
              "returncode": completed.returncode if completed else None,
              "run": spec["run"]}
    v15.write_json(run / "optimization_record.json", report)
    return report


def solve() -> None:
    for scenario, spec in SCENARIOS.items():
        gate = v15.read_json(v15.TARGET / "res" / spec["run"] / "generation_matrix_report.json")
        if gate.get("status") != "passed" or gate.get("optimizer_runs") != 0:
            raise RuntimeError(f"unclean generation gate for {scenario}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_solve_one, scenario, spec): scenario for scenario, spec in SCENARIOS.items()}
        reports = {futures[f]: f.result() for f in concurrent.futures.as_completed(futures)}
    # CSV extraction is sequential because DataFile also touches shared viewer state.
    df = v15.datafile()
    for scenario, report in reports.items():
        run = v15.TARGET / "res" / report["run"]
        if report["status"].startswith("Optimal"):
            df.generateCSVfromCBC(run / "data.txt", run / "results.txt", run)
    ordered = {scenario: reports[scenario] for scenario in SCENARIOS}
    v15.write_json(v15.TARGET / "documentation" / "vis15_policy_validation.json", ordered)
    with (v15.TARGET / "documentation" / "MODEL_FIXES_WATER_BOUNDARY_VIS15_2026-08-31.md").open("a", encoding="utf-8") as stream:
        stream.write("\n## Policy-scenario validation\n\n")
        for scenario, report in ordered.items():
            stream.write(f"- {scenario}: `{report['status']}`, {report['solve_seconds']:.3f} seconds "
                         f"under a {report['timeout_seconds']}-second limit; objective {report['objective']}.\n")
        stream.write("\nThe three optimizations ran concurrently in isolated run directories; CSV extraction was sequential.\n")
    print(json.dumps(ordered, indent=2))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("generate", "solve"))
    args = parser.parse_args()
    generate() if args.phase == "generate" else solve()
