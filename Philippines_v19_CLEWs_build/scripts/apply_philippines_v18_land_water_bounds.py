#!/usr/bin/env python3
"""Build the parameter-only Philippines v18 land-water closure candidate.

The eight hydrological clusters are fixed to their existing source-derived
geographic TAUs by matching TALs. This replaces the aggregate UDC experiment,
which exceeded the solve-time incident threshold. Land-cover and crop modes
inside each fixed cluster remain endogenous.
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
from decimal import Decimal
from pathlib import Path
from typing import Any

import apply_philippines_v18_land_water_closure as common


def annual_row(payload: dict[str, Any], parameter: str, tech_id: str) -> dict[str, Any]:
    found = [row for row in payload[parameter][common.BASE] if row["TechId"] == tech_id]
    if len(found) != 1:
        raise AssertionError((parameter, tech_id, len(found)))
    return found[0]


def apply_land_bounds(
    gen: dict[str, Any], ryt: dict[str, Any]
) -> tuple[list[dict[str, str]], dict[str, str]]:
    technologies = common.keyed(gen["osy-tech"], "Tech")
    areas = common.assert_land_envelope(gen, ryt)
    changes: list[dict[str, str]] = []
    for name in common.CLUSTERS:
        tech_id = technologies[name]["TechId"]
        lower = annual_row(ryt, "TAL", tech_id)
        upper = annual_row(ryt, "TAU", tech_id)
        for year in common.YEARS:
            before = common.dec(lower[year])
            after = common.dec(upper[year])
            if before > after:
                raise AssertionError(f"cluster lower bound exceeds TAU: {name}/{year}")
            lower[year] = common.number(after)
            changes.append(
                {
                    "technology": name,
                    "technology_id": tech_id,
                    "year": year,
                    "before": str(before),
                    "after": str(after),
                }
            )
    return changes, areas


def bounds_ledger(
    gen: dict[str, Any],
    water_changes: list[dict[str, Any]],
    land_changes: list[dict[str, str]],
    cluster_areas: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:
    ledger = common.ledger_rows(gen, water_changes, cluster_areas)
    calculations = ledger["CALCULATIONS.csv"]
    calculations[0] = {
        "calculation_id": "CALC_PHL_V18_LAND_HYDROLOGY_BOUNDS",
        "formula": "TAL[LNDAGRPHLC01..C08,y] = existing TAU[LNDAGRPHLC01..C08,y]",
        "source_ids": "SRC_PHL_V15_MANIFEST;SRC_MUIO_FORMULATION",
        "assumption_ids": "ASM_PHL_V18_ALL_LAND_THROUGH_HYDROLOGY",
        "input_calculation_ids": "",
        "input_values": ";".join(f"{name}={value}" for name, value in cluster_areas.items()),
        "input_units": "1000 km2",
        "output_value": "eight fixed cluster totals sum to 295.8131 in every year",
        "output_unit": "1000 km2/year activity bounds",
        "script_path": "scripts/apply_philippines_v18_land_water_bounds.py",
        "script_version": "v1",
        "notes": "Existing source-derived geographic TAUs become matching TALs. The 30 modes inside every cluster remain endogenous. This parameter-only formulation replaces the aggregate UDC that exceeded the runtime threshold.",
    }

    maps = [
        row
        for row in ledger["MODEL_MAP.csv"]
        if not row["map_id"].startswith("MAP_PHL_V18_LAND_HYD_")
        and row["map_id"] != "MAP_PHL_V18_LAND_HYDROLOGY_CLOSURE"
    ]
    for item in land_changes:
        maps.append(
            {
                "map_id": f"MAP_PHL_V18_LAND_HYD_TAL_{item['technology']}_{item['year']}",
                "model_file": "case/Philippines_v18/RYT.json",
                "parameter": "TotalTechnologyAnnualActivityLowerLimit",
                "entity": f"{item['technology_id']} / {item['technology']}",
                "mode": "",
                "scenario": "SC_0; policy scenarios inherit",
                "years": item["year"],
                "value_or_expression": item["after"],
                "model_unit": "1000 km2/year",
                "evidence_ids": "CALC_PHL_V18_LAND_HYDROLOGY_BOUNDS;ASM_PHL_V18_ALL_LAND_THROUGH_HYDROLOGY",
                "superseded_by": "",
                "evidence_type": "derived",
                "notes": f"before TAL={item['before']}; unchanged TAU={item['after']}; geographic cluster total, not a crop/mode result",
            }
        )
    maps.append(
        {
            "map_id": "MAP_PHL_V18_LAND_HYDROLOGY_BOUNDS",
            "model_file": "case/Philippines_v18/RYT.json",
            "parameter": "TotalTechnologyAnnualActivityLowerLimit",
            "entity": "LNDAGRPHLC01..LNDAGRPHLC08",
            "mode": "all 30 modes remain endogenous",
            "scenario": "SC_0; policy scenarios inherit",
            "years": "2020-2053",
            "value_or_expression": "cluster TAL = existing source-derived cluster TAU; sum=295.8131",
            "model_unit": "1000 km2/year",
            "evidence_ids": "CALC_PHL_V18_LAND_HYDROLOGY_BOUNDS;ASM_PHL_V18_ALL_LAND_THROUGH_HYDROLOGY",
            "superseded_by": "",
            "evidence_type": "derived",
            "notes": "Aggregate index for 272 cell-level TAL mappings.",
        }
    )
    ledger["MODEL_MAP.csv"] = maps
    change = ledger["CHANGES.csv"][0]
    change["model_objects"] = "RYT.json TAL; RYTCM.json IAR/OAR"
    change["map_rows_affected"] = "MAP_PHL_V18_LAND_HYDROLOGY_BOUNDS;MAP_PHL_V18_WATER_COEFFICIENT_CLOSURE"
    change["notes"] = (
        "No crop, land-cover, irrigated-area, water-source share, withdrawal total or dispatch outcome is fixed. "
        "Eight continuing source-derived geographic cluster totals are fixed; the aggregate UDC experiment was rejected after a >430-second timeout."
    )
    return ledger


def model_fix_text(summary: dict[str, Any]) -> str:
    return f"""# Philippines v18 land-water closure repair — 2026-08-13

