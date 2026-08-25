#!/usr/bin/env python3
"""Validate the Philippines v18 non-forcing power-investment cleanup."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


BASE = "SC_0"
COAL_PHASEOUT = "SC_3hgjb"
YEARS = tuple(range(2020, 2054))
PIN_TECHS = (
    "PHL_POW_PP_SPV",
    "PHL_POW_PP_COAL",
    "PHL_POW_CHP_OIL_OLD",
    "PHL_POW_CHP_BIOM_OLD",
    "PHL_POW_PP_HY_LA",
    "PHL_POW_GEO_OLD",
    "PHL_POW_PP_NGCC",
)
STOCK_ONLY = (
    "PHL_POW_CHP_COAL_OLD",
    "PHL_POW_CHP_NG_OLD",
    "PHL_POW_CHP_OIL_OLD",
    "PHL_POW_CHP_BIOM_OLD",
)
BENCHMARK_ADDITIONS = {
    "PHL_POW_PP_SPV": {2021: 0.3024, 2022: 0.3049, 2023: 0.1568, 2024: 1.0012, 2025: 0.2749},
    "PHL_POW_PP_COAL": {2021: 0.725, 2022: 0.7694, 2024: 0.6},
    "PHL_POW_CHP_OIL_OLD": {2021: 0.1798, 2022: 0.0973, 2024: 0.0112},
    "PHL_POW_CHP_BIOM_OLD": {2022: 0.082, 2023: 0.006, 2024: 0.0099},
    "PHL_POW_PP_HY_LA": {2022: 0.0159, 2023: 0.0468, 2024: 0.0352},
    "PHL_POW_GEO_OLD": {2022: 0.0037, 2025: 0.0357},
    "PHL_POW_PP_NGCC": {2025: 0.88},
}
SUPPLY_TECHS = (
    "PHL_PRO_EXTR_COAL",
    "PHL_PRO_IMP_COAL",
    "PHL_PRO_EXP_COAL",
    "PHL_PRO_EXTR_OIL",
    "PHL_PRO_IMP_OIL",
    "PHL_PRO_EXP_OIL",
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows_by_name(block: dict, scenario: str, id_to_name: dict[str, str]) -> dict[str, dict]:
    return {id_to_name[row["TechId"]]: row for row in block[scenario]}


def source_diff(control: Path, candidate: Path, manifest: dict) -> dict:
    control_files = {path.name: digest(path) for path in control.glob("*.json")}
    candidate_files = {
        name: digest(candidate / name)
        for name in control_files
        if (candidate / name).is_file()
    }
    if control_files.keys() != candidate_files.keys():
        raise AssertionError("top-level source JSON inventory changed")
    changed_files = sorted(name for name in control_files if control_files[name] != candidate_files[name])
    if changed_files != ["RYT.json"]:
        raise AssertionError(f"expected only RYT.json to change, found {changed_files}")

    c = load(control / "RYT.json")
    n = load(candidate / "RYT.json")
    gen = load(candidate / "genData.json")
    names = {row["TechId"]: row["Tech"] for row in gen["osy-tech"]}
    actual = []
    for parameter, scenarios in c.items():
        for scenario, rows in scenarios.items():
            n_rows = {row["TechId"]: row for row in n[parameter][scenario]}
            for row in rows:
                for year in YEARS:
                    key = str(year)
                    after = n_rows[row["TechId"]][key]
                    if row[key] != after:
                        actual.append(
                            {
                                "parameter": parameter,
                                "scenario": scenario,
                                "technology": names[row["TechId"]],
                                "year": year,
                                "before": row[key],
                                "after": after,
                            }
                        )
    expected = manifest["changes"]
    normalize = lambda rows: sorted(rows, key=lambda row: (row["parameter"], row["scenario"], row["technology"], row["year"]))
    if normalize(actual) != normalize(expected):
        raise AssertionError("source diff does not equal the 62-cell manifest allowlist")
    if c["RC"] != n["RC"]:
        raise AssertionError("ResidualCapacity changed")
    for parameter in n:
        if parameter not in {"TAMinCI", "TAMaxCI"} and c[parameter] != n[parameter]:
            raise AssertionError(f"unapproved RYT parameter changed: {parameter}")
    for parameter in ("TAMinCI", "TAMaxCI"):
        for scenario in n[parameter]:
            if scenario != BASE and c[parameter][scenario] != n[parameter][scenario]:
                raise AssertionError(f"scenario overlay changed: {parameter}.{scenario}")

    min_rows = rows_by_name(n["TAMinCI"], BASE, names)
    max_rows = rows_by_name(n["TAMaxCI"], BASE, names)
    for technology, benchmarks in BENCHMARK_ADDITIONS.items():
        for year in benchmarks:
            if min_rows[technology][str(year)] != 0:
                raise AssertionError(f"pin remains: {technology} {year}")
    for technology in STOCK_ONLY:
        if any(max_rows[technology][str(year)] != 0 for year in YEARS):
            raise AssertionError(f"stock-only entry remains open: {technology}")
    coal = max_rows["PHL_POW_PP_COAL"]
    expected_coal = {
        **{year: 2 for year in range(2020, 2030)},
        **{year: 2.5 for year in range(2030, 2040)},
        **{year: 3 for year in range(2040, 2051)},
        **{year: 5 for year in range(2051, 2054)},
    }
    if any(coal[str(year)] != value for year, value in expected_coal.items()):
        raise AssertionError("base coal construction envelope is incorrect")
    phaseout = rows_by_name(n["TAMaxCI"], COAL_PHASEOUT, names)["PHL_POW_PP_COAL"]
    if any(phaseout[str(year)] is not None for year in range(2020, 2031)):
        raise AssertionError("CoalPhaseOut must inherit the base envelope through 2030")
    if any(phaseout[str(year)] != 0 for year in range(2031, 2054)):
        raise AssertionError("CoalPhaseOut must explicitly prohibit new coal from 2031")

    return {
        "changed_source_files": changed_files,
        "changed_cells": len(actual),
        "changed_parameter_counts": manifest["changed_parameter_counts"],
        "residual_capacity_byte_unchanged": True,
        "scenario_overlays_unchanged": True,
        "pins_remaining": 0,
        "stock_only_entry_zero_all_years": True,
        "base_coal_envelope_verified": True,
        "coal_phaseout_exact_zero_verified": True,
        "candidate_ryt_sha256": digest(candidate / "RYT.json"),
    }


def parameter_row(
    data_path: Path,
    parameter: str,
    technology: str,
    *,
    omitted_default: float | None = None,
) -> list[float]:
    text = data_path.read_text(encoding="utf-8")
    start = text.index(f"param {parameter}")
    end = text.index(";", start)
    for line in text[start:end].splitlines():
        fields = line.split()
        if fields and fields[0] == technology:
            values = [float(value) for value in fields[1:]]
            if len(values) != len(YEARS):
                raise AssertionError(f"wrong generated row length for {parameter}.{technology}")
            return values
    if omitted_default is not None:
        return [omitted_default] * len(YEARS)
    raise AssertionError(f"missing generated row {parameter}.{technology}")


def generated_checks(candidate: Path) -> dict:
    run_dir = candidate / "res" / "TOMORROWLAND"
    data_path = run_dir / "data.txt"
    min_rows = {
        technology: parameter_row(
            data_path,
            "TotalAnnualMinCapacityInvestment",
            technology,
            omitted_default=0.0,
        )
        for technology in PIN_TECHS
    }
    for technology, benchmarks in BENCHMARK_ADDITIONS.items():
        for year in benchmarks:
            if min_rows[technology][year - 2020] != 0:
                raise AssertionError(f"generated minimum pin remains: {technology} {year}")
    coal = parameter_row(data_path, "TotalAnnualMaxCapacityInvestment", "PHL_POW_PP_COAL")
    expected = [2.0] * 10 + [2.5] + [0.0] * 23
    if coal != expected:
        raise AssertionError(f"unexpected effective TOMORROWLAND coal row: {coal}")
    for technology in STOCK_ONLY:
        if any(abs(value) > 0 for value in parameter_row(data_path, "TotalAnnualMaxCapacityInvestment", technology)):
            raise AssertionError(f"generated stock-only entry is nonzero: {technology}")
    return {
        "data_txt_sha256": digest(data_path),
        "effective_tomorrowland_coal_tamaxci": {"2020-2029": 2, "2030": 2.5, "2031-2053": 0},
        "generated_pin_minima_zero": True,
        "generated_stock_only_entry_zero": True,
    }


ROW = re.compile(r"^\s*\d+\s+(\S+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$")


def selected_solution(path: Path) -> tuple[str, dict[str, float]]:
    values: dict[str, float] = {}
    with path.open(encoding="utf-8") as stream:
        status = next(stream).strip()
        for line in stream:
            match = ROW.match(line)
            if not match:
                continue
            name = match.group(1)
            if name.startswith("NewCapacity(RE1,PHL_POW_") or any(
                name.startswith(f"TotalTechnologyAnnualActivity(RE1,{technology},") for technology in SUPPLY_TECHS
            ):
                values[name] = float(match.group(2))
    return status, values


def solve_checks(candidate: Path, baseline_run: Path | None) -> dict:
    run_dir = candidate / "res" / "TOMORROWLAND"
    status, values = selected_solution(run_dir / "results.txt")
    if not status.startswith("Optimal - objective value"):
        raise AssertionError(f"candidate solve is not optimal: {status}")
    objective = float(status.rsplit(" ", 1)[1])

    additions = {}
    for technology in PIN_TECHS:
        additions[technology] = {}
        for year in range(2020, 2026):
            name = f"NewCapacity(RE1,{technology},{year})"
            additions[technology][year] = values[name]
    for technology in STOCK_ONLY:
        for year in YEARS:
            name = f"NewCapacity(RE1,{technology},{year})"
            if abs(values[name]) > 1e-8:
                raise AssertionError(f"stock-only candidate build: {name}={values[name]}")
    for year in YEARS:
        name = f"NewCapacity(RE1,PHL_POW_PP_COAL,{year})"
        cap = 2 if year <= 2029 else 2.5 if year == 2030 else 0
        if values[name] > cap + 1e-8:
            raise AssertionError(f"coal construction cap violated: {name}={values[name]} > {cap}")

    benchmark_comparison = {}
    for technology, benchmarks in BENCHMARK_ADDITIONS.items():
        benchmark_comparison[technology] = {
            year: {
                "benchmark_gw": benchmark,
                "model_gw": additions[technology][year],
                "difference_gw": additions[technology][year] - benchmark,
            }
            for year, benchmark in benchmarks.items()
        }

    supply = {}
    for technology in SUPPLY_TECHS:
        supply[technology] = {}
        for year in YEARS:
            name = f"TotalTechnologyAnnualActivity(RE1,{technology},{year})"
            supply[technology][year] = values.get(name, 0.0)

    baseline = None
    if baseline_run is not None:
        baseline_status, baseline_values = selected_solution(baseline_run / "results.txt")
        baseline_objective = float(baseline_status.rsplit(" ", 1)[1])
        differences = []
        for name, value in values.items():
            if name.startswith("NewCapacity(RE1,PHL_POW_") and name in baseline_values:
                delta = value - baseline_values[name]
                if abs(delta) > 1e-7:
                    differences.append({"variable": name, "baseline": baseline_values[name], "candidate": value, "delta": delta})
        baseline = {
            "status": baseline_status,
            "objective": baseline_objective,
            "objective_difference": objective - baseline_objective,
            "objective_percent_difference": (objective - baseline_objective) / baseline_objective * 100,
            "source_identity": "nearest retained canonical only; not source-identical because current source contains intervening fossil-supply structure",
            "changed_power_new_capacity_cells_over_1e-7": differences,
        }

    cbc_log = (run_dir / "cbc.log").read_text(encoding="utf-8")
    wall = re.search(r"Total time \(CPU seconds\):\s+([0-9.]+)\s+\(Wallclock seconds\):\s+([0-9.]+)", cbc_log)
    glpk = (run_dir / "glpk_check.log").read_text(encoding="utf-8")
    matrix = re.search(
        r"Number of rows\s*=\s*(\d+).*?Number of columns\s*=\s*(\d+).*?"
        r"Number of non-zeros \(matrix\)\s*=\s*(\d+).*?Number of non-zeros \(objrow\)\s*=\s*(\d+)",
        glpk,
        re.DOTALL,
    )
    if wall is None or matrix is None:
        raise AssertionError("could not parse CBC timing or GLPK matrix")
    return {
        "status": status,
        "objective": objective,
        "cbc_cpu_seconds": float(wall.group(1)),
        "cbc_wall_seconds": float(wall.group(2)),
        "matrix": {
            "rows": int(matrix.group(1)),
            "columns": int(matrix.group(2)),
            "matrix_nonzeros": int(matrix.group(3)),
            "objective_nonzeros": int(matrix.group(4)),
        },
        "stock_only_new_capacity_zero": True,
        "coal_new_capacity_within_effective_cap": True,
        "observed_additions_are_benchmark_only": benchmark_comparison,
        "fossil_supply_activity_pj": supply,
        "baseline_comparison": baseline,
        "results_sha256": digest(run_dir / "results.txt"),
        "lp_sha256": digest(run_dir / "lp.lp"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--baseline-run", type=Path)
    parser.add_argument("--with-generated", action="store_true")
    parser.add_argument("--with-solve", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    control = args.control.resolve()
    candidate = args.candidate.resolve()
    report = {
        "schema": "philippines-v18-power-investment-cleanup-validation-v1",
        "status": "pass",
        "control": str(control),
        "candidate": str(candidate),
        "source": source_diff(control, candidate, load(args.manifest.resolve())),
        "generated": generated_checks(candidate) if args.with_generated else "not run",
        "solve": solve_checks(candidate, args.baseline_run.resolve() if args.baseline_run else None) if args.with_solve else "not run",
        "optimizer_runs_for_candidate": 1 if args.with_solve else 0,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
