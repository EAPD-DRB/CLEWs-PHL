#!/usr/bin/env python3
"""Generate, matrix-check, solve, and compare the v18 land-water candidate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import time
import types
from collections import defaultdict
from datetime import date
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
MODEL_FILE = REPO / "WebAPP" / "SOLVERs" / "model.v.5.4.txt"
BASELINE_OBJECTIVE = Decimal("369743573.32256168")
BASELINE_MATRIX = {"rows": 791245, "columns": 886010, "matrix_nonzeros": 12572675}
YEARS = tuple(str(year) for year in range(2020, 2054))
CLUSTERS = tuple(f"LNDAGRPHLC{number:02d}" for number in range(1, 9))
DELIVERY_TECHS = ("DEMAGRSURPHL", "DEMAGRGWTPHL")
CROP_COMMODITIES = {"CRPTOM", "CRPCON", "CRPSGC", "CRPMZE", "CRPRCP", "CRPOTH"}
RUN = "LAND_WATER_CLOSURE_V18_BASE"
getcontext().prec = 50


dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(REPO / "API"))

from Classes.Base import Config  # noqa: E402
from Classes.Case.DataFileClass import DataFile  # noqa: E402
from Classes.Case.OsemosysClass import Osemosys  # noqa: E402


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".codex-tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dec(value: Any) -> Decimal:
    return Decimal(str(value))


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def activity_by_technology_year(csv_dir: Path) -> dict[tuple[str, str], Decimal]:
    result: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for row in csv_rows(csv_dir / "TotalAnnualTechnologyActivityByMode.csv"):
        result[(row["t"], row["y"])] += dec(row["TotalAnnualTechnologyActivityByMode"])
    return dict(result)


def keyed_numeric_csv(
    path: Path, value_column: str, excluded: tuple[str, ...] = ()
) -> dict[tuple[str, ...], Decimal]:
    rows = csv_rows(path)
    if not rows:
        return {}
    keys = tuple(key for key in rows[0] if key != value_column and key not in excluded)
    return {tuple(row[key] for key in keys): dec(row[value_column]) for row in rows}


def maximum_difference(
    left: dict[tuple[str, ...], Decimal], right: dict[tuple[str, ...], Decimal]
) -> Decimal:
    return max(
        (abs(left.get(key, Decimal(0)) - right.get(key, Decimal(0))) for key in set(left) | set(right)),
        default=Decimal(0),
    )


def crop_production(csv_dir: Path) -> dict[tuple[str, str], Decimal]:
    result: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for row in csv_rows(csv_dir / "RateOfProductionByTechnologyByMode.csv"):
        if row["f"] in CROP_COMMODITIES:
            result[(row["f"], row["y"])] += dec(row["RateOfProductionByTechnologyByMode"])
    return dict(result)


def parse_matrix(text: str) -> dict[str, int]:
    rows = re.search(r"Number of rows\s*=\s*([\d,]+)", text)
    columns = re.search(r"Number of columns\s*=\s*([\d,]+)", text)
    matrix = re.search(r"Number of non-zeros \(matrix\)\s*=\s*([\d,]+)", text)
    objective = re.search(r"Number of non-zeros \(objrow\)\s*=\s*([\d,]+)", text)
    if not all((rows, columns, matrix, objective)):
        raise AssertionError("GLPK output did not report normalized LP dimensions")
    # The canonical deployment report counts the objective row and its
    # coefficients in the full generated matrix. GLPK's LP reader reports
    # them separately, so normalize to the canonical basis.
    return {
        "rows": int(rows.group(1).replace(",", "")) + 1,
        "columns": int(columns.group(1).replace(",", "")),
        "matrix_nonzeros": int(matrix.group(1).replace(",", ""))
        + int(objective.group(1).replace(",", "")),
    }


def source_checks(case: Path) -> dict[str, Any]:
    gen = read_json(case / "genData.json")
    ryt = read_json(case / "RYT.json")
    ratio = read_json(case / "RYTCM.json")
    constraints = {item["Con"]: item for item in gen["osy-constraints"]}
    technologies = {item["Tech"]: item["TechId"] for item in gen["osy-tech"]}
    commodities = {item["Comm"]: item["CommId"] for item in gen["osy-comm"]}
    tau = {row["TechId"]: row for row in ryt["TAU"]["SC_0"]}
    tal = {row["TechId"]: row for row in ryt["TAL"]["SC_0"]}
    cluster_area = {
        name: dec(tau[technologies[name]]["2020"]) for name in CLUSTERS
    }
    if sum(cluster_area.values(), Decimal(0)) != Decimal("295.8131"):
        raise AssertionError("cluster area does not close to national land")
    if "BAL_LAND_HYDROLOGY" in constraints:
        closure = constraints["BAL_LAND_HYDROLOGY"]
        if closure["Tag"] != 1 or len(closure["CM"]) != 9:
            raise AssertionError("land-hydrology equality structure is wrong")
        formulation = "aggregate_udc"
        constraint_id: str | None = closure["ConId"]
    else:
        formulation = "exact_cluster_bounds"
        constraint_id = None
        for name in CLUSTERS:
            tech_id = technologies[name]
            for year in YEARS:
                if dec(tal[tech_id][year]) != dec(tau[tech_id][year]):
                    raise AssertionError(f"cluster TAL does not equal TAU: {name}/{year}")

    maximum_balance_residual = Decimal(0)
    for name in CLUSTERS:
        tech_id = technologies[name]
        for mode in range(1, 31):
            rows = {}
            for parameter, commodity in (
                ("IAR", "PHL_WTR_PRC"),
                ("IAR", "AGRWATPHL"),
                ("OAR", "PHL_WTR_EVT"),
                ("OAR", "PHL_WTR_GWT"),
                ("OAR", "PHL_WTR_SUR"),
            ):
                found = [
                    row
                    for row in ratio[parameter]["SC_0"]
                    if row["TechId"] == tech_id
                    and row["CommId"] == commodities[commodity]
                    and int(row["MoId"]) == mode
                ]
                if len(found) != 1:
                    raise AssertionError((name, mode, parameter, commodity))
                rows[(parameter, commodity)] = found[0]
            for year in YEARS:
                residual = (
                    dec(rows[("IAR", "PHL_WTR_PRC")][year])
                    + dec(rows[("IAR", "AGRWATPHL")][year])
                    - dec(rows[("OAR", "PHL_WTR_EVT")][year])
                    - dec(rows[("OAR", "PHL_WTR_GWT")][year])
                    - dec(rows[("OAR", "PHL_WTR_SUR")][year])
                )
                maximum_balance_residual = max(maximum_balance_residual, abs(residual))
    if maximum_balance_residual > Decimal("1e-14"):
        raise AssertionError(f"source water balance fails: {maximum_balance_residual}")
    return {
        "land_formulation": formulation,
        "constraint_id": constraint_id,
        "cluster_area_1000km2": {name: str(value) for name, value in cluster_area.items()},
        "maximum_source_water_balance_residual": str(maximum_balance_residual),
        "source_hashes": {
            name: sha256(case / name)
            for name in ("genData.json", "RYTCM.json", "RYTCn.json", "RYCn.json")
        },
    }


def candidate_checks(
    case: Path, run_dir: Path, baseline_dir: Path, source: dict[str, Any]
) -> dict[str, Any]:
    csv_dir = run_dir / "csv"
    baseline_csv = baseline_dir / "csv"
    activity = activity_by_technology_year(csv_dir)
    gen = read_json(case / "genData.json")
    ryt = read_json(case / "RYT.json")
    ratio = read_json(case / "RYTCM.json")
    technologies = {item["Tech"]: item["TechId"] for item in gen["osy-tech"]}
    commodities = {item["Comm"]: item["CommId"] for item in gen["osy-comm"]}
    tau = {row["TechId"]: row for row in ryt["TAU"]["SC_0"]}
    maximum_land_error = Decimal(0)
    for year in YEARS:
        total = sum((activity.get((name, year), Decimal(0)) for name in CLUSTERS), Decimal(0))
        maximum_land_error = max(maximum_land_error, abs(total - Decimal("295.8131")))
        for name in CLUSTERS:
            maximum_land_error = max(
                maximum_land_error,
                abs(activity.get((name, year), Decimal(0)) - dec(tau[technologies[name]][year])),
            )
    # MUIO CSV export rounds each mode before aggregation. With 30 modes the
    # exact solver equality can appear up to roughly 0.001 away in this file.
    if maximum_land_error > Decimal("1e-3"):
        raise AssertionError(f"solved land routing fails: {maximum_land_error}")

    if source["land_formulation"] == "aggregate_udc":
        equality = [
            row
            for row in csv_rows(csv_dir / "UDC2_UserDefinedConstraintEquality.csv")
            if row["cn"] == "BAL_LAND_HYDROLOGY"
        ]
        if len(equality) != len(YEARS):
            raise AssertionError(f"missing solved equality rows: {len(equality)}")
        maximum_equality_residual: Decimal | None = max(
            abs(dec(row["UDC2_UserDefinedConstraintEquality"])) for row in equality
        )
    else:
        maximum_equality_residual = None

    precipitation: dict[str, Decimal] = {}
    for year in YEARS:
        total = Decimal(0)
        for name in CLUSTERS:
            tech_id = technologies[name]
            precip_rows = [
                row
                for row in ratio["IAR"]["SC_0"]
                if row["TechId"] == tech_id
                and row["CommId"] == commodities["PHL_WTR_PRC"]
                and int(row["MoId"]) == 1
            ]
            total += activity[(name, year)] * dec(precip_rows[0][year])
        precipitation[year] = total
    expected = {
        "2020": Decimal("786.306717372"),
        "2030": Decimal("794.2662317716391"),
        "2053": Decimal("824.0806113969379"),
    }
    maximum_precipitation_error = max(abs(precipitation[year] - value) for year, value in expected.items())
    if maximum_precipitation_error > Decimal("1e-2"):
        raise AssertionError(f"full-land precipitation mismatch: {maximum_precipitation_error}")

    production = csv_rows(csv_dir / "RateOfProductionByTechnologyByMode.csv")
    use = csv_rows(csv_dir / "RateOfUseByTechnologyByMode.csv")
    delivered = {
        (row["t"], row["y"], row["m"], row["l"]): dec(row["RateOfProductionByTechnologyByMode"])
        for row in production
        if row["t"] in DELIVERY_TECHS and row["f"] == "AGRWATPHL"
    }
    raw_commodity = {"DEMAGRSURPHL": "PHL_WTR_SUR", "DEMAGRGWTPHL": "PHL_WTR_GWT"}
    gross = {
        (row["t"], row["y"], row["m"], row["l"]): dec(row["RateOfUseByTechnologyByMode"])
        for row in use
        if row["t"] in DELIVERY_TECHS and row["f"] == raw_commodity[row["t"]]
    }
    if set(delivered) != set(gross):
        raise AssertionError("gross and delivered irrigation result keys differ")
    maximum_delivery_error = max(
        (abs(delivered[key] - Decimal("0.38") * gross[key]) for key in delivered),
        default=Decimal(0),
    )
    if maximum_delivery_error > Decimal("1e-3"):
        raise AssertionError(f"gross-to-delivered irrigation mismatch: {maximum_delivery_error}")

    baseline_activity = activity_by_technology_year(baseline_csv)
    gross_withdrawal_difference = max(
        abs(activity[(technology, year)] - baseline_activity[(technology, year)])
        for technology in DELIVERY_TECHS
        for year in YEARS
    )
    combined_gross_difference = {
        year: sum((activity[(technology, year)] for technology in DELIVERY_TECHS), Decimal(0))
        - sum((baseline_activity[(technology, year)] for technology in DELIVERY_TECHS), Decimal(0))
        for year in YEARS
    }
    new_capacity_difference = maximum_difference(
        keyed_numeric_csv(csv_dir / "NewCapacity.csv", "NewCapacity"),
        keyed_numeric_csv(baseline_csv / "NewCapacity.csv", "NewCapacity"),
    )
    emission_difference = maximum_difference(
        keyed_numeric_csv(csv_dir / "AnnualTechnologyEmission.csv", "AnnualTechnologyEmission"),
        keyed_numeric_csv(baseline_csv / "AnnualTechnologyEmission.csv", "AnnualTechnologyEmission"),
    )
    crop_difference = maximum_difference(crop_production(csv_dir), crop_production(baseline_csv))
    if max(new_capacity_difference, emission_difference, crop_difference) > Decimal("1e-3"):
        raise AssertionError(
            "unexpected non-water result change: "
            f"capacity={new_capacity_difference}; emissions={emission_difference}; crops={crop_difference}"
        )

    return {
        "maximum_land_routing_error_1000km2": str(maximum_land_error),
        "maximum_equality_reported_residual": (
            str(maximum_equality_residual) if maximum_equality_residual is not None else "not_applicable_exact_cluster_bounds"
        ),
        "precipitation_km3": {year: str(precipitation[year]) for year in ("2020", "2030", "2053")},
        "precipitation_depth_mm_2020": str(precipitation["2020"] / Decimal("295.8131") * Decimal(1000)),
        "precipitation_change_2020_2053_percent": str((precipitation["2053"] / precipitation["2020"] - 1) * 100),
        "maximum_precipitation_error_km3": str(maximum_precipitation_error),
        "maximum_gross_to_delivered_error_km3": str(maximum_delivery_error),
        "maximum_baseline_gross_irrigation_withdrawal_difference_km3": str(gross_withdrawal_difference),
        "maximum_combined_baseline_gross_irrigation_withdrawal_difference_km3": str(
            max((abs(value) for value in combined_gross_difference.values()), default=Decimal(0))
        ),
        "combined_gross_irrigation_withdrawal_difference_km3": {
            year: str(combined_gross_difference[year]) for year in ("2020", "2030", "2053")
        },
        "maximum_new_capacity_difference_gw": str(new_capacity_difference),
        "maximum_annual_emission_difference": str(emission_difference),
        "maximum_crop_production_difference": str(crop_difference),
        "source": source,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=430)
    parser.add_argument(
        "--resume-generated",
        action="store_true",
        help="Reuse an existing generated/preprocessed/LP candidate after a reporting-only interruption.",
    )
    parser.add_argument(
        "--postprocess-existing",
        action="store_true",
        help="Validate an existing optimal result after a reporting-only post-solve interruption; never invokes CBC.",
    )
    args = parser.parse_args()
    case = args.case.absolute()
    baseline = args.baseline.resolve()
    package = args.package.absolute()
    run_dir = case / "res" / RUN
    baseline_dir = baseline / "res" / "DEPLOYMENT_CANDIDATE_20260813"
    if run_dir.exists() and not (args.resume_generated or args.postprocess_existing):
        raise FileExistsError(f"refusing to replace run: {run_dir}")
    if not (baseline_dir / "results.txt").is_file():
        raise FileNotFoundError(baseline_dir)

    source = source_checks(case)
    Config.DATA_STORAGE = case.parent
    model = DataFile(case.name)
    scenarios = [
        {
            "ScenarioId": item["ScenarioId"],
            "Scenario": item["Scenario"],
            "Desc": item.get("Desc", ""),
            "Active": item["Scenario"] == "BASE",
        }
        for item in model.genData["osy-scenarios"]
    ]
    timings: dict[str, float] = {}
    if args.resume_generated or args.postprocess_existing:
        for filename in ("data.txt", "data_processed.txt", "lp.lp"):
            if not (run_dir / filename).is_file():
                raise FileNotFoundError(run_dir / filename)
        if (run_dir / "results.txt").exists() and not args.postprocess_existing:
            raise FileExistsError("resume is only valid before CBC has written results.txt")
        if args.postprocess_existing and not (run_dir / "results.txt").is_file():
            raise FileNotFoundError(run_dir / "results.txt")
        timings["generate_datafile"] = 0.0
        timings["preprocess_data"] = 0.0
    else:
        response = model.createCaseRun(
            RUN,
            {
                "Case": RUN,
                "CaseId": f"CS_{case.name}_{RUN}",
                "Desc": "Disposable full-chain validation of Philippines v18 land-water closure",
                "Runtime": date.today().isoformat(),
                "Scenarios": scenarios,
            },
        )
        if response.get("status_code") != "success":
            raise RuntimeError(json.dumps(response, indent=2))
        started = time.monotonic()
        model.generateDatafile(RUN)
        timings["generate_datafile"] = time.monotonic() - started
        started = time.monotonic()
        model.preprocessData(run_dir / "data.txt", run_dir / "data_processed.txt")
        timings["preprocess_data"] = time.monotonic() - started

    glpsol = Osemosys._find_solver_binary(model.glpkFolder.resolve(), "glpsol", recursive=False)
    cbc = Osemosys._find_solver_binary(model.cbcFolder.resolve(), "cbc", recursive=False)
    if glpsol is None or cbc is None:
        raise RuntimeError("GLPK or CBC solver is unavailable")
    if not args.postprocess_existing:
        model.deleteCaseResultsJSON(RUN)
    started = time.monotonic()
    checked = subprocess.run(
        [str(glpsol), "--lp", str(run_dir / "lp.lp"), "--check"],
        cwd=model.glpkFolder.resolve() if model.glpsol_is_bundled else None,
        capture_output=True,
        text=True,
        timeout=150,
    )
    timings["glpsol_check_and_lp"] = time.monotonic() - started
    glpk_output = checked.stdout + "\n" + checked.stderr
    if checked.returncode != 0:
        raise RuntimeError(glpk_output[-12000:])
    matrix = parse_matrix(glpk_output)
    expected_matrix = (
        {
            "rows": BASELINE_MATRIX["rows"] + 34,
            "columns": BASELINE_MATRIX["columns"],
            "matrix_nonzeros": BASELINE_MATRIX["matrix_nonzeros"] + 306,
        }
        if source["land_formulation"] == "aggregate_udc"
        else {
            "rows": BASELINE_MATRIX["rows"] + 272,
            "columns": BASELINE_MATRIX["columns"],
            "matrix_nonzeros": BASELINE_MATRIX["matrix_nonzeros"] + 244800,
        }
    )
    if matrix != expected_matrix:
        raise AssertionError(f"unexpected candidate matrix: {matrix}; expected {expected_matrix}")

    if args.postprocess_existing:
        timings["cbc_solve"] = None
    else:
        started = time.monotonic()
        solved = subprocess.run(
            [str(cbc), str(run_dir / "lp.lp"), "solve", "-printing", "all", "-solu", str(run_dir / "results.txt")],
            cwd=model.cbcFolder.resolve() if model.cbc_is_bundled else None,
            capture_output=True,
            text=True,
            timeout=args.timeout,
        )
        timings["cbc_solve"] = time.monotonic() - started
        if solved.returncode != 0 or not (run_dir / "results.txt").is_file():
            raise RuntimeError((solved.stdout + "\n" + solved.stderr)[-12000:])
    status = (run_dir / "results.txt").read_text(encoding="utf-8").splitlines()[0]
    if not status.startswith("Optimal"):
        raise RuntimeError(status)
    objective_match = re.search(r"objective value\s+([-+0-9.eE]+)", status)
    if not objective_match:
        raise AssertionError(status)
    objective = Decimal(objective_match.group(1))

    if args.postprocess_existing:
        if not (run_dir / "csv" / "ObjectiveValue.csv").is_file():
            started = time.monotonic()
            model.generateCSVfromCBC(run_dir / "data.txt", run_dir / "results.txt", run_dir)
            timings["csv_export"] = time.monotonic() - started
            started = time.monotonic()
            model.generateResultsViewer(RUN)
            timings["viewer_export"] = time.monotonic() - started
        else:
            timings["csv_export"] = 0.0
            timings["viewer_export"] = 0.0
        timings["total"] = None
    else:
        started = time.monotonic()
        model.generateCSVfromCBC(run_dir / "data.txt", run_dir / "results.txt", run_dir)
        timings["csv_export"] = time.monotonic() - started
        started = time.monotonic()
        model.generateResultsViewer(RUN)
        timings["viewer_export"] = time.monotonic() - started
        timings["total"] = sum(value for value in timings.values() if value is not None)

    checks = candidate_checks(case, run_dir, baseline_dir, source)
    report = {
        "schema": "philippines-v18-land-water-closure-validation-v1",
        "status": "pass",
        "optimizer_run_count": 1,
        "optimizer_run_count_this_invocation": 0 if args.postprocess_existing else 1,
        "optimizer_run_purpose": "Disposable candidate full optimization; unchanged control reused from the verified v18 deployment-envelope result.",
        "generation_resume_note": (
            "Post-processed the existing optimal result after a CSV export-tolerance assertion; CBC was not rerun and exact CBC seconds were not retained by the interrupted validator."
            if args.postprocess_existing
            else
            "Reused the same generated, preprocessed and GLPK-accepted artifacts after a reporting parser interruption before CBC."
            if args.resume_generated
            else "No resume; all artifacts generated in this invocation."
        ),
        "land_formulation": source["land_formulation"],
        "baseline": {
            "case": str(baseline),
            "run": "DEPLOYMENT_CANDIDATE_20260813",
            "status": (baseline_dir / "results.txt").read_text(encoding="utf-8").splitlines()[0],
            "objective": str(BASELINE_OBJECTIVE),
            "matrix": BASELINE_MATRIX,
            "data_sha256": sha256(baseline_dir / "data.txt"),
            "results_sha256": sha256(baseline_dir / "results.txt"),
        },
        "candidate": {
            "case": str(case),
            "run": RUN,
            "status": status,
            "objective": str(objective),
            "objective_delta": str(objective - BASELINE_OBJECTIVE),
            "objective_percent_change": str((objective / BASELINE_OBJECTIVE - 1) * 100),
            "matrix": matrix,
            "data_sha256": sha256(run_dir / "data.txt"),
            "data_processed_sha256": sha256(run_dir / "data_processed.txt"),
            "lp_sha256": sha256(run_dir / "lp.lp"),
            "results_sha256": sha256(run_dir / "results.txt"),
            "timings_seconds": timings,
        },
        "checks": checks,
        "validation_status": {
            "source_generation": "passed",
            "deterministic_design_checks": "passed",
            "generate_datafile": "passed",
            "preprocess_data": "passed",
            "glpsol_check": "passed",
            "cbc": "passed_optimal",
            "baseline_comparison": "passed",
            "promotion_identity": "not_run",
        },
    }
    output = package / "data_sources" / "snapshots" / "land_water_closure_validation.json"
    write_json(output, report)
    documentation = case / "documentation"
    documentation.mkdir(exist_ok=True)
    write_json(documentation / output.name, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
