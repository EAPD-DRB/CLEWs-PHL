#!/usr/bin/env python3
"""Append the canonical Philippines v16 irrigated-rice water ledger records."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
LEDGER = PACKAGE / "data_sources"
SNAPSHOTS = LEDGER / "snapshots"


def digest(name: str) -> str:
    return hashlib.sha256((SNAPSHOTS / name).read_bytes()).hexdigest()


def append(filename: str, key: str, rows: list[dict[str, str]]) -> None:
    path = LEDGER / filename
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        existing = {row[key] for row in reader}
    missing = [row for row in rows if row[key] not in existing]
    if not missing:
        return
    with path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        for row in missing:
            writer.writerow({name: row.get(name, "") for name in fieldnames})
    print(f"{filename}: appended {len(missing)}")


def main() -> None:
    live_validation = SNAPSHOTS / "irrigation_water_live_validation.json"
    sources = [
        {"source_id": "SRC_FAO_PADDY_SCHEDULING", "provider": "Food and Agriculture Organization of the United Nations", "product": "Irrigation water management: Irrigation scheduling, Chapter 4", "edition": "Training manual no. 4", "reference_period": "engineering guidance", "geography": "general; applied to Philippines paddy", "variable": "Paddy saturation, percolation and standing-water requirement", "source_unit": "mm; mm/day", "exact_locator": "Chapter 4 rice irrigation scheduling: SAT=200 mm; PERC=2 mm/day for heavy well-puddled clay; WL=20-100 mm", "url": "https://www.fao.org/4/T7202E/t7202e07.htm", "access_date": "2026-08-11", "license": "FAO publication terms", "notes": "Engineering input; not an observed national withdrawal."},
        {"source_id": "SRC_FAO_SCHEME_WATER_NEED", "provider": "Food and Agriculture Organization of the United Nations", "product": "Scheme Irrigation Water Need and Supply", "edition": "Irrigation Water Management Training Manual", "reference_period": "engineering guidance", "geography": "general; applied to Philippines paddy", "variable": "Rice saturation, standing-water and gross irrigation relation", "source_unit": "mm; fraction", "exact_locator": "Rice scheme need: SAT about 200 mm; WL about 50 mm; gross requirement equals net requirement divided by efficiency", "url": "https://www.fao.org/4/u5835e/u5835e04.htm", "access_date": "2026-08-11", "license": "FAO publication terms"},
        {"source_id": "SRC_FAO_RICE_WATER_REQUIREMENT", "provider": "Food and Agriculture Organization of the United Nations", "product": "Rice and water: a long and diversified story", "edition": "International Year of Rice conference paper", "reference_period": "100-day reference season", "geography": "general rice systems", "variable": "Seasonal rice field-water requirement and components", "source_unit": "mm/season", "exact_locator": "100-day basis; land preparation 150-250 mm; percolation 200-700 mm; drainage 50-100 mm; total field requirement 900-2250 mm", "url": "https://www.fao.org/4/y5682e/y5682e09.htm", "access_date": "2026-08-11", "license": "FAO publication terms", "notes": "Independent engineering-range check."},
        {"source_id": "SRC_NIA_IRRIGATION_DESIGN_DUTY_2025", "provider": "Philippines National Irrigation Administration", "product": "Updated Design Criteria for Irrigation Canal Structures", "edition": "Memorandum Circular No. 125 s. 2025", "reference_period": "2025 design standard", "geography": "Philippines", "variable": "Soil-based irrigation design duty", "source_unit": "L/s/ha", "exact_locator": "Design-duty table: clay 1.0 through sandy loam 5.0 L/s/ha", "url": "https://omcrs.nia.gov.ph/?q=system/files/mc/2025_125.pdf", "access_date": "2026-08-11", "license": "Philippine government publication"},
        {"source_id": "SRC_PHL_V16_IRRIGATION_ENGINEERING_INPUTS", "provider": "EAPD-DRB", "product": "Philippines v16 irrigated-rice water engineering input register", "edition": "2026-08-11", "reference_period": "2020-2053", "geography": "Philippines; eight model clusters", "variable": "Frozen source values, classifications, formulas, GAEZ deficits and limitations", "source_unit": "record", "exact_locator": "snapshots/irrigation_water_engineering_2026.json", "access_date": "2026-08-11", "license": "MUIOGO repository terms", "sha256": digest("irrigation_water_engineering_2026.json"), "local_file": "snapshots/irrigation_water_engineering_2026.json"},
        {"source_id": "SRC_PHL_V16_IRRIGATION_ENGINEERING_MANIFEST", "provider": "EAPD-DRB", "product": "Philippines v16 irrigated-rice water candidate manifest", "edition": "2026-08-11", "reference_period": "2020-2053", "geography": "Philippines; eight model clusters", "variable": "Exact 544-cell source delta and non-forcing assertions", "source_unit": "record", "exact_locator": "snapshots/irrigation_water_manifest.json", "access_date": "2026-08-11", "license": "MUIOGO repository terms", "sha256": digest("irrigation_water_manifest.json"), "local_file": "snapshots/irrigation_water_manifest.json"},
        {"source_id": "SRC_PHL_V16_IRRIGATION_ENGINEERING_VALIDATION", "provider": "EAPD-DRB", "product": "Philippines v16 irrigated-rice water matched A/B validation", "edition": "2026-08-11", "reference_period": "2020-2053", "geography": "Philippines", "variable": "Source diff, engineering range, matrix, optimum and affected-result checks", "source_unit": "record", "exact_locator": "snapshots/irrigation_water_validation.json", "access_date": "2026-08-11", "license": "MUIOGO repository terms", "sha256": digest("irrigation_water_validation.json"), "local_file": "snapshots/irrigation_water_validation.json", "notes": "Wind-complete control and candidate; all recorded checks passed."},
    ]
    if live_validation.is_file():
        sources.append({"source_id": "SRC_PHL_V16_IRRIGATION_ENGINEERING_LIVE_VALIDATION", "provider": "EAPD-DRB", "product": "Philippines v16 promoted irrigation-water live validation", "edition": "2026-08-11", "reference_period": "2020-2053", "geography": "Philippines", "variable": "Promoted source identity, live optimum and physical result reproduction", "source_unit": "record", "exact_locator": "snapshots/irrigation_water_live_validation.json", "access_date": "2026-08-11", "license": "MUIOGO repository terms", "sha256": digest("irrigation_water_live_validation.json"), "local_file": "snapshots/irrigation_water_live_validation.json"})
    append("SOURCES.csv", "source_id", sources)

    calculations = [
        {"calculation_id": "CALC_PHL_V16_RICE_CROPPING_INTENSITY", "formula": "cropping intensity = irrigated palay harvested area / physical irrigation service area", "source_ids": "SRC_PSA_OPENSTAT_AGRICULTURE_2020;SRC_PSA_SSAF_2022", "assumption_ids": "ASM_PHL_V16_IRRIGATION_CROPPING_INTENSITY", "input_values": "3253454.36;2006000", "input_units": "ha harvested;ha service area", "output_value": "1.621861595214357", "output_unit": "crops/year", "script_path": "scripts/calibrate_philippines_v16_irrigation_water_engineering.py", "script_version": "2026-08-11", "notes": "Annualizes physical service-area activity; does not constrain area."},
        {"calculation_id": "CALC_PHL_V16_RICE_PADDY_ADDITION", "formula": "paddy addition = saturation + percolation rate * season days + standing water", "source_ids": "SRC_FAO_PADDY_SCHEDULING;SRC_FAO_SCHEME_WATER_NEED;SRC_FAO_RICE_WATER_REQUIREMENT", "assumption_ids": "ASM_PHL_V16_CONSERVATIVE_PADDY_ENGINEERING", "input_values": "200;2;100;50", "input_units": "mm;mm/day;day;mm", "output_value": "450", "output_unit": "mm/crop", "script_path": "scripts/calibrate_philippines_v16_irrigation_water_engineering.py", "script_version": "2026-08-11"},
        {"calculation_id": "CALC_PHL_V16_RICE_ANNUAL_GROSS_IAR", "formula": "annual gross IAR = (GAEZ WDe + 0.450 m/crop) * 1.621861595214357 crops/year / 0.38", "source_ids": "SRC_GAEZ_V4;SRC_GAEZ_CWD_HIGH_TABLE;SRC_GAEZ_CWD_LOW_TABLE;SRC_PHILRICE_IRRIGATION_EFFICIENCY;SRC_PHL_V16_IRRIGATION_ENGINEERING_INPUTS", "assumption_ids": "ASM_PHL_V16_CONSERVATIVE_PADDY_ENGINEERING;ASM_PHL_V16_IRRIGATION_CROPPING_INTENSITY;ASM_PHL_IRRIGATION_EFFICIENCY_38;ASM_PHL_V16_NO_NATIONAL_WATER_SCALING", "input_calculation_ids": "CALC_PHL_V16_RICE_CROPPING_INTENSITY;CALC_PHL_V16_RICE_PADDY_ADDITION", "input_values": "16 cluster/mode GAEZ WDe values;0.450;1.621861595214357;0.38", "input_units": "m/crop;m/crop;crops/year;fraction", "output_value": "1.9248936301-3.5424871685", "output_unit": "km3 gross diversion per 1000 km2 per year", "script_path": "scripts/calibrate_philippines_v16_irrigation_water_engineering.py", "script_version": "2026-08-11", "notes": "Mode- and cluster-specific source mapping; national withdrawal totals are not used."},
        {"calculation_id": "CALC_PHL_V16_RICE_NIA_DUTY_CHECK", "formula": "100-day duty = ((GAEZ WDe + 0.450) / 0.38) / 0.864", "source_ids": "SRC_NIA_IRRIGATION_DESIGN_DUTY_2025;SRC_FAO_RICE_WATER_REQUIREMENT;SRC_PHL_V16_IRRIGATION_ENGINEERING_INPUTS", "assumption_ids": "ASM_PHL_V16_CONSERVATIVE_PADDY_ENGINEERING;ASM_PHL_IRRIGATION_EFFICIENCY_38", "input_calculation_ids": "CALC_PHL_V16_RICE_PADDY_ADDITION", "input_values": "16 GAEZ WDe values;0.450;0.38;100", "input_units": "m/crop;m/crop;fraction;days", "output_value": "1.3736598441-2.5280214425", "output_unit": "L/s/ha", "script_path": "scripts/calibrate_philippines_v16_irrigation_water_engineering.py", "script_version": "2026-08-11", "notes": "Within NIA 1-5 L/s/ha; an engineering check rather than a fitted target."},
        {"calculation_id": "CALC_PHL_V16_IRRIGATION_ENGINEERING_RUN", "formula": "matched unchanged control and one-file candidate; DataFile generation/preprocessing; GLPK matrix check; CBC solve; affected-result comparison", "source_ids": "SRC_PHL_V16_IRRIGATION_ENGINEERING_MANIFEST;SRC_PHL_V16_IRRIGATION_ENGINEERING_VALIDATION", "assumption_ids": "ASM_PHL_V16_NO_NATIONAL_WATER_SCALING;ASM_PHL_V16_GROSS_WITHDRAWAL_BOUNDARY", "input_calculation_ids": "CALC_PHL_V16_RICE_ANNUAL_GROSS_IAR;CALC_PHL_V16_RICE_NIA_DUTY_CHECK", "input_values": "control objective=369730088.2957077;candidate=369730088.3625874;rows=791109;columns=884956;nonzeros=12552173", "input_units": "model objective;matrix counts", "output_value": "optimal; objective change=1.8088787418e-8 percent; all checks passed", "output_unit": "status;percent", "script_path": "scripts/validate_philippines_v16_irrigation_water_engineering.py", "script_version": "2026-08-11", "notes": "2020 rice irrigation becomes 40.403 km3; irrigated area capacity emissions demand bounds and user constraints are unchanged."},
    ]
    if live_validation.is_file():
        live = json.loads(live_validation.read_text())
        calculations.append({"calculation_id": "CALC_PHL_V16_IRRIGATION_ENGINEERING_LIVE_RUN", "formula": "promoted source identity; DataFile generation/preprocessing; GLPK matrix check; CBC solve; candidate reproduction", "source_ids": "SRC_PHL_V16_IRRIGATION_ENGINEERING_VALIDATION;SRC_PHL_V16_IRRIGATION_ENGINEERING_LIVE_VALIDATION", "assumption_ids": "ASM_PHL_V16_NO_NATIONAL_WATER_SCALING;ASM_PHL_V16_GROSS_WITHDRAWAL_BOUNDARY", "input_calculation_ids": "CALC_PHL_V16_IRRIGATION_ENGINEERING_RUN", "input_values": f"candidate objective=369730088.3625874;live objective={live['solver']['objective']}", "input_units": "model objective", "output_value": "optimal; promoted source and physical checks passed", "output_unit": "status", "script_path": "scripts/validate_philippines_v16_irrigation_water_live.py", "script_version": "2026-08-11"})
    append("CALCULATIONS.csv", "calculation_id", calculations)

    assumptions = [
        {"assumption_id": "ASM_PHL_V16_CONSERVATIVE_PADDY_ENGINEERING", "statement": "Use FAO's conservative heavy well-puddled clay values where cluster paddy-soil measurements are absent: 200 mm saturation 2 mm/day percolation for 100 days and 50 mm standing water.", "central_value": "450", "unit": "mm/crop", "evidence_source_ids": "SRC_FAO_PADDY_SCHEDULING;SRC_FAO_SCHEME_WATER_NEED;SRC_FAO_RICE_WATER_REQUIREMENT", "lower_bound": "450", "upper_bound": "450", "rationale": "This is the documented lower engineering case and avoids selecting a sandy high-loss value without cluster soil evidence.", "notes": "Cluster soil measurements are a high-priority gap."},
        {"assumption_id": "ASM_PHL_V16_IRRIGATION_CROPPING_INTENSITY", "statement": "Hold the observed 2020 national irrigated-palay harvested-area to physical-service-area ratio constant when annualizing the rice water coefficient.", "central_value": "1.621861595214357", "unit": "crops/year", "evidence_source_ids": "SRC_PSA_OPENSTAT_AGRICULTURE_2020;SRC_PSA_SSAF_2022;SRC_PHL_V16_IRRIGATION_ENGINEERING_INPUTS", "rationale": "The model's land activity is physical service area while the calibrated annual crop OAR already embodies multiple cropping.", "notes": "Does not impose annual activity or harvested area."},
        {"assumption_id": "ASM_PHL_V16_NO_NATIONAL_WATER_SCALING", "statement": "Do not calibrate rice IAR by scaling to a national irrigation or agricultural withdrawal total.", "central_value": "engineering calculation", "unit": "method", "evidence_source_ids": "SRC_PHL_V16_IRRIGATION_ENGINEERING_INPUTS;SRC_NIA_IRRIGATION_DESIGN_DUTY_2025", "rationale": "Crop and cluster coefficients must preserve physical engineering meaning; national totals remain validation benchmarks.", "notes": "Consistent with the non-forcing calibration rule."},
        {"assumption_id": "ASM_PHL_V16_GROSS_WITHDRAWAL_BOUNDARY", "statement": "Represent gross irrigation diversion at AGRWATPHL without adding an unsupported structural allocation of seepage drainage conveyance loss and recoverable return flow.", "central_value": "gross withdrawal", "unit": "water-account boundary", "evidence_source_ids": "SRC_FAO_SCHEME_WATER_NEED;SRC_PHL_V16_IRRIGATION_ENGINEERING_INPUTS", "rationale": "The requested repair is data-only and no source supports a cluster-specific return-flow partition.", "notes": "Return-flow structure is retained as a disclosed gap."},
    ]
    append("ASSUMPTIONS.csv", "assumption_id", assumptions)

    inputs = json.loads((SNAPSHOTS / "irrigation_water_engineering_2026.json").read_text())
    values = json.loads((SNAPSHOTS / "irrigation_water_manifest.json").read_text())["after_km3_per_1000km2_year"]
    cluster = {"TEC_ibnh8": "C01", "TEC_9lvqs": "C02", "TEC_3mwof": "C03", "TEC_ckkki": "C04", "TEC_1ky0a": "C05", "TEC_oeqz2": "C06", "TEC_72dqm": "C07", "TEC_xaiae": "C08"}
    maps = []
    for mode in (17, 19):
        for tech, code in cluster.items():
            maps.append({"map_id": f"MAP_PHL_V16_IRRIGATION_IAR_{code}_M{mode}", "model_file": "case/Philippines_v16/RYTCM.json", "parameter": "InputActivityRatio", "entity": f"{tech} / LNDAGRPHL{code} / AGRWATPHL", "mode": str(mode), "scenario": "SC_0; policy rows inherit", "years": "2020-2053", "value_or_expression": str(values[f"{tech}|{mode}"]), "model_unit": "km3 gross diversion per 1000 km2 per year", "evidence_ids": "CALC_PHL_V16_RICE_ANNUAL_GROSS_IAR;CALC_PHL_V16_RICE_NIA_DUTY_CHECK;SRC_PHL_V16_IRRIGATION_ENGINEERING_MANIFEST", "evidence_type": "derived", "notes": f"GAEZ WDe={inputs['gaez_water_deficit_m_per_crop'][str(mode)][tech]} m/crop plus sourced paddy components; no national-total scaling."})
    maps.extend([
        {"map_id": "MAP_PHL_V16_IRRIGATION_ENGINEERING_INPUTS", "model_file": "case/Philippines_v16/RYTCM.json", "parameter": "source and calculation register", "entity": "irrigated rice modes 17 and 19", "mode": "17;19", "scenario": "source evidence", "years": "2020-2053", "value_or_expression": "FAO paddy components + GAEZ WDe + PSA cropping intensity + PhilRice efficiency; NIA duty check", "model_unit": "record", "evidence_ids": "SRC_PHL_V16_IRRIGATION_ENGINEERING_INPUTS", "evidence_type": "direct"},
        {"map_id": "MAP_PHL_V16_IRRIGATION_ENGINEERING_VALIDATION", "model_file": "case/Philippines_v16", "parameter": "matched A/B validation", "entity": "IRRIGATION_WATER_TEST", "mode": "17;19", "scenario": "SC_0", "years": "2020-2053", "value_or_expression": "optimal objective 369730088.3625874; matrix 791109 x 884956 with 12552173 nonzeros; all checks passed", "model_unit": "status;objective;matrix counts", "evidence_ids": "SRC_PHL_V16_IRRIGATION_ENGINEERING_VALIDATION;CALC_PHL_V16_IRRIGATION_ENGINEERING_RUN", "evidence_type": "derived"},
        {"map_id": "MAP_PHL_V16_LIVE_SOURCE_IRRIGATION_20260811", "model_file": "case/Philippines_v16/RYTCM.json", "parameter": "complete current live source delta", "entity": "Philippines_v16 irrigated rice AGRWATPHL", "mode": "17;19", "scenario": "SC_0; policy rows inherit", "years": "2020-2053", "value_or_expression": "544 rice-water IAR cells from engineering calculation", "model_unit": "source directory", "evidence_ids": "SRC_PHL_V16_IRRIGATION_ENGINEERING_INPUTS;SRC_PHL_V16_IRRIGATION_ENGINEERING_MANIFEST;SRC_PHL_V16_IRRIGATION_ENGINEERING_VALIDATION;CALC_PHL_V16_RICE_ANNUAL_GROSS_IAR", "evidence_type": "derived", "notes": "Current authoritative inputs are live source JSON files; generated solver files remain outputs."},
    ])
    if live_validation.is_file():
        maps.append({"map_id": "MAP_PHL_V16_IRRIGATION_ENGINEERING_LIVE_VALIDATION", "model_file": "case/Philippines_v16/res/IRRIGATION_WATER_BASE", "parameter": "promoted live validation evidence", "entity": "IRRIGATION_WATER_BASE", "mode": "17;19", "scenario": "SC_0", "years": "2020-2053", "value_or_expression": "optimal live solve reproduces validated source and physical water effect", "model_unit": "status", "evidence_ids": "SRC_PHL_V16_IRRIGATION_ENGINEERING_LIVE_VALIDATION;CALC_PHL_V16_IRRIGATION_ENGINEERING_LIVE_RUN", "evidence_type": "derived"})
    append("MODEL_MAP.csv", "map_id", maps)

    append("GAPS.csv", "item", [
        {"item": "Cluster paddy soil percolation and scheme delivery efficiency", "why_absent": "Only a national 38 percent delivery observation and FAO soil-class engineering values are frozen; the eight model clusters lack matched scheme soil and conveyance measurements.", "upgrade_source": "NIA scheme design reports and monitored diversion field-delivery and soil-percolation records mapped to the eight cluster geometries.", "priority": "high", "notes": "Do not fit coefficients to national withdrawal totals or impose cluster water shares."},
        {"item": "Irrigation return-flow partition and future cropping intensity", "why_absent": "The current structure does not distinguish recoverable paddy seepage drainage and conveyance returns and the annualization uses the 2020 national cropping-intensity ratio through 2053.", "upgrade_source": "Scheme water-balance studies with recoverable fractions and crop-season projections linked to physical service area by cluster.", "priority": "medium", "notes": "A future structural extension must preserve gross withdrawals and avoid double counting return water."},
    ])

    map_ids = ";".join(row["map_id"] for row in maps)
    append("CHANGES.csv", "change_id", [{"change_id": "CHG_PHL_V16_IRRIGATION_ENGINEERING_20260811", "date": "2026-08-11", "class": "B", "description": "Replaced irrigated-rice GAEZ deficit-only AGRWATPHL coefficients with crop- and cluster-specific annual gross engineering requirements including paddy saturation ponding percolation multiple cropping and delivery efficiency.", "model_objects": "RYTCM.json IAR COM_sp9qb modes 17 and 19; no structural objects", "evidence_path": "calculation_notes/irrigation_water_engineering_v16_2026-08-11.md", "map_rows_affected": map_ids, "resolve_status": "resolved" if live_validation.is_file() else "candidate_validated", "author": "Codex", "notes": "Data-only non-forcing repair; no national-total scaling and no technology commodity mode demand bound share or UDC change."}])
    if live_validation.is_file():
        path = LEDGER / "CHANGES.csv"
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            fieldnames = reader.fieldnames
            change_rows = list(reader)
        for row in change_rows:
            if row["change_id"] == "CHG_PHL_V16_IRRIGATION_ENGINEERING_20260811":
                row["resolve_status"] = "resolved"
                live_map = "MAP_PHL_V16_IRRIGATION_ENGINEERING_LIVE_VALIDATION"
                affected = row["map_rows_affected"].split(";") if row["map_rows_affected"] else []
                if live_map not in affected:
                    row["map_rows_affected"] = ";".join(affected + [live_map])
                row["notes"] = "Data-only non-forcing repair; promoted live source and full-chain validation passed; no national-total scaling and no technology commodity mode demand bound share or UDC change."
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(change_rows)
        print("CHANGES.csv: finalized live validation status")


if __name__ == "__main__":
    main()
