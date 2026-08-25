#!/usr/bin/env python3
"""Append the Philippines v16 energy-input calibration to the canonical ledger."""

from __future__ import annotations

import csv
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
LEDGER = PACKAGE / "data_sources"
DATE = "2026-08-11"
CHANGE = "CHG_PHL_V16_ENERGY_INPUTS_20260811"


def read(name: str) -> tuple[list[str], list[dict[str, str]]]:
    with (LEDGER / name).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def write(name: str, fields: list[str], rows: list[dict[str, str]]) -> None:
    with (LEDGER / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)


def append_unique(name: str, id_field: str, additions: list[dict[str, str]]) -> None:
    fields, rows = read(name)
    existing = {row[id_field]: row for row in rows}
    for row in additions:
        missing = set(fields) - set(row)
        extra = set(row) - set(fields)
        if missing or extra:
            raise AssertionError(f"{name} schema mismatch for {row[id_field]}: missing={missing} extra={extra}")
        if row[id_field] in existing:
            existing[row[id_field]].update(row)
        else:
            rows.append(row)
    write(name, fields, rows)


def main() -> None:
    append_unique("SOURCES.csv", "source_id", [
        {
            "source_id": "SRC_OSEMOSYS_GLOBAL_TECH_CODES",
            "provider": "OSeMOSYS Global",
            "product": "Model Structure documentation",
            "edition": "documentation accessed 2026-08-11",
            "reference_period": "current naming convention",
            "geography": "global",
            "variable": "Power-generation technology code suffixes",
            "source_unit": "code definition",
            "exact_locator": "Power Generation Technology Codes table and following paragraph: suffix 00 is non-investable historical capacity and suffix 01 is investable capacity",
            "url": "https://osemosys-global.readthedocs.io/en/latest/model-structure.html#power-generation-technology-codes",
            "access_date": DATE,
            "license": "OSeMOSYS Global documentation terms",
            "sha256": "",
            "local_file": "",
            "notes": "Establishes that 01 is not a resource-quality tier."
        },
        {
            "source_id": "SRC_NREL_PHL_OFFSHORE_CREZ_2025",
            "provider": "National Renewable Energy Laboratory",
            "product": "Integrating Offshore Wind Into Competitive Renewable Energy Zones (CREZ) for the Philippines",
            "edition": "NREL/TP-5R00-92293",
            "reference_period": "2009-2021 wind record; 2022 costs",
            "geography": "Philippines offshore development zones A-G",
            "variable": "Net offshore capacity factor, technical-potential capacity and modeled losses",
            "source_unit": "percent; MW",
            "exact_locator": "Table 2 printed p.9; Figure 10 printed p.10; Table 4 printed p.13",
            "url": "https://www.nrel.gov/docs/fy25osti/92293.pdf",
            "access_date": DATE,
            "license": "U.S. Department of Energy/NREL public report",
            "sha256": "",
            "local_file": "",
            "notes": "Zone CFs: A 35.28 B 20.80 C 28.67 D 28.78 E 24.56 F 27.18 G 21.17 percent; the report applies 15 percent losses."
        },
        {
            "source_id": "SRC_NREL_USAID_SEA_RE_2020",
            "provider": "USAID-NREL Partnership",
            "product": "Exploring Renewable Energy Opportunities in Select Southeast Asian Countries",
            "edition": "Revised June 2020; NREL/TP-7A40-71814",
            "reference_period": "screened technical potential",
            "geography": "Philippines",
            "variable": "Restricted-screen onshore-wind generation potential by LCOE band",
            "source_unit": "TWh/year",
            "exact_locator": "Table B-2 printed p.62: Philippines restricted rows 27.0 120.9 and 36.5 TWh",
            "url": "https://docs.nrel.gov/docs/fy19osti/71814.pdf",
            "access_date": DATE,
            "license": "U.S. Department of Energy/NREL public report",
            "sha256": "",
            "local_file": "",
            "notes": "The three bands sum to 184.4 TWh/year or 663.84 PJ/year."
        },
        {
            "source_id": "SRC_PHL_DOE_CAPACITY_2020",
            "provider": "Philippines Department of Energy",
            "product": "2020 Power Situation Report",
            "edition": "as of 9 September 2021",
            "reference_period": "2020",
            "geography": "Philippines",
            "variable": "Geothermal installed and dependable generating capacity",
            "source_unit": "MW",
            "exact_locator": "Installed and Dependable Capacity by Grid/System table: geothermal total installed 1928 MW and dependable 1753 MW",
            "url": "https://doe.gov.ph/sites/default/files/pdf/electric_power/2020_power-situation-report_as_of_09-september-2021.pdf",
            "access_date": DATE,
            "license": "Philippine government publication",
            "sha256": "",
            "local_file": "",
            "notes": "Used only to calculate utilization benchmarks; it does not set the availability factor."
        },
        {
            "source_id": "SRC_PHL_DOE_GENERATION_2023",
            "provider": "Philippines Department of Energy",
            "product": "Gross Power Generation by Grid and by Technology",
            "edition": "2023 historical series",
            "reference_period": "2020-2023",
            "geography": "Philippines",
            "variable": "Geothermal gross generation",
            "source_unit": "MWh",
            "exact_locator": "Philippines total geothermal row: 2020 gross generation 10756815 MWh",
            "url": "https://legacy.doe.gov.ph/sites/default/files/pdf/energy_statistics/03_2023_Gross_Generation_per_Grid_and_per_technology_rev2.pdf",
            "access_date": DATE,
            "license": "Philippine government publication",
            "sha256": "",
            "local_file": "",
            "notes": "Benchmark-only observation paired with DOE capacity data."
        },
        {
            "source_id": "SRC_PHL_V16_ENERGY_INPUTS",
            "provider": "EAPD-DRB",
            "product": "Philippines v16 energy-input register",
            "edition": DATE,
            "reference_period": "2020-2053",
            "geography": "Philippines",
            "variable": "Technology renames, offshore zone data, geothermal availability and onshore resource ceiling",
            "source_unit": "record",
            "exact_locator": "snapshots/energy_inputs_2026-08-11.json",
            "url": "",
            "access_date": DATE,
            "license": "MUIOGO repository terms",
            "sha256": "d16ac808cda4bf15b19c4969e406234cd1cd66a40ba96948b610c23b69cdf744",
            "local_file": "snapshots/energy_inputs_2026-08-11.json",
            "notes": "Full-precision normalized inputs and exact publication locators used by the generator."
        },
        {
            "source_id": "SRC_PHL_V16_ENERGY_INPUT_MANIFEST",
            "provider": "EAPD-DRB",
            "product": "Philippines v16 energy-input candidate manifest",
            "edition": DATE,
            "reference_period": "2020-2053",
            "geography": "Philippines",
            "variable": "Source hashes, exact changed files, calculated factors and non-forcing assertions",
            "source_unit": "record",
            "exact_locator": "snapshots/energy_input_calibration_manifest.json",
            "url": "",
            "access_date": DATE,
            "license": "MUIOGO repository terms",
            "sha256": "051e573de329679c6f0686791d1c9859ec53ccbb9aff56409a6a3366f83e5e6e",
            "local_file": "snapshots/energy_input_calibration_manifest.json",
            "notes": "Generated after UpdateCase and before solver generation."
        },
        {
            "source_id": "SRC_PHL_V16_ENERGY_INPUT_VALIDATION",
            "provider": "EAPD-DRB",
            "product": "Philippines v16 energy-input validation record",
            "edition": DATE,
            "reference_period": "2020-2053",
            "geography": "Philippines",
            "variable": "Source diff, generated names, matrix, optimum and affected-result checks",
            "source_unit": "record",
            "exact_locator": "snapshots/energy_input_validation.json",
            "url": "",
            "access_date": DATE,
            "license": "MUIOGO repository terms",
            "sha256": "92cc6074c4cae05b06cd4e92c905f1370e44fa2299dfc472bafe011630be823d",
            "local_file": "snapshots/energy_input_validation.json",
            "notes": "Disposable BASE candidate solved optimally; all eight recorded checks passed."
        },
        {
            "source_id": "SRC_PHL_V16_ENERGY_INPUT_LIVE_VALIDATION",
            "provider": "EAPD-DRB",
            "product": "Philippines v16 promoted energy-input live validation",
            "edition": DATE,
            "reference_period": "2020-2053",
            "geography": "Philippines",
            "variable": "Promoted source identity, live optimum, generated representation, affected results and solve reproducibility",
            "source_unit": "record",
            "exact_locator": "snapshots/energy_input_live_validation.json",
            "url": "",
            "access_date": DATE,
            "license": "MUIOGO repository terms",
            "sha256": "7381fa0bc00c834d9a6b85b25f8fb0092f7c85b84b695abd52eb70d36d5a7940",
            "local_file": "snapshots/energy_input_live_validation.json",
            "notes": "The live full-chain run solved optimally and reproduced the candidate objective within 0.00001; all seven live checks passed."
        },
    ])

    append_unique("ASSUMPTIONS.csv", "assumption_id", [
        {
            "assumption_id": "ASM_PHL_V16_INVESTABLE_SUFFIX",
            "statement": "Interpret the inherited OSeMOSYS Global 01 suffix as investable status and remove the misleading MUIO _T1 resource-tier label.",
            "central_value": "01 = investable",
            "unit": "technology-code meaning",
            "evidence_source_ids": "SRC_OSEMOSYS_GLOBAL_TECH_CODES;SRC_PHL_INHERITED_BASE_SNAPSHOT",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "The upstream naming specification explicitly defines 01 as investable and does not define wind or solar resource tiers.",
            "notes": "Stable TechId values are preserved; no commodity carries _T1."
        },
        {
            "assumption_id": "ASM_PHL_V16_OFFSHORE_AGGREGATION",
            "statement": "Represent the single national offshore-wind option with the technical-capacity-weighted net mean of the seven current Philippine offshore development zones.",
            "central_value": "0.2847380261587777",
            "unit": "fraction",
            "evidence_source_ids": "SRC_NREL_PHL_OFFSHORE_CREZ_2025;SRC_PHL_V16_ENERGY_INPUTS",
            "lower_bound": "0.2080",
            "upper_bound": "0.3528",
            "rationale": "The model has one aggregated investable offshore technology rather than a zone or resource-tier supply curve.",
            "notes": "The NREL data include 15 percent losses, so wind AvailabilityFactor remains 1 to avoid double derating."
        },
        {
            "assumption_id": "ASM_PHL_V16_OFFSHORE_PROFILE_SHAPE",
            "statement": "Preserve the inherited 30-timeslice relative offshore-wind shape and scale every nonzero value by one common factor to the sourced annual mean.",
            "central_value": "1.4656121710190289",
            "unit": "profile multiplier",
            "evidence_source_ids": "SRC_NREL_PHL_OFFSHORE_CREZ_2025;SRC_PHL_V16_ENERGY_INPUTS;SRC_PHL_INHERITED_BASE_SNAPSHOT",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "The report establishes annual and seasonal behavior but the exact hourly zone files were not frozen into this build; uniform scaling preserves the existing adequacy shape without fabricating hourly observations.",
            "notes": "A future hourly rebuild is recorded as a gap."
        },
        {
            "assumption_id": "ASM_PHL_V16_GEOTHERMAL_AVAILABILITY",
            "statement": "Restore the inherited engineering availability factor of 0.9 for the existing geothermal technology; use observed 2020 utilization only as a validation benchmark.",
            "central_value": "0.9",
            "unit": "fraction",
            "evidence_source_ids": "SRC_PHL_INHERITED_BASE_SNAPSHOT;SRC_PHL_DOE_CAPACITY_2020;SRC_PHL_DOE_GENERATION_2023",
            "lower_bound": "0",
            "upper_bound": "1",
            "rationale": "Availability 1.0 incorrectly assumes no planned or forced outage; directly fitting the 2020 utilization outcome would conceal dispatch, steam-field and outage drivers.",
            "notes": "The existing 4 GW capacity ceiling remains unchanged and limits annual output to 113.5296 PJ at 0.9 availability."
        },
        {
            "assumption_id": "ASM_PHL_V16_ONSHORE_SCREEN",
            "statement": "Use the NREL/USAID restricted land-use screen as the continuing national onshore-wind technical resource ceiling.",
            "central_value": "663.84",
            "unit": "PJ/year",
            "evidence_source_ids": "SRC_NREL_USAID_SEA_RE_2020;SRC_PHL_V16_ENERGY_INPUTS",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "The stricter screen excludes land that is not realistically available and replaces an unsupported 1594.08 PJ ceiling.",
            "notes": "This is an upper resource limit, not an observed generation target."
        },
    ])

    append_unique("CALCULATIONS.csv", "calculation_id", [
        {
            "calculation_id": "CALC_PHL_V16_OFFSHORE_WEIGHTED_CF",
            "formula": "sum_z[(fixed_MW_z + floating_MW_z) * CF_z] / sum_z[fixed_MW_z + floating_MW_z]",
            "source_ids": "SRC_NREL_PHL_OFFSHORE_CREZ_2025;SRC_PHL_V16_ENERGY_INPUTS",
            "assumption_ids": "ASM_PHL_V16_OFFSHORE_AGGREGATION",
            "input_calculation_ids": "",
            "input_values": "A=3147MW@35.28%;B=1358@20.80%;C=6099@28.67%;D=27220@28.78%;E=573@24.56%;F=2234@27.18%;G=2108@21.17%",
            "input_units": "MW; percent",
            "output_value": "0.2847380261587776971852406467",
            "output_unit": "fraction",
            "script_path": "scripts/calibrate_philippines_v16_energy_inputs.py",
            "script_version": DATE,
            "notes": "Total technical-potential capacity is 42739 MW; NREL net factors already contain the report's 15 percent losses."
        },
        {
            "calculation_id": "CALC_PHL_V16_OFFSHORE_PROFILE_SCALE",
            "formula": "new_CF_timeslice = old_CF_timeslice * target_weighted_CF / sum_ts(old_CF_timeslice * YearSplit_timeslice)",
            "source_ids": "SRC_NREL_PHL_OFFSHORE_CREZ_2025;SRC_PHL_V16_ENERGY_INPUTS;SRC_PHL_INHERITED_BASE_SNAPSHOT",
            "assumption_ids": "ASM_PHL_V16_OFFSHORE_AGGREGATION;ASM_PHL_V16_OFFSHORE_PROFILE_SHAPE",
            "input_calculation_ids": "CALC_PHL_V16_OFFSHORE_WEIGHTED_CF",
            "input_values": "old annual CF=0.19427924507532; target=0.2847380261587777",
            "input_units": "fraction; fraction",
            "output_value": "1.4656121710190289",
            "output_unit": "profile multiplier",
            "script_path": "scripts/calibrate_philippines_v16_energy_inputs.py",
            "script_version": DATE,
            "notes": "Applied to 30 SC_0 rows and 34 years; null policy overrides remain null and inherit SC_0."
        },
        {
            "calculation_id": "CALC_PHL_V16_ONSHORE_TAU",
            "formula": "TAU = (27.0 + 120.9 + 36.5) TWh/year * 3.6 PJ/TWh",
            "source_ids": "SRC_NREL_USAID_SEA_RE_2020;SRC_PHL_V16_ENERGY_INPUTS",
            "assumption_ids": "ASM_PHL_V16_ONSHORE_SCREEN",
            "input_calculation_ids": "",
            "input_values": "27.0;120.9;36.5;3.6",
            "input_units": "TWh/year by LCOE band; PJ/TWh",
            "output_value": "663.84",
            "output_unit": "PJ/year",
            "script_path": "scripts/calibrate_philippines_v16_energy_inputs.py",
            "script_version": DATE,
            "notes": "Replaces 1594.08 PJ/year in SC_0 for 2020-2053; policy scenarios inherit."
        },
        {
            "calculation_id": "CALC_PHL_V16_GEOTHERMAL_BENCHMARK_CF",
            "formula": "observed utilization = gross generation MWh / (capacity MW * 8760 h/year)",
            "source_ids": "SRC_PHL_DOE_CAPACITY_2020;SRC_PHL_DOE_GENERATION_2023",
            "assumption_ids": "ASM_PHL_V16_GEOTHERMAL_AVAILABILITY",
            "input_calculation_ids": "",
            "input_values": "generation=10756815; installed=1928; dependable=1753; hours=8760",
            "input_units": "MWh; MW; MW; h/year",
            "output_value": "installed basis=0.6368577375; dependable basis=0.7004594018",
            "output_unit": "fraction",
            "script_path": "scripts/data/philippines_v16_energy_inputs.json",
            "script_version": DATE,
            "notes": "Benchmark only; the model AF is not fitted to observed generation."
        },
        {
            "calculation_id": "CALC_PHL_V16_GEOTHERMAL_ENVELOPE",
            "formula": "annual capacity envelope = 4 GW * 31.536 PJ/GW-year * 0.9",
            "source_ids": "SRC_PHL_INHERITED_BASE_SNAPSHOT;SRC_PHL_V16_ENERGY_INPUTS",
            "assumption_ids": "ASM_PHL_V16_GEOTHERMAL_AVAILABILITY",
            "input_calculation_ids": "",
            "input_values": "4;31.536;0.9",
            "input_units": "GW; PJ/GW-year; fraction",
            "output_value": "113.5296",
            "output_unit": "PJ/year",
            "script_path": "scripts/validate_philippines_v16_energy_inputs.py",
            "script_version": DATE,
            "notes": "The unchanged 126 PJ TAU is slack once the unchanged 4 GW capacity ceiling and corrected availability apply."
        },
        {
            "calculation_id": "CALC_PHL_V16_ENERGY_INPUT_RUN",
            "formula": "UpdateCase structural regeneration; source-diff proof; DataFile generation and preprocessing; GLPK matrix check; CBC optimization; MUIO CSV export; affected-result validation",
            "source_ids": "SRC_PHL_V16_ENERGY_INPUT_MANIFEST;SRC_PHL_V16_ENERGY_INPUT_VALIDATION",
            "assumption_ids": "ASM_PHL_V16_INVESTABLE_SUFFIX;ASM_PHL_V16_OFFSHORE_AGGREGATION;ASM_PHL_V16_OFFSHORE_PROFILE_SHAPE;ASM_PHL_V16_GEOTHERMAL_AVAILABILITY;ASM_PHL_V16_ONSHORE_SCREEN",
            "input_calculation_ids": "CALC_PHL_V16_OFFSHORE_WEIGHTED_CF;CALC_PHL_V16_OFFSHORE_PROFILE_SCALE;CALC_PHL_V16_ONSHORE_TAU;CALC_PHL_V16_GEOTHERMAL_ENVELOPE",
            "input_values": "baseline objective=369729000.2004411; candidate objective=369730088.2957073; rows=791109; columns=884956; nonzeros=12552173",
            "input_units": "model objective; matrix counts",
            "output_value": "optimal; objective change=0.00029429535296936703%; eight checks passed",
            "output_unit": "status; percent",
            "script_path": "scripts/validate_philippines_v16_energy_inputs.py",
            "script_version": DATE,
            "notes": "Application-chain wall time was 215.64 seconds. Offshore new capacity remained zero with a positive 2025 reduced cost of 1639.5751; no build was forced."
        },
        {
            "calculation_id": "CALC_PHL_V16_ENERGY_INPUT_LIVE_RUN",
            "formula": "regenerate promoted source through DataFile and preprocessData; GLPK matrix check; CBC optimization; CSV export; compare source hashes, objective and affected physical results with validated candidate",
            "source_ids": "SRC_PHL_V16_ENERGY_INPUT_MANIFEST;SRC_PHL_V16_ENERGY_INPUT_VALIDATION;SRC_PHL_V16_ENERGY_INPUT_LIVE_VALIDATION",
            "assumption_ids": "ASM_PHL_V16_INVESTABLE_SUFFIX;ASM_PHL_V16_OFFSHORE_AGGREGATION;ASM_PHL_V16_OFFSHORE_PROFILE_SHAPE;ASM_PHL_V16_GEOTHERMAL_AVAILABILITY;ASM_PHL_V16_ONSHORE_SCREEN",
            "input_calculation_ids": "CALC_PHL_V16_ENERGY_INPUT_RUN",
            "input_values": "candidate objective=369730088.2957073; live objective=369730088.29570782; rows=791109; columns=884956; nonzeros=12552173",
            "input_units": "model objective; matrix counts",
            "output_value": "optimal; objective difference=0.00000053; seven live checks passed",
            "output_unit": "status; model objective",
            "script_path": "scripts/validate_philippines_v16_energy_inputs_live.py",
            "script_version": DATE,
            "notes": "Live chain wall time was 334.14 seconds and CBC wall time 263.58 seconds. Repeated solves selected alternative degenerate capacity/activity optima; demand, annual technology emissions and all affected physical checks reproduced."
        },
    ])

    map_fields, map_rows = read("MODEL_MAP.csv")
    for row in map_rows:
        if row["map_id"] == "MAP_PHL_V16_LIVE_SOURCE_20260811":
            if row["superseded_by"] and row["superseded_by"] != CHANGE:
                raise AssertionError("MAP_PHL_V16_LIVE_SOURCE_20260811 already superseded")
            row["superseded_by"] = CHANGE
    write("MODEL_MAP.csv", map_fields, map_rows)
    append_unique("MODEL_MAP.csv", "map_id", [
        {"map_id":"MAP_PHL_V16_RENAME_WON","model_file":"case/Philippines_v16/genData.json","parameter":"technology name and description","entity":"TEC_1wdli","mode":"","scenario":"all scenarios structurally","years":"2020-2053","value_or_expression":"PHL_POW_PP_WON; Onshore wind","model_unit":"metadata","evidence_ids":"SRC_OSEMOSYS_GLOBAL_TECH_CODES;ASM_PHL_V16_INVESTABLE_SUFFIX;SRC_PHL_V16_ENERGY_INPUT_MANIFEST","superseded_by":"","evidence_type":"estimated","notes":"Before PHL_POW_PP_WON_T1 / Onshore wind tier 1; stable TechId preserved."},
        {"map_id":"MAP_PHL_V16_RENAME_WOF","model_file":"case/Philippines_v16/genData.json","parameter":"technology name and description","entity":"TEC_bl1d7","mode":"","scenario":"all scenarios structurally","years":"2020-2053","value_or_expression":"PHL_POW_PP_WOF; Offshore wind","model_unit":"metadata","evidence_ids":"SRC_OSEMOSYS_GLOBAL_TECH_CODES;ASM_PHL_V16_INVESTABLE_SUFFIX;SRC_PHL_V16_ENERGY_INPUT_MANIFEST","superseded_by":"","evidence_type":"estimated","notes":"Before PHL_POW_PP_WOF_T1 / Offshore wind tier 1; stable TechId preserved."},
        {"map_id":"MAP_PHL_V16_RENAME_SPV","model_file":"case/Philippines_v16/genData.json","parameter":"technology name and description","entity":"TEC_1k064","mode":"","scenario":"all scenarios structurally","years":"2020-2053","value_or_expression":"PHL_POW_PP_SPV; Solar photovoltaic","model_unit":"metadata","evidence_ids":"SRC_OSEMOSYS_GLOBAL_TECH_CODES;ASM_PHL_V16_INVESTABLE_SUFFIX;SRC_PHL_V16_ENERGY_INPUT_MANIFEST","superseded_by":"","evidence_type":"estimated","notes":"Before PHL_POW_PP_SPV_T1 / Solar photovoltaic tier 1; stable TechId preserved."},
        {"map_id":"MAP_PHL_V16_OFFSHORE_CF","model_file":"case/Philippines_v16/RYTTs.json","parameter":"CapacityFactor","entity":"TEC_bl1d7 / PHL_POW_PP_WOF","mode":"all 30 timeslices","scenario":"SC_0; policy rows inherit","years":"2020-2053","value_or_expression":"old timeslice CF * 1.4656121710190289; YearSplit-weighted annual mean=0.2847380261587777","model_unit":"fraction","evidence_ids":"CALC_PHL_V16_OFFSHORE_WEIGHTED_CF;CALC_PHL_V16_OFFSHORE_PROFILE_SCALE;ASM_PHL_V16_OFFSHORE_AGGREGATION;ASM_PHL_V16_OFFSHORE_PROFILE_SHAPE;SRC_PHL_V16_ENERGY_INPUT_MANIFEST","superseded_by":"","evidence_type":"derived","notes":"NREL zone values include 15 percent losses; wind AF remains 1 to avoid double derating."},
        {"map_id":"MAP_PHL_V16_GEOTHERMAL_AF","model_file":"case/Philippines_v16/RYT.json","parameter":"AvailabilityFactor","entity":"TEC_0qr3z / PHL_POW_GEO_OLD","mode":"","scenario":"SC_0; policy rows inherit","years":"2020-2053","value_or_expression":"0.9","model_unit":"fraction","evidence_ids":"ASM_PHL_V16_GEOTHERMAL_AVAILABILITY;SRC_PHL_INHERITED_BASE_SNAPSHOT;CALC_PHL_V16_GEOTHERMAL_BENCHMARK_CF;CALC_PHL_V16_GEOTHERMAL_ENVELOPE;SRC_PHL_V16_ENERGY_INPUT_MANIFEST","superseded_by":"","evidence_type":"derived","notes":"Before 1.0; restores inherited availability. DOE utilization is benchmark-only."},
        {"map_id":"MAP_PHL_V16_ONSHORE_TAU","model_file":"case/Philippines_v16/RYT.json","parameter":"TotalTechnologyAnnualActivityUpperLimit","entity":"TEC_1wdli / PHL_POW_PP_WON","mode":"","scenario":"SC_0; policy rows inherit","years":"2020-2053","value_or_expression":"663.84","model_unit":"PJ/year","evidence_ids":"CALC_PHL_V16_ONSHORE_TAU;ASM_PHL_V16_ONSHORE_SCREEN;SRC_NREL_USAID_SEA_RE_2020;SRC_PHL_V16_ENERGY_INPUT_MANIFEST","superseded_by":"","evidence_type":"derived","notes":"Before 1594.08; continuing screened physical resource ceiling, not a generation target."},
        {"map_id":"MAP_PHL_V16_ENERGY_INPUT_VALIDATION","model_file":"case/Philippines_v16","parameter":"validation evidence","entity":"ENERGY_INPUTS_BASE","mode":"","scenario":"BASE","years":"2020-2053","value_or_expression":"optimal objective 369730088.2957073; matrix 791109 x 884956 with 12552173 nonzeros; eight checks passed","model_unit":"status; objective; matrix counts","evidence_ids":"SRC_PHL_V16_ENERGY_INPUT_VALIDATION;CALC_PHL_V16_ENERGY_INPUT_RUN","superseded_by":"","evidence_type":"derived","notes":"Offshore capacity remains endogenous and is zero with positive reduced costs; corrected inputs do not force construction."},
        {"map_id":"MAP_PHL_V16_ENERGY_INPUT_LIVE_VALIDATION","model_file":"case/Philippines_v16/res/ENERGY_INPUTS_BASE","parameter":"promoted live validation evidence","entity":"ENERGY_INPUTS_BASE","mode":"","scenario":"BASE","years":"2020-2053","value_or_expression":"optimal objective 369730088.29570782; matrix 791109 x 884956 with 12552173 nonzeros; seven live checks passed","model_unit":"status; objective; matrix counts","evidence_ids":"SRC_PHL_V16_ENERGY_INPUT_LIVE_VALIDATION;CALC_PHL_V16_ENERGY_INPUT_LIVE_RUN","superseded_by":"","evidence_type":"derived","notes":"Source hashes equal the validated candidate. Repeated CBC solves have degenerate activity/capacity alternatives at the same objective; affected physical checks pass."},
        {"map_id":"MAP_PHL_V16_LIVE_SOURCE_ENERGY_20260811","model_file":"case/Philippines_v16","parameter":"complete current live source case","entity":"Philippines_v16","mode":"all","scenario":"all scenarios","years":"2020-2053","value_or_expression":"prior documented v16 deltas plus renewable naming repair offshore CF geothermal availability and onshore technical ceiling","model_unit":"source directory","evidence_ids":"SRC_PHL_V16_ENERGY_INPUTS;SRC_PHL_V16_ENERGY_INPUT_MANIFEST;SRC_PHL_V16_ENERGY_INPUT_VALIDATION;SRC_PHL_V16_ENERGY_INPUT_LIVE_VALIDATION;CALC_PHL_V16_ENERGY_INPUT_RUN;CALC_PHL_V16_ENERGY_INPUT_LIVE_RUN","superseded_by":"","evidence_type":"derived","notes":"Current authoritative inputs are live source JSON files; generated solver files and result files remain reproducible outputs."},
    ])

    append_unique("GAPS.csv", "item", [
        {
            "item": "Offshore hourly aggregation and resource-ceiling alignment",
            "why_absent": "The NREL report provides zone annual means and states that hourly grid-cell data exist, but the exact hourly zone files are not frozen here; the inherited 30-timeslice relative shape is therefore retained. The existing broad offshore activity ceiling is not redefined by this correction.",
            "upgrade_source": "Freeze the NREL Southeast Asia hourly zone/grid-cell dataset, document eligible-area coverage, aggregate it to the model timeslices, and align an offshore capacity or generation ceiling to the same geography.",
            "priority": "medium",
            "notes": "The annual net CF is sourced exactly; do not infer a best-resource tier from the retired _T1 suffix."
        },
        {
            "item": "Philippine geothermal outage and steam-field availability series",
            "why_absent": "The restored 0.9 availability is the inherited engineering assumption; DOE generation and capacity data provide utilization benchmarks but do not separate outages, steam-field decline, curtailment and economic dispatch.",
            "upgrade_source": "Plant-level DOE availability, outage and steam-field production records by year, with planned and forced outage definitions compatible with OSeMOSYS AvailabilityFactor.",
            "priority": "medium",
            "notes": "Do not fit AF directly to gross generation because generation is an endogenous outcome."
        },
    ])

    append_unique("CHANGES.csv", "change_id", [
        {
            "change_id": CHANGE,
            "date": DATE,
            "class": "B",
            "description": "Corrected renewable technology naming, replaced the offshore-wind annual capacity factor with a capacity-weighted NREL Philippine development-zone value, restored geothermal availability, and replaced the onshore-wind ceiling with the NREL/USAID screened potential.",
            "model_objects": "genData.json; RYT.json; RYTTs.json",
            "evidence_path": "calculation_notes/energy_inputs_v16_2026-08-11.md",
            "map_rows_affected": "MAP_PHL_V16_LIVE_SOURCE_20260811;MAP_PHL_V16_RENAME_WON;MAP_PHL_V16_RENAME_WOF;MAP_PHL_V16_RENAME_SPV;MAP_PHL_V16_OFFSHORE_CF;MAP_PHL_V16_GEOTHERMAL_AF;MAP_PHL_V16_ONSHORE_TAU;MAP_PHL_V16_ENERGY_INPUT_VALIDATION;MAP_PHL_V16_ENERGY_INPUT_LIVE_VALIDATION;MAP_PHL_V16_LIVE_SOURCE_ENERGY_20260811",
            "resolve_status": "resolved",
            "author": "Codex",
            "commit": "",
            "notes": "Non-forcing input repair: no technology IDs, commodities, demands, lower bounds, shares or user constraints changed; solved disposable and regenerated live BASE runs remained optimal."
        }
    ])


if __name__ == "__main__":
    main()
