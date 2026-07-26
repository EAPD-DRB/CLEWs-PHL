#!/usr/bin/env python3
"""Validate the derived Philippines v12 ENV_LAND case and write evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
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

import generate_environmental_land_case as generation


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = REPO_ROOT / "WebAPP" / "DataStorage" / "Philippines_v12"
DEFAULT_CANDIDATE = (
    REPO_ROOT / "WebAPP" / "DataStorage" / generation.TARGET_CASE_NAME
)
DEFAULT_CONTROL = (
    REPO_ROOT
    / "WebAPP"
    / "DataStorage"
    / "Philippines_v12_ENV_LAND_Control_20260725"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "Philippines_v12_CLEWs_build"
    / "diagnostics"
    / "environmental_accounting"
)
DEFAULT_COMPARE_SCRIPT = (
    REPO_ROOT.parent
    / "Model-tools"
    / "skills"
    / "add-environmental-accounting"
    / "scripts"
    / "compare_muio_results.py"
)
RUNS = ("Base_v12", "PEP_v12")
RESULT_TOLERANCE = 0.005
FLOW_TOLERANCE = 0.05
OBJECTIVE_TOLERANCE = 0.005
RELATIVE_TOLERANCE = 1e-8

ACCOUNT_DICTIONARY = (
    {
        "mode": 1,
        "account": "forest",
        "interpretation": "Model-defined forest land state",
    },
    {
        "mode": 2,
        "account": "grassland",
        "interpretation": "Model-defined grassland state",
    },
    {
        "mode": 3,
        "account": "other_land",
        "interpretation": "Model-defined other land; no forest suitability implied",
    },
    {
        "mode": 4,
        "account": "barren_or_savannah",
        "interpretation": "Model-defined barren or savannah land state",
    },
    {
        "mode": 5,
        "account": "built_up_land",
        "interpretation": "Model-defined built-up land state",
    },
    {
        "mode": 6,
        "account": "inland_water_bodies",
        "interpretation": "Land-cover area classified as inland water bodies",
    },
    {
        "mode": 7,
        "account": "cropland",
        "interpretation": "Sum of the 24 modeled crop-land options",
    },
    {
        "mode": 8,
        "account": "unallocated_modeled_land",
        "interpretation": "Modeled PHL_LND supply not allocated to modes 1-7",
    },
)


class ValidationError(RuntimeError):
    """Raised when the generated case or its results fail validation."""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValidationError(f"Missing result CSV: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_optimal(result_path: Path) -> dict[str, Any]:
    if not result_path.is_file():
        raise ValidationError(f"Missing solver result: {result_path}")
    first_line = result_path.open(
        encoding="utf-8-sig", errors="replace"
    ).readline().strip()
    match = re.fullmatch(
        r"Optimal - objective value "
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)",
        first_line,
    )
    if match is None:
        raise ValidationError(f"Non-optimal solver status: {first_line!r}")
    return {"status": "Optimal", "objective": float(match.group(1))}


def aggregate(
    rows: Iterable[dict[str, str]],
    value_column: str,
    key_columns: tuple[str, ...],
    predicate: Any | None = None,
) -> dict[tuple[str, ...], float]:
    result: dict[tuple[str, ...], float] = defaultdict(float)
    for row in rows:
        if predicate is not None and not predicate(row):
            continue
        value = float(row[value_column])
        if not math.isfinite(value):
            raise ValidationError(f"Non-finite result row: {row}")
        result[tuple(row[column] for column in key_columns)] += value
    return dict(result)


def activity_index(result_root: Path) -> dict[tuple[str, int, str], float]:
    rows = read_csv(result_root / "csv" / "TotalAnnualTechnologyActivityByMode.csv")
    index: dict[tuple[str, int, str], float] = {}
    for row in rows:
        key = (row["t"], int(row["m"]), row["y"])
        if key in index:
            raise ValidationError(f"Duplicate activity key: {key}")
        value = float(row["TotalAnnualTechnologyActivityByMode"])
        if not math.isfinite(value):
            raise ValidationError(f"Non-finite activity: {row}")
        index[key] = value
    return index


def expected_land_accounts(
    activity: dict[tuple[str, int, str], float],
    years: list[str],
) -> dict[tuple[int, str], float]:
    result: dict[tuple[int, str], float] = {}
    represented_technologies: list[str] = []
    for category in generation.LAND_CATEGORIES:
        represented_technologies.extend(category["technologies"])
        for year in years:
            result[(category["mode"], year)] = sum(
                activity.get((technology, 1, year), 0.0)
                for technology in category["technologies"]
            )
    for year in years:
        supply = activity.get((generation.LAND_SUPPLY_TECH, 1, year), 0.0)
        represented = sum(
            activity.get((technology, 1, year), 0.0)
            for technology in represented_technologies
        )
        result[(8, year)] = supply - represented
    return result


def terminal_land_accounts(
    activity: dict[tuple[str, int, str], float],
    years: list[str],
) -> dict[tuple[int, str], float]:
    return {
        (mode, year): activity.get((generation.ENV_TECH_NAME, mode, year), 0.0)
        for mode in range(1, 9)
        for year in years
    }


def max_difference(
    left: dict[tuple[Any, ...], float],
    right: dict[tuple[Any, ...], float],
) -> tuple[float, tuple[Any, ...] | None]:
    keys = set(left) | set(right)
    maximum = 0.0
    maximum_key: tuple[Any, ...] | None = None
    for key in keys:
        difference = abs(left.get(key, 0.0) - right.get(key, 0.0))
        if difference > maximum:
            maximum = difference
            maximum_key = key
    return maximum, maximum_key


def load_compare_module(path: Path) -> ModuleType:
    if not path.is_file():
        raise ValidationError(f"Missing comparison script: {path}")
    specification = importlib.util.spec_from_file_location(
        "environmental_accounting_compare", path
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
    exclusions = [
        ("t", generation.ENV_TECH_NAME),
        ("cn", generation.ENV_CONSTRAINT_NAME),
        *(
            ("f", category["commodity"])
            for category in generation.LAND_CATEGORIES
        ),
    ]
    return module.compare(
        baseline,
        candidate,
        exclusions,
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


def invariant_results_pass(report: dict[str, Any]) -> tuple[bool, dict[str, str]]:
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
    statuses = {name: variables[name]["status"] for name in required}
    return all(status == "same" for status in statuses.values()), statuses


def stock_flow_closure(
    result_root: Path,
    terminal: dict[tuple[int, str], float],
) -> dict[str, Any]:
    production = read_csv(result_root / "csv" / "ProductionByTechnologyByMode.csv")
    use = read_csv(result_root / "csv" / "UseByTechnologyByMode.csv")
    production_index = aggregate(
        production,
        "ProductionByTechnologyByMode",
        ("f", "y"),
        lambda row: row["f"].startswith("ENV_LND_"),
    )
    use_index = aggregate(
        use,
        "UseByTechnologyByMode",
        ("f", "y"),
        lambda row: row["f"].startswith("ENV_LND_"),
    )
    maximum_production_use = 0.0
    maximum_flow_terminal = 0.0
    maximum_key: tuple[Any, ...] | None = None
    for category in generation.LAND_CATEGORIES:
        commodity = category["commodity"]
        mode = category["mode"]
        for _mode, year in sorted(terminal):
            if _mode != mode:
                continue
            produced = production_index.get((commodity, year), 0.0)
            consumed = use_index.get((commodity, year), 0.0)
            terminal_value = terminal[(mode, year)]
            production_use = abs(produced - consumed)
            flow_terminal = max(
                abs(produced - terminal_value),
                abs(consumed - terminal_value),
            )
            if max(production_use, flow_terminal) > max(
                maximum_production_use, maximum_flow_terminal
            ):
                maximum_key = (commodity, year)
            maximum_production_use = max(
                maximum_production_use, production_use
            )
            maximum_flow_terminal = max(maximum_flow_terminal, flow_terminal)
    return {
        "maximum_production_use_difference": maximum_production_use,
        "maximum_flow_terminal_difference": maximum_flow_terminal,
        "maximum_key": maximum_key,
        "tolerance": FLOW_TOLERANCE,
    }


def udc_closure(result_root: Path) -> float:
    rows = read_csv(
        result_root / "csv" / "UDC2_UserDefinedConstraintEquality.csv"
    )
    values = [
        abs(float(row["UDC2_UserDefinedConstraintEquality"]))
        for row in rows
        if row["cn"] == generation.ENV_CONSTRAINT_NAME
    ]
    if len(values) != 34:
        raise ValidationError(
            f"Expected 34 BAL_ENV_LAND result rows, found {len(values)}"
        )
    return max(values, default=0.0)


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--control", type=Path, default=DEFAULT_CONTROL)
    parser.add_argument("--compare-script", type=Path, default=DEFAULT_COMPARE_SCRIPT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    source = args.source.resolve()
    candidate = args.candidate.resolve()
    control = args.control.resolve()
    for path in (source, candidate, control):
        if not path.is_dir():
            raise ValidationError(f"Model directory does not exist: {path}")

    audit = generation.audit_source(source)
    generated = {
        path.name: generation.read_json(path)
        for path in sorted(candidate.glob("*.json"))
    }
    structural = generation.validate_generated_data(source, generated, audit)
    source_manifest = generation.manifest(source)
    control_manifest = generation.manifest(control)
    checks: list[dict[str, Any]] = []
    add_check(
        checks,
        "unchanged_control_source",
        source_manifest == control_manifest,
        {
            "source_digest": generation.manifest_digest(source_manifest),
            "control_digest": generation.manifest_digest(control_manifest),
        },
    )
    add_check(checks, "generated_structure", True, structural)

    compare_module = load_compare_module(args.compare_script)
    account_rows: list[dict[str, Any]] = []
    regression_reports: dict[str, dict[str, Any]] = {}
    run_summaries: dict[str, dict[str, Any]] = {}
    years = audit["years"]

    for run in RUNS:
        candidate_root = candidate / "res" / run
        control_root = control / "res" / run
        candidate_solver = parse_optimal(candidate_root / "results.txt")
        control_solver = parse_optimal(control_root / "results.txt")
        add_check(
            checks,
            f"{run}_optimal",
            True,
            {
                "candidate": candidate_solver,
                "control": control_solver,
            },
        )

        candidate_activity = activity_index(candidate_root)
        control_activity = activity_index(control_root)
        terminal = terminal_land_accounts(candidate_activity, years)
        expected_candidate = expected_land_accounts(candidate_activity, years)
        expected_control = expected_land_accounts(control_activity, years)

        terminal_modes = {
            mode
            for technology, mode, _year in candidate_activity
            if technology == generation.ENV_TECH_NAME
        }
        add_check(
            checks,
            f"{run}_terminal_modes",
            terminal_modes == set(range(1, 9)),
            sorted(terminal_modes),
        )

        candidate_difference, candidate_key = max_difference(
            terminal, expected_candidate
        )
        add_check(
            checks,
            f"{run}_terminal_source_reconciliation",
            candidate_difference <= RESULT_TOLERANCE,
            {
                "maximum_difference": candidate_difference,
                "maximum_key": candidate_key,
                "tolerance": RESULT_TOLERANCE,
            },
        )

        control_difference, control_key = max_difference(
            terminal, expected_control
        )
        add_check(
            checks,
            f"{run}_control_land_non_interference",
            control_difference <= RESULT_TOLERANCE,
            {
                "maximum_difference": control_difference,
                "maximum_key": control_key,
                "tolerance": RESULT_TOLERANCE,
            },
        )

        stock = stock_flow_closure(candidate_root, terminal)
        add_check(
            checks,
            f"{run}_parallel_stock_closure",
            stock["maximum_production_use_difference"] <= FLOW_TOLERANCE
            and stock["maximum_flow_terminal_difference"] <= FLOW_TOLERANCE,
            stock,
        )

        maximum_aggregate = 0.0
        for year in years:
            terminal_total = sum(terminal[(mode, year)] for mode in range(1, 9))
            supply = candidate_activity.get(
                (generation.LAND_SUPPLY_TECH, 1, year), 0.0
            )
            maximum_aggregate = max(
                maximum_aggregate, abs(terminal_total - supply)
            )
        add_check(
            checks,
            f"{run}_aggregate_land_closure",
            maximum_aggregate <= RESULT_TOLERANCE,
            {
                "maximum_difference": maximum_aggregate,
                "tolerance": RESULT_TOLERANCE,
            },
        )

        maximum_udc = udc_closure(candidate_root)
        add_check(
            checks,
            f"{run}_udc_result",
            maximum_udc <= 1e-8,
            {"maximum_absolute_value": maximum_udc, "tolerance": 1e-8},
        )

        maximum_terminal_activity = max(
            sum(terminal[(mode, year)] for mode in range(1, 9))
            for year in years
        )
        add_check(
            checks,
            f"{run}_terminal_capacity_nonbinding",
            maximum_terminal_activity
            < structural["annual_terminal_activity_upper_bound"],
            {
                "maximum_activity": maximum_terminal_activity,
                "annual_upper_bound": structural[
                    "annual_terminal_activity_upper_bound"
                ],
            },
        )

        regression = compare_results(compare_module, control_root, candidate_root)
        regression_reports[run] = regression
        invariants_pass, invariant_statuses = invariant_results_pass(regression)
        add_check(
            checks,
            f"{run}_regression_invariants",
            invariants_pass,
            invariant_statuses,
        )
        objective_difference = abs(
            candidate_solver["objective"] - control_solver["objective"]
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

        source_data = source / "res" / run / "data.txt"
        control_data = control_root / "data.txt"
        add_check(
            checks,
            f"{run}_control_data_hash",
            source_data.is_file()
            and control_data.is_file()
            and sha256(source_data) == sha256(control_data),
            {
                "saved_source": sha256(source_data)
                if source_data.is_file()
                else None,
                "fresh_control": sha256(control_data)
                if control_data.is_file()
                else None,
            },
        )

        for entry in ACCOUNT_DICTIONARY:
            for year in years:
                account_rows.append(
                    {
                        "run": run,
                        "region": "RE1",
                        "year": year,
                        "technology": generation.ENV_TECH_NAME,
                        "mode": entry["mode"],
                        "account": entry["account"],
                        "value": terminal[(entry["mode"], year)],
                        "unit": generation.LAND_UNIT,
                    }
                )
        run_summaries[run] = {
            "candidate_solver": candidate_solver,
            "control_solver": control_solver,
            "terminal_source_maximum_difference": candidate_difference,
            "control_land_maximum_difference": control_difference,
            "parallel_stock_closure": stock,
            "aggregate_closure_maximum_difference": maximum_aggregate,
            "udc_maximum_absolute_value": maximum_udc,
            "maximum_terminal_activity": maximum_terminal_activity,
            "regression": comparison_summary(regression),
        }

    add_check(
        checks,
        "unsafe_water_terminal_absent",
        not any(
            row["Tech"] == "ENV_WATER"
            for row in generated["genData.json"]["osy-tech"]
        ),
        "Water accounts remain reporting-only because the water proof fails.",
    )
    failed = [check["name"] for check in checks if check["status"] != "PASS"]
    validation = {
        "status": "PASS" if not failed else "FAIL",
        "failed_checks": failed,
        "source": str(source),
        "candidate": str(candidate),
        "control": str(control),
        "comparison_script": str(args.compare_script.resolve()),
        "checks": checks,
        "runs": run_summaries,
        "source_manifest": source_manifest,
        "control_manifest": control_manifest,
    }

    destination = args.output_root.resolve() / args.label
    if destination.exists():
        raise ValidationError(f"Evidence destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(
            prefix=f".{args.label}.stage.", dir=destination.parent
        )
    )
    try:
        write_csv(
            stage / "land_accounts.csv",
            [
                "run",
                "region",
                "year",
                "technology",
                "mode",
                "account",
                "value",
                "unit",
            ],
            account_rows,
        )
        write_csv(
            stage / "land_account_dictionary.csv",
            ["technology", "mode", "account", "unit", "interpretation"],
            (
                {
                    "technology": generation.ENV_TECH_NAME,
                    "mode": entry["mode"],
                    "account": entry["account"],
                    "unit": generation.LAND_UNIT,
                    "interpretation": entry["interpretation"],
                }
                for entry in ACCOUNT_DICTIONARY
            ),
        )
        write_json(stage / "validation.json", validation)
        for run, report in regression_reports.items():
            write_json(
                stage / f"regression_{run}.json",
                report,
            )
        write_json(
            stage / "summary.json",
            {
                "status": validation["status"],
                "check_count": len(checks),
                "failed_checks": failed,
                "account_row_count": len(account_rows),
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
                "account_row_count": len(account_rows),
            },
            indent=2,
        )
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
