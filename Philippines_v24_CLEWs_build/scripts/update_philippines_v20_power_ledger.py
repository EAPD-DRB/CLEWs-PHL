#!/usr/bin/env python3
"""Append the Philippines v20 power-history calibration to all six ledgers."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
LEDGER = PACKAGE / "data_sources"


def digest(relative: str) -> str:
    return hashlib.sha256((LEDGER / relative).read_bytes()).hexdigest()


def append_rows(filename: str, rows: list[dict[str, str]], key: str) -> None:
    path = LEDGER / filename
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        header = reader.fieldnames
        existing = list(reader)
    assert header is not None
    assert all(set(row) == set(header) for row in rows), (filename, header)
    known = {row[key] for row in existing}
    rows = [row for row in rows if row[key] not in known]
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=header, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(existing + rows)


def reconcile_existing_rows() -> None:
    path = LEDGER / "SOURCES.csv"
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream); header = reader.fieldnames; rows = list(reader)
    assert header is not None
    for item in rows:
        if item["source_id"] in {"SRC_V10_ENERGY_DONOR", "SRC_PHL_V15_MODEL_ARCHIVE"}:
            item["local_file"] = "evidence/INHERITED_V18_CURRENT_MODEL_ARCHIVE_MANIFEST.csv"
            if item["source_id"] == "SRC_PHL_V15_MODEL_ARCHIVE":
                item["exact_locator"] = "evidence/INHERITED_V18_CURRENT_MODEL_ARCHIVE_MANIFEST.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=header, lineterminator="\r\n"); writer.writeheader(); writer.writerows(rows)

    path = LEDGER / "MODEL_MAP.csv"
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream); header = reader.fieldnames; rows = list(reader)
    assert header is not None
    kinds = {
        "MAP_PHL_V20_AF_COAL_OLD": "derived", "MAP_PHL_V20_AF_GAS_OLD": "derived",
        "MAP_PHL_V20_AF_OIL_OLD": "derived", "MAP_PHL_V20_AF_BIOMASS_OLD": "derived",
        "MAP_PHL_V20_GAS_CONTRACT_FC_2020": "derived", "MAP_PHL_V20_GAS_CONTRACT_FC_2021": "derived",
        "MAP_PHL_V20_GAS_CONTRACT_VC_2020": "derived", "MAP_PHL_V20_GAS_CONTRACT_VC_2021": "derived",
        "MAP_PHL_V20_GENERATION_BENCHMARK": "derived", "MAP_PHL_V20_CAPACITY_BENCHMARK": "estimated",
        "MAP_PHL_V20_MODEL_ARCHIVE": "direct",
    }
    for item in rows:
        if item["map_id"] in kinds:
            item["evidence_type"] = kinds[item["map_id"]]
        if item["map_id"] in {"MAP_PHL_V20_GAS_CONTRACT_FC_2021", "MAP_PHL_V20_GAS_CONTRACT_VC_2021"}:
            for value in ("SRC_PHL_PEP_2023_2050_VOL2", "ASM_PHL_V20_NO_CONTRACT_CREDIT_AFTER_2021"):
                if value not in item["evidence_ids"].split(";"):
                    item["evidence_ids"] += ";" + value
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=header, lineterminator="\r\n"); writer.writeheader(); writer.writerows(rows)

    path = LEDGER / "CHANGES.csv"
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream); header = reader.fieldnames; rows = list(reader)
    assert header is not None
    for item in rows:
        if item["change_id"] == "CHG_PHL_V20_POWER_HISTORY_20260820":
            item["resolve_status"] = "resolved"
            lineage_note = "Historical CURRENT_MODEL_ARCHIVE pointers were repointed to a retained inherited byte before publishing the v20 current manifest."
            if lineage_note not in item["notes"]:
                item["notes"] += " " + lineage_note
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=header, lineterminator="\r\n"); writer.writeheader(); writer.writerows(rows)


def main() -> None:
    reconcile_existing_rows()
    sources = [
        {"source_id": "SRC_PHL_DOE_POWER_SUMMARY_2024", "provider": "Philippines Department of Energy", "product": "2024 Power Statistics Summary", "edition": "updated 2025-06-15", "reference_period": "2003-2024", "geography": "Philippines", "variable": "Gross generation; installed and dependable capacity by plant type", "source_unit": "GWh; MW", "exact_locator": "National summary tables and notes", "url": "https://legacy.doe.gov.ph/sites/default/files/pdf/energy_statistics/02_Summary.pdf", "access_date": "2026-08-20", "license": "Philippines government publication", "sha256": digest("snapshots/doe_power_validation_2020_2024.csv"), "local_file": "snapshots/doe_power_validation_2020_2024.csv", "notes": "Local derived extract retains every 2020-2024 generation row and the DOE boundary break; capacity extract is retained separately."},
        {"source_id": "SRC_PHL_DOE_POWER_CAPACITY_2020_2024", "provider": "Philippines Department of Energy", "product": "Derived 2020-2024 installed-capacity extract", "edition": "from 2024 Power Statistics Summary", "reference_period": "2020-2024", "geography": "Philippines", "variable": "Installed capacity by model technology group", "source_unit": "MW", "exact_locator": "Installed Capacity by Plant Type", "url": "https://legacy.doe.gov.ph/sites/default/files/pdf/energy_statistics/02_Summary.pdf", "access_date": "2026-08-20", "license": "Philippines government publication", "sha256": digest("snapshots/doe_power_capacity_2020_2024.csv"), "local_file": "snapshots/doe_power_capacity_2020_2024.csv", "notes": "2020 includes off-grid; 2021 onward is grid-only. Realized changes are validation benchmarks, not investment constraints."},
        {"source_id": "SRC_PHL_DOE_EXISTING_PLANTS_2020", "provider": "Philippines Department of Energy", "product": "List of Existing Power Plants as of 31 December 2020", "edition": "2020", "reference_period": "2020-12-31", "geography": "Philippines", "variable": "Installed and dependable capacity; plant type; commissioning date; grid", "source_unit": "MW; date", "exact_locator": "Luzon, Visayas, Mindanao and off-grid plant lists", "url": "https://legacy.doe.gov.ph/electric-power/list-existing-power-plants-december-31-2020", "access_date": "2026-08-20", "license": "Philippines government publication", "sha256": digest("snapshots/power_plant_clusters_2020.csv"), "local_file": "snapshots/power_plant_clusters_2020.csv", "notes": "Four defensible legacy plant-class clusters are retained; this is not a fabricated plant-by-plant register."},
        {"source_id": "SRC_PHL_NATGAS_MASTER_PLAN", "provider": "Philippines Department of Energy", "product": "Natural Gas Master Plan first report", "edition": "official report", "reference_period": "historical Malampaya contracts", "geography": "Luzon", "variable": "Gas-sales agreement structure and dispatch implication", "source_unit": "qualitative contract evidence", "exact_locator": "Discussion of Ilijan, Santa Rita and San Lorenzo take-or-pay GSPAs", "url": "https://legacy.doe.gov.ph/sites/default/files/pdf/downstream_natgas/first_report_naturalgasmasterplan.pdf", "access_date": "2026-08-20", "license": "Philippines government publication", "sha256": "", "local_file": "", "notes": "Reports that take-or-pay contracts made the plants effectively baseload; absent them they would be mid-merit."},
        {"source_id": "SRC_PHL_PEP_2023_2050_VOL2", "provider": "Philippines Department of Energy", "product": "Philippine Energy Plan 2023-2050 Volume II", "edition": "2023-2050", "reference_period": "2022 onward", "geography": "Philippines", "variable": "Malampaya GSPA expiry chronology", "source_unit": "date and narrative", "exact_locator": "Natural-gas supply discussion", "url": "https://doe.gov.ph/sites/default/files/pdf/pep/PEP%202023-2050%20%28Volume%20II%29.pdf", "access_date": "2026-08-20", "license": "Philippines government publication", "sha256": "", "local_file": "", "notes": "Documents that one GSPA ended in June 2022 and contracts began expiring in 2022; no v20 contract credit is extrapolated past 2021."},
        {"source_id": "SRC_PHL_V20_POWER_BUILD", "provider": "MUIOGO Philippines v20 workflow", "product": "Power calibration build manifest", "edition": "v20", "reference_period": "2020-2053", "geography": "Philippines", "variable": "Exact source hashes, availability ratios and contract-cost cells", "source_unit": "model-native", "exact_locator": "complete JSON", "url": "", "access_date": "2026-08-20", "license": "Repository license", "sha256": digest("snapshots/power_calibration_v20_build_manifest.json"), "local_file": "snapshots/power_calibration_v20_build_manifest.json", "notes": "Exact candidate source transformation."},
        {"source_id": "SRC_PHL_V20_POWER_VALIDATION", "provider": "MUIOGO Philippines v20 workflow", "product": "Power history validation", "edition": "v20", "reference_period": "2020-2024 and model horizon", "geography": "Philippines", "variable": "Source diffs; optimizer ledger; generation/capacity errors; bindings; runtime; promotion identity", "source_unit": "mixed validation units", "exact_locator": "complete JSON and technology CSV", "url": "", "access_date": "2026-08-20", "license": "Repository license", "sha256": digest("snapshots/power_calibration_v20_validation.json"), "local_file": "snapshots/power_calibration_v20_validation.json", "notes": "Generation observations remain benchmark-only; r1 rejected diagnostic and accepted r2 are both recorded."},
        {"source_id": "SRC_PHL_V20_MODEL_ARCHIVE", "provider": "MUIOGO Philippines v20 workflow", "product": "Philippines v20 result-free portable case", "edition": "v20.0.0", "reference_period": "2020-2053", "geography": "Philippines", "variable": "Complete editable source and documentation archive identity", "source_unit": "ZIP manifest", "exact_locator": "complete CSV", "url": "", "access_date": "2026-08-20", "license": "Repository license; third-party data retain provider terms", "sha256": digest("V20_MODEL_ARCHIVE_MANIFEST.csv"), "local_file": "V20_MODEL_ARCHIVE_MANIFEST.csv", "notes": "The archive itself is pinned by the hash inside the manifest and muio/SHA256SUMS; runtime results are excluded."},
    ]
    append_rows("SOURCES.csv", sources, "source_id")

    calculations = [
        {"calculation_id": "CALC_PHL_V20_AF_COAL_OLD", "formula": "dependable MW / installed MW", "source_ids": "SRC_PHL_DOE_EXISTING_PLANTS_2020", "assumption_ids": "ASM_PHL_V20_DEPENDABLE_RATIO_CONTINUES", "input_calculation_ids": "", "input_values": "10245.3;10943.9", "input_units": "MW;MW", "output_value": "0.9361653523880883", "output_unit": "fraction", "script_path": "scripts/apply_power_calibration.py", "script_version": "v20", "notes": "Applied to surviving closed legacy coal stock for 2020-2053."},
        {"calculation_id": "CALC_PHL_V20_AF_GAS_OLD", "formula": "dependable MW / installed MW", "source_ids": "SRC_PHL_DOE_EXISTING_PLANTS_2020", "assumption_ids": "ASM_PHL_V20_DEPENDABLE_RATIO_CONTINUES", "input_calculation_ids": "", "input_values": "3286.1;3452.5", "input_units": "MW;MW", "output_value": "0.9518030412744388", "output_unit": "fraction", "script_path": "scripts/apply_power_calibration.py", "script_version": "v20", "notes": "Applied to surviving closed legacy gas stock for 2020-2053."},
        {"calculation_id": "CALC_PHL_V20_AF_OIL_OLD", "formula": "dependable MW / installed MW", "source_ids": "SRC_PHL_DOE_EXISTING_PLANTS_2020", "assumption_ids": "ASM_PHL_V20_DEPENDABLE_RATIO_CONTINUES", "input_calculation_ids": "", "input_values": "3053.6;4236.6", "input_units": "MW;MW", "output_value": "0.7207666525043667", "output_unit": "fraction", "script_path": "scripts/apply_power_calibration.py", "script_version": "v20", "notes": "Applied to surviving closed legacy oil stock for 2020-2053."},
        {"calculation_id": "CALC_PHL_V20_AF_BIOMASS_OLD", "formula": "dependable MW / installed MW", "source_ids": "SRC_PHL_DOE_EXISTING_PLANTS_2020", "assumption_ids": "ASM_PHL_V20_DEPENDABLE_RATIO_CONTINUES", "input_calculation_ids": "", "input_values": "285.4;447.4", "input_units": "MW;MW", "output_value": "0.6379079123826553", "output_unit": "fraction", "script_path": "scripts/apply_power_calibration.py", "script_version": "v20", "notes": "Applied to surviving closed legacy biomass stock for 2020-2053."},
        {"calculation_id": "CALC_PHL_V20_GAS_RAW_PER_POWER", "formula": "power gas IAR * gas-processing IAR", "source_ids": "SRC_PHL_V20_POWER_BUILD", "assumption_ids": "", "input_calculation_ids": "", "input_values": "1.870042735;1.056771911", "input_units": "PJ processed gas/PJ power;PJ raw gas/PJ processed gas", "output_value": "1.9762086347176167", "output_unit": "PJ raw gas/PJ power activity", "script_path": "scripts/apply_power_calibration.py", "script_version": "v20", "notes": "Exact inherited full-precision source values."},
        {"calculation_id": "CALC_PHL_V20_GAS_CONTRACT_2020", "formula": "plant VC credit = -extraction VC * raw gas per power; fixed-cost addition = gas envelope * extraction VC / residual GW", "source_ids": "SRC_PHL_NATGAS_MASTER_PLAN;SRC_PHL_V20_POWER_BUILD", "assumption_ids": "ASM_PHL_V20_CONTRACT_ENVELOPE", "input_calculation_ids": "CALC_PHL_V20_GAS_RAW_PER_POWER", "input_values": "6.662111756970275;154.9184424432652;3.4525", "input_units": "MUSD/PJ raw gas;PJ raw gas;GW", "output_value": "VC=-13.16562277957841;FC=320.93815402543083", "output_unit": "MUSD/PJ power;MUSD/GW-year", "script_path": "scripts/apply_power_calibration.py", "script_version": "v20", "notes": "Full-envelope cost before/after is exactly 1108.0468159472537 MUSD."},
        {"calculation_id": "CALC_PHL_V20_GAS_CONTRACT_2021", "formula": "plant VC credit = -extraction VC * raw gas per power; fixed-cost addition = gas envelope * extraction VC / residual GW", "source_ids": "SRC_PHL_NATGAS_MASTER_PLAN;SRC_PHL_V20_POWER_BUILD", "assumption_ids": "ASM_PHL_V20_CONTRACT_ENVELOPE", "input_calculation_ids": "CALC_PHL_V20_GAS_RAW_PER_POWER", "input_values": "6.68807478018528;132.3548618308677;3.4525", "input_units": "MUSD/PJ raw gas;PJ raw gas;GW", "output_value": "VC=-13.216931130239278;FC=278.39368962952454", "output_unit": "MUSD/PJ power;MUSD/GW-year", "script_path": "scripts/apply_power_calibration.py", "script_version": "v20", "notes": "Full-envelope cost differs by only -1.14e-13 MUSD from the original due to floating point."},
        {"calculation_id": "CALC_PHL_V20_GENERATION_VALIDATION", "formula": "PJ=GWh*0.0036; WAPE=sum(abs(model-observed))/observed total; share TV=0.5*sum(abs(model share-observed share))", "source_ids": "SRC_PHL_DOE_POWER_SUMMARY_2024;SRC_PHL_V20_POWER_VALIDATION", "assumption_ids": "ASM_PHL_V20_GENERATION_BENCHMARK_ONLY", "input_calculation_ids": "", "input_values": "2020-2024 DOE rows and exported endogenous production", "input_units": "GWh;PJ", "output_value": "annual metrics in snapshots/power_calibration_v20_validation.json", "output_unit": "PJ;percent;percentage points", "script_path": "scripts/compare_power_history.py", "script_version": "v20", "notes": "No observed generation enters the solver."},
    ]
    append_rows("CALCULATIONS.csv", calculations, "calculation_id")

    assumptions = [
        {"assumption_id": "ASM_PHL_V20_DEPENDABLE_RATIO_CONTINUES", "statement": "The DOE 2020 dependable/nameplate ratio is a continuing availability proxy for each surviving closed legacy plant class.", "central_value": "technology-specific ratio", "unit": "fraction", "evidence_source_ids": "SRC_PHL_DOE_EXISTING_PLANTS_2020", "lower_bound": "", "upper_bound": "", "rationale": "Independent physical availability is preferable to AF=1 and is not inferred from generation.", "notes": "Applied across 2020-2053; residual-capacity retirement still controls survival."},
        {"assumption_id": "ASM_PHL_V20_CONTRACT_ENVELOPE", "statement": "The full domestic production envelope is the maximum 2020-2021 take-or-pay payment proxy because exact plant GSPA quantities were not recovered.", "central_value": "154.9184424432652 in 2020;132.3548618308677 in 2021", "unit": "PJ raw gas/year", "evidence_source_ids": "SRC_PHL_NATGAS_MASTER_PLAN;SRC_PHL_V20_POWER_BUILD", "lower_bound": "", "upper_bound": "", "rationale": "Preserves the known sunk-payment economics without imposing power generation or reallocating the sourced gas price to other sectors.", "notes": "Fixed cost is on closed residual capacity; activity remains endogenous."},
        {"assumption_id": "ASM_PHL_V20_NO_CONTRACT_CREDIT_AFTER_2021", "statement": "No take-or-pay credit is extrapolated after 2021 because GSPAs began expiring in 2022 and exact contract tranches were not recovered.", "central_value": "credit=0 from 2022", "unit": "MUSD/PJ power activity", "evidence_source_ids": "SRC_PHL_PEP_2023_2050_VOL2", "lower_bound": "", "upper_bound": "", "rationale": "Avoids inventing a historical obligation after documented expiry began.", "notes": "Post-2021 gas generation remains endogenous under ordinary delivered fuel cost."},
        {"assumption_id": "ASM_PHL_V20_GENERATION_BENCHMARK_ONLY", "statement": "DOE technology generation and realized installed-capacity changes are validation benchmarks and never solver targets.", "central_value": "no forcing", "unit": "classification", "evidence_source_ids": "SRC_PHL_DOE_POWER_SUMMARY_2024", "lower_bound": "", "upper_bound": "", "rationale": "Dispatch, shares, and investment are endogenous outcomes.", "notes": "No TAL/TAU, fixed share, realized investment equality, or deviation penalty was added."},
    ]
    append_rows("ASSUMPTIONS.csv", assumptions, "assumption_id")

    maps = [
        {"map_id": "MAP_PHL_V20_AF_COAL_OLD", "model_file": "RYT.json", "parameter": "AF", "entity": "TEC_pyjfk / PHL_POW_CHP_COAL_OLD", "mode": "", "scenario": "SC_0; others inherit", "years": "2020-2053", "value_or_expression": "0.9361653523880883", "model_unit": "fraction", "evidence_ids": "SRC_PHL_DOE_EXISTING_PLANTS_2020;CALC_PHL_V20_AF_COAL_OLD;ASM_PHL_V20_DEPENDABLE_RATIO_CONTINUES", "superseded_by": "", "evidence_type": "E physical driver", "notes": "136 total AF cells change across four legacy fleets."},
        {"map_id": "MAP_PHL_V20_AF_GAS_OLD", "model_file": "RYT.json", "parameter": "AF", "entity": "TEC_ze7d4 / PHL_POW_CHP_NG_OLD", "mode": "", "scenario": "SC_0; others inherit", "years": "2020-2053", "value_or_expression": "0.9518030412744388", "model_unit": "fraction", "evidence_ids": "SRC_PHL_DOE_EXISTING_PLANTS_2020;CALC_PHL_V20_AF_GAS_OLD;ASM_PHL_V20_DEPENDABLE_RATIO_CONTINUES", "superseded_by": "", "evidence_type": "E physical driver", "notes": "No generation value used."},
        {"map_id": "MAP_PHL_V20_AF_OIL_OLD", "model_file": "RYT.json", "parameter": "AF", "entity": "TEC_2hnym / PHL_POW_CHP_OIL_OLD", "mode": "", "scenario": "SC_0; others inherit", "years": "2020-2053", "value_or_expression": "0.7207666525043667", "model_unit": "fraction", "evidence_ids": "SRC_PHL_DOE_EXISTING_PLANTS_2020;CALC_PHL_V20_AF_OIL_OLD;ASM_PHL_V20_DEPENDABLE_RATIO_CONTINUES", "superseded_by": "", "evidence_type": "E physical driver", "notes": "No generation value used."},
        {"map_id": "MAP_PHL_V20_AF_BIOMASS_OLD", "model_file": "RYT.json", "parameter": "AF", "entity": "TEC_gthhk / PHL_POW_CHP_BIOM_OLD", "mode": "", "scenario": "SC_0; others inherit", "years": "2020-2053", "value_or_expression": "0.6379079123826553", "model_unit": "fraction", "evidence_ids": "SRC_PHL_DOE_EXISTING_PLANTS_2020;CALC_PHL_V20_AF_BIOMASS_OLD;ASM_PHL_V20_DEPENDABLE_RATIO_CONTINUES", "superseded_by": "", "evidence_type": "E physical driver", "notes": "Detailed 447.4 MW plant-list cluster used; rounded national summary difference disclosed."},
        {"map_id": "MAP_PHL_V20_GAS_CONTRACT_FC_2020", "model_file": "RYT.json", "parameter": "FC", "entity": "TEC_ze7d4 / PHL_POW_CHP_NG_OLD", "mode": "", "scenario": "SC_0; others inherit", "years": "2020", "value_or_expression": "320.93815402543083", "model_unit": "MUSD/GW-year", "evidence_ids": "SRC_PHL_NATGAS_MASTER_PLAN;CALC_PHL_V20_GAS_CONTRACT_2020;ASM_PHL_V20_CONTRACT_ENVELOPE", "superseded_by": "", "evidence_type": "E contract driver + J quantity proxy", "notes": "Before 22; closed residual stock makes payment sunk."},
        {"map_id": "MAP_PHL_V20_GAS_CONTRACT_FC_2021", "model_file": "RYT.json", "parameter": "FC", "entity": "TEC_ze7d4 / PHL_POW_CHP_NG_OLD", "mode": "", "scenario": "SC_0; others inherit", "years": "2021", "value_or_expression": "278.39368962952454", "model_unit": "MUSD/GW-year", "evidence_ids": "SRC_PHL_NATGAS_MASTER_PLAN;CALC_PHL_V20_GAS_CONTRACT_2021;ASM_PHL_V20_CONTRACT_ENVELOPE", "superseded_by": "", "evidence_type": "E contract driver + J quantity proxy", "notes": "Before 22; closed residual stock makes payment sunk."},
        {"map_id": "MAP_PHL_V20_GAS_CONTRACT_VC_2020", "model_file": "RYTM.json", "parameter": "VC", "entity": "TEC_ze7d4 / PHL_POW_CHP_NG_OLD", "mode": "1", "scenario": "SC_0; others inherit", "years": "2020", "value_or_expression": "-13.16562277957841", "model_unit": "MUSD/PJ activity", "evidence_ids": "SRC_PHL_NATGAS_MASTER_PLAN;CALC_PHL_V20_GAS_CONTRACT_2020;ASM_PHL_V20_CONTRACT_ENVELOPE", "superseded_by": "", "evidence_type": "E contract driver + J quantity proxy", "notes": "Plant-specific credit; extraction VC remains 6.662111756970275 for all gas users."},
        {"map_id": "MAP_PHL_V20_GAS_CONTRACT_VC_2021", "model_file": "RYTM.json", "parameter": "VC", "entity": "TEC_ze7d4 / PHL_POW_CHP_NG_OLD", "mode": "1", "scenario": "SC_0; others inherit", "years": "2021", "value_or_expression": "-13.216931130239278", "model_unit": "MUSD/PJ activity", "evidence_ids": "SRC_PHL_NATGAS_MASTER_PLAN;CALC_PHL_V20_GAS_CONTRACT_2021;ASM_PHL_V20_CONTRACT_ENVELOPE", "superseded_by": "", "evidence_type": "E contract driver + J quantity proxy", "notes": "Plant-specific credit; extraction VC remains 6.68807478018528 for all gas users."},
        {"map_id": "MAP_PHL_V20_GENERATION_BENCHMARK", "model_file": "data_sources/snapshots/doe_power_validation_2020_2024.csv", "parameter": "validation only", "entity": "coal;oil;gas;geothermal;hydro;biomass;solar;wind;total", "mode": "", "scenario": "BASE comparison", "years": "2020-2024", "value_or_expression": "45 retained rows; PJ=GWh*0.0036", "model_unit": "PJ", "evidence_ids": "SRC_PHL_DOE_POWER_SUMMARY_2024;CALC_PHL_V20_GENERATION_VALIDATION;ASM_PHL_V20_GENERATION_BENCHMARK_ONLY", "superseded_by": "", "evidence_type": "H benchmark only", "notes": "Not present in source parameter JSON or solver input."},
        {"map_id": "MAP_PHL_V20_CAPACITY_BENCHMARK", "model_file": "data_sources/snapshots/doe_power_capacity_2020_2024.csv", "parameter": "validation only", "entity": "technology-group installed capacity", "mode": "", "scenario": "BASE comparison", "years": "2020-2024", "value_or_expression": "45 retained rows", "model_unit": "MW", "evidence_ids": "SRC_PHL_DOE_POWER_CAPACITY_2020_2024;ASM_PHL_V20_GENERATION_BENCHMARK_ONLY", "superseded_by": "", "evidence_type": "H initial stock / benchmark only", "notes": "2021-2024 realized stock changes are not new-capacity equalities."},
        {"map_id": "MAP_PHL_V20_MODEL_ARCHIVE", "model_file": "muio/Philippines_v20_v20.0.0_MUIO.zip", "parameter": "portable source archive", "entity": "Philippines_v20", "mode": "", "scenario": "all source scenarios", "years": "2020-2053", "value_or_expression": "SHA-256 and member count in V20_MODEL_ARCHIVE_MANIFEST.csv", "model_unit": "archive identity", "evidence_ids": "SRC_PHL_V20_MODEL_ARCHIVE", "superseded_by": "", "evidence_type": "A retained artifact", "notes": "Result-free archive; internal root Philippines_v20/."},
    ]
    append_rows("MODEL_MAP.csv", maps, "map_id")

    gaps = [
        {"item": "Plant-by-plant power vintage and dependable-capacity register", "why_absent": "V20 uses four defensible DOE plant-class clusters; a full plant register was not needed for the bounded calibration and would add maintenance burden.", "upgrade_source": "Freeze DOE plant-list bytes; reconcile unit COD, retirement, dependable MW, heat rate, fuel compatibility and outage history.", "priority": "medium", "notes": "Recommended since v14 but not previously implemented or rejected."},
        {"item": "Luzon-Visayas-Mindanao dispatch and off-grid topology", "why_absent": "Regionalizing generation alone would be cosmetic; physical implementation requires regional final demands, transmission balances and interconnection limits and would expand solve time.", "upgrade_source": "DOE regional sales/generation/capacity, NGCP transmission limits and losses, and off-grid service demands.", "priority": "high", "notes": "Main reason oil/biomass remain zero and later gas is under-produced."},
        {"item": "Independent hydro inflow and annual energy budgets", "why_absent": "The inherited hydro annual availability binds at about 19.08 PJ; observed production cannot be used to back-calculate AF.", "upgrade_source": "Reservoir inflows, releases, storage, run-of-river hydrology, outages and seasonal deratings.", "priority": "high", "notes": "2020 hydro constraint dual is -7.6428744."},
        {"item": "Plant-level Malampaya GSPA contract quantities and expiry tranches", "why_absent": "Official sources establish take-or-pay economics and expiry beginning in 2022 but not the exact retained contract volumes by modeled plant and year.", "upgrade_source": "ERC-approved GSPAs, amendments, invoices or plant-level fuel procurement disclosures.", "priority": "medium", "notes": "V20 uses the full domestic production envelope as a disclosed maximum payment proxy only in 2020-2021."},
        {"item": "Consistent gross/net and grid/off-grid historical power boundary", "why_absent": "DOE 2020 includes grid-connected, embedded, off-grid and test output; the national summary is grid-only from 2021 onward.", "upgrade_source": "Freeze and reconcile DOE grid, off-grid, embedded generation, plant own-use and T&D loss tables for each year.", "priority": "medium", "notes": "Boundary break is retained in every validation row rather than silently spliced."},
    ]
    append_rows("GAPS.csv", gaps, "item")

    changes = [{"change_id": "CHG_PHL_V20_POWER_HISTORY_20260820", "date": "2026-08-20", "class": "B", "description": "Applied DOE dependable-capacity availability to four closed legacy power fleets and represented 2020-2021 Malampaya take-or-pay economics as a sunk fixed payment plus plant-specific contract credit; all generation and realized builds remain endogenous.", "model_objects": "genData.json;RYT.json:AF,FC;RYTM.json:VC", "evidence_path": "documentation/MODEL_FIXES_POWER_HISTORY_V20_2026-08-20.md;data_sources/snapshots/power_calibration_v20_validation.json", "map_rows_affected": ";".join(row["map_id"] for row in maps), "resolve_status": "validated_and_promoted", "author": "Codex", "commit": "", "notes": "Two optimizer runs total: r1 rejected diagnostic after sector-wide gas subsidy was identified; r2 accepted. Zero sensitivity runs. Live source and generated data.txt are byte-identical to accepted candidate."}]
    append_rows("CHANGES.csv", changes, "change_id")


if __name__ == "__main__":
    main()
