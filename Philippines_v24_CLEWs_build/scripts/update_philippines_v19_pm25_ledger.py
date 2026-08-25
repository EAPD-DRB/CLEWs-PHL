#!/usr/bin/env python3
"""Append the v19 PM2.5 extension to the inherited six-table ledger."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
LEDGER = PACKAGE / "data_sources"
EVIDENCE = LEDGER / "evidence" / "pm25_v19"
SNAPSHOT = LEDGER / "snapshots" / "pm25_coverage_v19_2026-08-19.json"
VALIDATION = LEDGER / "snapshots" / "pm25_coverage_v19_validation.json"
DATE = "2026-08-19"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append_rows(filename: str, key: str, rows: list[dict]) -> None:
    path = LEDGER / filename
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        existing = list(reader)
    assert fields
    new_ids = {row[key] for row in rows}
    existing = [row for row in existing if row[key] not in new_ids]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(existing + rows)


def update_rows(filename: str, key: str, updates: dict[str, dict[str, str]]) -> None:
    path = LEDGER / filename
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        records = list(reader)
    assert fields
    found = set()
    for row in records:
        if row[key] in updates:
            row.update(updates[row[key]])
            found.add(row[key])
    missing = set(updates) - found
    if missing:
        raise KeyError(f"missing inherited {filename} rows: {sorted(missing)}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    current_archive_manifest = LEDGER / "evidence" / "CURRENT_MODEL_ARCHIVE_MANIFEST.csv"
    v18_archive_manifest = LEDGER / "V18_MODEL_ARCHIVE_MANIFEST.csv"
    update_rows("SOURCES.csv", "source_id", {
        "SRC_V10_ENERGY_DONOR": {"sha256": digest(current_archive_manifest)},
        "SRC_PHL_V15_MODEL_ARCHIVE": {"sha256": digest(current_archive_manifest)},
        "SRC_PHL_V18_MODEL_ARCHIVE": {
            "edition": "v18.0.1", "sha256": digest(v18_archive_manifest),
            "notes": "Complete editable v18.0.1 case; runtime results excluded; exact archive hash is in V18_MODEL_ARCHIVE_MANIFEST.csv.",
        },
    })
    update_rows("MODEL_MAP.csv", "map_id", {
        "MAP_PHL_V18_CANONICAL_PACKAGE": {
            "model_file": "muio/Philippines_v18_v18.0.1_MUIO.zip",
            "value_or_expression": "result-free v18.0.1 archive",
        },
        "MAP_PHL_V18_PWR_COAL_PHASEOUT_ZERO": {"evidence_type": "estimated"},
        "MAP_PHL_V18_PWR_VALIDATED_SOLUTION": {"evidence_type": "direct"},
        "MAP_PHL_V18_FOSSIL_BORDER_VALIDATED_SOLUTION": {"evidence_type": "estimated"},
        "MAP_PHL_V18_PWR_FOSSIL_TRADE_DIAGNOSTIC": {
            "superseded_by": ""
        },
    })
    source_manifest = list(csv.DictReader((EVIDENCE / "SOURCE_MANIFEST.csv").open(newline="", encoding="utf-8")))
    source_meta = {
        "EEA_2023_1A1_energy_industries.pdf": ("SRC_EEA_2023_ENERGY_INDUSTRIES", "EMEP/EEA air pollutant emission inventory guidebook 2023, 1.A.1 Energy industries", "2023", "Energy-industry PM2.5 Tier 1 emission factors"),
        "EEA_2023_1A2_industry_combustion.pdf": ("SRC_EEA_2023_INDUSTRY_COMBUSTION", "EMEP/EEA air pollutant emission inventory guidebook 2023, 1.A.2 Manufacturing industries and construction", "2023", "Industrial-combustion PM2.5 Tier 1 emission factors"),
        "EEA_2023_1A4_nonroad_machinery.pdf": ("SRC_EEA_2023_NONROAD_MACHINERY", "EMEP/EEA air pollutant emission inventory guidebook 2023, 1.A.4 Non-road mobile machinery", "2023", "Agricultural-machinery diesel PM2.5 Tier 1 emission factor"),
        "EEA_2023_1A4_small_combustion.pdf": ("SRC_EEA_2023_SMALL_COMBUSTION", "EMEP/EEA air pollutant emission inventory guidebook 2023, 1.A.4 Small combustion", "2023", "Commercial, institutional, agricultural and residential PM2.5 Tier 1 factors"),
        "EEA_2023_1B1a_coal_mining_handling.pdf": ("SRC_EEA_2023_COAL_MINING_HANDLING", "EMEP/EEA air pollutant emission inventory guidebook 2023, 1.B.1.a Coal mining and handling", "2023", "Coal mining and handling PM2.5 Tier 1 emission factors"),
        "EEA_2025_1A3bvi_vii_road_nonexhaust.pdf": ("SRC_EEA_2025_ROAD_NONEXHAUST", "EMEP/EEA air pollutant emission inventory guidebook 2023, 2025 update, 1.A.3.b.vi-vii Road non-exhaust", "2025", "Tyre, brake and road-surface wear PM2.5 Tier 1 emission factors"),
    }
    sources = []
    for record in source_manifest:
        source_id, product, edition, variable = source_meta[record["file"]]
        sources.append({
            "source_id": source_id, "provider": "European Environment Agency", "product": product,
            "edition": edition, "reference_period": "technology-average", "geography": "Europe; used as Tier 1 fallback for Philippines",
            "variable": variable, "source_unit": "g/GJ; g or kg/Mg fuel; g/vehicle-km",
            "exact_locator": "See evidence/pm25_v19/FACTOR_SELECTION.csv for page and table by factor",
            "url": record["source_url"], "access_date": record["access_date"], "license": "EEA reuse policy",
            "sha256": record["sha256"], "local_file": f"evidence/pm25_v19/{record['file']}",
            "notes": "Authoritative methodological source retained byte-for-byte; factor uncertainty bounds are recorded where published.",
        })
    factor_file = EVIDENCE / "FACTOR_SELECTION.csv"
    sources.extend([
        {
            "source_id": "SRC_PHL_V19_PM25_FACTOR_REGISTER", "provider": "MUIOGO Philippines v19 workflow",
            "product": "PM2.5 factor-selection register", "edition": DATE, "reference_period": "2020-2053",
            "geography": "Philippines", "variable": "Selected factors, source locators, uncertainty ranges, applications and boundaries",
            "source_unit": "record", "exact_locator": "all 23 rows", "url": "", "access_date": DATE,
            "license": "Repository license", "sha256": digest(factor_file), "local_file": "evidence/pm25_v19/FACTOR_SELECTION.csv",
            "notes": "Machine-readable bridge between the retained EEA evidence and model calculations.",
        },
        {
            "source_id": "SRC_PHL_FISHERIES_DIESEL_BASIS", "provider": "Inherited Philippines fisheries calibration",
            "product": "FSH_CALIBRATION_v2.3", "edition": "v2.3", "reference_period": "model calibration basis",
            "geography": "Philippines", "variable": "Diesel lower-heating-value basis", "source_unit": "43.1 MJ/kg",
            "exact_locator": "lines 100-102", "url": "", "access_date": DATE, "license": "Repository license",
            "sha256": "1987ccea97ba413b8b8e5a4187a1ba65b31f8fdd297b160ab13b5c8f779ae733",
            "local_file": "evidence/inherited_base/calculation_notes/fisheries/FSH_CALIBRATION_v2.3.md",
            "notes": "Reused only to preserve the model's existing diesel energy conversion basis.",
        },
        {
            "source_id": "SRC_PHL_V19_PM25_BUILD", "provider": "MUIOGO Philippines v19 workflow",
            "product": "PM2.5 coverage build snapshot", "edition": DATE, "reference_period": "2020-2053",
            "geography": "Philippines", "variable": "Changed technologies, values, exclusions and source-file hashes",
            "source_unit": "record", "exact_locator": "technologies and explicit_exclusions", "url": "", "access_date": DATE,
            "license": "Repository license", "sha256": digest(SNAPSHOT), "local_file": "snapshots/pm25_coverage_v19_2026-08-19.json",
            "notes": "Complete machine-readable change manifest relative to Philippines v18.",
        },
        {
            "source_id": "SRC_PHL_V19_PM25_VALIDATION", "provider": "MUIOGO Philippines v19 workflow",
            "product": "PM2.5 source and generated-model validation", "edition": DATE, "reference_period": "2020-2053",
            "geography": "Philippines", "variable": "Scope, source integrity, scenario inheritance, generated data and matrix checks",
            "source_unit": "record", "exact_locator": "checks", "url": "", "access_date": DATE,
            "license": "Repository license", "sha256": digest(VALIDATION), "local_file": "snapshots/pm25_coverage_v19_validation.json",
            "notes": "Solve status is deliberately separate from the static and full-chain generation status.",
        },
    ])
    archive_manifest = LEDGER / "V19_MODEL_ARCHIVE_MANIFEST.csv"
    if archive_manifest.exists():
        archive = next(csv.DictReader(archive_manifest.open(newline="", encoding="utf-8")))
        sources.append({
            "source_id": "SRC_PHL_V19_MODEL_ARCHIVE", "provider": "MUIOGO Philippines v19 workflow",
            "product": "Philippines v19 result-free portable case", "edition": "v19.0.0", "reference_period": "2020-2053",
            "geography": "Philippines", "variable": "Complete editable v19 case delivery", "source_unit": "record",
            "exact_locator": f"{archive['member_count']} files under {archive['internal_root']}", "url": "", "access_date": DATE,
            "license": "Repository license", "sha256": digest(archive_manifest),
            "local_file": "V19_MODEL_ARCHIVE_MANIFEST.csv",
            "notes": f"Manifest for verified result-free archive; archive SHA-256={archive['sha256']} and result exclusion is false.",
        })
    append_rows("SOURCES.csv", "source_id", sources)

    calculations = [
        ("CALC_PHL_V19_INDUSTRY_PM25", "EAR[y] = EEA Tier 1 g/GJ fuel input * InputActivityRatio[y] * 0.001 kt/PJ per g/GJ", "SRC_EEA_2023_INDUSTRY_COMBUSTION;SRC_PHL_V19_PM25_FACTOR_REGISTER", "ASM_PHL_V19_TIER1_FALLBACK;ASM_PHL_V19_CCS_NO_PM_CREDIT", "20;0.78;108;140; endogenous IAR by technology and year", "g/GJ;PJ input/PJ activity", "technology-specific annual series", "kt/PJ activity"),
        ("CALC_PHL_V19_SMALL_COMBUSTION_PM25", "EAR[y] = EEA Tier 1 g/GJ fuel input * InputActivityRatio[y] * 0.001", "SRC_EEA_2023_SMALL_COMBUSTION;SRC_PHL_V19_PM25_FACTOR_REGISTER", "ASM_PHL_V19_TIER1_FALLBACK", "18;0.78;108;160;1.2; endogenous IAR", "g/GJ;PJ input/PJ activity", "technology-specific annual series", "kt/PJ activity"),
        ("CALC_PHL_V19_AGR_DIESEL_PM25", "EAR = (1913 g/Mg diesel / 43.1 GJ/Mg) * IAR 2.5 * 0.001", "SRC_EEA_2023_NONROAD_MACHINERY;SRC_PHL_FISHERIES_DIESEL_BASIS", "ASM_PHL_V19_TIER1_FALLBACK", "1913;43.1;2.5;0.001", "g/Mg;GJ/Mg;PJ input/PJ activity;kt/PJ per g/GJ", "0.11096287703016242", "kt/PJ activity"),
        ("CALC_PHL_V19_POWER_CCS_PM25", "EAR = EEA Tier 1 g/GJ fuel input * endogenous CCS-route IAR * 0.001", "SRC_EEA_2023_ENERGY_INDUSTRIES;SRC_PHL_V19_PM25_FACTOR_REGISTER", "ASM_PHL_V19_TIER1_FALLBACK;ASM_PHL_V19_CCS_NO_PM_CREDIT", "0.14;3.4;133; endogenous IAR", "g/GJ;PJ input/PJ activity", "technology-specific annual series", "kt/PJ activity"),
        ("CALC_PHL_V19_ROAD_NONEXHAUST_PM25", "EAR = tyre-and-brake PM2.5 + road-surface PM2.5; because activity is 10^9 vehicle-km, 1 g/vehicle-km = 1 kt/10^9 vehicle-km; add inherited exhaust where present", "SRC_EEA_2025_ROAD_NONEXHAUST;SRC_PHL_V19_PM25_FACTOR_REGISTER", "ASM_PHL_V19_ROAD_CLASS_TRANSFER", "0.0034+0.0016;0.0093+0.0041;0.0139+0.0057;0.0316+0.0205", "g/vehicle-km", "0.0050;0.0134;0.0196;0.0521", "kt/10^9 vehicle-km"),
        ("CALC_PHL_V19_COAL_EXTRACTION_PM25", "EAR = 0.005 kg/Mg coal / 22.1 GJ/Mg", "SRC_EEA_2023_COAL_MINING_HANDLING;SRC_PHL_V18_FOSSIL_BORDER_INPUTS", "ASM_PHL_V19_TIER1_FALLBACK;ASM_PHL_V19_RETAINED_ENERGY_BASIS", "0.005;22.1", "kg/Mg;GJ/Mg", "0.0002262443438914027", "kt/PJ coal"),
        ("CALC_PHL_V19_COAL_IMPORT_PM25", "EAR = 0.3 g/Mg coal * 0.001 kg/g / 22.1 GJ/Mg", "SRC_EEA_2023_COAL_MINING_HANDLING;SRC_PHL_V18_FOSSIL_BORDER_INPUTS", "ASM_PHL_V19_TIER1_FALLBACK;ASM_PHL_V19_RETAINED_ENERGY_BASIS", "0.3;0.001;22.1", "g/Mg;kg/g;GJ/Mg", "0.00001357466063348416", "kt/PJ coal"),
    ]
    append_rows("CALCULATIONS.csv", "calculation_id", [{
        "calculation_id": a, "formula": b, "source_ids": c, "assumption_ids": d, "input_calculation_ids": "",
        "input_values": e, "input_units": f, "output_value": g, "output_unit": h,
        "script_path": "scripts/apply_philippines_v19_pm25_coverage.py", "script_version": "v1", "notes": "Mode 1 and SC_0 only; other modes are zero and policy scenarios inherit.",
    } for a, b, c, d, e, f, g, h in calculations])

    assumptions = [
        ("ASM_PHL_V19_TIER1_FALLBACK", "Use current authoritative EMEP/EEA Tier 1 PM2.5 factors where Philippines-specific technology, control and fleet factors matching the model activities are unavailable.", "source-specific Tier 1 central factor", "published source unit", "SRC_EEA_2023_ENERGY_INDUSTRIES;SRC_EEA_2023_INDUSTRY_COMBUSTION;SRC_EEA_2023_SMALL_COMBUSTION;SRC_EEA_2023_NONROAD_MACHINERY;SRC_EEA_2023_COAL_MINING_HANDLING", "Published uncertainty bounds are retained in FACTOR_SELECTION.csv; model sensitivity is not added.", "Does not assert that European average technologies equal Philippine conditions."),
        ("ASM_PHL_V19_CCS_NO_PM_CREDIT", "Apply the combustion PM2.5 factor to CCS routes without inferring particulate removal by the CO2 capture train.", "no PM capture credit", "dimensionless", "SRC_EEA_2023_ENERGY_INDUSTRIES;SRC_EEA_2023_INDUSTRY_COMBUSTION", "The source factors describe combustion, not a model-specific CCS particulate-control configuration.", "Conservative pending control-specific evidence."),
        ("ASM_PHL_V19_ROAD_CLASS_TRANSFER", "Apply class-specific tyre, brake and road-surface wear to all modeled powertrains in that road class and retain existing liquid-fuel exhaust factors additively.", "class factor independent of modeled powertrain", "g/vehicle-km", "SRC_EEA_2025_ROAD_NONEXHAUST", "The aggregate model lacks weight, regenerative-braking, road and driving-cycle detail.", "Exhaust for alternative-fuel and PHEV vehicles is not inferred."),
        ("ASM_PHL_V19_RETAINED_ENERGY_BASIS", "Reuse the model's retained 43.1 GJ/Mg diesel and 22.1 GJ/Mg coal conversion bases when translating mass-based factors.", "43.1 diesel;22.1 coal", "GJ/Mg", "SRC_PHL_FISHERIES_DIESEL_BASIS;SRC_PHL_V18_FOSSIL_BORDER_INPUTS", "Maintains unit consistency with the inherited model.", "Not a new fuel-quality calibration."),
        ("ASM_PHL_V19_EXPLICIT_BOUNDARY", "Add no residual PM2.5 inventory and no activity proxy where the model has no explicit matching technology or adequate activity detail.", "technology-linked accounting only", "scope rule", "SRC_PHL_V19_PM25_BUILD", "Prevents unsupported emissions from being attached to unrelated endogenous activity.", "Explicit omissions remain in GAPS.csv and the calculation note."),
    ]
    append_rows("ASSUMPTIONS.csv", "assumption_id", [{
        "assumption_id": a, "statement": b, "central_value": c, "unit": d, "evidence_source_ids": e,
        "lower_bound": "", "upper_bound": "", "rationale": f, "notes": g,
    } for a, b, c, d, e, f, g in assumptions])

    calc_for = lambda name: (
        "CALC_PHL_V19_ROAD_NONEXHAUST_PM25" if name.startswith("PHL_TRA_") else
        "CALC_PHL_V19_AGR_DIESEL_PM25" if name == "PHL_AGR_MOT_LIQ" else
        "CALC_PHL_V19_COAL_EXTRACTION_PM25" if name == "PHL_PRO_EXTR_COAL" else
        "CALC_PHL_V19_COAL_IMPORT_PM25" if name == "PHL_PRO_IMP_COAL" else
        "CALC_PHL_V19_POWER_CCS_PM25" if name.startswith("PHL_POW_") else
        "CALC_PHL_V19_INDUSTRY_PM25" if name.startswith("PHL_INDU_") else
        "CALC_PHL_V19_SMALL_COMBUSTION_PM25"
    )
    maps = []
    for name, record in snapshot["technologies"].items():
        road = name.startswith("PHL_TRA_")
        assumptions_for_row = "ASM_PHL_V19_TIER1_FALLBACK"
        if road:
            assumptions_for_row = "ASM_PHL_V19_ROAD_CLASS_TRANSFER"
        elif "CCS" in name:
            assumptions_for_row += ";ASM_PHL_V19_CCS_NO_PM_CREDIT"
        if name in {"PHL_AGR_MOT_LIQ", "PHL_PRO_EXTR_COAL", "PHL_PRO_IMP_COAL"}:
            assumptions_for_row += ";ASM_PHL_V19_RETAINED_ENERGY_BASIS"
        maps.append({
            "map_id": f"MAP_PHL_V19_PM25_{name.removeprefix('PHL_')}", "model_file": "case/Philippines_v19/RYTEM.json",
            "parameter": "EmissionActivityRatio", "entity": f"{record['tech_id']} / {name} / EMI_xpvk3 / PM2_5",
            "mode": "1", "scenario": "SC_0; policy scenarios inherit", "years": "2020-2053",
            "value_or_expression": f"2020={record['new_2020']:.15g};2030={record['new_2030']:.15g};2053={record['new_2053']:.15g}",
            "model_unit": "kt/10^9 vehicle-km" if road else "kt/PJ activity",
            "evidence_ids": f"{calc_for(name)};{assumptions_for_row};{record['source']};SRC_PHL_V19_PM25_FACTOR_REGISTER;SRC_PHL_V19_PM25_BUILD",
            "superseded_by": "", "evidence_type": "derived",
            "notes": f"{record['method']}. Old 2020 value={record['old_2020']:.15g}; modes 2-30 are zero; EACR is zero.",
        })
    maps.append({
        "map_id": "MAP_PHL_V19_PM25_TECH_LINKS", "model_file": "case/Philippines_v19/genData.json",
        "parameter": "Technology EAR membership", "entity": "46 existing technologies newly linked to EMI_xpvk3; six road-liquid links already existed",
        "mode": "", "scenario": "all", "years": "2020-2053", "value_or_expression": "See SRC_PHL_V19_PM25_BUILD technologies",
        "model_unit": "identifier relationship", "evidence_ids": "SRC_PHL_V19_PM25_BUILD;SRC_PHL_V19_PM25_VALIDATION;ASM_PHL_V19_EXPLICIT_BOUNDARY",
        "superseded_by": "", "evidence_type": "estimated", "notes": "No technology, commodity or emission identifier was added or removed.",
    })
    if archive_manifest.exists():
        maps.append({
            "map_id": "MAP_PHL_V19_CANONICAL_PACKAGE", "model_file": "muio/Philippines_v19_v19.0.0_MUIO.zip",
            "parameter": "canonical portable case", "entity": "Philippines_v19", "mode": "", "scenario": "all",
            "years": "2020-2053", "value_or_expression": "Exact result-free copy of case/Philippines_v19",
            "model_unit": "ZIP archive", "evidence_ids": "SRC_PHL_V19_MODEL_ARCHIVE;SRC_PHL_V19_PM25_VALIDATION",
            "superseded_by": "", "evidence_type": "direct", "notes": "See V19_MODEL_ARCHIVE_MANIFEST.csv and muio/SHA256SUMS.",
        })
    append_rows("MODEL_MAP.csv", "map_id", maps)

    gaps = [
        ("Philippines-specific PM2.5 technology factors", "No complete Philippine factor set resolves the model's fuel, device, control and fleet classes; EMEP/EEA Tier 1 central factors are used.", "Compile Philippine stack tests, fuel properties, control penetration, vehicle standards and fleet shares; replace Tier 1 factors by technology and year.", "high", "Published EEA uncertainty ranges are retained in the factor register."),
        ("Alternative-powertrain road exhaust and road-wear differentiation", "The model lacks vehicle-standard shares, duty cycles, mass and regenerative-braking parameters; only class-average non-exhaust is added.", "Build Philippine fleet/standard/duty-cycle data and drivetrain-specific tyre/brake corrections.", "medium", "Liquid-road inherited exhaust is retained; no NG, H2, PHEV or EV exhaust is invented."),
        ("Aviation and rail PM2.5 extension", "Aircraft PM depends on aircraft, engine, payload and LTO/CCD activity not represented; reviewed rail guidance does not justify drivetrain-neutral rail wear.", "Add aircraft/LTO/CCD and rail vehicle-km or fuel/engine classes before assigning factors.", "medium", "Explicitly excluded from v19."),
        ("Agriculture oil and gas stationary heat", "The two technologies have no corresponding input-fuel relationship in the inherited model, so a fuel-input factor cannot be applied safely.", "Repair or document the activity/fuel boundary first, then apply the matching small-combustion factor.", "medium", "Coal and biomass agriculture heat are covered."),
        ("PM2.5 sources without explicit model activity", "Crop-residue and waste burning, cement/process dust, road resuspension and similar inventory sources cannot be attached to an explicit existing model activity.", "Add explicit source activities with defensible activity data if these emissions are needed for a use case.", "medium", "No exogenous residual inventory was added."),
    ]
    append_rows("GAPS.csv", "item", [{"item": a, "why_absent": b, "upgrade_source": c, "priority": d, "notes": e} for a, b, c, d, e in gaps])
    append_rows("CHANGES.csv", "change_id", [{
        "change_id": "CHG_PHL_V19_PM25_COVERAGE_20260819", "date": DATE, "class": "C",
        "description": "Created Philippines v19 from the complete v18 package and added source-traceable endogenous PM2.5 factors to 52 existing technologies: 46 first-time links and six road-liquid non-exhaust extensions.",
        "model_objects": "case/Philippines_v19/genData.json EAR links; case/Philippines_v19/RYTEM.json EAR/EACR rows",
        "evidence_path": "documentation/MODEL_FIXES_PM25_COVERAGE_2026-08-19.md;data_sources/evidence/pm25_v19/FACTOR_SELECTION.csv;data_sources/snapshots/pm25_coverage_v19_2026-08-19.json;data_sources/snapshots/pm25_coverage_v19_validation.json",
        "map_rows_affected": ";".join(row["map_id"] for row in maps), "resolve_status": "resolved", "author": "Codex", "commit": "",
        "notes": "PM2.5-only parameter extension. CO2e, other PM2.5 rows, technologies, commodities, constraints, costs, demands and historical calibration were unchanged.",
    }, {
        "change_id": "CHG_PHL_V19_LEDGER_HYGIENE_20260819", "date": DATE, "class": "C",
        "description": "Reconciled inherited archive-manifest digests, v18.0.1 package labels, three evidence-type classifications, and one supersession reference with the current ledger schema.",
        "model_objects": "data_sources/SOURCES.csv;data_sources/MODEL_MAP.csv",
        "evidence_path": "diagnostics/provenance_validation_v19.json;data_sources/V18_MODEL_ARCHIVE_MANIFEST.csv;data_sources/evidence/CURRENT_MODEL_ARCHIVE_MANIFEST.csv",
        "map_rows_affected": "MAP_PHL_V18_CANONICAL_PACKAGE;MAP_PHL_V18_PWR_COAL_PHASEOUT_ZERO;MAP_PHL_V18_PWR_VALIDATED_SOLUTION;MAP_PHL_V18_PWR_FOSSIL_TRADE_DIAGNOSTIC;MAP_PHL_V18_FOSSIL_BORDER_VALIDATED_SOLUTION",
        "resolve_status": "resolved", "author": "Codex", "commit": "",
        "notes": "Documentation/schema repair only; no model JSON, coefficient, bound, cost, demand, result, or retained evidence byte changed.",
    }])
    print(f"Updated cumulative v19 ledger with {len(sources)} sources and {len(maps)} model-map rows")


if __name__ == "__main__":
    main()
