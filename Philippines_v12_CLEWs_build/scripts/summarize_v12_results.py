#!/usr/bin/env python3
"""Summarize sector representation and crop-balance checks for v12."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
CASE = REPO / "WebAPP/DataStorage/Philippines_v12"
YEARS_TO_REPORT = {2020, 2030, 2050, 2053}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    gen = json.loads((CASE / "genData.json").read_text(encoding="utf-8"))
    tech_names = {item["Tech"] for item in gen["osy-tech"]}
    crop_options = sorted(
        name
        for name in tech_names
        if re.fullmatch(r"LND(CON|MZE|OTH|RCP|SGC|TOM)(H|L)(I|R)TOT", name)
    )
    clusters = sorted(
        name for name in tech_names if re.fullmatch(r"LNDAGRPHLC\d{2}", name)
    )
    land_cover = sorted(
        tech_names
        & {
            "LNDBARTOT",
            "LNDBLTTOT",
            "LNDFORTOT",
            "LNDGRSTOT",
            "LNDOTHTOT",
            "LNDWATTOT",
        }
    )
    irrigation = sorted(
        tech_names & {"DEMAGRGWTPHL", "DEMAGRSURPHL"}
    )
    endowments = sorted(tech_names & {"MINLNDTOT", "MINPRCPHL"})
    fisheries = sorted(
        name
        for name in tech_names
        if name.startswith("PHL_FSH_") or name == "PHL_POW_TD_FSH"
    )

    demand = {
        (row["FUEL"], int(row["YEAR"])): float(row["VALUE"])
        for row in rows(ROOT / "model/inputs/clewsy/AccumulatedAnnualDemand.csv")
    }
    balance_rows: list[dict[str, object]] = []
    run_summaries = {}
    for run_name in ("Base_v12", "PEP_v12"):
        result_dir = CASE / "res" / run_name
        production: dict[tuple[str, int], float] = defaultdict(float)
        for row in rows(result_dir / "csv/ProductionByTechnologyByMode.csv"):
            fuel = row["f"]
            year = int(row["y"])
            if fuel.startswith("CRP") and year in YEARS_TO_REPORT:
                production[(fuel, year)] += float(row["ProductionByTechnologyByMode"])
        for key, target in sorted(demand.items()):
            fuel, year = key
            if year not in YEARS_TO_REPORT:
                continue
            modeled = production[key]
            absolute_error = modeled - target
            relative_error = absolute_error / target if target else 0
            balance_rows.append(
                {
                    "run": run_name,
                    "crop": fuel,
                    "year": year,
                    "demand_Mt": target,
                    "production_Mt": modeled,
                    "absolute_error_Mt": absolute_error,
                    "relative_error": relative_error,
                    "status": "PASS" if abs(relative_error) <= 0.001 else "FAIL",
                }
            )

        result_header = (
            result_dir / "results.txt"
        ).read_text(encoding="utf-8", errors="replace").splitlines()[0]
        objective_match = re.search(r"objective value\s+([0-9.eE+-]+)", result_header)
        fisheries_activity_2020 = {
            row["t"]: float(row["TotalAnnualTechnologyActivityByMode"])
            for row in rows(
                result_dir / "csv/TotalAnnualTechnologyActivityByMode.csv"
            )
            if row["t"] in fisheries and int(row["y"]) == 2020
        }
        fisheries_new_capacity_2020 = {
            row["t"]: float(row["NewCapacity"])
            for row in rows(result_dir / "csv/NewCapacity.csv")
            if row["t"] in fisheries and int(row["y"]) == 2020
        }
        fisheries_electricity_2020 = sum(
            float(row["UseByTechnologyByMode"])
            for row in rows(result_dir / "csv/UseByTechnologyByMode.csv")
            if row["f"] == "PHL_FSH_ELE" and int(row["y"]) == 2020
        )
        run_summaries[run_name] = {
            "status": "Optimal" if result_header.startswith("Optimal") else result_header,
            "objective": (
                float(objective_match.group(1)) if objective_match else None
            ),
            "max_crop_balance_relative_error": max(
                abs(float(item["relative_error"]))
                for item in balance_rows
                if item["run"] == run_name
            ),
            "fisheries_2020": {
                "activity_PJ_useful": fisheries_activity_2020,
                "new_capacity_GW_useful": fisheries_new_capacity_2020,
                "delivered_electricity_PJ": fisheries_electricity_2020,
            },
        }

    with (ROOT / "diagnostics/crop_balance.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(balance_rows[0]))
        writer.writeheader()
        writer.writerows(balance_rows)

    cluster_rows = rows(
        ROOT / "geospatial/summary_stats/PHL_LandCover_byCluster_summary.csv"
    )
    summary = {
        "technology_count": len(gen["osy-tech"]),
        "commodity_count": len(gen["osy-comm"]),
        "inherited_v10_technology_count": 130,
        "fisheries": {
            "version": "v2.3",
            "technology_count": len(fisheries),
            "technologies": fisheries,
            "import_audit": "diagnostics/fisheries_v23_import_audit.json",
        },
        "new_nexus": {
            "technology_count": (
                len(crop_options)
                + len(clusters)
                + len(land_cover)
                + len(irrigation)
                + len(endowments)
            ),
            "crop_option_technologies": len(crop_options),
            "spatial_cluster_technologies": len(clusters),
            "land_cover_technologies": len(land_cover),
            "irrigation_technologies": len(irrigation),
            "land_and_precipitation_endowments": len(endowments),
            "crop_outputs": sorted({fuel for fuel, _ in demand}),
            "cluster_area_km2": sum(float(row["sqkm"]) for row in cluster_rows),
        },
        "integrated_runs": run_summaries,
        "crop_balance_status": (
            "PASS"
            if all(item["status"] == "PASS" for item in balance_rows)
            else "FAIL"
        ),
    }
    (ROOT / "diagnostics/sector_representation.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    if summary["crop_balance_status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
