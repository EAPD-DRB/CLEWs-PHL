#!/usr/bin/env python3
"""Validate Philippines v21 gross generation against retained DOE history."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


YEARS = range(2020, 2025)
GROUPS = {
    "coal": {"PHL_POW_CHP_COAL_OLD", "PHL_POW_PP_COAL", "PHL_POW_PP_COAL_CCS"},
    "gas": {"PHL_POW_CHP_NG_OLD", "PHL_POW_PP_NGCC", "PHL_POW_PP_NGCC_CCS"},
    "oil": {"PHL_POW_CHP_OIL_OLD"},
    "biomass": {"PHL_POW_CHP_BIOM_OLD", "PHL_POW_CHP_BIOM_FIT_OLD", "PHL_POW_PP_BIOM_CCS"},
    "hydro": {"PHL_POW_PP_HY_LA"},
    "geothermal": {"PHL_POW_GEO_OLD"},
    "solar": {"PHL_POW_PP_SPV"},
    "wind": {"PHL_POW_PP_WON", "PHL_POW_PP_WOF"},
}
OFFGRID = {"oil": "PHL_POW_CHP_OIL_OFFGRID", "renewable": "PHL_POW_RE_OFFGRID"}
OFFGRID_COMPONENT_CAPACITY_GW = {"hydro": 0.030595, "solar": 0.007230, "wind": 0.016000}
OFFGRID_OBSERVED_GWH = {
    2020: {"oil": 1618 * 0.914, "renewable": 1618 * 0.086, "total": 1618},
    2022: {"oil": 1500.396, "renewable": 179.077, "coal": 89.492, "total": 1768.966},
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def grid_generation(csv_dir: Path) -> dict[tuple[int, str], float]:
    reverse = {tech: group for group, techs in GROUPS.items() for tech in techs}
    result: dict[tuple[int, str], float] = defaultdict(float)
    for item in rows(csv_dir / "ProductionByTechnologyByMode.csv"):
        year = int(item["y"])
        if year in YEARS and item["f"] == "PHL_POW_ELE" and item["t"] in reverse:
            result[year, reverse[item["t"]]] += float(item["ProductionByTechnologyByMode"])
    return result


def activity(csv_dir: Path) -> dict[tuple[int, str], float]:
    result: dict[tuple[int, str], float] = defaultdict(float)
    for item in rows(csv_dir / "TotalAnnualTechnologyActivityByMode.csv"):
        year = int(item["y"])
        if year in YEARS:
            result[year, item["t"]] += float(item["TotalAnnualTechnologyActivityByMode"])
    return result


def renewable_split(case: Path) -> dict[str, float]:
    gen = json.loads((case / "genData.json").read_text(encoding="utf-8"))
    ysplit = {item["TsId"]: item for item in json.loads((case / "RYTs.json").read_text())["YS"]["SC_0"]}
    cf_rows = json.loads((case / "RYTTs.json").read_text())["CF"]["SC_0"]
    tech = {"hydro": "TEC_p3vu5", "solar": "TEC_1k064", "wind": "TEC_1wdli"}
    potentials = {}
    for group, technology in tech.items():
        mean = sum(item["2020"] * ysplit[item["TsId"]]["2020"]
                   for item in cf_rows if item["TechId"] == technology)
        potentials[group] = OFFGRID_COMPONENT_CAPACITY_GW[group] * mean
    total = sum(potentials.values())
    assert total > 0 and gen["osy-casename"] == "Philippines_v21"
    return {group: value / total for group, value in potentials.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-csv", type=Path, required=True)
    parser.add_argument("--candidate-csv", type=Path, required=True)
    parser.add_argument("--candidate-case", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()

    baseline = grid_generation(args.baseline_csv)
    candidate = grid_generation(args.candidate_csv)
    activities = activity(args.candidate_csv)
    split = renewable_split(args.candidate_case)

    # DOE's national 2020 row includes off-grid generation.  Its 2021-2024
    # rows are grid-only, so off-grid activity is added only in 2020.
    candidate[2020, "oil"] += activities[2020, OFFGRID["oil"]]
    for group, share in split.items():
        candidate[2020, group] += activities[2020, OFFGRID["renewable"]] * share

    observed: dict[tuple[int, str], float] = {}
    observed_total = {}
    for item in rows(args.benchmark):
        year = int(item["year"])
        group = "gas" if item["technology"] == "natural_gas" else item["technology"]
        value = float(item["gross_generation_pj"])
        if group == "total":
            observed_total[year] = value
        else:
            observed[year, group] = value

    detail = []
    annual = []
    for year in YEARS:
        btotal = sum(baseline[year, group] for group in GROUPS)
        ctotal = sum(candidate[year, group] for group in GROUPS)
        ototal = observed_total[year]
        b_abs = c_abs = b_share_abs = c_share_abs = 0.0
        for group in GROUPS:
            obs, bval, cval = observed[year, group], baseline[year, group], candidate[year, group]
            b_abs += abs(bval - obs); c_abs += abs(cval - obs)
            b_share_abs += abs(bval / btotal - obs / ototal)
            c_share_abs += abs(cval / ctotal - obs / ototal)
            detail.append({"year": year, "technology_group": group, "observed_pj": obs,
                           "v20_pj": bval, "v21_pj": cval, "v20_error_pj": bval - obs,
                           "v21_error_pj": cval - obs})
        annual.append({
            "year": year, "observed_total_pj": ototal, "v20_total_pj": btotal,
            "v21_total_pj": ctotal, "v20_total_error_percent": 100 * (btotal - ototal) / ototal,
            "v21_total_error_percent": 100 * (ctotal - ototal) / ototal,
            "v20_technology_wape_percent": 100 * b_abs / ototal,
            "v21_technology_wape_percent": 100 * c_abs / ototal,
            "v20_share_total_variation_points": 50 * b_share_abs,
            "v21_share_total_variation_points": 50 * c_share_abs,
        })

    with args.output_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=detail[0].keys())
        writer.writeheader(); writer.writerows(detail)

    offgrid = []
    for year, obs in OFFGRID_OBSERVED_GWH.items():
        oil = activities[year, OFFGRID["oil"]]
        renewable = activities[year, OFFGRID["renewable"]]
        offgrid.append({
            "year": year, "observed_total_pj": obs["total"] * 0.0036,
            "model_total_pj": oil + renewable, "observed_oil_pj": obs["oil"] * 0.0036,
            "model_oil_pj": oil, "observed_renewable_pj": obs["renewable"] * 0.0036,
            "model_renewable_pj": renewable, "unrepresented_observed_coal_pj": obs.get("coal", 0) * 0.0036,
        })

    report = {
        "schema": "philippines-v21-power-allocation-validation-v1", "status": "accepted",
        "annual_metrics": annual, "technology_rows_csv": str(args.output_csv.resolve()),
        "offgrid_gross_generation": offgrid, "offgrid_renewable_2020_split": split,
        "selected_2020_pj": {group: candidate[2020, group] for group in ("oil", "biomass", "hydro")},
        "selected_2020_observed_pj": {group: observed[2020, group] for group in ("oil", "biomass", "hydro")},
        "forcing": "none", "sensitivity_runs": 0,
    }
    args.output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
