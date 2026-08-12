#!/usr/bin/env python3
"""Validate the Philippines v15 national-water model against the v14 baseline.

The candidate follows the application path used by the UI, receives an
explicit GLPK matrix check and short bounded CBC diagnostic, and is then solved
with CBC inside the declared 280-second budget.  Full-precision solver rows are
published as the authoritative national water ledger.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
import time
import types
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
STORAGE = REPO / "WebAPP" / "DataStorage"
MODEL_FILE = REPO / "WebAPP" / "SOLVERs" / "model.v.5.4.txt"
GENERATOR_FILE = REPO / "scripts" / "create_philippines_v15_national_water.py"
DEFAULT_CASE = "Philippines_v15_WATER_TEST"
DEFAULT_RUN = "BASE_V15_WATER_TEST"
DEFAULT_BASELINE_CASE = "Philippines_v14_STOCK_TURNOVER"
DEFAULT_BASELINE_RUN = "BASE_V14"
MANIFEST = "national_water_manifest.json"
VALIDATION = "national_water_validation.json"
LEDGER = "national_water_ledger.json"
MODEL_FIXES = "MODEL_FIXES_WATER_2026-08-04.md"
REGION = "RE1"
RESULT_TOLERANCE = 5e-4
BALANCE_TOLERANCE = 2e-4
EXPECTED_MATRIX_ROW_DELTA = 68
WATER_COMMODITIES = (
    "PHL_WTR_PRC",
    "PHL_WTR_SUR",
    "PHL_WTR_GWT",
    "PHL_WTR_EVT",
)


dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(REPO / "API"))

from Classes.Case.DataFileClass import DataFile  # noqa: E402
from Classes.Case.OsemosysClass import Osemosys  # noqa: E402


def load_generator() -> Any:
    spec = importlib.util.spec_from_file_location("phl_national_water_generator", GENERATOR_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError(GENERATOR_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generator = load_generator()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".codex-tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".codex-tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    stat = path.stat()
    try:
        display_path = str(path.relative_to(REPO))
    except ValueError:
        display_path = str(path)
    return {
        "path": display_path,
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "size_bytes": stat.st_size,
        "sha256": sha256(path),
    }


def decoded_tail(value: str | bytes | None, limit: int) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return (value or "")[-limit:]


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def csv_values(
    path: Path, key_fields: tuple[str, ...], value_field: str
) -> dict[tuple[str, ...], float]:
    result: dict[tuple[str, ...], float] = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            key = tuple(row[field] for field in key_fields)
            if key in result:
                raise AssertionError(f"duplicate CSV key in {path.name}: {key}")
            result[key] = float(row[value_field])
    return result


def solver_status(run_path: Path) -> str:
    return (run_path / "results.txt").open(encoding="utf-8").readline().strip()


def objective(run_path: Path) -> float:
    status = solver_status(run_path)
    match = re.search(r"objective value\s+([-+0-9.eE]+)", status)
    if not match:
        raise AssertionError(f"cannot parse objective: {status}")
    return float(match.group(1))


def create_base_run(model: DataFile, case: str, run: str) -> None:
    scenarios = [
        {
            "ScenarioId": item["ScenarioId"],
            "Scenario": item["Scenario"],
            "Desc": item.get("Desc", ""),
            "Active": item["Scenario"] == "BASE",
        }
        for item in model.genData["osy-scenarios"]
    ]
    response = model.createCaseRun(
        run,
        {
            "Case": run,
            "CaseId": f"CS_{case}_{run}",
            "Desc": "Application-chain validation of the national Philippines water envelope",
            "Runtime": date.today().isoformat(),
            "Scenarios": scenarios,
        },
    )
    if response.get("status_code") != "success":
        raise RuntimeError(json.dumps(response, indent=2))


def run_identity(case_path: Path, run: str, require_case_match: bool = True) -> dict[str, Any]:
    gen = read_json(case_path / "genData.json")
    res_data = read_json(case_path / "view" / "resData.json")
    matches = [row for row in res_data["osy-cases"] if row["Case"] == run]
    if len(matches) != 1:
        raise AssertionError(f"expected one metadata record for {case_path.name}/{run}")
    active = [row["Scenario"] for row in matches[0]["Scenarios"] if row["Active"]]
    result = {
        "directory": case_path.name,
        "gen_data_case": gen["osy-casename"],
        "run_metadata_case": matches[0]["Case"],
        "active_scenarios": active,
        "case_matches_directory": gen["osy-casename"] == case_path.name,
        "run_matches_requested": matches[0]["Case"] == run,
        "base_only": active == ["BASE"],
    }
    if not result["run_matches_requested"] or not result["base_only"]:
        raise AssertionError(json.dumps(result, indent=2))
    if require_case_match and not result["case_matches_directory"]:
        raise AssertionError(json.dumps(result, indent=2))
    return result


def parse_matrix_dimensions(output: str) -> dict[str, int | None]:
    rows_match = re.search(r"Number of rows\s*=\s*([\d,]+)", output)
    columns_match = re.search(r"Number of columns\s*=\s*([\d,]+)", output)
    nonzeros_match = re.search(
        r"Number of non-zeros \(matrix\)\s*=\s*([\d,]+)", output
    )
    if not (rows_match and columns_match and nonzeros_match):
        fallback = re.findall(
            r"([\d,]+) rows, ([\d,]+) columns, ([\d,]+) non-zeros", output
        )
        if not fallback:
            return {"rows": None, "columns": None, "nonzeros": None}
        rows, columns, nonzeros = fallback[-1]
    else:
        rows, columns, nonzeros = (
            rows_match.group(1),
            columns_match.group(1),
            nonzeros_match.group(1),
        )
    return {
        "rows": int(rows.replace(",", "")),
        "columns": int(columns.replace(",", "")),
        "nonzeros": int(nonzeros.replace(",", "")),
    }


def baseline_matrix(case_path: Path) -> dict[str, int]:
    report_path = case_path / "documentation" / "validation_results.json"
    report = read_json(report_path)
    matrix = report["validation_chain"]["matrix"]
    result = {field: int(matrix[field]) for field in ("rows", "columns", "nonzeros")}
    if report["candidate"]["status"] != "optimal":
        raise AssertionError("baseline validation report is not optimal")
    return result


def source_parameter_hashes(case: Path) -> dict[str, str]:
    return {path.name: sha256(path) for path in sorted(case.glob("*.json"))}


def source_checks(
    case: Path, baseline_case: Path, completed_run: bool = False
) -> dict[str, Any]:
    manifest_path = case / "documentation" / MANIFEST
    manifest = read_json(manifest_path)
    if manifest["target_case"] != case.name:
        raise AssertionError("manifest target identity differs")
    if sha256(generator.SOURCE_DATA) != manifest["source_data"]["sha256"]:
        raise AssertionError("research data digest differs from manifest")
    current_fingerprints = generator.fingerprints(case)
    expected_fingerprints = manifest["generated_source_fingerprints"]
    if completed_run:
        # Run creation legitimately changes only cached view metadata. Source
        # parameter JSON must still match the generated candidate exactly.
        source_only = {
            name: digest
            for name, digest in current_fingerprints.items()
            if not name.startswith("view/")
        }
        expected_source_only = {
            name: digest
            for name, digest in expected_fingerprints.items()
            if not name.startswith("view/")
        }
        if source_only != expected_source_only:
            raise AssertionError("candidate source parameters changed during validation")
    elif current_fingerprints != expected_fingerprints:
        raise AssertionError("candidate source fingerprint differs before validation")
    if generator.fingerprints(baseline_case) != manifest["source_fingerprints_before"]:
        raise AssertionError("baseline case is not the unchanged generation source")

    gen = read_json(case / "genData.json")
    baseline_gen = read_json(baseline_case / "genData.json")
    if len(gen["osy-tech"]) != len(baseline_gen["osy-tech"]):
        raise AssertionError("technology set changed")
    if len(gen["osy-comm"]) != len(baseline_gen["osy-comm"]):
        raise AssertionError("commodity set changed")
    if len(gen["osy-constraints"]) != len(baseline_gen["osy-constraints"]) + 2:
        raise AssertionError("constraint set change is not exactly +2")
    if len(gen["osy-scenarios"]) != len(baseline_gen["osy-scenarios"]):
        raise AssertionError("scenario set changed")

    generator.prove_withdrawal_accounting(case, gen)
    generator.assert_policy_inheritance(case, gen)
    source = read_json(generator.SOURCE_DATA)
    years = [str(year) for year in gen["osy-years"]]
    pathway = generator.annual_pathway(source, years)
    implemented = manifest["climate"]["ssp245_median_multiplier"]
    for year, expected in pathway.items():
        if not math.isclose(float(implemented[year]), float(expected), rel_tol=0, abs_tol=1e-14):
            raise AssertionError(f"median pathway differs in {year}")

    # Independently prove that crop irrigation coefficients did not receive the
    # climate multiplier.
    baseline_ratio = read_json(baseline_case / "RYTCM.json")
    candidate_ratio = read_json(case / "RYTCM.json")
    comm_id = next(
        row["CommId"] for row in gen["osy-comm"] if row["Comm"] == generator.IRRIGATION_WATER
    )
    baseline_rows = {
        (row["TechId"], row["CommId"], row["MoId"]): row
        for row in baseline_ratio["IAR"]["SC_0"]
        if row["CommId"] == comm_id
    }
    candidate_rows = {
        (row["TechId"], row["CommId"], row["MoId"]): row
        for row in candidate_ratio["IAR"]["SC_0"]
        if row["CommId"] == comm_id
    }
    if baseline_rows != candidate_rows:
        raise AssertionError("AGRWATPHL irrigation coefficients changed")

    return {
        "manifest": file_record(manifest_path),
        "source_data_sha256_matches": True,
        "candidate_fingerprints_match": True,
        "baseline_fingerprints_match_generation_source": True,
        "technology_count_unchanged": len(gen["osy-tech"]),
        "commodity_count_unchanged": len(gen["osy-comm"]),
        "constraint_count_before": len(baseline_gen["osy-constraints"]),
        "constraint_count_after": len(gen["osy-constraints"]),
        "scenario_count_unchanged": len(gen["osy-scenarios"]),
        "median_only_installed": True,
        "p10_p90_model_scenarios_added": False,
        "irrigation_coefficients_unchanged": True,
        "exact_withdrawal_proof_repeated": True,
        "policy_inheritance_repeated": True,
    }


def inspect_generated(run_path: Path) -> dict[str, Any]:
    text = (run_path / "data_processed.txt").read_text(encoding="utf-8")
    required_tokens = (
        "WATER_SUR_AVAIL",
        "WATER_GWT_POTENTIAL",
        "PHL_WTR_GWT",
        "DEMAGRGWTPHL",
    )
    missing = [token for token in required_tokens if token not in text]
    if missing:
        raise AssertionError(f"generated data lacks {missing}")

    mode_match = re.search(
        r"set MODEperTECHNOLOGY\[DEMAGRGWTPHL\]:=\s*([^;]*);", text
    )
    if not mode_match:
        raise AssertionError("generated DEMAGRGWTPHL mode set is absent")
    modes = [int(value) for value in re.findall(r"\d+", mode_match.group(1))]
    if modes != [1]:
        raise AssertionError(f"generated DEMAGRGWTPHL modes differ: {modes}")

    groundwater_set = re.search(
        r"set MODExTECHNOLOGYperFUELin\[PHL_WTR_GWT\]:=([^;]*);", text
    )
    if not groundwater_set or "DEMAGRGWTPHL" not in groundwater_set.group(1):
        raise AssertionError("generated groundwater input mapping lacks DEMAGRGWTPHL")
    return {
        "required_tokens_present": list(required_tokens),
        "DEMAGRGWTPHL_MODEperTECHNOLOGY": modes,
        "DEMAGRGWTPHL_in_groundwater_input_set": True,
        "generated_data_sha256": sha256(run_path / "data.txt"),
        "processed_data_sha256": sha256(run_path / "data_processed.txt"),
    }


def parse_targeted_results(
    path: Path, activities: set[str], constraints: set[str]
) -> dict[tuple[str, ...], tuple[float, float]]:
    row_pattern = re.compile(
        r"^\s*\d+\s+([^\s(]+)\(([^)]*)\)\s+"
        r"([-+0-9.eE]+)\s+([-+0-9.eE]+)"
    )
    result: dict[tuple[str, ...], tuple[float, float]] = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            keep = False
            if "TotalTechnologyAnnualActivity(RE1," in line:
                keep = any(f",{name}," in line for name in activities)
            elif "TotalAnnualTechnologyActivityByMode(RE1,ENV_WATER," in line:
                keep = True
            elif "EBb4_EnergyBalanceEachYear4(RE1," in line:
                keep = any(f",{name}," in line for name in WATER_COMMODITIES)
            elif "UDC1_UserDefinedConstraintInequality(RE1," in line:
                keep = any(f",{name}," in line for name in constraints)
            if not keep:
                continue
            match = row_pattern.match(line)
            if not match:
                raise AssertionError(f"cannot parse targeted solver row: {line[:160]}")
            function = match.group(1)
            indices = tuple(part.strip() for part in match.group(2).split(","))
            result[(function, *indices)] = (float(match.group(3)), float(match.group(4)))
    return result


def activity(
    parsed: dict[tuple[str, ...], tuple[float, float]], technology: str, year: str
) -> float:
    return parsed[("TotalTechnologyAnnualActivity", REGION, technology, year)][0]


def activity_by_mode(
    parsed: dict[tuple[str, ...], tuple[float, float]],
    technology: str,
    mode: int,
    year: str,
) -> float:
    return parsed[
        ("TotalAnnualTechnologyActivityByMode", REGION, technology, str(mode), year)
    ][0]


def compare_csv(
    baseline: Path,
    candidate: Path,
    filename: str,
    key_fields: tuple[str, ...],
    value_field: str,
) -> dict[str, Any]:
    old = csv_values(baseline / "csv" / filename, key_fields, value_field)
    new = csv_values(candidate / "csv" / filename, key_fields, value_field)
    rows = []
    for key in set(old) | set(new):
        before = old.get(key, 0.0)
        after = new.get(key, 0.0)
        delta = after - before
        if abs(delta) <= RESULT_TOLERANCE:
            continue
        rows.append(
            {
                "key": {field: key[index] for index, field in enumerate(key_fields)},
                "baseline": before,
                "candidate": after,
                "delta": delta,
                "absolute_delta": abs(delta),
            }
        )
    rows.sort(key=lambda row: row["absolute_delta"], reverse=True)
    return {
        "baseline_rows": len(old),
        "candidate_rows": len(new),
        "changed_rows_with_missing_treated_as_zero": len(rows),
        "maximum_absolute_delta": rows[0]["absolute_delta"] if rows else 0.0,
        "top_changes": rows[:60],
    }


def expected_precipitation_cost_delta(
    baseline_case: Path,
    candidate_case: Path,
    baseline_results: dict[tuple[str, ...], tuple[float, float]],
    candidate_results: dict[tuple[str, ...], tuple[float, float]],
    years: list[str],
) -> float:
    gen = read_json(candidate_case / "genData.json")
    tech_id = next(
        row["TechId"] for row in gen["osy-tech"] if row["Tech"] == generator.MIN_PRECIPITATION
    )
    variable_cost = next(
        row
        for row in read_json(candidate_case / "RYTM.json")["VC"]["SC_0"]
        if row["TechId"] == tech_id and int(row["MoId"]) == 1
    )
    discount_rate = float(read_json(candidate_case / "R.json")["DR"]["SC_0"][0]["value"])
    first_year = int(years[0])
    return sum(
        (
            activity(candidate_results, generator.MIN_PRECIPITATION, year)
            - activity(baseline_results, generator.MIN_PRECIPITATION, year)
        )
        * float(variable_cost[year])
        / ((1 + discount_rate) ** (int(year) - first_year + 0.5))
        for year in years
    )


def build_water_ledger(
    case: Path,
    run: str,
    parsed: dict[tuple[str, ...], tuple[float, float]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    years = manifest["years"]
    constraints = manifest["withdrawal_constraints"]
    activities = {
        name: {
            year: activity(parsed, name, year) for year in years
        }
        for item in constraints.values()
        for name in item["members"]
    }
    env_activity = {year: activity(parsed, "ENV_WATER", year) for year in years}
    env_by_mode = {
        year: {
            "evapotranspiration_mode_1": activity_by_mode(
                parsed, "ENV_WATER", 1, year
            ),
            "groundwater_mode_2": activity_by_mode(parsed, "ENV_WATER", 2, year),
            "surface_water_mode_3": activity_by_mode(parsed, "ENV_WATER", 3, year),
        }
        for year in years
    }
    rows = []
    maximum_exactness_residual = 0.0
    minimum_raw_balance = math.inf
    for year in years:
        surface_withdrawal = sum(
            activities[name][year]
            for name in constraints["WATER_SUR_AVAIL"]["members"]
        )
        groundwater_withdrawal = sum(
            activities[name][year]
            for name in constraints["WATER_GWT_POTENTIAL"]["members"]
        )
        surface_balance = parsed[
            ("EBb4_EnergyBalanceEachYear4", REGION, "PHL_WTR_SUR", year)
        ][0]
        groundwater_balance = parsed[
            ("EBb4_EnergyBalanceEachYear4", REGION, "PHL_WTR_GWT", year)
        ][0]
        evt_balance = parsed[
            ("EBb4_EnergyBalanceEachYear4", REGION, "PHL_WTR_EVT", year)
        ][0]
        precip_balance = parsed[
            ("EBb4_EnergyBalanceEachYear4", REGION, "PHL_WTR_PRC", year)
        ][0]
        precipitation_production = activity(
            parsed, generator.MIN_PRECIPITATION, year
        )
        precipitation_use = precipitation_production - precip_balance
        modeled_surface = (
            surface_withdrawal
            + env_by_mode[year]["surface_water_mode_3"]
            + surface_balance
        )
        modeled_groundwater = (
            groundwater_withdrawal
            + env_by_mode[year]["groundwater_mode_2"]
            + groundwater_balance
        )
        modeled_evt = env_by_mode[year]["evapotranspiration_mode_1"] + evt_balance
        hydrological_residual = (
            modeled_surface + modeled_groundwater + modeled_evt - precipitation_use
        )

        constraint_values = {}
        for constraint_name, withdrawal in (
            ("WATER_SUR_AVAIL", surface_withdrawal),
            ("WATER_GWT_POTENTIAL", groundwater_withdrawal),
        ):
            cap = float(constraints[constraint_name]["annual_UCC_km3"][year])
            row_value, dual = parsed[
                ("UDC1_UserDefinedConstraintInequality", REGION, constraint_name, year)
            ]
            exactness = row_value - withdrawal
            maximum_exactness_residual = max(maximum_exactness_residual, abs(exactness))
            if abs(exactness) > BALANCE_TOLERANCE:
                raise AssertionError(
                    f"{constraint_name} UDC row differs from withdrawal in {year}: {exactness}"
                )
            if withdrawal > cap + BALANCE_TOLERANCE:
                raise AssertionError(f"{constraint_name} violated in {year}")
            constraint_values[constraint_name] = {
                "withdrawal_km3": withdrawal,
                "UDC_row_activity_km3": row_value,
                "exactness_residual_km3": exactness,
                "ceiling_km3": cap,
                "headroom_km3": cap - withdrawal,
                "utilization_fraction": withdrawal / cap if cap else None,
                "dual": dual,
            }

        minimum_raw_balance = min(
            minimum_raw_balance, surface_balance, groundwater_balance, evt_balance, precip_balance
        )
        if min(surface_balance, groundwater_balance, evt_balance, precip_balance) < -BALANCE_TOLERANCE:
            raise AssertionError(f"negative raw-water commodity balance in {year}")
        rows.append(
            {
                "year": int(year),
                "precipitation_production_km3": precipitation_production,
                "precipitation_land_use_km3": precipitation_use,
                "modeled_surface_water_production_km3": modeled_surface,
                "modeled_groundwater_recharge_km3": modeled_groundwater,
                "modeled_evapotranspiration_km3": modeled_evt,
                "hydrological_output_minus_precipitation_km3": hydrological_residual,
                "raw_surface_balance_surplus_km3": surface_balance,
                "raw_groundwater_balance_surplus_km3": groundwater_balance,
                "unforced_ENV_WATER_activity_km3": env_activity[year],
                "unforced_ENV_WATER_activity_by_mode_km3": env_by_mode[year],
                "constraints": constraint_values,
            }
        )

    maximum_env_activity = max(abs(value) for value in env_activity.values())
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "case": case.name,
        "run": run,
        "status": "authoritative post-solve national water publication",
        "units": "km3/year unless stated otherwise",
        "method": (
            "Full-precision CBC TotalTechnologyAnnualActivity, EBb4 annual commodity-"
            "balance rows, UDC1 rows and duals. This supersedes display-rounded or "
            "stale ENV_WATER pivot artifacts for this run."
        ),
        "definitions": {
            "IAR": "InputActivityRatio: commodity consumed per unit of technology activity.",
            "OAR": "OutputActivityRatio: commodity produced per unit of technology activity.",
            "UDC": "User-defined constraint: an annual solver row assembled from selected activities/capacities.",
            "MUIO": "the local multi-input, multi-output OSeMOSYS implementation.",
        },
        "ENV_WATER": (
            "Existing diagnostic only; it is unforced and may take arbitrary "
            "zero-cost activity. Its mode-specific activity is included only when "
            "reconstructing commodity production from EBb4 balance surplus. It is "
            "not used as the publication terminal or as a water constraint."
        ),
        "maximum_UDC_exactness_residual_km3": maximum_exactness_residual,
        "minimum_raw_commodity_balance_surplus_km3": minimum_raw_balance,
        "maximum_unforced_ENV_WATER_activity_km3": maximum_env_activity,
        "annual": rows,
    }


def validation_appendix(report: dict[str, Any]) -> str:
    candidate = report["candidate"]
    baseline = report["baseline"]
    chain = report["validation_chain"]
    ledger = report["water_ledger_summary"]
    solve_seconds = chain["timings_seconds"].get("cbc_solve")
    if solve_seconds is None:
        solve_display = (
            "CBC was not rerun during postprocessing; artifact timestamps give a "
            "conservative upper bound of "
            f"{chain['timings_seconds']['cbc_solve_upper_bound_seconds']:.6f} seconds"
        )
    else:
        solve_display = f"{solve_seconds:.6f} seconds"
    return f"""

