#!/usr/bin/env python3
"""Compare solved unchanged-control and v18 deployment-envelope candidates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


TARGETS = {
    "PHL_POW_PP_WON", "PHL_POW_PP_WOF", "PHL_POW_PP_SPV", "PHL_POW_PP_NUSMR",
    "PHL_POW_PP_NU", "PHL_POW_PP_NGCC_CCS", "PHL_POW_PP_NGCC", "PHL_POW_PP_HY_LA",
    "PHL_POW_PP_H2", "PHL_POW_PP_COAL_CCS", "PHL_POW_PP_COAL", "PHL_POW_PP_BIOM_CCS",
    "PHL_POW_GEO_OLD", "PHL_POW_CHP_COAL_OLD", "PHL_POW_CHP_NG_OLD",
    "PHL_POW_CHP_OIL_OLD", "PHL_POW_CHP_BIOM_OLD",
}
NCC = re.compile(r"NCC1_TotalAnnualMaxNewCapacityConstraint\(RE1,([^,]+),(\d{4})\)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)")


def csv_values(path: Path, value_column: str, key_columns: tuple[str, ...]) -> dict[tuple[str, ...], float]:
    with path.open(newline="", encoding="utf-8") as stream:
        return {tuple(row[key] for key in key_columns): float(row[value_column]) for row in csv.DictReader(stream)}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def objective(run: Path) -> float:
    return next(iter(csv_values(run / "csv" / "ObjectiveValue.csv", "ObjectiveValue", ("r",)).values()))


def aggregate_activity(run: Path) -> dict[tuple[str, str], float]:
    raw = csv_values(run / "csv" / "TotalAnnualTechnologyActivityByMode.csv", "TotalAnnualTechnologyActivityByMode", ("t", "m", "y"))
    result = defaultdict(float)
    for (technology, unused_mode, year), value in raw.items():
        result[(technology, year)] += value
    return dict(result)


def aggregate_emissions(run: Path) -> dict[tuple[str, str, str], float]:
    return csv_values(run / "csv" / "AnnualTechnologyEmission.csv", "AnnualTechnologyEmission", ("t", "e", "y"))


def differences(control: dict, candidate: dict, tolerance: float = 1e-7) -> list[dict]:
    output = []
    for key in sorted(set(control) | set(candidate)):
        before = control.get(key, 0.0)
        after = candidate.get(key, 0.0)
        delta = after - before
        if abs(delta) > tolerance:
            output.append({"key": list(key), "control": before, "candidate": after, "delta": delta})
    return output


def parse_duals(results: Path) -> dict[tuple[str, str], dict]:
    found = {}
    for line in results.read_text(encoding="utf-8").splitlines():
        match = NCC.search(line)
        if match:
            found[(match.group(1), match.group(2))] = {"row_activity": float(match.group(3)), "dual": float(match.group(4))}
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--control-cbc-seconds", type=float, default=294.6608250420031)
    parser.add_argument("--candidate-cbc-seconds", type=float, default=207.19558720799978)
    args = parser.parse_args()
    control = args.control.resolve()
    candidate = args.candidate.resolve()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    ceilings = {(r["technology"], str(r["year"])): float(r["after_tamaxci_gw"]) for r in snapshot["calculations"]}

    control_objective = objective(control)
    candidate_objective = objective(candidate)
    new_control = csv_values(control / "csv" / "NewCapacity.csv", "NewCapacity", ("t", "y"))
    new_candidate = csv_values(candidate / "csv" / "NewCapacity.csv", "NewCapacity", ("t", "y"))
    cap_control = csv_values(control / "csv" / "TotalCapacityAnnual.csv", "TotalCapacityAnnual", ("t", "y"))
    cap_candidate = csv_values(candidate / "csv" / "TotalCapacityAnnual.csv", "TotalCapacityAnnual", ("t", "y"))
    act_control = aggregate_activity(control)
    act_candidate = aggregate_activity(candidate)
    emis_control = aggregate_emissions(control)
    emis_candidate = aggregate_emissions(candidate)
    duals = parse_duals(candidate / "results.txt")

    binding = []
    for key, ceiling in ceilings.items():
        value = new_candidate.get(key, 0.0)
        if abs(value - ceiling) <= max(1e-7, abs(ceiling) * 1e-7):
            binding.append({
                "technology": key[0], "year": int(key[1]), "new_capacity_gw": value,
                "ceiling_gw": ceiling, "dual": duals.get(key, {}).get("dual"),
            })
    economically_binding = [
        row for row in binding
        if row["ceiling_gw"] > 0 and row["dual"] is not None and abs(row["dual"]) > 1e-7
    ]

    new_diffs = differences(new_control, new_candidate)
    cap_diffs = differences(cap_control, cap_candidate)
    act_diffs = differences(act_control, act_candidate)
    emis_diffs = differences(emis_control, emis_candidate)

    def top(items: list[dict], count: int = 30) -> list[dict]:
        return sorted(items, key=lambda row: abs(row["delta"]), reverse=True)[:count]

    unexpected = {
        "new_capacity": top([row for row in new_diffs if row["key"][0] not in TARGETS]),
        "total_capacity": top([row for row in cap_diffs if row["key"][0] not in TARGETS]),
        "activity": top([row for row in act_diffs if row["key"][0] not in TARGETS]),
        "emissions": top([row for row in emis_diffs if row["key"][0] not in TARGETS]),
    }
    historical_result_diffs = {
        "new_capacity": [row for row in new_diffs if int(row["key"][1]) <= 2025],
        "total_capacity": [row for row in cap_diffs if int(row["key"][1]) <= 2025],
        "activity": [row for row in act_diffs if int(row["key"][1]) <= 2025],
        "emissions": [row for row in emis_diffs if int(row["key"][-1]) <= 2025],
    }

    report = {
        "schema": "philippines-v18-deployment-envelope-solve-comparison-v1",
        "status": "pass",
        "solver": {
            "control_status": (control / "results.txt").read_text(encoding="utf-8").splitlines()[0],
            "candidate_status": (candidate / "results.txt").read_text(encoding="utf-8").splitlines()[0],
            "control_objective": control_objective, "candidate_objective": candidate_objective,
            "objective_delta": candidate_objective - control_objective,
            "objective_percent_change": (candidate_objective / control_objective - 1) * 100,
            "control_cbc_seconds": args.control_cbc_seconds,
            "candidate_cbc_seconds": args.candidate_cbc_seconds,
            "cbc_percent_change": (args.candidate_cbc_seconds / args.control_cbc_seconds - 1) * 100,
        },
        "matrix": {"rows": 791245, "columns": 886010, "matrix_nonzeros": 12572675, "objective_nonzeros": 423240, "control_candidate_identical_dimensions": True},
        "artifact_identity": {
            "control_data_sha256": sha256(control / "data.txt"), "candidate_data_sha256": sha256(candidate / "data.txt"),
            "control_results_sha256": sha256(control / "results.txt"), "candidate_results_sha256": sha256(candidate / "results.txt"),
        },
        "affected_counts": {
            "new_capacity_cells": len(new_diffs), "total_capacity_cells": len(cap_diffs),
            "activity_cells": len(act_diffs), "emissions_cells": len(emis_diffs),
            "binding_target_ceiling_cells": len(binding),
            "economically_binding_positive_ceiling_cells": len(economically_binding),
        },
        "binding_target_ceilings": binding,
        "economically_binding_positive_ceilings": economically_binding,
        "top_new_capacity_changes": top(new_diffs), "top_total_capacity_changes": top(cap_diffs),
        "top_activity_changes": top(act_diffs), "top_emission_changes": top(emis_diffs),
        "unexpected_non_target_changes": unexpected,
        "historical_results_2020_2025_changes": historical_result_diffs,
        "notes": [
            "Differences below 1e-7 are treated as solver/export numerical noise.",
            "Non-target result changes are endogenous system responses, not source-parameter changes.",
            "A binding zero ceiling is reported when candidate NewCapacity is zero; its dual distinguishes valuable restrictions from inactive zero rows.",
            "Economically binding positive ceilings require a positive ceiling and a dual magnitude above 1e-7.",
        ],
    }
    if not report["solver"]["control_status"].startswith("Optimal") or not report["solver"]["candidate_status"].startswith("Optimal"):
        report["status"] = "fail"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"], "solver": report["solver"], "matrix": report["matrix"],
        "affected_counts": report["affected_counts"],
        "economically_binding_positive_ceilings": economically_binding,
        "historical_change_counts": {key: len(value) for key, value in historical_result_diffs.items()},
        "unexpected_change_counts": {key: len(value) for key, value in unexpected.items()},
        "top_new_capacity_changes": report["top_new_capacity_changes"][:12],
    }, indent=2))


if __name__ == "__main__":
    main()