## Outcome and physical classification

All fixed national land is required to pass through the eight existing
hydrological clusters. The cluster totals are geography: their existing TAUs
sum exactly to the fixed 295.8131 thousand km2 national land account. Matching
TALs now require those source-derived areas to participate in hydrology.

The optimizer still chooses among all 30 crop and land-cover modes inside each
cluster. No crop output, land-cover mix, irrigated area, water-source share,
withdrawal total, generation or dispatch result is fixed.

- Initial stocks: unchanged.
- Final demands: unchanged.
- Continuing physical constraints: eight geographic cluster areas and
  conservation of water within every cluster-mode.
- Benchmark-only observations: rainfall volume, withdrawal and crop outcomes.

## Equation and parameter mapping

`RYT.json` receives `TAL = existing TAU` for `LNDAGRPHLC01` through `C08`,
2020-2053. This uses the existing annual activity-bound equations. The eight
areas sum to 295.8131 thousand km2, equal to fixed `MINLNDTOT`.

`RYTCM.json` places the existing 0.38 irrigation efficiency at the correct
boundary. `DEMAGRSURPHL` and `DEMAGRGWTPHL` retain raw-water IAR=1 and pumping
electricity, but produce 0.38 units of delivered `AGRWATPHL` per gross unit
withdrawn. Positive cluster irrigation IARs are multiplied by 0.38. For each
cluster, mode and year, precipitation and evapotranspiration remain unchanged;
groundwater and surface outputs are recalculated so
`P + delivered irrigation = ET + GWT + SUR`, preserving the former GWT share.

## Runtime formulation decision

The initially tested aggregate nine-member Tag-1 equality was mathematically
equivalent but timed out after 430 seconds, exceeding twice the prior v18 CBC
benchmark of 207.20 seconds. It was not promoted. The parameter-only TAL/TAU
formulation is therefore the candidate subject to a dedicated runtime A/B.

## Deterministic checks

- Cluster/national area: {summary['national_land_area_1000km2']} thousand km2.
- TAL cells changed: {summary['land_bound_cells_changed']}.
- Water coefficient cells changed: {summary['water_cells_changed']}.
- Maximum serialized cluster-mode water residual: {summary['water_checks']['maximum_absolute_serialized_water_balance_residual']}.
- Minimum nonnegative excess water: {summary['water_checks']['minimum_nonnegative_excess_water']} km3 per 1000 km2.
- Full-routing precipitation expected: 786.306717372 km3 (2658.12 mm) in
  2020 and 824.0806113969379 km3 in 2053, a 4.80396 percent increase.

