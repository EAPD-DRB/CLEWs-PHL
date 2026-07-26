#!/usr/bin/env python3
"""Validate the unforced Philippines v12 ENV_WATER diagnostic case."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import re
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable

import generate_environmental_water_diagnostic_case as generation
import report_environmental_accounting as accounting
import validate_environmental_land_case as land_validation


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = generation.DEFAULT_SOURCE
DEFAULT_CANDIDATE = generation.DEFAULT_TARGET
DEFAULT_COMPARE_SCRIPT = (
    REPO_ROOT.parent
    / "Model-tools"
    / "skills"
    / "add-environmental-accounting"
    / "scripts"
    / "compare_muio_results.py"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "Philippines_v12_CLEWs_build"
    / "diagnostics"
    / "environmental_accounting"
)
RUNS = ("Base_v12", "PEP_v12")
RESULT_TOLERANCE = 0.005
OBJECTIVE_TOLERANCE = 0.005
RELATIVE_TOLERANCE = 1e-8


class ValidationError(RuntimeError):
    """Raised when the diagnostic case or its evidence is invalid."""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValidationError(f"Missing result CSV: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValidationError(f"Missing CSV header: {path}")
        rows = list(reader)
    return rows


def load_compare_module(path: Path) -> ModuleType:
    if not path.is_file():
        raise ValidationError(f"Missing comparison script: {path}")
    specification = importlib.util.spec_from_file_location(
        "environmental_water_diagnostic_compare", path
    )
    if specification is None or specification.loader is None:
        raise ValidationError(f"Cannot load comparison script: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def compare_results(
    module: ModuleType,
    baseline: Path,
    candidate: Path,
) -> dict[str, Any]:
    return module.compare(
        baseline,
        candidate,
        [("t", generation.ENV_WATER_TECH_NAME)],
        [],
        RESULT_TOLERANCE,
        RELATIVE_TOLERANCE,
        {},
        re.compile(r"^Optimal - objective value "),
        set(),
    )


def comparison_summary(report: dict[str, Any]) -> dict[str, Any]:
    case = report["cases"]["."]
    changed = {
        name: details
        for name, details in case["variables"].items()
        if details["status"] != "same"
    }
    return {
        "baseline_solver": case["baseline_solver"],
        "candidate_solver": case["candidate_solver"],
        "missing_files": case["missing_files"],
        "changed_variable_count": len(changed),
        "changed_variables": sorted(changed),
        "changes": changed,
    }


def invariant_results_pass(
    report: dict[str, Any],
) -> tuple[bool, dict[str, str]]:
    required = (
        "ObjectiveValue",
        "Demand",
        "AnnualTechnologyEmission",
        "AnnualTechnologyEmissionByMode",
        "AnnualFixedOperatingCost",
        "AnnualVariableOperatingCost",
        "AnnualizedInvestmentCost",
        "CapitalInvestment",
        "TechnologyEmissionsPenalty",
        "SalvageValue",
    )
    variables = report["cases"]["."]["variables"]
    missing = [name for name in required if name not in variables]
    if missing:
        return False, {name: "missing" for name in missing}
    statuses = {name: variables[name]["status"] for name in required}
    return all(status == "same" for status in statuses.values()), statuses


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    detail: Any,
) -> None:
    checks.append(
        {
            "name": name,
            "status": "PASS" if passed else "FAIL",
            "detail": detail,
        }
    )


def write_csv(
    path: Path,
    fieldnames: list[str],
    rows: Iterable[dict[str, Any]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def terminal_capacity_usage(
    result_root: Path,
    annual_upper: float,
) -> dict[str, Any]:
    rows = read_csv(result_root / "csv" / "TotalAnnualTechnologyActivityByMode.csv")
    annual: dict[str, float] = defaultdict(float)
    for row in rows:
        if row["t"] != generation.ENV_WATER_TECH_NAME:
            continue
        value = float(row["TotalAnnualTechnologyActivityByMode"])
        if not math.isfinite(value):
            raise ValidationError(f"Non-finite ENV_WATER activity: {row}")
        annual[row["y"]] += value
    maximum = max(annual.values(), default=0.0)
    return {
        "maximum_terminal_activity": maximum,
        "annual_terminal_activity_upper_bound": annual_upper,
        "headroom": annual_upper - maximum,
        "nonbinding": maximum < annual_upper - RESULT_TOLERANCE,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--compare-script", type=Path, default=DEFAULT_COMPARE_SCRIPT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    source = args.source.resolve()
    candidate = args.candidate.resolve()
    for path in (source, candidate):
        if not path.is_dir():
            raise ValidationError(f"Model directory does not exist: {path}")

    audit = generation.audit_source(source)
    generated = {
        path.name: generation.land.read_json(path)
        for path in sorted(candidate.glob("*.json"))
    }
    structural = generation.validate_generated_data(
        source, generated, audit
    )
    checks: list[dict[str, Any]] = []
    add_check(checks, "generated_structure", True, structural)

    generation_record_path = candidate / "documentation" / "generation.json"
    if not generation_record_path.is_file():
        raise ValidationError(
            f"Missing diagnostic generation record: {generation_record_path}"
        )
    generation_record = generation.land.read_json(generation_record_path)
    current_source_manifest = generation.land.manifest(source)
    recorded_source_manifest = generation_record.get("source_manifest")
    add_check(
        checks,
        "source_manifest",
        recorded_source_manifest == current_source_manifest,
        {
            "recorded_digest": generation_record.get("source_manifest_digest"),
            "current_digest": generation.land.manifest_digest(
                current_source_manifest
            ),
            "file_count": len(current_source_manifest),
        },
    )

    compare_module = load_compare_module(args.compare_script.resolve())
    regression_reports: dict[str, dict[str, Any]] = {}
    run_summaries: dict[str, dict[str, Any]] = {}
    reconciliation_rows: list[dict[str, Any]] = []
    years = audit["years"]

    for run in RUNS:
        baseline_root = source / "res" / run
        candidate_root = candidate / "res" / run
        baseline_solver = land_validation.parse_optimal(
            baseline_root / "results.txt"
        )
        candidate_solver = land_validation.parse_optimal(
            candidate_root / "results.txt"
        )
        add_check(
            checks,
            f"{run}_optimal",
            True,
            {
                "baseline": baseline_solver,
                "candidate": candidate_solver,
            },
        )

        candidate_activity = land_validation.activity_index(candidate_root)
        terminal_modes = {
            mode
            for technology, mode, _year in candidate_activity
            if technology == generation.ENV_WATER_TECH_NAME
        }
        add_check(
            checks,
            f"{run}_water_terminal_modes",
            terminal_modes == {1, 2, 3},
            sorted(terminal_modes),
        )

        _, _, run_reconciliation, report_validation = (
            accounting.build_run_accounts(
                candidate,
                run,
                generated["genData.json"],
                has_env_land=True,
                has_env_water=True,
            )
        )
        reconciliation_rows.extend(run_reconciliation)
        status_counts: dict[str, int] = defaultdict(int)
        for row in run_reconciliation:
            status_counts[row["status"]] += 1
        invalid = status_counts.get("INVALID", 0)
        add_check(
            checks,
            f"{run}_water_terminal_reconciliation_valid",
            invalid == 0,
            {
                "row_count": len(run_reconciliation),
                "status_counts": dict(sorted(status_counts.items())),
                "minimum_coverage_percent": report_validation[
                    "water_terminal_minimum_coverage_percent"
                ],
                "maximum_unaccounted_gap": report_validation[
                    "water_terminal_maximum_unaccounted_gap"
                ],
            },
        )

        land_terminal = land_validation.terminal_land_accounts(
            candidate_activity, years
        )
        expected_land = land_validation.expected_land_accounts(
            candidate_activity, years
        )
        land_difference, land_key = land_validation.max_difference(
            land_terminal, expected_land
        )
        add_check(
            checks,
            f"{run}_land_terminal_still_exact",
            land_difference <= RESULT_TOLERANCE,
            {
                "maximum_difference": land_difference,
                "maximum_key": land_key,
                "tolerance": RESULT_TOLERANCE,
            },
        )
        maximum_udc = land_validation.udc_closure(candidate_root)
        add_check(
            checks,
            f"{run}_land_udc_still_exact",
            maximum_udc <= 1e-8,
            {
                "maximum_absolute_value": maximum_udc,
                "tolerance": 1e-8,
            },
        )

        capacity = terminal_capacity_usage(
            candidate_root,
            structural["annual_terminal_activity_upper_bound"],
        )
        add_check(
            checks,
            f"{run}_water_terminal_capacity_nonbinding",
            capacity["nonbinding"],
            capacity,
        )

        regression = compare_results(
            compare_module, baseline_root, candidate_root
        )
        regression_reports[run] = regression
        invariants_pass, invariant_statuses = invariant_results_pass(regression)
        add_check(
            checks,
            f"{run}_regression_invariants",
            invariants_pass,
            invariant_statuses,
        )
        objective_difference = abs(
            candidate_solver["objective"] - baseline_solver["objective"]
        )
        add_check(
            checks,
            f"{run}_objective",
            objective_difference <= OBJECTIVE_TOLERANCE,
            {
                "difference": objective_difference,
                "tolerance": OBJECTIVE_TOLERANCE,
            },
        )

        run_summaries[run] = {
            "baseline_solver": baseline_solver,
            "candidate_solver": candidate_solver,
            "water_terminal_reconciliation_status_counts": dict(
                sorted(status_counts.items())
            ),
            "minimum_water_terminal_coverage_percent": report_validation[
                "water_terminal_minimum_coverage_percent"
            ],
            "maximum_unaccounted_water_gap": report_validation[
                "water_terminal_maximum_unaccounted_gap"
            ],
            "land_terminal_maximum_difference": land_difference,
            "land_udc_maximum_absolute_value": maximum_udc,
            "water_terminal_capacity": capacity,
            "regression": comparison_summary(regression),
        }

    failed = [row["name"] for row in checks if row["status"] != "PASS"]
    validation = {
        "status": "PASS" if not failed else "FAIL",
        "failed_checks": failed,
        "source": str(source),
        "candidate": str(candidate),
        "comparison_script": str(args.compare_script.resolve()),
        "diagnostic_interpretation": (
            "FULL, PARTIAL, ZERO, and EMPTY are empirical solver outcomes; "
            "only INVALID is a reconciliation failure. The external reference "
            "remains authoritative even when every row is FULL."
        ),
        "checks": checks,
        "runs": run_summaries,
        "source_manifest": current_source_manifest,
    }

    destination = args.output_root.resolve() / args.label
    if destination.exists():
        raise ValidationError(f"Evidence destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix=f".{args.label}.stage.", dir=destination.parent)
    )
    try:
        write_csv(
            stage / "water_terminal_reconciliation.csv",
            [
                "run",
                "region",
                "year",
                "mode",
                "account",
                "commodity",
                "unit",
                "reference_available",
                "terminal_counted",
                "unaccounted_gap",
                "coverage_percent",
                "status",
            ],
            reconciliation_rows,
        )
        write_json(stage / "validation.json", validation)
        for run, report in regression_reports.items():
            write_json(stage / f"regression_{run}.json", report)
        write_json(
            stage / "summary.json",
            {
                "status": validation["status"],
                "check_count": len(checks),
                "failed_checks": failed,
                "reconciliation_row_count": len(reconciliation_rows),
                "runs": run_summaries,
            },
        )
        stage.rename(destination)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise

    print(
        json.dumps(
            {
                "status": validation["status"],
                "evidence": str(destination),
                "check_count": len(checks),
                "failed_checks": failed,
                "reconciliation_row_count": len(reconciliation_rows),
            },
            indent=2,
        )
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