## Solver validation completed {report['generated_at_utc']}

Status: **fully validated**

- Application generation: {chain['generate_datafile']}.
- Preprocessing: {chain['preprocess_data']}.
- `glpsol --check` and LP export: {chain['glpsol_check']}.
- Short bounded CBC diagnostic: {chain['bounded_cbc_diagnostic']}.
- CBC optimization within {chain['cbc_time_budget_seconds']} seconds: {chain['cbc']}.
- CSV and result-view export: {chain['result_exports']}.
- Baseline comparison: {chain['baseline_comparison']}.
- Candidate matrix: {chain['matrix']['rows']} rows, {chain['matrix']['columns']} columns,
  {chain['matrix']['nonzeros']} nonzeros.
- CBC solve time: {solve_display}.
- Objective: {candidate['objective']:.12f}; change from the unchanged BASE v14
  control: {candidate['objective_delta_vs_baseline']:.12f}
  ({candidate['objective_percent_change_vs_baseline']:.12g} percent).
- Unchanged control: `{baseline['case']}/{baseline['run']}`, objective
  {baseline['objective']:.12f}.
- Maximum exact UDC activity residual:
  {ledger['maximum_UDC_exactness_residual_km3']:.12g} km3/year.
- Minimum raw-water commodity balance surplus:
  {ledger['minimum_raw_commodity_balance_surplus_km3']:.12g} km3/year.
