#!/usr/bin/env python3
"""Validate solved v30 land identities, crop availability, and scenario outputs."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

from build_philippines_v30_yields_re_land import (
    ACTIVE_MODES, BASE, BUILT, CLUSTERS, INACTIVE_MODES, POPULATION_BUILT_2020,
    PV, PV_FOOTPRINT, WIND, WIND_FOOTPRINT, YEARS,
)


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "WebAPP" / "DataStorage" / "Philippines_v30"
RUNS = ["BASE_V30", "COAL_PHASEOUT_V30", "RE_V30", "EV_V30"]
TECH = {
    "supply": "TEC_dgw1l", "cropland": "TEC_phl_crop_v29", "barren": "TEC_mzni5",
    "built": BUILT, "forest": "TEC_hjgww", "grass": "TEC_nozrj", "other": "TEC_zty92",
    "water": "TEC_6rzgn", "pv": PV, "wind": WIND,
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def find_row(rows: list[dict[str, Any]], **keys: Any) -> dict[str, Any]:
    found = [row for row in rows if all(row.get(key) == value for key, value in keys.items())]
    if len(found) != 1:
        raise AssertionError(f"expected one row for {keys}, found {len(found)}")
    return found[0]


def parse_results(path: Path) -> tuple[str, dict[tuple[str, tuple[str, ...]], float]]:
    values: dict[tuple[str, tuple[str, ...]], float] = {}
    with path.open(encoding="utf-8") as stream:
        status = stream.readline().strip()
        if not status.startswith("Optimal - objective value"):
            raise AssertionError(f"result is not optimal: {status}")
        for line in stream:
            match = re.search(r"([A-Za-z0-9_]+)\(([^)]*)\)\s+([-+0-9.eE]+)\s+", line)
            if match and match.group(1) in {"TotalTechnologyAnnualActivity", "TotalAnnualTechnologyActivityByMode", "TotalCapacityAnnual"}:
                values[(match.group(1), tuple(match.group(2).split(",")))] = float(match.group(3))
    return status, values


def result(values: dict[tuple[str, tuple[str, ...]], float], variable: str, *indices: str) -> float:
    key = (variable, tuple(indices))
    if key not in values:
        raise AssertionError(f"missing {variable}{indices}")
    return values[key]


def validate_run(run_name: str, names: dict[str, str], population: dict[str, Any]) -> dict[str, Any]:
    run = CASE / "res" / run_name
    record_path = run / "optimization_record.json"
    if not record_path.is_file():
        return {"status": "not_run"}
    optimization = read_json(record_path)
    if optimization["status"] != "optimal":
        return {"status": optimization["status"], "optimization": optimization}
    status, values = parse_results(run / "results.txt")
    rows = []
    max_land_error = 0.0
    max_dynamic_error = 0.0
    max_inactive = 0.0
    previous_built = None
    for year in YEARS:
        activity = {
            key: result(values, "TotalTechnologyAnnualActivity", "RE1", names[tech], year)
            for key, tech in TECH.items() if key not in {"pv", "wind"}
        }
        # LNDOTHTOT mode 1 is physical fishpond/other land; mode 2 is idle
        # cropland and must not be counted again in the national direct classes.
        activity["other"] = result(values, "TotalAnnualTechnologyActivityByMode", "RE1", names[TECH["other"]], "1", year)
        pv_capacity = result(values, "TotalCapacityAnnual", "RE1", names[PV], year)
        wind_capacity = result(values, "TotalCapacityAnnual", "RE1", names[WIND], year)
        expected_built = float(population[year]) + PV_FOOTPRINT * pv_capacity + WIND_FOOTPRINT * wind_capacity
        dynamic_error = activity["built"] - expected_built
        cluster_total = sum(result(values, "TotalTechnologyAnnualActivity", "RE1", names[cluster], year) for cluster in CLUSTERS)
        built_cluster = sum(result(values, "TotalAnnualTechnologyActivityByMode", "RE1", names[cluster], "26", year) for cluster in CLUSTERS)
        idle = result(values, "TotalAnnualTechnologyActivityByMode", "RE1", names[TECH["other"]], "2", year)
        crop_active = sum(result(values, "TotalAnnualTechnologyActivityByMode", "RE1", names[cluster], str(mode), year) for cluster in CLUSTERS for mode in ACTIVE_MODES)
        crop_inactive = [result(values, "TotalAnnualTechnologyActivityByMode", "RE1", names[cluster], str(mode), year) for cluster in CLUSTERS for mode in INACTIVE_MODES]
        max_inactive = max(max_inactive, max(crop_inactive))
        direct_total = sum(activity[key] for key in ("cropland", "barren", "built", "forest", "grass", "other", "water"))
        errors = [
            activity["supply"] - direct_total,
            cluster_total - activity["supply"],
            activity["cropland"] - crop_active - sum(crop_inactive) - idle,
            activity["built"] - built_cluster,
            dynamic_error,
        ]
        if max(abs(item) for item in errors) > 3e-4:
            raise AssertionError(f"{run_name}/{year} land identity errors {errors}")
        if max(crop_inactive) > 1.1e-6:
            raise AssertionError(f"{run_name}/{year} unsupported crop mode exceeds operational zero")
        if previous_built is not None and activity["built"] < previous_built - 3e-4:
            raise AssertionError(f"{run_name}/{year} built land declines")
        previous_built = activity["built"]
        max_land_error = max(max_land_error, *(abs(item) for item in errors[:4]))
        max_dynamic_error = max(max_dynamic_error, abs(dynamic_error))
        rows.append({
            "run": run_name, "year": year, "land_supply": activity["supply"],
            "cropland": activity["cropland"], "cultivated_active": crop_active,
            "unsupported_mode_activity": sum(crop_inactive), "idle_cropland": idle,
            "forest": activity["forest"], "grass": activity["grass"], "other": activity["other"],
            "barren": activity["barren"], "water": activity["water"], "built": activity["built"],
            "population_built": float(population[year]), "pv_capacity_gw": pv_capacity,
            "pv_footprint": PV_FOOTPRINT * pv_capacity, "wind_capacity_gw": wind_capacity,
            "wind_footprint": WIND_FOOTPRINT * wind_capacity, "expected_built": expected_built,
            "dynamic_built_error": dynamic_error, "cluster_total": cluster_total, "built_cluster_activity": built_cluster,
        })
    csv_path = CASE / "documentation" / f"land_account_{run_name.lower()}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return {
        "status": "pass", "solver_status": status, "objective": optimization["objective"],
        "solve_seconds": optimization["elapsed_seconds"], "maximum_land_identity_error": max_land_error,
        "maximum_dynamic_built_error": max_dynamic_error, "maximum_inactive_mode_activity": max_inactive,
        "built_monotonic": True, "land_account_csv": str(csv_path),
        "selected_years": {row["year"]: row for row in rows if row["year"] in {"2020", "2030", "2040", "2050", "2053"}},
    }


def main() -> int:
    report_path = CASE / "documentation" / "validation_v30.json"
    report: dict[str, Any] = {"case": "Philippines_v30", "status": "running", "runs": {}}
    try:
        preflight = read_json(CASE / "documentation" / "preflight_v30.json")
        if preflight["status"] != "pass" or "scenario_matrices" not in preflight["checks"]:
            raise AssertionError("full preflight did not pass")
        gen = read_json(CASE / "genData.json")
        names = {row["TechId"]: row["Tech"] for row in gen["osy-tech"]}
        population = find_row(read_json(CASE / "RYC.json")["AAD"][BASE], CommId="COM_phl_built_site_v30")
        for run in RUNS:
            report["runs"][run] = validate_run(run, names, population)
        solved = [item for item in report["runs"].values() if item["status"] == "pass"]
        report["status"] = "pass" if len(solved) == len(RUNS) else "partial"
        report["optimal_validated_runs"] = len(solved)
        report["interpretation"] = "Every optimal run passed exact land, dynamic built-footprint, crop-mode, and monotonic-built checks; non-optimal runs are reported without being treated as validated solutions."
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0 if solved else 1
    except Exception as error:
        report["status"] = "fail"
        report["error"] = str(error)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
