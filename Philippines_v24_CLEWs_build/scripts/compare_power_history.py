#!/usr/bin/env python3
"""Build the retained Philippines v20 power-history validation record."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


GROUPS = {
    "coal": {"PHL_POW_CHP_COAL_OLD", "PHL_POW_PP_COAL", "PHL_POW_PP_COAL_CCS"},
    "gas": {"PHL_POW_CHP_NG_OLD", "PHL_POW_PP_NGCC", "PHL_POW_PP_NGCC_CCS"},
    "oil": {"PHL_POW_CHP_OIL_OLD"},
    "biomass": {"PHL_POW_CHP_BIOM_OLD", "PHL_POW_PP_BIOM_CCS"},
    "hydro": {"PHL_POW_PP_HY_LA"},
    "geothermal": {"PHL_POW_GEO_OLD"},
    "solar": {"PHL_POW_PP_SPV"},
    "wind": {"PHL_POW_PP_WON", "PHL_POW_PP_WOF"},
}
YEARS = range(2020, 2025)


def read_generation(path: Path) -> dict[tuple[int, str], float]:
    reverse = {technology: group for group, technologies in GROUPS.items() for technology in technologies}
    result: dict[tuple[int, str], float] = defaultdict(float)
    with path.open(newline="", encoding="utf-8") as stream:
        for item in csv.DictReader(stream):
            year = int(item["y"])
            if year in YEARS and item["f"] == "PHL_POW_ELE" and item["t"] in reverse:
                result[year, reverse[item["t"]]] += float(item["ProductionByTechnologyByMode"])
    return result


def read_capacity(path: Path, value_column: str) -> dict[tuple[int, str], float]:
    reverse = {technology: group for group, technologies in GROUPS.items() for technology in technologies}
    result: dict[tuple[int, str], float] = defaultdict(float)
    with path.open(newline="", encoding="utf-8") as stream:
        for item in csv.DictReader(stream):
            year = int(item["y"])
            if year in YEARS and item["t"] in reverse:
                result[year, reverse[item["t"]]] += float(item[value_column])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-csv", type=Path, required=True)
    parser.add_argument("--candidate-csv", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--capacity-benchmark", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()

    baseline = read_generation(args.baseline_csv / "ProductionByTechnologyByMode.csv")
    candidate = read_generation(args.candidate_csv / "ProductionByTechnologyByMode.csv")
    total_capacity = read_capacity(args.candidate_csv / "TotalCapacityAnnual.csv", "TotalCapacityAnnual")
    new_capacity = read_capacity(args.candidate_csv / "NewCapacity.csv", "NewCapacity")

    observed: dict[tuple[int, str], float] = {}
    observed_total: dict[int, float] = {}
    benchmark_group = {"natural_gas": "gas"}
    with args.benchmark.open(newline="", encoding="utf-8") as stream:
        for item in csv.DictReader(stream):
            year = int(item["year"])
            group = benchmark_group.get(item["technology"], item["technology"])
            if group == "total":
                observed_total[year] = float(item["gross_generation_pj"])
            else:
                observed[year, group] = float(item["gross_generation_pj"])

    observed_capacity: dict[tuple[int, str], float] = {}
    with args.capacity_benchmark.open(newline="", encoding="utf-8") as stream:
        for item in csv.DictReader(stream):
            if item["technology_group"] != "total":
                observed_capacity[int(item["year"]), item["technology_group"]] = float(item["installed_capacity_mw"]) / 1000

    technology_rows = []
    annual = []
    for year in YEARS:
        btotal = sum(baseline[year, group] for group in GROUPS)
        ctotal = sum(candidate[year, group] for group in GROUPS)
        ototal = observed_total[year]
        b_abs = c_abs = b_share_abs = c_share_abs = 0.0
        for group in GROUPS:
            obs = observed[year, group]
            bval, cval = baseline[year, group], candidate[year, group]
            b_abs += abs(bval - obs)
            c_abs += abs(cval - obs)
            bshare, cshare, oshare = bval / btotal, cval / ctotal, obs / ototal
            b_share_abs += abs(bshare - oshare)
            c_share_abs += abs(cshare - oshare)
            technology_rows.append({
                "year": year, "technology_group": group, "observed_generation_pj": obs,
                "baseline_generation_pj": bval, "candidate_generation_pj": cval,
                "baseline_error_pj": bval - obs, "candidate_error_pj": cval - obs,
                "observed_share_percent": 100 * oshare, "baseline_share_percent": 100 * bshare,
                "candidate_share_percent": 100 * cshare,
                "observed_capacity_gw": observed_capacity[year, group],
                "candidate_total_capacity_gw": total_capacity[year, group],
                "candidate_new_capacity_gw": new_capacity[year, group],
            })
        annual.append({
            "year": year, "observed_total_generation_pj": ototal,
            "baseline_total_generation_pj": btotal, "candidate_total_generation_pj": ctotal,
            "baseline_total_error_percent": 100 * (btotal - ototal) / ototal,
            "candidate_total_error_percent": 100 * (ctotal - ototal) / ototal,
            "baseline_generation_wape_percent": 100 * b_abs / ototal,
            "candidate_generation_wape_percent": 100 * c_abs / ototal,
            "baseline_share_total_variation_percentage_points": 50 * b_share_abs,
            "candidate_share_total_variation_percentage_points": 50 * c_share_abs,
        })

    with args.output_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=technology_rows[0].keys())
        writer.writeheader()
        writer.writerows(technology_rows)

    report = {
        "schema": "philippines-v20-power-history-validation-v1",
        "status": "accepted",
        "observation_classification": {
            "E": ["DOE dependable capacity as a physical availability driver", "documented 2020-2021 power-plant take-or-pay contract economics"],
            "J": ["full domestic production envelope used as the disclosed maximum contract-payment proxy because plant GSPA quantities are unavailable"],
            "H": ["DOE 2020-2024 generation, installed capacity, and realized stock changes retained as benchmark-only history"],
            "forcing": "none",
        },
        "annual_metrics": annual,
        "technology_rows_csv": str(args.output_csv.resolve()),
        "binding_findings": [
            {"constraint": "AAC2_TotalAnnualTechnologyActivityUpperLimit(RE1,PHL_PRO_EXTR_NG,2020)", "activity_pj": 154.91844, "dual": -3.8673493},
            {"constraint": "AAC2_TotalAnnualTechnologyActivityUpperLimit(RE1,PHL_PRO_EXTR_NG,2021)", "activity_pj": 132.35486, "dual": -6.193906},
            {"constraint": "CAb1_PlannedMaintenance(RE1,PHL_POW_PP_HY_LA,2020)", "activity_pj": 19.075515, "dual": -7.6428744},
        ],
        "optimizer_run_ledger": [
            {"candidate": "r1", "status": "rejected diagnostic", "reason": "upstream marginal-cost reclassification subsidized every gas-using sector rather than the contracted power plants", "sensitivity": False},
            {"candidate": "r2", "status": "accepted", "reason": "plant-specific contract credit preserves other users' sourced gas price", "sensitivity": False},
        ],
        "known_limits": [
            "Oil and biomass generation remain zero because a national copperplate lacks off-grid, embedded, cogeneration and must-run service drivers.",
            "Hydro remains limited by its inherited annual availability profile; no observed hydro output was used to set it.",
            "The 2020 benchmark includes off-grid and embedded generation, while the DOE summary is grid-only from 2021 onward.",
            "Realized 2021-2024 installed-capacity changes are validation benchmarks and are not imposed as model investment equalities.",
            "No three-grid topology was added because regional generation without regional final-demand and network balances would not be a physical representation and would materially expand runtime.",
        ],
        "sensitivity_runs": 0,
    }
    args.output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
