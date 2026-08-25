#!/usr/bin/env python3
"""Static equation, source-diff and provenance gates for the v18 envelopes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path


BASE = "SC_0"
FIRST_YEAR = 2026
LAST_YEAR = 2053
PREFIXES = ("PHL_POW_PP_", "PHL_POW_GEO_OLD", "PHL_POW_CHP_")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    control = args.control.resolve()
    candidate = args.candidate.resolve()
    package = args.package.resolve()
    checks = []

    def check(name: str, condition: bool, detail) -> None:
        checks.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})

    control_hash = {p.name: sha256(p) for p in sorted(control.glob("*.json"))}
    candidate_hash = {p.name: sha256(p) for p in sorted(candidate.glob("*.json"))}
    changed_files = sorted(name for name in control_hash if control_hash[name] != candidate_hash[name])
    check("source_file_allowlist", changed_files == ["RYT.json"], changed_files)

    c = read_json(control / "RYT.json")
    n = read_json(candidate / "RYT.json")
    gen = read_json(candidate / "genData.json")
    names = {row["TechId"]: row["Tech"] for row in gen["osy-tech"]}
    snapshot = read_json(package / "data_sources" / "snapshots" / "deployment_envelopes_v18_2026-08-13.json")
    expected = {(row["technology_id"], str(row["year"])): row for row in snapshot["calculations"]}
    target_ids = {tid for tid, unused_year in expected}
    c_base = {row["TechId"]: row for row in c["TAMaxCI"][BASE]}
    n_base = {row["TechId"]: row for row in n["TAMaxCI"][BASE]}

    historical_diffs = []
    for tid in target_ids:
        for year in range(2020, FIRST_YEAR):
            if c_base[tid][str(year)] != n_base[tid][str(year)]:
                historical_diffs.append([names[tid], year, c_base[tid][str(year)], n_base[tid][str(year)]])
    check("target_cells_2020_2025_unchanged", not historical_diffs, historical_diffs[:10])

    unexpected_cells = []
    expected_cells = set(expected)
    for c_row in c["TAMaxCI"][BASE]:
        n_row = n_base[c_row["TechId"]]
        for year in range(2020, LAST_YEAR + 1):
            key = (c_row["TechId"], str(year))
            if c_row[str(year)] != n_row[str(year)] and key not in expected_cells:
                unexpected_cells.append([names[c_row["TechId"]], year])
    check("tamaxci_cell_allowlist", not unexpected_cells, unexpected_cells[:10])

    other_parameter_diffs = []
    for parameter in c:
        if parameter != "TAMaxCI" and c[parameter] != n[parameter]:
            other_parameter_diffs.append(parameter)
    check("only_tamaxci_parameter_changed", not other_parameter_diffs, other_parameter_diffs)
    check("scenario_overrides_unchanged", all(c["TAMaxCI"][sc] == n["TAMaxCI"][sc] for sc in c["TAMaxCI"] if sc != BASE), sorted(sc for sc in c["TAMaxCI"] if sc != BASE))

    formula_errors = []
    for key, record in expected.items():
        tid, year = key
        actual = Decimal(str(n_base[tid][year]))
        calculated = (
            Decimal(str(record["existing_committed_allowance_gw"]))
            if Decimal(str(record["existing_committed_allowance_gw"])) >= Decimal(str(record["expansion_envelope_gw"]))
            else Decimal(str(record["expansion_envelope_gw"]))
        ) + Decimal(str(record["residual_retirement_allowance_gw"])) + Decimal(str(record["recycled_allowance_gw"]))
        if actual != calculated or actual < 0:
            formula_errors.append([names[tid], year, str(actual), str(calculated)])
    check("annual_formula_and_nonnegative", not formula_errors, formula_errors[:10])

    calc_rows = rows(package / "data_sources" / "CALCULATIONS.csv")
    map_rows = rows(package / "data_sources" / "MODEL_MAP.csv")
    calc_ids = {row["calculation_id"] for row in calc_rows}
    map_ids = {row["map_id"] for row in map_rows}
    missing_calc = []
    missing_map = []
    for tid, year in expected:
        suffix = f"{names[tid].removeprefix('PHL_POW_')}_{year}"
        if f"CALC_PHL_V18_TAMAXCI_{suffix}" not in calc_ids:
            missing_calc.append(suffix)
        if f"MAP_PHL_V18_TAMAXCI_{suffix}" not in map_ids:
            missing_map.append(suffix)
    check("annual_calculation_coverage", not missing_calc and len(expected) == 476, {"expected_cells": len(expected), "missing": missing_calc[:10]})
    check("annual_model_map_coverage", not missing_map and len(expected) == 476, {"expected_cells": len(expected), "missing": missing_map[:10]})

    model_text = (package / "data_sources" / "snapshots" / "model.v.5.4.txt").read_text(encoding="utf-8")
    equation_ok = "NewCapacity[r,t,y] <= TotalAnnualMaxCapacityInvestment[r,t,y]" in model_text
    check("active_ncc1_equation", equation_ok, "NCC1 upper bound on NewCapacity")
    check("no_minimum_share_or_activity_change", c["TAMinCI"] == n["TAMinCI"] and c["TAMinC"] == n["TAMinC"] and c["TAL"] == n["TAL"] and c["TAU"] == n["TAU"], "TAMinCI, TAMinC, TAL and TAU unchanged")

    physical_roles = snapshot["technology_roles"]
    classified = set(physical_roles["expansion_capable_physical_generation"]) | set(physical_roles["combined_existing_field_repowering_and_greenfield"]) | set(physical_roles["inherited_physical_stock_only"])
    check("technology_role_coverage", classified == {names[tid] for tid in target_ids}, {"classified": len(classified), "targeted": len(target_ids)})

    replacement_errors = []
    for record in snapshot["calculations"]:
        if Decimal(str(record["after_tamaxci_gw"])) < Decimal(str(record["residual_retirement_allowance_gw"])) + Decimal(str(record["recycled_allowance_gw"])):
            replacement_errors.append([record["technology"], record["year"]])
    check("full_horizon_replacement_allowance", not replacement_errors, replacement_errors[:10])

    report = {
        "schema": "philippines-v18-deployment-envelope-static-validation-v1",
        "control": str(control), "candidate": str(candidate),
        "status": "pass" if all(item["status"] == "pass" for item in checks) else "fail",
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