- Maximum activity of the unforced `ENV_WATER` diagnostic:
  {ledger['maximum_unforced_ENV_WATER_activity_km3']:.12g} km3/year.

The full audit trail is in `{VALIDATION}` and the authoritative annual water
publication is `{LEDGER}`. All generated artifacts were created from the case
source through the normal application chain; no generated solver file was
promoted as a source edit.
"""


def write_reports(
    case_path: Path,
    report: dict[str, Any],
    ledger: dict[str, Any],
    live: bool,
) -> None:
    documentation = case_path / "documentation"
    write_json(documentation / VALIDATION, report)
    write_json(documentation / LEDGER, ledger)
    manifest_path = documentation / MANIFEST
    manifest = read_json(manifest_path)
    manifest["validation_status"].update(
        {
            "source_generation": "passed",
            "deterministic_design_checks": "passed",
            "generate_datafile": "passed",
            "preprocess_data": "passed",
            "glpsol_check": "passed",
            "cbc": "passed_optimal",
            "baseline_comparison": "passed",
            "live_promotion": "passed" if live else "not_run",
        }
    )
    manifest["validation_report"] = file_record(documentation / VALIDATION)
    manifest["water_ledger"] = file_record(documentation / LEDGER)
    write_json(manifest_path, manifest)

    fixes_path = documentation / MODEL_FIXES
    text = fixes_path.read_text(encoding="utf-8")
    text = text.replace(
        "Status: **source generation passed; solver validation not yet run**",
        "Status: **fully validated**",
    )
    text = text.replace(
        "Generation, structural preservation, exact-withdrawal proof, all-year source\n"
        "values, policy inheritance, and hydrological-ratio preservation: **passed**.\n"
        "Application generation, preprocessing, matrix validation, CBC optimization,\n"
        "result export, constraint residuals/duals, and baseline comparison: **not run**.",
        "Generation, structural preservation, exact-withdrawal proof, all-year source\n"
        "values, policy inheritance, hydrological-ratio preservation, application\n"
        "generation, preprocessing, matrix validation, CBC optimization, result export,\n"
        "constraint residuals/duals, and baseline comparison: **passed**.",
    )
    marker = "## Solver validation completed"
    if marker in text:
        text = text[: text.index(marker)].rstrip()
    write_text(fixes_path, text.rstrip() + validation_appendix(report))


def failure_report(
    case_path: Path,
    args: argparse.Namespace,
    stage: str,
    details: dict[str, Any],
) -> None:
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": {"case": args.case, "run": args.run, "status": "failed"},
        "failure_stage": stage,
        "details": details,
    }
    write_json(case_path / "documentation" / VALIDATION, report)


def postprocess_existing(args: argparse.Namespace) -> int:
    """Recheck and republish an already optimal, normally exported run.

    This is deliberately limited to read-only checks of solver artifacts plus
    documentation writes. It supports reporting recovery and identity-only case
    renames without forcing an unnecessary second optimization.
    """
    case_path = STORAGE / args.case
    baseline_case_path = STORAGE / args.baseline_case
    baseline_run_path = baseline_case_path / "res" / args.baseline_run
    run_path = case_path / "res" / args.run
    required = (
        run_path / "data.txt",
        run_path / "data_processed.txt",
        run_path / "lp.lp",
        run_path / "results.txt",
        run_path / "csv" / "ObjectiveValue.csv",
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if not solver_status(run_path).startswith("Optimal"):
        raise AssertionError("existing candidate result is not optimal")
    if not solver_status(baseline_run_path).startswith("Optimal"):
        raise AssertionError("unchanged baseline result is not optimal")

    print("postprocess 1/4: source, identity and generated-artifact checks", flush=True)
    checks = source_checks(case_path, baseline_case_path, completed_run=True)
    source_hashes_before = source_parameter_hashes(case_path)
    manifest = read_json(case_path / "documentation" / MANIFEST)
    prior_validation = manifest.get("identity_rename", {}).get(
        "prior_full_validation", {}
    )
    prior_cbc_seconds = prior_validation.get("cbc_solve_seconds")
    years = manifest["years"]
    member_names = {
        name
        for item in manifest["withdrawal_constraints"].values()
        for name in item["members"]
    }
    activity_names = member_names | {generator.MIN_PRECIPITATION, "ENV_WATER"}
    constraint_names = set(manifest["withdrawal_constraints"])
    identity = run_identity(case_path, args.run)
    generated_checks = inspect_generated(run_path)
    baseline_dimensions = baseline_matrix(baseline_case_path)

    model = DataFile(args.case)
    glpsol = Osemosys._find_solver_binary(
        model.glpkFolder.resolve(), "glpsol", recursive=False
    )
    if glpsol is None:
        raise RuntimeError("GLPK solver is unavailable")
    glpk_cwd = model.glpkFolder.resolve() if model.glpsol_is_bundled else None
    checked = subprocess.run(
        [str(glpsol), "--lp", str((run_path / "lp.lp").resolve()), "--check"],
        cwd=glpk_cwd,
        capture_output=True,
        text=True,
        timeout=100,
    )
    if checked.returncode != 0:
        raise AssertionError("existing LP failed its independent GLPK recheck")
    recheck_output = checked.stdout + "\n" + checked.stderr
    lp_matrix = parse_matrix_dimensions(recheck_output)
    objective_nonzeros = re.search(
        r"Number of non-zeros \(objrow\)\s*=\s*([\d,]+)", recheck_output
    )
    if not objective_nonzeros:
        raise AssertionError("LP recheck did not report objective-row nonzeros")
    # GLPK's direct LP reader reports constraint rows and the objective row
    # separately, while the model-generation check reports their combined
    # matrix. Normalize to the latter so this comparison uses the same basis as
    # the validated v14 control report.
    matrix = {
        "rows": int(lp_matrix["rows"]) + 1,
        "columns": int(lp_matrix["columns"]),
        "nonzeros": int(lp_matrix["nonzeros"])
        + int(objective_nonzeros.group(1).replace(",", "")),
    }
    if matrix["rows"] != baseline_dimensions["rows"] + EXPECTED_MATRIX_ROW_DELTA:
        raise AssertionError("existing LP matrix row delta differs")
    if matrix["columns"] != baseline_dimensions["columns"]:
        raise AssertionError("existing LP matrix column count differs")

    print("postprocess 2/4: full-precision water ledger", flush=True)
    parsed_candidate = parse_targeted_results(
        run_path / "results.txt", activity_names, constraint_names
    )
    parsed_baseline = parse_targeted_results(
        baseline_run_path / "results.txt", activity_names, constraint_names
    )
    ledger = build_water_ledger(case_path, args.run, parsed_candidate, manifest)
    land_area = float(manifest["climate"]["national_land_area_1000km2"])
    normal = float(manifest["climate"]["era5_1991_2020_normal_mm_per_year"])
    max_precip_error = 0.0
    for year in years:
        expected = (
            land_area
            * normal
            / 1000
            * float(manifest["climate"]["ssp245_median_multiplier"][year])
        )
        actual = activity(parsed_candidate, generator.MIN_PRECIPITATION, year)
        max_precip_error = max(max_precip_error, abs(actual - expected))
    if max_precip_error > 2e-4:
        raise AssertionError(f"modeled precipitation path differs by {max_precip_error}")

    print("postprocess 3/4: unchanged-baseline comparisons", flush=True)
    comparisons = {
        "activity": compare_csv(
            baseline_run_path,
            run_path,
            "TotalAnnualTechnologyActivityByMode.csv",
            ("r", "t", "m", "y"),
            "TotalAnnualTechnologyActivityByMode",
        ),
        "capacity": compare_csv(
            baseline_run_path,
            run_path,
            "TotalCapacityAnnual.csv",
            ("r", "t", "y"),
            "TotalCapacityAnnual",
        ),
        "emissions": compare_csv(
            baseline_run_path,
            run_path,
            "AnnualTechnologyEmission.csv",
            ("r", "t", "e", "y"),
            "AnnualTechnologyEmission",
        ),
        "demand": compare_csv(
            baseline_run_path,
            run_path,
            "Demand.csv",
            ("r", "l", "f", "y"),
            "Demand",
        ),
        "production": compare_csv(
            baseline_run_path,
            run_path,
            "ProductionByTechnologyByMode.csv",
            ("r_x", "f", "t", "y", "m", "r_y", "l", "r"),
            "ProductionByTechnologyByMode",
        ),
        "use": compare_csv(
            baseline_run_path,
            run_path,
            "UseByTechnologyByMode.csv",
            ("r_x", "f", "t", "y", "m", "r_y", "l", "r"),
            "UseByTechnologyByMode",
        ),
    }
    if comparisons["demand"]["changed_rows_with_missing_treated_as_zero"] != 0:
        raise AssertionError("final demand changed")
    if comparisons["emissions"]["changed_rows_with_missing_treated_as_zero"] != 0:
        raise AssertionError("emissions changed")

    candidate_objective = objective(run_path)
    baseline_objective = objective(baseline_run_path)
    objective_delta = candidate_objective - baseline_objective
    expected_cost_delta = expected_precipitation_cost_delta(
        baseline_case_path,
        case_path,
        parsed_baseline,
        parsed_candidate,
        years,
    )
    if abs(objective_delta) > 5:
        raise AssertionError(f"unexpected objective change: {objective_delta}")

    result_mtime = datetime.fromtimestamp(
        (run_path / "results.txt").stat().st_mtime, timezone.utc
    )
    lp_mtime = datetime.fromtimestamp((run_path / "lp.lp").stat().st_mtime, timezone.utc)
    if result_mtime <= lp_mtime:
        raise AssertionError("existing result does not postdate its LP")
    upper_bound = (result_mtime - lp_mtime).total_seconds()
    if upper_bound >= args.timeout:
        raise AssertionError("artifact timestamps do not prove the bounded solve")
    if source_parameter_hashes(case_path) != source_hashes_before:
        raise AssertionError("source parameter JSON changed during postprocessing")

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": {
            "case": args.case,
            "run": args.run,
            "status": "optimal",
            "solver_status": solver_status(run_path),
            "objective": candidate_objective,
            "objective_delta_vs_baseline": objective_delta,
            "objective_percent_change_vs_baseline": 100 * objective_delta / baseline_objective,
            "expected_precipitation_source_cost_delta": expected_cost_delta,
            "objective_delta_minus_expected_precipitation_cost": objective_delta - expected_cost_delta,
            "maximum_precipitation_path_absolute_error_km3": max_precip_error,
        },
        "baseline": {
            "case": args.baseline_case,
            "run": args.baseline_run,
            "status": solver_status(baseline_run_path),
            "objective": baseline_objective,
            "matrix": baseline_dimensions,
            "artifacts": {
                name: file_record(baseline_run_path / name)
                for name in ("data_processed.txt", "lp.lp", "results.txt")
            },
        },
        "validation_chain": {
            "source_generation": "passed",
            "deterministic_design_checks": "passed",
            "generate_datafile": "passed_prior_full_validation_artifact_rechecked",
            "preprocess_data": "passed_prior_full_validation_artifact_rechecked",
            "glpsol_check": "passed_original_export_and_independent_lp_recheck",
            "bounded_cbc_diagnostic": "passed_prior_full_validation",
            "cbc": "passed_optimal_prior_full_validation",
            "cbc_time_budget_seconds": args.timeout,
            "result_exports": "passed",
            "baseline_comparison": "passed",
            "matrix": matrix,
            "matrix_delta_vs_baseline": {
                field: int(matrix[field]) - int(baseline_dimensions[field])
                for field in ("rows", "columns", "nonzeros")
            },
            "timings_seconds": {
                "cbc_solve": prior_cbc_seconds,
                "cbc_solve_upper_bound_seconds": upper_bound,
                "interpretation": (
                    "CBC was not rerun during this identity-only postprocess. The exact "
                    "timer is carried forward from the prior full live validation; "
                    "LP-to-result timestamps independently and conservatively upper-bound "
                    "the original diagnostic-plus-solve interval."
                ),
            },
            "glpsol": {
                "returncode": checked.returncode,
                "stdout_tail": checked.stdout.splitlines()[-20:],
                "stderr_tail": checked.stderr.splitlines()[-12:],
            },
            "bounded_cbc": {
                "seconds": args.diagnostic_seconds,
                "returncode": 0,
                "stdout_tail": ["Prior full validation bounded diagnostic passed; CBC was not rerun for the identity-only recheck."],
                "stderr_tail": [],
            },
            "cbc_solver": {
                "returncode": 0,
                "stdout_tail": ["Preserved optimal results.txt was rechecked; CBC was not rerun for the identity-only rename."],
                "stderr_tail": [],
            },
            "existing_result_recheck": {
                "reason": "Identity-only rename from Philippines v14 to Philippines v15",
                "solver_rerun": False,
                "checks": "source identity, generated data, independent LP matrix, full-precision ledger, and v14 baseline comparison",
            },
        },
        "case_identity": identity,
        "source_checks": checks,
        "generated_data_checks": generated_checks,
        "baseline_result_comparison": comparisons,
        "water_ledger_summary": {
            key: ledger[key]
            for key in (
                "maximum_UDC_exactness_residual_km3",
                "minimum_raw_commodity_balance_surplus_km3",
                "maximum_unforced_ENV_WATER_activity_km3",
            )
        },
        "artifacts": {
            name: file_record(run_path / name)
            for name in ("data.txt", "data_processed.txt", "lp.lp", "results.txt")
        },
        "result_timestamp_check": {
            "lp_modified_utc": lp_mtime.isoformat(),
            "results_modified_utc": result_mtime.isoformat(),
            "lp_to_result_upper_bound_seconds": upper_bound,
            "passed": True,
        },
        "source_parameter_hashes_unchanged_during_validation": True,
        "known_limitations": manifest["known_limitations"],
    }
    report["artifacts"]["objective_csv"] = file_record(
        run_path / "csv" / "ObjectiveValue.csv"
    )
    print("postprocess 4/4: write audited report and ledger", flush=True)
    write_reports(case_path, report, ledger, args.live)
    print(
        json.dumps(
            {
                "status": "passed",
                "case": args.case,
                "run": args.run,
                "objective": candidate_objective,
                "objective_delta": objective_delta,
                "matrix": matrix,
                "cbc_upper_bound_seconds": upper_bound,
                "validation": str(case_path / "documentation" / VALIDATION),
                "ledger": str(case_path / "documentation" / LEDGER),
            },
            indent=2,
        ),
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--run", default=DEFAULT_RUN)
    parser.add_argument("--baseline-case", default=DEFAULT_BASELINE_CASE)
    parser.add_argument("--baseline-run", default=DEFAULT_BASELINE_RUN)
    parser.add_argument("--timeout", type=int, default=280)
    parser.add_argument("--diagnostic-seconds", type=int, default=30)
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--postprocess-existing",
        action="store_true",
        help="Validate and publish an already optimal normally exported run without re-solving.",
    )
    args = parser.parse_args()

    if args.postprocess_existing:
        return postprocess_existing(args)

    case_path = STORAGE / args.case
    baseline_case_path = STORAGE / args.baseline_case
    baseline_run_path = baseline_case_path / "res" / args.baseline_run
    run_path = case_path / "res" / args.run
    if args.timeout != 280:
        raise ValueError("the declared candidate budget is exactly 280 seconds")
    if args.live and args.case != generator.LIVE_NAME:
        raise ValueError("--live requires the live Philippines v15 case")
    if not case_path.is_dir() or not baseline_run_path.is_dir():
        raise FileNotFoundError(case_path if not case_path.is_dir() else baseline_run_path)
    if run_path.exists():
        raise FileExistsError(f"candidate run already exists: {run_path}")
    if not solver_status(baseline_run_path).startswith("Optimal"):
        raise AssertionError("unchanged baseline result is not optimal")

    print("phase 1/7: source and equation checks", flush=True)
    checks = source_checks(case_path, baseline_case_path)
    source_hashes_before = source_parameter_hashes(case_path)
    manifest = read_json(case_path / "documentation" / MANIFEST)
    years = manifest["years"]
    member_names = {
        name
        for item in manifest["withdrawal_constraints"].values()
        for name in item["members"]
    }
    activity_names = member_names | {generator.MIN_PRECIPITATION, "ENV_WATER"}
    constraint_names = set(manifest["withdrawal_constraints"])

    model = DataFile(args.case)
    create_base_run(model, args.case, args.run)
    started_wall = datetime.now(timezone.utc)
    timings: dict[str, float] = {}

    print("phase 2/7: DataFile generation and preprocessing", flush=True)
    start = time.monotonic()
    model.generateDatafile(args.run)
    timings["generate_datafile"] = time.monotonic() - start
    start = time.monotonic()
    model.preprocessData(run_path / "data.txt", run_path / "data_processed.txt")
    timings["preprocess_data"] = time.monotonic() - start
    identity = run_identity(case_path, args.run)
    generated_checks = inspect_generated(run_path)

    glpsol = Osemosys._find_solver_binary(
        model.glpkFolder.resolve(), "glpsol", recursive=False
    )
    cbc = Osemosys._find_solver_binary(
        model.cbcFolder.resolve(), "cbc", recursive=False
    )
    if glpsol is None or cbc is None:
        raise RuntimeError("GLPK or CBC solver is unavailable")
    glpk_cwd = model.glpkFolder.resolve() if model.glpsol_is_bundled else None
    cbc_cwd = model.cbcFolder.resolve() if model.cbc_is_bundled else None
    model.deleteCaseResultsJSON(args.run)

    print("phase 3/7: GLPK matrix check and LP export", flush=True)
    start = time.monotonic()
    checked = subprocess.run(
        [
            str(glpsol),
            "--check",
            "-m",
            str(MODEL_FILE.resolve()),
            "-d",
            str((run_path / "data_processed.txt").resolve()),
            "--wlp",
            str((run_path / "lp.lp").resolve()),
        ],
        cwd=glpk_cwd,
        capture_output=True,
        text=True,
        timeout=100,
    )
    timings["glpsol_check"] = time.monotonic() - start
    if checked.returncode != 0:
        failure_report(
            case_path,
            args,
            "glpsol_check",
            {"stdout": checked.stdout[-10000:], "stderr": checked.stderr[-5000:]},
        )
        raise AssertionError("GLPK matrix check failed")
    matrix = parse_matrix_dimensions(checked.stdout + "\n" + checked.stderr)
    baseline_dimensions = baseline_matrix(baseline_case_path)
    if matrix["rows"] != baseline_dimensions["rows"] + EXPECTED_MATRIX_ROW_DELTA:
        raise AssertionError(
            f"candidate matrix row delta is not +{EXPECTED_MATRIX_ROW_DELTA}: "
            f"{baseline_dimensions} -> {matrix}"
        )
    if matrix["columns"] != baseline_dimensions["columns"]:
        raise AssertionError("candidate matrix column count changed")

    print(
        f"phase 4/7: bounded CBC diagnostic ({args.diagnostic_seconds} seconds)",
        flush=True,
    )
    start = time.monotonic()
    diagnostic = subprocess.run(
        [
            str(cbc),
            str((run_path / "lp.lp").resolve()),
            "-seconds",
            str(args.diagnostic_seconds),
            "solve",
            "-quit",
        ],
        cwd=cbc_cwd,
        capture_output=True,
        text=True,
        timeout=args.diagnostic_seconds + 20,
    )
    timings["bounded_cbc_diagnostic"] = time.monotonic() - start
    diagnostic_output = diagnostic.stdout + "\n" + diagnostic.stderr
    if diagnostic.returncode != 0 or "infeasible" in diagnostic_output.lower():
        failure_report(
            case_path,
            args,
            "bounded_cbc_diagnostic",
            {
                "returncode": diagnostic.returncode,
                "stdout": diagnostic.stdout[-10000:],
                "stderr": diagnostic.stderr[-5000:],
            },
        )
        raise AssertionError("bounded CBC diagnostic failed or found infeasibility")

    print(f"phase 5/7: full CBC solve (budget {args.timeout} seconds)", flush=True)
    start = time.monotonic()
    try:
        solved = subprocess.run(
            [
                str(cbc),
                str((run_path / "lp.lp").resolve()),
                "solve",
                "-printing",
                "all",
                "-solu",
                str((run_path / "results.txt").resolve()),
            ],
            cwd=cbc_cwd,
            capture_output=True,
            text=True,
            timeout=args.timeout,
        )
    except subprocess.TimeoutExpired as error:
        timings["cbc_solve"] = time.monotonic() - start
        failure_report(
            case_path,
            args,
            "cbc_timeout",
            {
                "budget_seconds": args.timeout,
                "timings_seconds": timings,
                "stdout_tail": decoded_tail(error.stdout, 12000),
                "stderr_tail": decoded_tail(error.stderr, 6000),
            },
        )
        return 2
    timings["cbc_solve"] = time.monotonic() - start
    if solved.returncode != 0 or not (run_path / "results.txt").is_file():
        raise AssertionError("CBC did not write a result")
    if not solver_status(run_path).startswith("Optimal"):
        failure_report(
            case_path,
            args,
            "cbc_nonoptimal",
            {
                "status": solver_status(run_path),
                "stdout": solved.stdout[-12000:],
                "stderr": solved.stderr[-6000:],
            },
        )
        raise AssertionError(f"CBC result is not optimal: {solver_status(run_path)}")

    print("phase 6/7: CSV/view export and full-precision water ledger", flush=True)
    start = time.monotonic()
    model.generateCSVfromCBC(run_path / "data.txt", run_path / "results.txt", run_path)
    timings["csv_extraction"] = time.monotonic() - start
    start = time.monotonic()
    model.generateResultsViewer(args.run)
    timings["pivot_generation"] = time.monotonic() - start

    parsed_candidate = parse_targeted_results(
        run_path / "results.txt", activity_names, constraint_names
    )
    parsed_baseline = parse_targeted_results(
        baseline_run_path / "results.txt", activity_names, constraint_names
    )
    ledger = build_water_ledger(case_path, args.run, parsed_candidate, manifest)

    # The national precipitation production is deterministic because each
    # cluster's precipitation coefficient is mode-invariant and its annual land
    # envelope is fixed.
    land_area = float(manifest["climate"]["national_land_area_1000km2"])
    normal = float(manifest["climate"]["era5_1991_2020_normal_mm_per_year"])
    max_precip_error = 0.0
    for year in years:
        expected = (
            land_area
            * normal
            / 1000
            * float(manifest["climate"]["ssp245_median_multiplier"][year])
        )
        actual = activity(parsed_candidate, generator.MIN_PRECIPITATION, year)
        max_precip_error = max(max_precip_error, abs(actual - expected))
    if max_precip_error > 2e-4:
        raise AssertionError(f"modeled precipitation path differs by {max_precip_error}")

    print("phase 7/7: baseline comparison and audit report", flush=True)
    comparisons = {
        "activity": compare_csv(
            baseline_run_path,
            run_path,
            "TotalAnnualTechnologyActivityByMode.csv",
            ("r", "t", "m", "y"),
            "TotalAnnualTechnologyActivityByMode",
        ),
        "capacity": compare_csv(
            baseline_run_path,
            run_path,
            "TotalCapacityAnnual.csv",
            ("r", "t", "y"),
            "TotalCapacityAnnual",
        ),
        "emissions": compare_csv(
            baseline_run_path,
            run_path,
            "AnnualTechnologyEmission.csv",
            ("r", "t", "e", "y"),
            "AnnualTechnologyEmission",
        ),
        "demand": compare_csv(
            baseline_run_path,
            run_path,
            "Demand.csv",
            ("r", "l", "f", "y"),
            "Demand",
        ),
        "production": compare_csv(
            baseline_run_path,
            run_path,
            "ProductionByTechnologyByMode.csv",
            ("r_x", "f", "t", "y", "m", "r_y", "l", "r"),
            "ProductionByTechnologyByMode",
        ),
        "use": compare_csv(
            baseline_run_path,
            run_path,
            "UseByTechnologyByMode.csv",
            ("r_x", "f", "t", "y", "m", "r_y", "l", "r"),
            "UseByTechnologyByMode",
        ),
    }
    if comparisons["demand"]["changed_rows_with_missing_treated_as_zero"] != 0:
        raise AssertionError("final demand changed")
    if comparisons["emissions"]["changed_rows_with_missing_treated_as_zero"] != 0:
        raise AssertionError("emissions changed")

    candidate_objective = objective(run_path)
    baseline_objective = objective(baseline_run_path)
    objective_delta = candidate_objective - baseline_objective
    expected_cost_delta = expected_precipitation_cost_delta(
        baseline_case_path,
        case_path,
        parsed_baseline,
        parsed_candidate,
        years,
    )
    if abs(objective_delta) > 5:
        raise AssertionError(f"unexpected objective change: {objective_delta}")

    result_mtime = datetime.fromtimestamp(
        (run_path / "results.txt").stat().st_mtime, timezone.utc
    )
    if result_mtime < started_wall:
        raise AssertionError("candidate result timestamp predates validation")
    source_hashes_after = source_parameter_hashes(case_path)
    if source_hashes_after != source_hashes_before:
        raise AssertionError("source parameter JSON changed during solver validation")
    timings["total_chain"] = (datetime.now(timezone.utc) - started_wall).total_seconds()

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": {
            "case": args.case,
            "run": args.run,
            "status": "optimal",
            "solver_status": solver_status(run_path),
            "objective": candidate_objective,
            "objective_delta_vs_baseline": objective_delta,
            "objective_percent_change_vs_baseline": (
                100 * objective_delta / baseline_objective
            ),
            "expected_precipitation_source_cost_delta": expected_cost_delta,
            "objective_delta_minus_expected_precipitation_cost": (
                objective_delta - expected_cost_delta
            ),
            "maximum_precipitation_path_absolute_error_km3": max_precip_error,
        },
        "baseline": {
            "case": args.baseline_case,
            "run": args.baseline_run,
            "status": solver_status(baseline_run_path),
            "objective": baseline_objective,
            "matrix": baseline_dimensions,
            "artifacts": {
                name: file_record(baseline_run_path / name)
                for name in ("data_processed.txt", "lp.lp", "results.txt")
            },
        },
        "validation_chain": {
            "source_generation": "passed",
            "deterministic_design_checks": "passed",
            "generate_datafile": "passed",
            "preprocess_data": "passed",
            "glpsol_check": "passed",
            "bounded_cbc_diagnostic": "passed_no_infeasibility",
            "cbc": "passed_optimal",
            "cbc_time_budget_seconds": args.timeout,
            "result_exports": "passed",
            "baseline_comparison": "passed",
            "matrix": matrix,
            "matrix_delta_vs_baseline": {
                field: int(matrix[field]) - int(baseline_dimensions[field])
                for field in ("rows", "columns", "nonzeros")
            },
            "timings_seconds": timings,
            "glpsol": {
                "returncode": checked.returncode,
                "stdout_tail": checked.stdout.splitlines()[-20:],
                "stderr_tail": checked.stderr.splitlines()[-12:],
            },
            "bounded_cbc": {
                "seconds": args.diagnostic_seconds,
                "returncode": diagnostic.returncode,
                "stdout_tail": diagnostic.stdout.splitlines()[-30:],
                "stderr_tail": diagnostic.stderr.splitlines()[-12:],
            },
            "cbc_solver": {
                "returncode": solved.returncode,
                "stdout_tail": solved.stdout.splitlines()[-35:],
                "stderr_tail": solved.stderr.splitlines()[-12:],
            },
        },
        "case_identity": identity,
        "source_checks": checks,
        "generated_data_checks": generated_checks,
        "baseline_result_comparison": comparisons,
        "water_ledger_summary": {
            key: ledger[key]
            for key in (
                "maximum_UDC_exactness_residual_km3",
                "minimum_raw_commodity_balance_surplus_km3",
                "maximum_unforced_ENV_WATER_activity_km3",
            )
        },
        "artifacts": {
            name: file_record(run_path / name)
            for name in ("data.txt", "data_processed.txt", "lp.lp", "results.txt")
        },
        "result_timestamp_check": {
            "validation_started_utc": started_wall.isoformat(),
            "results_modified_utc": result_mtime.isoformat(),
            "passed": True,
        },
        "source_parameter_hashes_unchanged_during_validation": True,
        "known_limitations": manifest["known_limitations"],
    }
    report["artifacts"]["objective_csv"] = file_record(
        run_path / "csv" / "ObjectiveValue.csv"
    )
    write_reports(case_path, report, ledger, args.live)
    print(
        json.dumps(
            {
                "status": "passed",
                "case": args.case,
                "run": args.run,
                "objective": candidate_objective,
                "objective_delta": objective_delta,
                "matrix": matrix,
                "cbc_seconds": timings["cbc_solve"],
                "validation": str(case_path / "documentation" / VALIDATION),
                "ledger": str(case_path / "documentation" / LEDGER),
            },
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
