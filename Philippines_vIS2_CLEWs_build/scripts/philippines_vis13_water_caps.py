#!/usr/bin/env python3
"""Build, gate, generate, and run the Philippines vIS1.3 water-cap repair."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import types
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP" / "DataStorage"
SOURCE = STORAGE / ".Philippines_vIS12-evfix2-check-20260828"
TARGET = STORAGE / ".Philippines_vIS13-water-cap-candidate-20260831"
BASELINE_RUN = STORAGE / ".Philippines_vIS12-candidate-20260828" / "res" / "BASE_VIS12_DIFFERENTIATED"
RUN_NAME = "BASE_VIS13_WATER_CAP_CLOSURE"
MODEL = ROOT / "WebAPP" / "SOLVERs" / "model.v.5.4.txt"
YEARS = tuple(str(year) for year in range(2020, 2054))
BASE = "SC_0"
BASELINE_OBJECTIVE = 892605.95176822
BASELINE_MATRIX = {"rows": 570115, "columns": 608330, "matrix_nonzeros": 9338087}

CAP_TECHS = {
    "WATER_SUR_AVAIL": (
        "PHL_DEM_PUB_SUR_WAT", "PHL_DEM_PWR_SUR_WAT", "DEMAGRSURPHL",
        "PHL_DEM_PWR_SUR_WAT_LUZ", "PHL_DEM_PWR_SUR_WAT_VIS", "PHL_DEM_PWR_SUR_WAT_MIN",
    ),
    "WATER_GWT_POTENTIAL": (
        "PHL_DEM_PUB_GWT_WAT", "PHL_DEM_PWR_GWT_WAT", "DEMAGRGWTPHL",
        "PHL_DEM_PWR_GWT_WAT_LUZ", "PHL_DEM_PWR_GWT_WAT_VIS", "PHL_DEM_PWR_GWT_WAT_MIN",
    ),
}
NEW_TECHS = {
    "WATER_SUR_AVAIL": CAP_TECHS["WATER_SUR_AVAIL"][3:],
    "WATER_GWT_POTENTIAL": CAP_TECHS["WATER_GWT_POTENTIAL"][3:],
}

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(ROOT / "API"))

from Classes.Base import Config  # noqa: E402
from Classes.Case.DataFileClass import DataFile  # noqa: E402
from Classes.Case.OsemosysClass import Osemosys  # noqa: E402
from Classes.Case.UpdateCaseClass import UpdateCase  # noqa: E402


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def maps(gen):
    return (
        {x["Tech"]: x["TechId"] for x in gen["osy-tech"]},
        {x["Con"]: x for x in gen["osy-constraints"]},
    )


def build() -> None:
    if TARGET.exists():
        raise FileExistsError(f"refusing to replace candidate: {TARGET}")
    # UpdateCase reads view/resData.json while normalizing source parameters.
    # Keep the inherited view cache for that operation; it is not validation evidence.
    shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("res", ".DS_Store"))
    gen = read_json(TARGET / "genData.json")
    tech_ids, constraints = maps(gen)
    gen["osy-casename"] = "Philippines_vIS1.3"
    gen["osy-date"] = "2026-08-31"
    gen["osy-desc"] = "Philippines vIS1.3: vIS1.2 plus complete national surface- and groundwater-cap membership."
    for con_name, names in CAP_TECHS.items():
        constraints[con_name]["CM"] = [tech_ids[name] for name in names]

    Config.DATA_STORAGE = STORAGE
    UpdateCase(TARGET.name, gen).updateCase()
    write_json(TARGET / "genData.json", gen)

    rtcn = read_json(TARGET / "RYTCn.json")
    for con_name, names in NEW_TECHS.items():
        con_id = constraints[con_name]["ConId"]
        for scenario_id, rows in rtcn["CAM"].items():
            for name in names:
                tech_id = tech_ids[name]
                matches = [row for row in rows if row["TechId"] == tech_id and row["ConId"] == con_id]
                if len(matches) != 1:
                    raise RuntimeError(f"UpdateCase did not create one CAM row for {scenario_id}/{name}/{con_name}")
                for year in YEARS:
                    matches[0][year] = 1 if scenario_id == BASE else None
    write_json(TARGET / "RYTCn.json", rtcn)

    note = TARGET / "MODEL_FIXES_WATER_CAP_CLOSURE_VIS13_2026-08-31.md"
    note.write_text(
        """# Philippines vIS1.3 water-cap closure

