#!/usr/bin/env python3
"""Apply the Philippines v18 non-forcing power-investment cleanup.

The model information cutoff is 2020. ResidualCapacity carries the fleet
operating at that cutoff and its physical retirement path. Observed additions
in 2021-2025 are validation benchmarks, not fixed NewCapacity outcomes.

This script changes only RYT.json in a caller-supplied disposable case:

* clear the 20 inherited 2021-2025 TAMinCI power-investment pins;
* open the matching investable technologies rather than retaining equal
  TAMinCI/TAMaxCI outcomes;
* make the four explicitly ``_OLD`` thermal technologies stock-only for the
  complete horizon;
* replace the mixed 2020-2025 coal values with the documented 2 GW/year
  construction envelope through 2029; and
* preserve every post-2029 deployment envelope and every scenario overlay.

No post-2020 observation is copied into ResidualCapacity and no project floor
is introduced. The December 2020 DOE committed-project register is retained as
screening evidence, but its aggregate categories are not a lossless mapping to
model technologies and the project rows include non-construction stages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


BASE = "SC_0"
EXPECTED_SOURCE_RYT_SHA256 = "d51fe9e4f249c06b9987ed311bbbd39d1ecd704c08a3a15819ab59dba52d571e"
DEFAULT_OPEN = 999999

PIN_VALUES: dict[str, dict[str, float]] = {
    "PHL_POW_PP_SPV": {
        "2021": 0.3024,
        "2022": 0.3049,
        "2023": 0.1568,
        "2024": 1.0012,
        "2025": 0.2749,
    },
    "PHL_POW_PP_COAL": {"2021": 0.725, "2022": 0.7694, "2024": 0.6},
    "PHL_POW_CHP_OIL_OLD": {"2021": 0.1798, "2022": 0.0973, "2024": 0.0112},
    "PHL_POW_CHP_BIOM_OLD": {"2022": 0.082, "2023": 0.006, "2024": 0.0099},
    "PHL_POW_PP_HY_LA": {"2022": 0.0159, "2023": 0.0468, "2024": 0.0352},
    "PHL_POW_GEO_OLD": {"2022": 0.0037, "2025": 0.0357},
    "PHL_POW_PP_NGCC": {"2025": 0.88},
}

INVESTABLE_PIN_TECHS = (
    "PHL_POW_PP_SPV",
    "PHL_POW_PP_NGCC",
    "PHL_POW_PP_HY_LA",
    "PHL_POW_GEO_OLD",
)

MATURE_2020_ENTRY = (
    "PHL_POW_PP_WON",
    "PHL_POW_PP_SPV",
    "PHL_POW_PP_NGCC",
    "PHL_POW_PP_HY_LA",
    "PHL_POW_GEO_OLD",
)

STOCK_ONLY = (
    "PHL_POW_CHP_COAL_OLD",
    "PHL_POW_CHP_NG_OLD",
    "PHL_POW_CHP_OIL_OLD",
    "PHL_POW_CHP_BIOM_OLD",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def rows_by_name(block: dict, scenario: str, id_to_name: dict[str, str]) -> dict[str, dict]:
    return {id_to_name[row["TechId"]]: row for row in block[scenario]}


def record_change(changes: list[dict], parameter: str, technology: str, year: str, row: dict, after) -> None:
    before = row[year]
    if before == after:
        return
    row[year] = after
    changes.append(
        {
            "parameter": parameter,
            "scenario": BASE,
            "technology": technology,
            "year": int(year),
            "before": before,
            "after": after,
        }
    )


def apply(case: Path, manifest_path: Path) -> dict:
    ryt_path = case / "RYT.json"
    gen_path = case / "genData.json"
    if sha256(ryt_path) != EXPECTED_SOURCE_RYT_SHA256:
        raise AssertionError("RYT source fingerprint is not the approved pre-change source")

    gen = read_json(gen_path)
    ryt_before = read_json(ryt_path)
    ryt = read_json(ryt_path)
    id_to_name = {item["TechId"]: item["Tech"] for item in gen["osy-tech"]}
    name_to_id = {name: tech_id for tech_id, name in id_to_name.items()}
    required = set(PIN_VALUES) | set(MATURE_2020_ENTRY) | set(STOCK_ONLY)
    missing = sorted(required - set(name_to_id))
    if missing:
        raise KeyError(f"missing technologies: {missing}")

    min_rows = rows_by_name(ryt["TAMinCI"], BASE, id_to_name)
    max_rows = rows_by_name(ryt["TAMaxCI"], BASE, id_to_name)
    changes: list[dict] = []

    # Observed 2021-2025 additions are benchmarks, not forced investment.
    for technology, year_values in PIN_VALUES.items():
        for year, expected in year_values.items():
            if min_rows[technology][year] != expected:
                raise AssertionError(
                    f"unexpected TAMinCI source value for {technology} {year}: "
                    f"{min_rows[technology][year]} != {expected}"
                )
            record_change(changes, "TAMinCI", technology, year, min_rows[technology], 0)

    # Mature investable generators may be selected in the first model year.
    for technology in MATURE_2020_ENTRY:
        if max_rows[technology]["2020"] != 0:
            raise AssertionError(f"unexpected 2020 TAMaxCI for {technology}")
        record_change(changes, "TAMaxCI", technology, "2020", max_rows[technology], DEFAULT_OPEN)

    # Remove the matching exact upper bounds for investable technologies.
    for technology in INVESTABLE_PIN_TECHS:
        for year, expected in PIN_VALUES[technology].items():
            if max_rows[technology][year] != expected:
                raise AssertionError(
                    f"unexpected TAMaxCI pin for {technology} {year}: "
                    f"{max_rows[technology][year]} != {expected}"
                )
            record_change(changes, "TAMaxCI", technology, year, max_rows[technology], DEFAULT_OPEN)

    # The OLD thermal representations are inherited stock, never new entry.
    for technology in STOCK_ONLY:
        for year in (str(value) for value in range(2020, 2054)):
            record_change(changes, "TAMaxCI", technology, year, max_rows[technology], 0)

    # A physical annual coal construction ceiling replaces pins and defaults.
    coal = max_rows["PHL_POW_PP_COAL"]
    for year in (str(value) for value in range(2020, 2030)):
        record_change(changes, "TAMaxCI", "PHL_POW_PP_COAL", year, coal, 2)

    # Preserve the established later coal envelope exactly.
    expected_later = {
        **{str(year): 2.5 for year in range(2030, 2040)},
        **{str(year): 3 for year in range(2040, 2051)},
        **{str(year): 5 for year in range(2051, 2054)},
    }
    for year, expected in expected_later.items():
        if coal[year] != expected:
            raise AssertionError(f"unexpected post-2029 coal envelope {year}: {coal[year]} != {expected}")

    # Only the two intended parameter blocks in SC_0 may move.
    years = [str(year) for year in gen["osy-years"]]
    moved = []
    for parameter, scenario_rows in ryt.items():
        for scenario, rows in scenario_rows.items():
            before_rows = {row["TechId"]: row for row in ryt_before[parameter][scenario]}
            for row in rows:
                for year in years:
                    if row[year] != before_rows[row["TechId"]][year]:
                        moved.append((parameter, scenario, id_to_name[row["TechId"]], int(year)))
    intended = {(item["parameter"], item["scenario"], item["technology"], item["year"]) for item in changes}
    if set(moved) != intended:
        raise AssertionError(f"source diff outside allowlist: {sorted(set(moved) ^ intended)[:10]}")

    if len([item for item in changes if item["parameter"] == "TAMinCI"]) != 20:
        raise AssertionError("the candidate must clear exactly 20 TAMinCI cells")
    if len([item for item in changes if item["parameter"] == "TAMaxCI"]) != 42:
        raise AssertionError("the candidate must change exactly 42 TAMaxCI cells")

    write_json(ryt_path, ryt)
    manifest = {
        "schema": "philippines-v18-power-investment-cleanup-v1",
        "case": str(case),
        "source_ryt_sha256": EXPECTED_SOURCE_RYT_SHA256,
        "candidate_ryt_sha256": sha256(ryt_path),
        "information_cutoff": "2020",
        "equations": {
            "new_capacity_ceiling": "NCC1: NewCapacity[r,t,y] <= TotalAnnualMaxCapacityInvestment[r,t,y]",
            "residual_and_vintage_capacity": "CAa1/CAa2",
        },
        "classifications": {
            "RC": "unchanged 2020 initial physical stock and retirement path",
            "2021_2025_observed_additions": "benchmark only",
            "coal_envelope": "continuing physical construction/permitting/financing/grid constraint",
            "old_thermal_entry_zero": "technology-role constraint; residual stock remains available",
            "project_minimums": "none added; no lossless project-to-technology/COD proof",
        },
        "changed_cell_count": len(changes),
        "changed_parameter_counts": {
            "TAMinCI": sum(item["parameter"] == "TAMinCI" for item in changes),
            "TAMaxCI": sum(item["parameter"] == "TAMaxCI" for item in changes),
        },
        "changes": changes,
        "unchanged": [
            "RC all scenarios",
            "all non-base scenario overlays",
            "all post-2029 PHL_POW_PP_COAL TAMaxCI values",
            "all non-RYT source files",
        ],
    }
    write_json(manifest_path, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    manifest = apply(args.case.resolve(), args.manifest.resolve())
    print(json.dumps({key: manifest[key] for key in ("candidate_ryt_sha256", "changed_cell_count", "changed_parameter_counts")}, indent=2))


if __name__ == "__main__":
    main()
