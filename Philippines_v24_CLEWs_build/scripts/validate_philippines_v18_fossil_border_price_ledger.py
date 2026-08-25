#!/usr/bin/env python3
"""Validate canonical-ledger coverage for the PHL v18 border-price change."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
LEDGER = PACKAGE / "data_sources"
CASE = PACKAGE.parent / "case" / "Philippines_v18"
OUTPUT = PACKAGE / "diagnostics" / "fossil_border_price_schema_ledger_validation.json"
CATEGORIES = {
    "coal_import": "PHL_PRO_IMP_COAL",
    "coal_export": "PHL_PRO_EXP_COAL",
    "oil_import": "PHL_PRO_IMP_OIL",
    "oil_export": "PHL_PRO_EXP_OIL",
}


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

    input_path = LEDGER / "snapshots" / "fossil_border_prices_inputs_2026-08-18.json"
    validation_path = LEDGER / "snapshots" / "fossil_border_prices_validation_2026-08-18.json"
    inputs = json.loads(input_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if validation["candidate"]["status"] != "optimal":
        raise AssertionError("candidate solve is not optimal")
    if validation["candidate"]["full_matrix"] != {
        "rows": 808384,
        "columns": 900022,
        "matrix_nonzeros": 12892647,
        "interpretation": "unchanged because the source edit changes objective coefficients only",
    }:
        raise AssertionError("candidate matrix record mismatch")

    required_sources = {
        "SRC_PHL_PSA_TRADE_HS2701_2020_2024",
        "SRC_PHL_DOE_CRUDE_IMPORTS_2020_2024",
        "SRC_PHL_PXP_GALOC_PRICES_2020_2024",
        "SRC_PHL_PSA_PSCC_HS2709",
        "SRC_PHL_V18_FOSSIL_BORDER_INPUTS",
        "SRC_PHL_V18_FOSSIL_BORDER_VALIDATION",
    }
    required_assumptions = {
        "ASM_PHL_V18_FOSSIL_BORDER_NONFORCING",
        "ASM_PHL_V18_COAL_ENERGY_CONTENT_22_1",
        "ASM_PHL_V18_CRUDE_ENERGY_CONVERSION",
        "ASM_PHL_V18_FOSSIL_HOMOGENEOUS_POOLS",
    }
    if not required_sources <= sources.keys() or not required_assumptions <= assumptions.keys():
        raise AssertionError("required source or assumption row is absent")

    retained_hashes = {}
    for source_id in ("SRC_PHL_V18_FOSSIL_BORDER_INPUTS", "SRC_PHL_V18_FOSSIL_BORDER_VALIDATION"):
        row = sources[source_id]
        path = LEDGER / row["local_file"]
        if not path.is_file() or sha256(path) != row["sha256"]:
            raise AssertionError(f"retained evidence hash failure: {source_id}")
        retained_hashes[source_id] = row["sha256"]

    gen = json.loads((CASE / "genData.json").read_text(encoding="utf-8"))
    ids = {row["Tech"]: row["TechId"] for row in gen["osy-tech"]}
    rytm = json.loads((CASE / "RYTM.json").read_text(encoding="utf-8"))
    source_rows = {(row["TechId"], row["MoId"]): row for row in rytm["VC"]["SC_0"]}
    cell_calculations = set()
    cell_mappings = set()
    for category, technology in CATEGORIES.items():
        for year, record in inputs["inputs"][category]["records"].items():
            suffix = f"{category.upper()}_{year}"
            calc_id = f"CALC_PHL_V18_FOSSIL_BORDER_{suffix}"
            map_id = f"MAP_PHL_V18_FOSSIL_BORDER_VC_{suffix}"
            calc = calculations[calc_id]
            mapping = mappings[map_id]
            expected = str(record["after"])
            if calc["output_value"] != expected or mapping["value_or_expression"] != expected:
                raise AssertionError(f"ledger value mismatch: {suffix}")
            if mapping["years"] != year or mapping["mode"] != "1":
                raise AssertionError(f"ledger coordinates mismatch: {suffix}")
            if mapping["entity"] != f"{ids[technology]} / {technology}":
                raise AssertionError(f"technology identity mismatch: {suffix}")
            if str(source_rows[(ids[technology], 1)][year]) != expected:
                raise AssertionError(f"live source mismatch: {suffix}")
            cell_calculations.add(calc_id)
            cell_mappings.add(map_id)

    if len(cell_calculations) != 20 or len(cell_mappings) != 20:
        raise AssertionError("expected exact 20-cell calculation and map coverage")
    summary_maps = {
        "MAP_PHL_V18_FOSSIL_BORDER_VALIDATED_SOLUTION",
        "MAP_PHL_V18_FOSSIL_BORDER_EQUATION",
    }
    all_evidence = set(sources) | set(calculations) | set(assumptions)
    for map_id in cell_mappings | summary_maps:
        row = mappings[map_id]
        missing = set(split_ids(row["evidence_ids"])) - all_evidence
        if missing:
            raise AssertionError(f"unresolved evidence in {map_id}: {sorted(missing)}")
    if mappings["MAP_PHL_V18_PWR_FOSSIL_TRADE_DIAGNOSTIC"]["superseded_by"] != "MAP_PHL_V18_FOSSIL_BORDER_VALIDATED_SOLUTION":
        raise AssertionError("prior fossil-trade diagnostic lacks lineage")

    change = changes["CHG_PHL_V18_FOSSIL_BORDER_PRICES_20260818"]
    if set(split_ids(change["map_rows_affected"])) != cell_mappings | summary_maps:
        raise AssertionError("change row does not close the exact affected maps")
    if change["resolve_status"] != "resolved":
        raise AssertionError("change row is not resolved")
    for item in (
        "Coal export-import grade, location and price-parity representation",
        "Crude grade and refinery-compatibility trade representation",
        "Fossil border-price real-currency normalization",
    ):
        if item not in gaps:
            raise AssertionError(f"missing gap: {item}")

    workbook = LEDGER / "PHILIPPINES_V18_CANONICAL_SCHEMA_LEDGER.xlsx"
    narrative = PACKAGE / "documentation" / "MODEL_FIXES_FOSSIL_BORDER_PRICES_2026-08-18.md"
    if not workbook.is_file() or not narrative.is_file():
        raise AssertionError("review workbook or narrative is missing")
    for path, marker in (
        (PACKAGE / "documentation" / "HISTORY.md", "v18 fossil border prices"),
        (PACKAGE / "documentation" / "KNOWN_LIMITATIONS.md", "corrected fossil border prices"),
        (PACKAGE / "documentation" / "README.md", "MODEL_FIXES_FOSSIL_BORDER_PRICES_2026-08-18.md"),
        (LEDGER / "README.md", "fossil_border_prices_inputs_2026-08-18.json"),
        (PACKAGE / "scripts" / "README.md", "document_philippines_v18_fossil_border_prices.py"),
    ):
        if marker not in path.read_text(encoding="utf-8"):
            raise AssertionError(f"missing narrative marker: {marker}")

    report = {
        "schema": "philippines-v18-fossil-border-price-ledger-validation-v1",
        "status": "pass",
        "changed_source_cells": 20,
        "cell_calculations_verified": len(cell_calculations),
        "cell_model_maps_verified": len(cell_mappings),
        "summary_model_maps_verified": len(summary_maps),
        "sources_verified": len(required_sources),
        "retained_evidence_hashes_verified": retained_hashes,
        "assumptions_verified": len(required_assumptions),
        "gaps_verified": 3,
        "prior_diagnostic_lineage_verified": True,
        "change_row_exact_map_set": True,
        "canonical_workbook_present": True,
        "narrative_markers_verified": 5,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