## Physical intent and observation classification

The existing national annual surface-water availability and groundwater-potential constraints are continuing physical resource constraints. vIS1.3 adds the LUZ, VIS and MIN power-cooling withdrawal routes to those constraints. It does not prescribe observed withdrawal, activity, dispatch, island share or groundwater share; all remain endogenous.

The six island cooling technologies are physical pass-through withdrawal routes. `WATER_SUR_AVAIL` and `WATER_GWT_POTENTIAL` are accounting constraints whose annual left-hand sides must include every corresponding national and island withdrawal route with coefficient 1. The cap values and all conversion ratios are unchanged.

## Source changes

- `genData.json`: case identity updated to vIS1.3; three island surface routes and three island groundwater routes added to the existing constraint memberships through `UpdateCase`.
- `RYTCn.json`: BASE `CAM=1` for those six new memberships in every model year; non-BASE overlays remain null and inherit BASE.
- No demand, capacity, activity bound, share, cost, efficiency or cap value is changed.

## Validation contract

Before optimization, the gate checks exact membership and coefficients, unchanged non-target parameters, mode/input-ratio exactness, positive finite cap values, and tests the retained optimal vIS1.2 BASE solution as a feasible witness for every corrected annual cap. Generation, preprocessing and GLPK matrix construction must then pass before the sole 300-second BASE optimization.
""",
        encoding="utf-8",
    )
    manifest = {
        "schema": "philippines-vis13-water-cap-build-v1",
        "source_case": str(SOURCE), "candidate_case": str(TARGET),
        "changed_physical_source_files": ["genData.json", "RYTCn.json"],
        "optimizer_runs": 0,
    }
    write_json(TARGET / "documentation" / "vis13_water_cap_build_manifest.json", manifest)
    print(json.dumps(manifest, indent=2))


def baseline_activity() -> dict[tuple[str, str], float]:
    path = BASELINE_RUN / "csv" / "TotalAnnualTechnologyActivityByMode.csv"
    values: dict[tuple[str, str], float] = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            key = (row["t"], row["y"])
            values[key] = values.get(key, 0.0) + float(row["TotalAnnualTechnologyActivityByMode"])
    return values


def preflight() -> None:
    failures = []
    checks = []

    def check(condition: bool, name: str, detail=None):
        checks.append({"check": name, "passed": bool(condition), "detail": detail})
        if not condition:
            failures.append(name)

    source_gen = read_json(SOURCE / "genData.json")
    gen = read_json(TARGET / "genData.json")
    tech_ids, constraints = maps(gen)
    check(gen["osy-casename"] == "Philippines_vIS1.3", "case identity")

    for filename in sorted(path.name for path in SOURCE.glob("*.json") if path.name not in {"genData.json", "RYTCn.json"}):
        check(read_json(SOURCE / filename) == read_json(TARGET / filename), f"unchanged parameter {filename}")

    expected_gen = json.loads(json.dumps(source_gen))
    expected_gen["osy-casename"] = gen["osy-casename"]
    expected_gen["osy-date"] = gen["osy-date"]
    expected_gen["osy-desc"] = gen["osy-desc"]
    expected_constraints = {x["Con"]: x for x in expected_gen["osy-constraints"]}
    for con_name, names in CAP_TECHS.items():
        expected_constraints[con_name]["CM"] = [tech_ids[name] for name in names]
    check(expected_gen == gen, "genData diff limited to identity and corrected cap memberships")

    for con_name, names in CAP_TECHS.items():
        actual = constraints[con_name]["CM"]
        expected = [tech_ids[name] for name in names]
        check(actual == expected and len(actual) == len(set(actual)), f"exact {con_name} membership", names)

    rtcn = read_json(TARGET / "RYTCn.json")["CAM"]
    for con_name, names in CAP_TECHS.items():
        con_id = constraints[con_name]["ConId"]
        for scenario_id, rows in rtcn.items():
            for name in names:
                matches = [row for row in rows if row["TechId"] == tech_ids[name] and row["ConId"] == con_id]
                expected_value = 1 if scenario_id == BASE else None
                good = len(matches) == 1 and all(matches[0][year] == expected_value for year in YEARS)
                check(good, f"CAM {scenario_id}/{con_name}/{name}")

    # Each added cooling route must count one-for-one with gross raw-water input.
    raw_commodity = {"WATER_SUR_AVAIL": "COM_0bnsj", "WATER_GWT_POTENTIAL": "COM_bssc5"}
    iar = read_json(TARGET / "RYTCM.json")["IAR"][BASE]
    for con_name, names in NEW_TECHS.items():
        for name in names:
            rows = [row for row in iar if row["TechId"] == tech_ids[name] and row["CommId"] == raw_commodity[con_name]]
            active = [row for row in rows if any(row[year] != 0 for year in YEARS)]
            inactive = [row for row in rows if row not in active]
            good = (len(active) == 1 and active[0]["MoId"] == 1
                    and all(active[0][year] == 1 for year in YEARS)
                    and all(all(row[year] == 0 for year in YEARS) for row in inactive))
            check(good, f"unit gross-withdrawal ratio {name}")

    # A retained optimal vIS1.2 point is a constructive feasibility witness:
    # all old equations are unchanged and it must satisfy each newly completed cap.
    record = read_json(BASELINE_RUN / "optimization_record.json")
    check(str(record.get("status", "")).startswith("Optimal"), "canonical BASE witness is optimal")
    check(abs(float(record.get("objective")) - BASELINE_OBJECTIVE) < 1e-6, "canonical BASE witness identity")
    activity = baseline_activity()
    ucc = read_json(TARGET / "RYCn.json")["UCC"][BASE]
    cap_rows = {row["ConId"]: row for row in ucc}
    witness = {}
    for con_name, names in CAP_TECHS.items():
        con_id = constraints[con_name]["ConId"]
        margins = {}
        for year in YEARS:
            lhs = sum(activity.get((name, year), 0.0) for name in names)
            rhs = cap_rows[con_id][year]
            check(isinstance(rhs, (int, float)) and rhs > 0, f"positive finite cap {con_name}/{year}")
            margins[year] = rhs - lhs
        check(min(margins.values()) >= -1e-7, f"vIS1.2 BASE witness satisfies corrected {con_name}",
              {"minimum_headroom": min(margins.values()), "binding_year": min(margins, key=margins.get)})
        witness[con_name] = {"minimum_headroom": min(margins.values()), "binding_year": min(margins, key=margins.get)}

    report = {
        "schema": "philippines-vis13-water-cap-preflight-v1",
        "status": "passed" if not failures else "failed",
        "optimizer_runs": 0, "generation_runs": 0,
        "proof": "The only physical changes are six added unit CAM terms. The retained vIS1.2 optimal BASE point satisfies every completed cap, so it is a feasible point of vIS1.3 before optimization.",
        "witness": witness, "checks": checks, "failures": failures,
    }
    write_json(TARGET / "documentation" / "vis13_water_cap_preflight.json", report)
    print(json.dumps({k: report[k] for k in ("status", "optimizer_runs", "generation_runs", "witness", "failures")}, indent=2))
    if failures:
        raise RuntimeError(f"preflight failed: {failures}")


def datafile() -> DataFile:
    Config.DATA_STORAGE = STORAGE
    return DataFile(TARGET.name)


def matrix_metrics(log: str):
    patterns = {
        "rows": r"Number of rows\s*=\s*(\d+)",
        "columns": r"Number of columns\s*=\s*(\d+)",
        "matrix_nonzeros": r"Number of non-zeros \(matrix\)\s*=\s*(\d+)",
    }
    return {key: int(re.search(pattern, log).group(1)) for key, pattern in patterns.items()}


def generate_check() -> None:
    pre = read_json(TARGET / "documentation" / "vis13_water_cap_preflight.json")
    if pre.get("status") != "passed" or pre.get("optimizer_runs") != 0:
        raise RuntimeError("blocking source preflight has not passed cleanly")
    run = TARGET / "res" / RUN_NAME
    if run.exists():
        raise FileExistsError(f"refusing to replace run: {run}")
    df = datafile()
    scenarios = [{
        "ScenarioId": item["ScenarioId"], "Scenario": item["Scenario"],
        "Desc": item.get("Desc", ""), "Active": item["Scenario"] == "BASE",
    } for item in df.genData["osy-scenarios"]]
    created = df.createCaseRun(RUN_NAME, {
        "Case": RUN_NAME, "CaseId": "CS_PHL_VIS13_WATER_CAP_BASE",
        "Desc": "Philippines vIS1.3 water-cap closure BASE", "Runtime": str(date.today()),
        "Scenarios": scenarios,
    })
    if created.get("status_code") != "success":
        raise RuntimeError(json.dumps(created, indent=2))
    timings = {}
    started = time.monotonic(); df.generateDatafile(RUN_NAME); timings["generate"] = time.monotonic() - started
    started = time.monotonic(); df.preprocessData(run / "data.txt", run / "data_processed.txt"); timings["preprocess"] = time.monotonic() - started
    glpsol = Osemosys._find_solver_binary(df.glpkFolder.resolve(), "glpsol", recursive=False)
    if glpsol is None:
        raise RuntimeError("GLPK solver unavailable")
    started = time.monotonic()
    checked = subprocess.run(
        [str(glpsol), "--check", "-m", str(MODEL), "-d", str(run / "data_processed.txt"), "--wlp", str(run / "lp.lp")],
        cwd=df.glpkFolder.resolve() if df.glpsol_is_bundled else None,
        capture_output=True, text=True, timeout=300,
    )
    timings["glpsol_check_and_lp"] = time.monotonic() - started
    log = checked.stdout + "\n" + checked.stderr
    (run / "glpsol_check.log").write_text(log, encoding="utf-8")
    if checked.returncode != 0:
        raise RuntimeError(log[-12000:])
    dimensions = matrix_metrics(log)
    expected = dict(BASELINE_MATRIX)
    expected["matrix_nonzeros"] += 6 * len(YEARS)
    matrix_ok = dimensions["rows"] == expected["rows"] and dimensions["columns"] == expected["columns"] and dimensions["matrix_nonzeros"] == expected["matrix_nonzeros"]

    # Inspect generated LP rows, not just source JSON.
    found = {name: False for names in CAP_TECHS.values() for name in names}
    in_water_row = False
    with (run / "lp.lp").open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if line.startswith(" UDC1_UserDefinedConstraintInequality(RE1,WATER_"):
                in_water_row = line.rstrip().endswith(",2020):")
            elif in_water_row and line.startswith(" UDC1_"):
                in_water_row = False
            if in_water_row:
                for name in found:
                    if f"TotalTechnologyAnnualActivity(RE1,{name},2020)" in line:
                        found[name] = True
            if all(found.values()):
                break
    generated_ok = all(found.values())
    report = {
        "status": "passed" if matrix_ok and generated_ok else "failed",
        "optimizer_runs": 0, "active_scenarios": ["BASE"], "timings_seconds": timings,
        "matrix_dimensions": dimensions, "expected_matrix_dimensions": expected,
        "generated_2020_water_terms": found,
        "hashes": {name: sha256(run / name) for name in ("data.txt", "data_processed.txt", "lp.lp")},
    }
    write_json(run / "generation_matrix_report.json", report)
    print(json.dumps(report, indent=2))
    if report["status"] != "passed":
        raise RuntimeError("generated matrix gate failed; optimizer blocked")


def solve(timeout: int) -> None:
    run = TARGET / "res" / RUN_NAME
    gate = read_json(run / "generation_matrix_report.json")
    if gate.get("status") != "passed" or gate.get("optimizer_runs") != 0:
        raise RuntimeError("generation/matrix gate is not a clean zero-optimizer pass")
    if sha256(run / "lp.lp") != gate["hashes"]["lp.lp"]:
        raise RuntimeError("LP changed after matrix gate")
    df = datafile()
    cbc = Osemosys._find_solver_binary(df.cbcFolder.resolve(), "cbc", recursive=False)
    if cbc is None:
        raise RuntimeError("CBC solver unavailable")
    command = [str(cbc), str(run / "lp.lp"), "solve", "-printing", "all", "-solu", str(run / "results.txt")]
    started = time.monotonic()
    try:
        completed = subprocess.run(command, cwd=df.cbcFolder.resolve() if df.cbc_is_bundled else None,
                                   capture_output=True, text=True, timeout=timeout)
        elapsed = time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - started
        out = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        (run / "cbc.log").write_text(out + "\n" + err, encoding="utf-8")
        report = {"status": "timed_out", "optimizer_runs": 1, "timeout_seconds": timeout, "solve_seconds": elapsed, "promotion_allowed": False}
        write_json(run / "optimization_record.json", report)
        print(json.dumps(report, indent=2))
        return
    log = completed.stdout + "\n" + completed.stderr
    (run / "cbc.log").write_text(log, encoding="utf-8")
    if completed.returncode != 0 or not (run / "results.txt").is_file():
        raise RuntimeError(log[-12000:])
    status = (run / "results.txt").read_text(encoding="utf-8").splitlines()[0]
    objective_match = re.search(r"objective value\s+([-+0-9.eE]+)", status)
    objective = float(objective_match.group(1)) if objective_match else None
    export_started = time.monotonic()
    df.generateCSVfromCBC(run / "data.txt", run / "results.txt", run)
    export_seconds = time.monotonic() - export_started

    gen = read_json(TARGET / "genData.json")
    _, constraints = maps(gen)
    activity = {}
    with (run / "csv" / "TotalAnnualTechnologyActivityByMode.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            key = (row["t"], row["y"])
            activity[key] = activity.get(key, 0.0) + float(row["TotalAnnualTechnologyActivityByMode"])
    cap_rows = {row["ConId"]: row for row in read_json(TARGET / "RYCn.json")["UCC"][BASE]}
    caps = {}
    for con_name, names in CAP_TECHS.items():
        rhs = cap_rows[constraints[con_name]["ConId"]]
        records = [{"year": year, "withdrawal": sum(activity.get((name, year), 0.0) for name in names), "cap": rhs[year]}
                   for year in YEARS]
        for item in records:
            item["headroom"] = item["cap"] - item["withdrawal"]
        caps[con_name] = {"minimum_headroom": min(x["headroom"] for x in records),
                          "binding_year": min(records, key=lambda x: x["headroom"])["year"],
                          "2020_withdrawal": records[0]["withdrawal"], "2020_cap": records[0]["cap"]}
    report = {
        "status": status, "optimizer_runs": 1, "timeout_seconds": timeout,
        "solve_seconds": elapsed, "csv_export_seconds": export_seconds,
        "objective": objective, "baseline_objective": BASELINE_OBJECTIVE,
        "objective_change": objective - BASELINE_OBJECTIVE if objective is not None else None,
        "objective_change_percent": 100 * (objective / BASELINE_OBJECTIVE - 1) if objective is not None else None,
        "water_caps": caps,
        "lp_sha256": sha256(run / "lp.lp"), "results_sha256": sha256(run / "results.txt"),
        "promotion_allowed": status.startswith("Optimal") and all(x["minimum_headroom"] >= -1e-6 for x in caps.values()),
        "cbc_tail": log[-3000:],
    }
    write_json(run / "optimization_record.json", report)
    write_json(TARGET / "documentation" / "vis13_base_validation.json", report)
    print(json.dumps({k: report[k] for k in ("status", "optimizer_runs", "timeout_seconds", "solve_seconds", "objective", "objective_change", "objective_change_percent", "water_caps", "promotion_allowed")}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("build", "preflight", "generate-check", "solve"))
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    {"build": build, "preflight": preflight, "generate-check": generate_check}.get(args.phase, lambda: solve(args.timeout))()


if __name__ == "__main__":
    main()