## Known limitation

The 62 percent gross-to-field delivery loss remains outside the field-hydrology
boundary. Its partition among conveyance evaporation, drainage, seepage and
recoverable return flow is not invented; it remains documented in `GAPS.csv`.

## Validation status

Source generation, semantic diff, policy inheritance and deterministic
physical checks: **passed**. Full application generation, matrix check, CBC,
baseline comparison and promotion identity are recorded in the validation
manifest after completion.
"""


def apply(source: Path, target: Path, package: Path) -> dict[str, Any]:
    common.assert_source_identity(source)
    common.copy_case(source, target)
    before = {path.name: common.read_json(path) for path in target.glob("*.json")}
    gen = before["genData.json"]
    ryt = copy.deepcopy(before["RYT.json"])
    ratio = copy.deepcopy(before["RYTCM.json"])
    land_changes, cluster_areas = apply_land_bounds(gen, ryt)
    water_changes, water_checks = common.apply_water_values(gen, ratio)
    common.write_json(target / "RYT.json", ryt)
    common.write_json(target / "RYTCM.json", ratio)
    common.assert_scenario_inheritance(target, gen)

    after = {path.name: common.read_json(path) for path in target.glob("*.json")}
    changed = sorted(name for name in before if before[name] != after[name])
    if changed != ["RYT.json", "RYTCM.json"]:
        raise AssertionError(f"unexpected semantic diff: {changed}")

    if package.exists():
        raise FileExistsError(package)
    source_package = source.parent / "package"
    if not source_package.is_dir():
        raise FileNotFoundError(source_package)
    shutil.copytree(source_package, package)
    ledger = bounds_ledger(gen, water_changes, land_changes, cluster_areas)
    for filename, rows in ledger.items():
        common.append_rows(package / "data_sources" / filename, rows)

    summary = {
        "schema": "philippines-v18-land-water-bounds-build-v1",
        "status": "pass",
        "source_case": str(source),
        "target_case": str(target),
        "formulation": "parameter-only exact geographic cluster activity bounds",
        "rejected_formulation": "aggregate Tag-1 UDC; CBC timeout after 430 seconds",
        "changed_source_files": changed,
        "source_hashes": {
            name: common.sha256(source / name)
            for name in ("RYT.json", "RYTCM.json", "genData.json")
        },
        "target_hashes": {
            name: common.sha256(target / name)
            for name in ("RYT.json", "RYTCM.json", "genData.json")
        },
        "national_land_area_1000km2": "295.8131",
        "cluster_areas_1000km2": cluster_areas,
        "land_bound_cells_changed": len(land_changes),
        "water_cells_changed": len(water_changes),
        "water_checks": water_checks,
        "ledger_rows_added": {filename: len(rows) for filename, rows in ledger.items()},
        "non_forcing_assertions": {
            "final_demand_changed": False,
            "crop_or_land_cover_mode_fixed": False,
            "irrigated_area_fixed": False,
            "withdrawal_total_or_source_share_fixed": False,
            "source_derived_geographic_cluster_totals_fixed": True,
            "cluster_mode_water_conservation_restored": True,
        },
        "validation_status": {
            "source_generation": "passed",
            "deterministic_design_checks": "passed",
            "generate_datafile": "not_run",
            "preprocess_data": "not_run",
            "glpsol_check": "not_run",
            "cbc": "not_run",
            "baseline_comparison": "not_run",
            "promotion_identity": "not_run",
        },
    }
    note_text = model_fix_text(summary)
    note = package / "data_sources" / "calculation_notes" / "land_water_closure_v18_2026-08-13.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(note_text, encoding="utf-8")
    documentation = target / "documentation"
    documentation.mkdir(exist_ok=True)
    (documentation / "MODEL_FIXES_LAND_WATER_CLOSURE_2026-08-13.md").write_text(note_text, encoding="utf-8")
    manifest = package / "data_sources" / "snapshots" / "land_water_closure_build_manifest.json"
    common.write_json(manifest, summary)
    shutil.copy2(manifest, documentation / manifest.name)
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    apply(args.source.resolve(), args.target.absolute(), args.package.absolute())


if __name__ == "__main__":
    main()
