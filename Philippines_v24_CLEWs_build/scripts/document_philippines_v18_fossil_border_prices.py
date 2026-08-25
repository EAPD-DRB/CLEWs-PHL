#!/usr/bin/env python3
"""Record the PHL v18 fossil border-price correction in the canonical ledger."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
LEDGER = PACKAGE / "data_sources"
SNAPSHOTS = LEDGER / "snapshots"
CASE = PACKAGE.parent / "case" / "Philippines_v18"
CASE_DOCS = CASE / "documentation"
INPUTS = CASE_DOCS / "fossil_border_prices_inputs_2026-08-18.json"
VALIDATION = CASE_DOCS / "fossil_border_prices_validation_2026-08-18.json"
NARRATIVE = CASE_DOCS / "MODEL_FIXES_FOSSIL_BORDER_PRICES_2026-08-18.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(name: str) -> tuple[list[str], list[dict[str, str]]]:
    with (LEDGER / name).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def write_csv(name: str, fields: list[str], rows: list[dict[str, str]]) -> None:
    with (LEDGER / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def append_unique(rows: list[dict[str, str]], key: str, additions: list[dict[str, str]]) -> None:
    positions = {row[key]: index for index, row in enumerate(rows)}
    for row in additions:
        if row[key] in positions:
            rows[positions[row[key]]] = row
        else:
            positions[row[key]] = len(rows)
            rows.append(row)


def append_text_once(path: Path, marker: str, text: str) -> None:
    current = path.read_text(encoding="utf-8")
    if marker not in current:
        path.write_text(current.rstrip() + "\n\n" + text.strip() + "\n", encoding="utf-8")


def main() -> None:
    inputs = json.loads(INPUTS.read_text(encoding="utf-8"))
    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if inputs["schema"] != "philippines-v18-fossil-border-prices-input-ledger-v1":
        raise AssertionError("unexpected input ledger")
    if not validation["status"].startswith("pass_"):
        raise AssertionError("validation is incomplete")
    if not validation["promotion_verification"]["live_data_txt_byte_identical_to_solved_candidate"]:
        raise AssertionError("promotion identity is incomplete")

    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    retained = {}
    for source in (INPUTS, VALIDATION):
        target = SNAPSHOTS / source.name
        target.write_bytes(source.read_bytes())
        retained[source.name] = target
    package_narrative = PACKAGE / "documentation" / NARRATIVE.name
    package_narrative.write_bytes(NARRATIVE.read_bytes())

    source_fields, sources = read_csv("SOURCES.csv")
    source_rows = [
        {
            "source_id": "SRC_PHL_PSA_TRADE_HS2701_2020_2024",
            "provider": "Philippine Statistics Authority / UN Comtrade",
            "product": "Philippine merchandise trade, HS 2701 coal",
            "edition": "annual records 2020-2024",
            "reference_period": "2020-2024",
            "geography": "Philippines; world partner",
            "variable": "customs CIF import value, FOB export value and reported mass",
            "source_unit": "USD and tonnes",
            "exact_locator": "Reporter 608; HS 2701; import and export annual records; exact values retained in fossil_border_prices_inputs_2026-08-18.json",
            "url": "https://openstat.psa.gov.ph/Database/Economic-and-Financial-Statistics/Trade-International-Merchandise-and-Domestic/Trade-Data-Downloads",
            "access_date": "2026-08-18",
            "license": "Official statistics / provider terms",
            "sha256": "",
            "local_file": "",
            "notes": "2024 import net weight was unavailable, so reported gross weight is used and explicitly flagged.",
        },
        {
            "source_id": "SRC_PHL_DOE_CRUDE_IMPORTS_2020_2024",
            "provider": "Philippines Department of Energy, Oil Industry Management Bureau",
            "product": "Year-end downstream oil industry reports FY2020, FY2022, FY2023 and FY2024",
            "edition": "published annual reports",
            "reference_period": "2020-2024",
            "geography": "Philippines",
            "variable": "crude import bill and crude import volume",
            "source_unit": "million USD and million litres",
            "exact_locator": "FY2020; FY2022 revised 2021 comparator and 2022; FY2023; FY2024 crude bill derived as total petroleum bill minus product bill",
            "url": "https://prod-cms.doe.gov.ph/documents/42673/843144/year-end-comprehensive-report-fy2022-v3.pdf/dd04a5e9-30ed-c5f5-cc97-5b82f8bcdf8a",
            "access_date": "2026-08-18",
            "license": "Philippine government publication; provider terms",
            "sha256": "",
            "local_file": "",
            "notes": "All report URLs and exact values are retained in the input snapshot; bill and volume use the same DOE statistical scope.",
        },
        {
            "source_id": "SRC_PHL_PXP_GALOC_PRICES_2020_2024",
            "provider": "PXP Energy Corporation",
            "product": "Annual reports and Galoc realized crude selling prices",
            "edition": "2020-2024 annual reports",
            "reference_period": "2020-2024",
            "geography": "Galoc field, offshore Palawan, Philippines",
            "variable": "realized crude selling price",
            "source_unit": "USD/barrel",
            "exact_locator": "38.18; 70.46; 94.50; 80.50; 80.00 USD/bbl for 2020-2024",
            "url": "https://www.pxpenergy.com.ph/investor-relations/annual-reports/",
            "access_date": "2026-08-18",
            "license": "Company publication; provider terms",
            "sha256": "",
            "local_file": "",
            "notes": "Uses asset-realized prices rather than generic Brent or aggregate HS 2709 crude-plus-condensate values.",
        },
        {
            "source_id": "SRC_PHL_PSA_PSCC_HS2709",
            "provider": "Philippine Statistics Authority",
            "product": "Philippine Standard Commodity Classification heading 27.09",
            "edition": "online classification",
            "reference_period": "current classification accessed 2026-08-18",
            "geography": "Philippines",
            "variable": "commodity scope for crude petroleum oils and condensates",
            "source_unit": "classification",
            "exact_locator": "Heading 27.09",
            "url": "https://psa.gov.ph/classification/pscc/heading/27.09",
            "access_date": "2026-08-18",
            "license": "Official classification / provider terms",
            "sha256": "",
            "local_file": "",
            "notes": "Supports rejecting a mixed HS 2709 numerator with a DOE crude-only denominator.",
        },
    ]
    for source_id, title, path, note in (
        ("SRC_PHL_V18_FOSSIL_BORDER_INPUTS", "Philippines v18 fossil border-price input ledger", retained[INPUTS.name], "Raw values, formulas, exact cells, source URLs, classification and limitations."),
        ("SRC_PHL_V18_FOSSIL_BORDER_VALIDATION", "Philippines v18 fossil border-price validation ledger", retained[VALIDATION.name], "Baseline, candidate, matrix, solve, results, promotion identity and incomplete checks."),
    ):
        source_rows.append({
            "source_id": source_id,
            "provider": "MUIOGO Philippines v18 workflow",
            "product": title,
            "edition": "2026-08-18",
            "reference_period": "2020-2053",
            "geography": "Philippines",
            "variable": "source, calculation, generated-model and validation audit record",
            "source_unit": "record",
            "exact_locator": f"data_sources/snapshots/{path.name}",
            "url": "",
            "access_date": "2026-08-18",
            "license": "Repository license",
            "sha256": sha256(path),
            "local_file": f"snapshots/{path.name}",
            "notes": note,
        })
    append_unique(sources, "source_id", source_rows)
    write_csv("SOURCES.csv", source_fields, sources)

    assumption_fields, assumptions = read_csv("ASSUMPTIONS.csv")
    assumption_rows = [
        {
            "assumption_id": "ASM_PHL_V18_FOSSIL_BORDER_NONFORCING",
            "statement": "Border prices are exogenous economic drivers; observed extraction, import, export and source-share quantities remain validation benchmarks and are not activity constraints.",
            "central_value": "no trade quantity constraint",
            "unit": "classification",
            "evidence_source_ids": "SRC_PHL_V18_FOSSIL_BORDER_INPUTS;SRC_MUIO_FORMULATION",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "The model should choose domestic use, import and export routes endogenously from physical envelopes and consistent economic drivers.",
            "notes": "No TAL, TAU, share, equality or calibration window is added by this correction.",
        },
        {
            "assumption_id": "ASM_PHL_V18_COAL_ENERGY_CONTENT_22_1",
            "statement": "Coal customs unit values are converted with 22.1 GJ per tonne, the retained Philippine coal energy-content basis.",
            "central_value": "22.1",
            "unit": "GJ/tonne",
            "evidence_source_ids": "SRC_PHL_V18_FOSSIL_BORDER_INPUTS",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "Provides one explicit energy normalization for CIF and FOB customs values.",
            "notes": "Grade-specific calorific values remain unavailable and are recorded as a gap.",
        },
        {
            "assumption_id": "ASM_PHL_V18_CRUDE_ENERGY_CONVERSION",
            "statement": "Crude values are converted with 6.119 GJ/barrel and 158.987294928 litres/barrel.",
            "central_value": "6.119;158.987294928",
            "unit": "GJ/barrel;litres/barrel",
            "evidence_source_ids": "SRC_PHL_V18_FOSSIL_BORDER_INPUTS",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "Converts DOE million-litre volumes and Galoc USD/barrel prices to the model's MUSD/PJ convention.",
            "notes": "MUSD/PJ is numerically equal to USD/GJ.",
        },
        {
            "assumption_id": "ASM_PHL_V18_FOSSIL_HOMOGENEOUS_POOLS",
            "statement": "The existing single coal pool and single crude pool treat domestic and imported energy as interchangeable after source tagging.",
            "central_value": "one pool per fuel",
            "unit": "topology",
            "evidence_source_ids": "SRC_PHL_V18_FOSSIL_BORDER_INPUTS;SRC_PHL_V18_FOSSIL_BORDER_VALIDATION",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "No grade, port, plant-specification or refinery-compatibility substructure is added in this minimal price correction.",
            "notes": "This causes zero modeled exports under corrected price parity and is disclosed rather than hidden with pins.",
        },
    ]
    append_unique(assumptions, "assumption_id", assumption_rows)
    write_csv("ASSUMPTIONS.csv", assumption_fields, assumptions)

    gen = json.loads((CASE / "genData.json").read_text(encoding="utf-8"))
    tech_ids = {row["Tech"]: row["TechId"] for row in gen["osy-tech"]}
    definitions = {
        "coal_import": ("PHL_PRO_IMP_COAL", "SRC_PHL_PSA_TRADE_HS2701_2020_2024", "ASM_PHL_V18_COAL_ENERGY_CONTENT_22_1", "CIF_USD / tonnes / 22.1", "cif_usd;tonnes;22.1", "USD;tonnes;GJ/tonne"),
        "coal_export": ("PHL_PRO_EXP_COAL", "SRC_PHL_PSA_TRADE_HS2701_2020_2024", "ASM_PHL_V18_COAL_ENERGY_CONTENT_22_1", "-FOB_USD / tonnes / 22.1", "fob_usd;tonnes;22.1", "USD;tonnes;GJ/tonne"),
        "oil_import": ("PHL_PRO_IMP_OIL", "SRC_PHL_DOE_CRUDE_IMPORTS_2020_2024", "ASM_PHL_V18_CRUDE_ENERGY_CONVERSION", "bill_MUSD * 1e6 / (volume_ML * 1e6 / 158.987294928 * 6.119)", "bill_musd;volume_million_litres;158.987294928;6.119", "MUSD;million litres;litres/barrel;GJ/barrel"),
        "oil_export": ("PHL_PRO_EXP_OIL", "SRC_PHL_PXP_GALOC_PRICES_2020_2024", "ASM_PHL_V18_CRUDE_ENERGY_CONVERSION", "-realized_USD_per_barrel / 6.119", "usd_per_barrel;6.119", "USD/barrel;GJ/barrel"),
    }
    calc_fields, calculations = read_csv("CALCULATIONS.csv")
    map_fields, mappings = read_csv("MODEL_MAP.csv")
    calculation_rows = []
    mapping_rows = []
    for category, (technology, source_id, assumption_id, formula, input_keys, input_units) in definitions.items():
        for year, record in inputs["inputs"][category]["records"].items():
            suffix = f"{category.upper()}_{year}"
            calc_id = f"CALC_PHL_V18_FOSSIL_BORDER_{suffix}"
            map_id = f"MAP_PHL_V18_FOSSIL_BORDER_VC_{suffix}"
            values = []
            for key in input_keys.split(";"):
                if key in record:
                    values.append(str(record[key]))
                elif key in {"22.1", "158.987294928", "6.119"}:
                    values.append(key)
                else:
                    raise AssertionError(f"missing {category}/{year}/{key}")
            calculation_rows.append({
                "calculation_id": calc_id,
                "formula": formula,
                "source_ids": f"{source_id};SRC_PHL_V18_FOSSIL_BORDER_INPUTS",
                "assumption_ids": f"{assumption_id};ASM_PHL_V18_FOSSIL_BORDER_NONFORCING",
                "input_calculation_ids": "",
                "input_values": ";".join(values),
                "input_units": input_units,
                "output_value": str(record["after"]),
                "output_unit": "MUSD/PJ",
                "script_path": "scripts/document_philippines_v18_fossil_border_prices.py",
                "script_version": "2026-08-18",
                "notes": f"Before={record['before']}; full precision retained; import cost positive and export revenue negative.",
            })
            mapping_rows.append({
                "map_id": map_id,
                "model_file": "case/Philippines_v18/RYTM.json",
                "parameter": "VariableCost",
                "entity": f"{tech_ids[technology]} / {technology}",
                "mode": "1",
                "scenario": "SC_0; SC_3hgjb, SC_huc7i and SC_w03qj inherit",
                "years": year,
                "value_or_expression": str(record["after"]),
                "model_unit": "MUSD/PJ",
                "evidence_ids": f"{calc_id};{source_id};{assumption_id};ASM_PHL_V18_FOSSIL_BORDER_NONFORCING;SRC_MUIO_FORMULATION",
                "superseded_by": "",
                "evidence_type": "derived",
                "notes": "External economic driver; no endogenous trade or production quantity is prescribed.",
            })
    mapping_rows.extend([
        {
            "map_id": "MAP_PHL_V18_FOSSIL_BORDER_VALIDATED_SOLUTION",
            "model_file": "case/Philippines_v18/RYTM.json",
            "parameter": "validated VariableCost correction",
            "entity": "PHL_PRO_IMP_COAL;PHL_PRO_EXP_COAL;PHL_PRO_IMP_OIL;PHL_PRO_EXP_OIL",
            "mode": "1",
            "scenario": "TOMORROWLAND active scenario stack",
            "years": "2020-2053",
            "value_or_expression": "optimal objective 369762721.4037087; zero coal and oil exports; live RYTM.json and data.txt byte-identical to solved candidate",
            "model_unit": "status, objective and PJ",
            "evidence_ids": "SRC_PHL_V18_FOSSIL_BORDER_VALIDATION;ASM_PHL_V18_FOSSIL_BORDER_NONFORCING;ASM_PHL_V18_FOSSIL_HOMOGENEOUS_POOLS",
            "superseded_by": "",
            "evidence_type": "derived",
            "notes": "One candidate CBC optimization; live GLPK check passed; no live re-solve.",
        },
        {
            "map_id": "MAP_PHL_V18_FOSSIL_BORDER_EQUATION",
            "model_file": "WebAPP/SOLVERs/model.v.5.4.txt",
            "parameter": "VariableCost objective mapping",
            "entity": "RateOfActivity * YearSplit * VariableCost; OC1_OperatingCostsVariable",
            "mode": "1",
            "scenario": "all",
            "years": "2020-2053",
            "value_or_expression": "positive import cost; negative export revenue",
            "model_unit": "MUSD/PJ",
            "evidence_ids": "SRC_MUIO_FORMULATION;SRC_PHL_V18_FOSSIL_BORDER_INPUTS",
            "superseded_by": "",
            "evidence_type": "direct",
            "notes": "Exact equation path inspected before editing.",
        },
    ])
    for row in mappings:
        if row["map_id"] == "MAP_PHL_V18_PWR_FOSSIL_TRADE_DIAGNOSTIC":
            row["superseded_by"] = "MAP_PHL_V18_FOSSIL_BORDER_VALIDATED_SOLUTION"
    append_unique(calculations, "calculation_id", calculation_rows)
    append_unique(mappings, "map_id", mapping_rows)
    write_csv("CALCULATIONS.csv", calc_fields, calculations)
    write_csv("MODEL_MAP.csv", map_fields, mappings)

    gap_fields, gaps = read_csv("GAPS.csv")
    gap_rows = [
        {
            "item": "Coal export-import grade, location and price-parity representation",
            "why_absent": "Corrected Philippine CIF/FOB price parity removes the false export-and-reimport arbitrage, but the single homogeneous coal pool then chooses zero exports and cannot reproduce simultaneous exports of local grades and imports of plant-compatible grades.",
            "upgrade_source": "Sourced mine-specific coal calorific value and quality, plant fuel specifications, domestic logistics, export terminal capacity and costs, and energy-normalized FOB/CIF price series by grade and location.",
            "priority": "high",
            "notes": "Do not force observed exports. The candidate routes domestic coal domestically and records zero exports as a disclosed aggregation gap.",
        },
        {
            "item": "Crude grade and refinery-compatibility trade representation",
            "why_absent": "The single crude pool cannot represent Galoc exports alongside higher-cost imports of refinery-compatible crude, so corrected landed and realized prices produce zero exports and leave the 2020 extraction envelope unused.",
            "upgrade_source": "Refinery crude-slate specifications, Galoc assay and sales destinations, import grades, port and transport costs, and grade-specific landed/realized prices.",
            "priority": "high",
            "notes": "Do not force Galoc production or exports; add differentiated commodities and routes only with sourced mappings.",
        },
        {
            "item": "Fossil border-price real-currency normalization",
            "why_absent": "The 2020-2024 official annual unit values are installed numerically as MUSD/PJ, but the inherited case does not retain a complete common price-year and deflator ledger for all costs.",
            "upgrade_source": "Document the model-wide currency year and convert all nominal annual fuel prices and technology costs consistently with an authoritative deflator and exchange-rate series.",
            "priority": "medium",
            "notes": "This correction improves source and statistical-scope consistency without claiming a model-wide real-price rebasing.",
        },
    ]
    append_unique(gaps, "item", gap_rows)
    write_csv("GAPS.csv", gap_fields, gaps)

    change_fields, changes = read_csv("CHANGES.csv")
    change_row = {
        "change_id": "CHG_PHL_V18_FOSSIL_BORDER_PRICES_20260818",
        "date": "2026-08-18",
        "class": "B",
        "description": "Replaced 20 undocumented or inconsistent 2020-2024 coal and crude import/export VariableCost cells with Philippine customs, DOE and Galoc realized unit values while leaving physical envelopes, imports and trade quantities endogenous.",
        "model_objects": "case/Philippines_v18/RYTM.json VC.SC_0 mode 1 for PHL_PRO_IMP_COAL, PHL_PRO_EXP_COAL, PHL_PRO_IMP_OIL and PHL_PRO_EXP_OIL; 2025-2053 unchanged",
        "evidence_path": "documentation/MODEL_FIXES_FOSSIL_BORDER_PRICES_2026-08-18.md;data_sources/snapshots/fossil_border_prices_inputs_2026-08-18.json;data_sources/snapshots/fossil_border_prices_validation_2026-08-18.json",
        "map_rows_affected": ";".join(row["map_id"] for row in mapping_rows),
        "resolve_status": "resolved",
        "author": "Codex",
        "commit": "",
        "notes": "One disposable CBC run solved optimally at 369762721.4037087 in 288.70 wall seconds. The 2022-2023 full-envelope coal export-and-reimport artifact is eliminated; zero modeled exports and zero 2020 oil extraction remain disclosed homogeneous-pool gaps. Live source and data.txt are byte-identical to the candidate; live GLPK check passed; no live CBC rerun.",
    }
    append_unique(changes, "change_id", [change_row])
    write_csv("CHANGES.csv", change_fields, changes)

    append_text_once(
        PACKAGE / "documentation" / "HISTORY.md",
        "v18 fossil border prices",
        "| 2026-08-18 | v18 fossil border prices | Replaced 2020-2024 coal and crude border-price drivers with source-consistent Philippine CIF/FOB, DOE bill/volume and Galoc realized values; removed the false coal export-and-reimport arbitrage without trade pins | `MODEL_FIXES_FOSSIL_BORDER_PRICES_2026-08-18.md`; `../data_sources/snapshots/fossil_border_prices_validation_2026-08-18.json` |",
    )
    append_text_once(
        PACKAGE / "documentation" / "KNOWN_LIMITATIONS.md",
        "corrected fossil border prices",
        "- corrected fossil border prices remove the artificial coal export-and-reimport incentive, but the single homogeneous coal and crude pools cannot represent grade-, port-, plant- or refinery-specific simultaneous imports and exports; zero modeled exports and zero 2020 oil extraction remain disclosed benchmark gaps; and\n- the inherited case still lacks a complete model-wide real-currency-year and deflator ledger, so the official nominal annual unit values are not presented as a full cost-base rebasing.",
    )
    append_text_once(
        PACKAGE / "documentation" / "README.md",
        "MODEL_FIXES_FOSSIL_BORDER_PRICES_2026-08-18.md",
        "- `MODEL_FIXES_FOSSIL_BORDER_PRICES_2026-08-18.md`: official 2020-2024 coal and crude border-price sources, exact conversions and cells, equation mapping, non-forcing classification, candidate solve, promotion identity and disclosed homogeneous-fuel-pool limitations.",
    )
    append_text_once(
        PACKAGE / "data_sources" / "README.md",
        "fossil_border_prices_inputs_2026-08-18.json",
        "- Use `snapshots/fossil_border_prices_inputs_2026-08-18.json` and `snapshots/fossil_border_prices_validation_2026-08-18.json` for the exact 2020-2024 border-price inputs, calculations, source URLs, solved comparison and promotion identity.",
    )
    append_text_once(
        PACKAGE / "scripts" / "README.md",
        "document_philippines_v18_fossil_border_prices.py",
        "- `document_philippines_v18_fossil_border_prices.py` records the official fossil border-price sources, four assumptions, 20 changed-cell calculations and maps, two validation maps, gaps, change lineage and retained snapshots in the six-table canonical ledger.\n- `validate_philippines_v18_fossil_border_price_ledger.py` verifies exact cell-to-calculation-to-map coverage, retained hashes, cross-references, narrative and review workbook.",
    )

    print(json.dumps({
        "status": "pass",
        "sources_added": len(source_rows),
        "assumptions_added": len(assumption_rows),
        "calculations_added": len(calculation_rows),
        "model_map_rows_added": len(mapping_rows),
        "gaps_added_or_updated": len(gap_rows),
        "changes_added": 1,
        "snapshots_retained": len(retained),
    }, indent=2))


if __name__ == "__main__":
    main()
