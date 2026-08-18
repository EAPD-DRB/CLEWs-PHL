#!/usr/bin/env python3
"""Validate the schema-ledger additions for the PHL v18 power cleanup."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
LEDGER = PACKAGE / "data_sources"
SNAPSHOTS = LEDGER / "snapshots"
OUTPUT = PACKAGE / "diagnostics" / "power_investment_schema_ledger_validation.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(name: str) -> list[dict[str, str]]:
    with (LEDGER / name).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream, restkey="_extra")
        rows = list(reader)
    if any(row.get("_extra") for row in rows):
        raise AssertionError(f"extra CSV fields in {name}")
    return rows


def by_id(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise AssertionError(f"duplicate {key}")
    return result


def split_ids(value: str) -> list[str]:
    return [item for item in value.replace(",", ";").split(";") if item]


def main() -> None:
    sources = by_id(table("SOURCES.csv"), "source_id")
    calculations = by_id(table("CALCULATIONS.csv"), "calculation_id")
    assumptions = by_id(table("ASSUMPTIONS.csv"), "assumption_id")
    mappings = by_id(table("MODEL_MAP.csv"), "map_id")
    changes = by_id(table("CHANGES.csv"), "change_id")
    gaps = {row["item"]: row for row in table("GAPS.csv")}

    manifest_path = SNAPSHOTS / "power_investment_cleanup_v18_2026-08-17.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if len(manifest["changes"]) != 62:
        raise AssertionError("manifest does not contain 62 cells")

    required_sources = {
        "SRC_PHL_DOE_POWER_PLANTS_DEC2020",
        "SRC_PHL_PEP_2020_2040_COMMITTED",
        "SRC_PHL_PEP_2023_2050_VOL2_COAL_TRADE",
        "SRC_PHL_V18_PWR_INV_MANIFEST",
        "SRC_PHL_V18_PWR_INV_VALIDATION",
        "SRC_PHL_V18_PWR_INV_SOLVE",
        "SRC_PHL_V18_PWR_INV_PROMOTION",
    }
    required_assumptions = {
        "ASM_PHL_V18_PWR_2020_INFORMATION_CUTOFF",
        "ASM_PHL_V18_PWR_NO_COMMITTED_MINIMA",
        "ASM_PHL_V18_PWR_MATURE_ENTRY_2020",
        "ASM_PHL_V18_DEPLOY_PP_COAL_2020_2029",
        "ASM_PHL_V18_PWR_ZERO_OVERRIDE_SEMANTICS",
    }
    required_extra_maps = {
        "MAP_PHL_V18_PWR_RC_UNCHANGED",
        "MAP_PHL_V18_PWR_COMMITTED_SCREEN",
        "MAP_PHL_V18_PWR_COAL_PHASEOUT_ZERO",
        "MAP_PHL_V18_PWR_VALIDATED_SOLUTION",
        "MAP_PHL_V18_PWR_FOSSIL_TRADE_DIAGNOSTIC",
    }
    if not required_sources <= sources.keys():
        raise AssertionError("missing cleanup source rows")
    if not required_assumptions <= assumptions.keys():
        raise AssertionError("missing cleanup assumption rows")
    if not required_extra_maps <= mappings.keys():
        raise AssertionError("missing cleanup summary map rows")

    retained_hashes = {}
    for source_id in sorted(required_sources):
        row = sources[source_id]
        if row.get("local_file"):
            path = LEDGER / row["local_file"]
            if not path.is_file() or sha256(path) != row["sha256"]:
                raise AssertionError(f"retained hash failure: {source_id}")
            retained_hashes[source_id] = row["sha256"]

    change_calc_ids = set()
    change_map_ids = set()
    for item in manifest["changes"]:
        slug = item["technology"].removeprefix("PHL_POW_")
        suffix = f"{item['parameter'].upper()}_{slug}_{item['year']}"
        calc_id = f"CALC_PHL_V18_PWR_INV_{suffix}"
        map_id = f"MAP_PHL_V18_PWR_INV_{suffix}"
        change_calc_ids.add(calc_id)
        change_map_ids.add(map_id)
        calc = calculations[calc_id]
        mapping = mappings[map_id]
        if calc["output_value"] != str(item["after"]):
            raise AssertionError(f"calculation value mismatch: {calc_id}")
        if mapping["years"] != str(item["year"]) or mapping["value_or_expression"] != str(item["after"]):
            raise AssertionError(f"model-map value mismatch: {map_id}")
        expected_parameter = (
            "TotalAnnualMinCapacityInvestment"
            if item["parameter"] == "TAMinCI"
            else "TotalAnnualMaxCapacityInvestment"
        )
        if mapping["parameter"] != expected_parameter:
            raise AssertionError(f"model-map parameter mismatch: {map_id}")

    if len(change_calc_ids) != 62 or len(change_map_ids) != 62:
        raise AssertionError("cell-level ledger coverage is not one-to-one")

    all_evidence = set(sources) | set(calculations) | set(assumptions)
    for map_id in sorted(change_map_ids | required_extra_maps):
        row = mappings[map_id]
        if row["evidence_type"] not in {"direct", "derived", "estimated"}:
            raise AssertionError(f"invalid evidence_type: {map_id}")
        missing = set(split_ids(row["evidence_ids"])) - all_evidence
        if missing:
            raise AssertionError(f"unresolved evidence in {map_id}: {sorted(missing)}")

    change = changes["CHG_PHL_V18_POWER_INVESTMENT_CLEANUP_20260817"]
    affected = set(split_ids(change["map_rows_affected"]))
    expected_maps = change_map_ids | required_extra_maps
    if affected != expected_maps or change["resolve_status"] != "resolved":
        raise AssertionError("CHANGES row does not close the exact map-row set")

    old_stock = assumptions["ASM_PHL_V18_DEPLOY_OLD_STOCK_ONLY"]
    if "2020-2053" not in old_stock["statement"]:
        raise AssertionError("legacy stock-only assumption was not extended to the full horizon")
    for item in (
        "Project-level mapping of end-2020 committed power capacity",
        "Coal export-import grade, location and price-parity representation",
        "Source-matched pre-change TOMORROWLAND result after fossil-supply restructuring",
    ):
        if item not in gaps:
            raise AssertionError(f"missing disclosed gap: {item}")

    workbook = LEDGER / "PHILIPPINES_V18_CANONICAL_SCHEMA_LEDGER.xlsx"
    narrative = PACKAGE / "documentation" / "MODEL_FIXES_POWER_INVESTMENT_CLEANUP_2026-08-17.md"
    if not workbook.is_file() or not narrative.is_file():
        raise AssertionError("review workbook or narrative is missing")

    report = {
        "schema": "philippines-v18-power-investment-ledger-validation-v1",
        "status": "pass",
        "cell_changes_in_manifest": 62,
        "cell_calculations_verified": len(change_calc_ids),
        "cell_model_maps_verified": len(change_map_ids),
        "summary_model_maps_verified": len(required_extra_maps),
        "sources_verified": len(required_sources),
        "retained_evidence_hashes_verified": len(retained_hashes),
        "assumptions_verified": len(required_assumptions) + 1,
        "gaps_verified": 3,
        "change_row_exact_map_set": True,
        "canonical_workbook_present": True,
        "narrative_present": True,
        "generic_provenance_validator_note": "New rows pass focused schema and cross-reference checks. The cumulative generic validator still reports three pre-existing archive-manifest digest mismatches unrelated to this change.",
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
