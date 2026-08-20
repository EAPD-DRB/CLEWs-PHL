#!/usr/bin/env python3
"""Append the Philippines v21 power-allocation change to all six ledgers."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data_sources"


def digest(relative: str) -> str:
    return hashlib.sha256((LEDGER / relative).read_bytes()).hexdigest()


def append(filename: str, rows: list[dict[str, str]], key: str) -> None:
    path = LEDGER / filename
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream); header = reader.fieldnames; existing = list(reader)
    assert header is not None and all(set(row) == set(header) for row in rows)
    known = {row[key] for row in existing}
    additions = [row for row in rows if row[key] not in known]
    if additions:
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=header, lineterminator="\r\n")
            writer.writeheader(); writer.writerows(existing + additions)


def reconcile_v21_rows() -> None:
    """Canonicalize v21 rows when rerunning the idempotent updater."""
    path = LEDGER / "ASSUMPTIONS.csv"
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream); header = reader.fieldnames; rows = list(reader)
    assert header is not None
    for item in rows:
        if item["assumption_id"] == "ASM_PHL_V21_BUILD_ENVELOPES":
            item["lower_bound"] = ""
            item["upper_bound"] = ""
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=header, lineterminator="\r\n")
        writer.writeheader(); writer.writerows(rows)

    path = LEDGER / "MODEL_MAP.csv"
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream); header = reader.fieldnames; rows = list(reader)
    assert header is not None
    kinds = {
        "MAP_PHL_V21_OFFGRID_COMMODITY": "derived",
        "MAP_PHL_V21_OFFGRID_OIL": "derived",
        "MAP_PHL_V21_OFFGRID_RE": "derived",
        "MAP_PHL_V21_BIOMASS_FIT": "derived",
        "MAP_PHL_V21_HYDRO_PROFILE": "derived",
        "MAP_PHL_V21_GENERATION_BENCHMARK": "derived",
        "MAP_PHL_V21_VALIDATION_CHAIN": "direct",
    }
    for item in rows:
        if item["map_id"] in kinds:
            item["evidence_type"] = kinds[item["map_id"]]
        if item["map_id"] == "MAP_PHL_V21_OFFGRID_COMMODITY":
            item["evidence_ids"] = (
                "SRC_PHL_DOE_2020_POWER_SITUATION;CALC_PHL_V21_OFFGRID_DEMAND;"
                "CALC_PHL_V21_OFFGRID_DELIVERY;ASM_PHL_V21_2021_SALES_ESTIMATE"
            )
            item["notes"] = (
                "Identical PJ removed from existing electricity final demands; "
                "E=final demand/accounting, J=2021 sales estimate."
            )
        if item["map_id"] == "MAP_PHL_V21_OFFGRID_OIL":
            item["notes"] = "No activity minimum; E=stock/availability, J=construction ceiling."
        if item["map_id"] == "MAP_PHL_V21_OFFGRID_RE":
            item["notes"] = "Ceiling binds 2021 onward; E=stock/profile, J=aggregation/ceiling."
        if item["map_id"] == "MAP_PHL_V21_BIOMASS_FIT":
            item["notes"] = "Resource ceiling slack in 2020; E=stock/resource/contract, J=collection cost."
        if item["map_id"] == "MAP_PHL_V21_HYDRO_PROFILE":
            item["notes"] = "Supersedes restrictive v20 profile; E=availability, J=retained profile proxy; no observed hydro PJ used."
        if item["map_id"] == "MAP_PHL_V21_GENERATION_BENCHMARK":
            item["notes"] = "H=benchmark only; not present in solver input."
        if item["map_id"] == "MAP_PHL_V21_VALIDATION_CHAIN":
            item["model_file"] = "data_sources/snapshots/power_allocation_v21_optimizer_ledger.json"
            item["notes"] = "A=validation artifact; four optimizer runs, zero sensitivities, and r2 deterministic failure retained."
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=header, lineterminator="\r\n")
        writer.writeheader(); writer.writerows(rows)

    path = LEDGER / "CHANGES.csv"
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream); header = reader.fieldnames; rows = list(reader)
    assert header is not None
    for item in rows:
        if item["change_id"] == "CHG_PHL_V21_POWER_ALLOCATION_20260820":
            item["resolve_status"] = "resolved"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=header, lineterminator="\r\n")
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    evidence_hash = digest("snapshots/offgrid_power_evidence_2020_2022.csv")
    sources = [
        {"source_id":"SRC_PHL_DOE_2020_POWER_SITUATION","provider":"Philippines Department of Energy","product":"2020 Power Situation Report and end-2020 off-grid plant list","edition":"2020","reference_period":"2020","geography":"Philippines off-grid","variable":"Gross generation, sales, losses, installed and dependable capacity, generation mix","source_unit":"GWh;MW;percent","exact_locator":"Figure 18, off-grid sales figure, technology subtotals","url":"https://doe.gov.ph/sites/default/files/pdf/electric_power/2020_power-situation-report_as_of_09-september-2021.pdf","access_date":"2026-08-20","license":"Philippines government publication","sha256":evidence_hash,"local_file":"snapshots/offgrid_power_evidence_2020_2022.csv","notes":"Derived lossless extract; generation shares remain benchmarks except gross/sales accounting."},
        {"source_id":"SRC_PHL_DOE_OFFGRID_PLANTS_2021","provider":"Philippines Department of Energy","product":"List of Existing Power Plants (Off-Grid) as of December 2021","edition":"released 2022","reference_period":"2021-12-31","geography":"Philippines off-grid","variable":"Installed and dependable capacity by plant and technology","source_unit":"MW","exact_locator":"Hydro, solar and wind subtotals","url":"https://legacy.doe.gov.ph/sites/default/files/pdf/electric_power/05_lvm_off-grid_loepp-11302022.pdf","access_date":"2026-08-20","license":"Philippines government publication","sha256":evidence_hash,"local_file":"snapshots/offgrid_power_evidence_2020_2022.csv","notes":"Used as a deployment-envelope cross-check, not a realized investment equality."},
        {"source_id":"SRC_PHL_DOE_2022_POWER_SITUATION","provider":"Philippines Department of Energy","product":"2022 Power Situation Report","edition":"2024 release","reference_period":"2022","geography":"Philippines off-grid","variable":"Annual new off-grid diesel capacity","source_unit":"MW","exact_locator":"Supply section: 31 MW off-grid diesel addition","url":"https://legacy.doe.gov.ph/sites/default/files/pdf/electric_power/2022_Power_Situation_Report_as_of_02Dec2024_ADLGB_DICE_CLEAN_rev1_FINAL.pdf","access_date":"2026-08-20","license":"Philippines government publication","sha256":evidence_hash,"local_file":"snapshots/offgrid_power_evidence_2020_2022.csv","notes":"Capability evidence for optional oil TAMaxCI."},
        {"source_id":"SRC_PHL_DOE_2022_OFFGRID_GENERATION","provider":"Philippines Department of Energy","product":"2022 Monthly Gross Generation by Grid and Technology","edition":"2022 statistics","reference_period":"2022","geography":"Philippines off-grid","variable":"Gross generation by oil, renewable, coal and total","source_unit":"MWh","exact_locator":"Philippines off-grid plant-type total","url":"https://legacy.doe.gov.ph/sites/default/files/pdf/energy_statistics/2022-MONTHLY-GROSS-GENERATION_power_statistics_10_per_grid_per_technology-08292023.pdf","access_date":"2026-08-20","license":"Philippines government publication","sha256":evidence_hash,"local_file":"snapshots/offgrid_power_evidence_2020_2022.csv","notes":"Benchmark only; 89.492 GWh off-grid coal is not represented in v21."},
        {"source_id":"SRC_PHL_DOE_PHILLIDAR2_BIOMASS","provider":"Philippines Department of Energy / Phil-LiDAR 2","product":"Nationwide Detailed Resources Assessment Terminal Report","edition":"terminal report","reference_period":"resource coefficients","geography":"Philippines","variable":"Residue fractions, lower heating values and availability","source_unit":"fraction;MJ/kg","exact_locator":"Table 25 and biomass availability tables","url":"https://legacy.doe.gov.ph/sites/default/files/pdf/renewable_energy/Terminal%20Report_Phil-LiDAR%202%20Program%20Nationwide%20Detailed%20Resources.pdf","access_date":"2026-08-20","license":"Philippines government publication","sha256":"","local_file":"","notes":"Rice husk, bagasse, coconut husk and shell coefficients."},
        {"source_id":"SRC_PHL_ERC_BIOMASS_FIT","provider":"Philippines Energy Regulatory Commission","product":"Biomass feed-in tariff resolutions and 2021-2025 adjustment notice","edition":"2012-2025","reference_period":"2020-2025","geography":"Philippines","variable":"Biomass FIT rate and 250 MW installation target","source_unit":"PHP/kWh;MW","exact_locator":"Resolution 10/2012, Resolution 06/2020 and adjusted biomass entrant rates","url":"https://www.erc.gov.ph/Files/Render/issuance/30680","access_date":"2026-08-20","license":"Philippines government publication","sha256":"","local_file":"","notes":"FIT changes cost only; it does not require activity."},
        {"source_id":"SRC_WB_PHL_OFFICIAL_FX_2020_2024","provider":"World Bank","product":"Official exchange rate (LCU per US$, period average)","edition":"World Development Indicators","reference_period":"2020-2024","geography":"Philippines","variable":"PHP per USD","source_unit":"PHP/USD","exact_locator":"PA.NUS.FCRF, Philippines","url":"https://data.worldbank.org/indicator/PA.NUS.FCRF?locations=PH","access_date":"2026-08-20","license":"World Bank data terms","sha256":"","local_file":"","notes":"Full-precision annual values retained in the build script."},
        {"source_id":"SRC_PHL_V21_POWER_BUILD","provider":"MUIOGO Philippines v21 workflow","product":"Power-allocation build manifest","edition":"compact r4","reference_period":"2020-2053","geography":"Philippines","variable":"Source hashes, stocks, demand, profiles, resource ceilings and build limits","source_unit":"model-native","exact_locator":"complete JSON","url":"","access_date":"2026-08-20","license":"Repository license","sha256":digest("snapshots/power_allocation_v21_build_manifest.json"),"local_file":"snapshots/power_allocation_v21_build_manifest.json","notes":"Exact accepted source transformation."},
        {"source_id":"SRC_PHL_V21_POWER_VALIDATION","provider":"MUIOGO Philippines v21 workflow","product":"Power-allocation validation","edition":"v21","reference_period":"2020-2024 and full horizon","geography":"Philippines","variable":"Generation errors, off-grid mix, deterministic checks, runtime and promotion identity","source_unit":"mixed","exact_locator":"validation JSON, technology CSV and optimizer ledger","url":"","access_date":"2026-08-20","license":"Repository license","sha256":digest("snapshots/power_allocation_v21_validation.json"),"local_file":"snapshots/power_allocation_v21_validation.json","notes":"Four optimizer runs recorded; zero sensitivities."},
    ]
    append("SOURCES.csv", sources, "source_id")

    calculations = [
        {"calculation_id":"CALC_PHL_V21_OFFGRID_DEMAND","formula":"sales PJ = GWh*0.0036; subtract identical sector-weighted PJ from existing final demands","source_ids":"SRC_PHL_DOE_2020_POWER_SITUATION;SRC_PHL_V21_POWER_BUILD","assumption_ids":"ASM_PHL_V21_OFFGRID_DEMAND_PROJECTION","input_calculation_ids":"","input_values":"1286 GWh in 2020;1352.86158 in 2021;1488 in 2022","input_units":"GWh","output_value":"4.6296 PJ in 2020; annual series in build manifest","output_unit":"PJ final demand","script_path":"scripts/apply_power_allocation_v21_compact.py","script_version":"r4","notes":"National final-demand identity error <=5.69e-14 PJ."},
        {"calculation_id":"CALC_PHL_V21_OFFGRID_DELIVERY","formula":"OAR = customer sales / gross generation","source_ids":"SRC_PHL_DOE_2020_POWER_SITUATION;SRC_PHL_V21_POWER_BUILD","assumption_ids":"ASM_PHL_V21_2021_SALES_ESTIMATE","input_calculation_ids":"CALC_PHL_V21_OFFGRID_DEMAND","input_values":"1286/1618;1352.86158/1654.491;1488/1769","input_units":"GWh/GWh","output_value":"0.7948084;0.81769;0.841153","output_unit":"PJ sales/PJ gross activity","script_path":"scripts/apply_power_allocation_v21_compact.py","script_version":"r4","notes":"2022 ratio continues after 2022."},
        {"calculation_id":"CALC_PHL_V21_STOCK_SPLIT","formula":"grid RC = original national RC*(1-offgrid2020/national2020); new RC = original national RC*offgrid2020/national2020","source_ids":"SRC_PHL_DOE_2020_POWER_SITUATION;SRC_PHL_V21_POWER_BUILD","assumption_ids":"ASM_PHL_V21_SCALED_STOCK_SPLIT","input_calculation_ids":"","input_values":"oil 0.569224/4.2366; hydro 0.030595/3.7793; solar 0.00723/1.0193; wind 0.016/0.4429; biomass FIT 0.25/0.4474","input_units":"GW/GW","output_value":"exact annual stock conservation","output_unit":"GW","script_path":"scripts/apply_power_allocation_v21_compact.py","script_version":"r4","notes":"Maximum identity error 5.56e-16 GW."},
        {"calculation_id":"CALC_PHL_V21_BUILD_LIMITS","formula":"2020=0 initial condition; 2021+=rounded headroom above demonstrated addition","source_ids":"SRC_PHL_DOE_2022_POWER_SITUATION;SRC_PHL_DOE_OFFGRID_PLANTS_2021","assumption_ids":"ASM_PHL_V21_BUILD_ENVELOPES","input_calculation_ids":"","input_values":"31 MW diesel;16 MW recent wind entry","input_units":"MW/year","output_value":"oil 0.10;renewable 0.02 from 2021","output_unit":"GW/year","script_path":"scripts/apply_power_allocation_v21_compact.py","script_version":"r4","notes":"Optional maxima; no investment minimum."},
        {"calculation_id":"CALC_PHL_V21_HYDRO_PROFILE","formula":"CF(ts)=wet/dry retained factor*scale; scale preserves sum(CF*YearSplit)=0.26438418","source_ids":"SRC_PHL_V21_POWER_BUILD","assumption_ids":"ASM_PHL_V21_RETAINED_HYDRO_PROFILE","input_calculation_ids":"","input_values":"wet 0.3834;dry 0.1447;current 30-slice YearSplit","input_units":"fraction","output_value":"0.264384211 annual mean after serialization","output_unit":"fraction","script_path":"scripts/apply_power_allocation_v21_compact.py","script_version":"r4","notes":"No observed generation used."},
        {"calculation_id":"CALC_PHL_V21_BIOMASS_RESIDUE","formula":"crop Mt*residue fraction*LHV GJ/t*availability","source_ids":"SRC_PHL_DOE_PHILLIDAR2_BIOMASS;SRC_PHL_V21_POWER_BUILD","assumption_ids":"ASM_PHL_V21_RESIDUE_AVAILABILITY","input_calculation_ids":"","input_values":"rice 0.225*16.5*0.81;sugar 0.29*16.56*0.61;coconut (0.35*21.75+0.15*25.32)*0.55","input_units":"fraction;GJ/t;fraction","output_value":"220.43963275 in 2020","output_unit":"PJ biomass input","script_path":"scripts/apply_power_allocation_v21_compact.py","script_version":"r4","notes":"TAU activity ceiling 55.10072473 PJ; capacity ceiling only 5.02926598 PJ."},
        {"calculation_id":"CALC_PHL_V21_BIOMASS_FIT_COST","formula":"VC=15.8 - FIT(PHP/kWh)*(1000/3.6)/FX - generic biomass supply VC*IAR + 0.0001","source_ids":"SRC_PHL_ERC_BIOMASS_FIT;SRC_WB_PHL_OFFICIAL_FX_2020_2024;SRC_PHL_V21_POWER_BUILD","assumption_ids":"ASM_PHL_V21_RESIDUE_COLLECTION_COST","input_calculation_ids":"CALC_PHL_V21_BIOMASS_RESIDUE","input_values":"FIT 6.63 in 2020 and adjusted 2021-2025 rates;15.8 collection cost","input_units":"PHP/kWh;MUSD/PJ electricity","output_value":"annual VC series in RYTM.json","output_unit":"MUSD/PJ activity","script_path":"scripts/apply_power_allocation_v21_compact.py","script_version":"r4","notes":"FIT credit ends after 2034; activity remains endogenous."},
        {"calculation_id":"CALC_PHL_V21_GENERATION_VALIDATION","formula":"WAPE=sum(abs(model technology PJ-observed PJ))/observed total PJ; total error=(model total-observed total)/observed total","source_ids":"SRC_PHL_DOE_POWER_SUMMARY_2024;SRC_PHL_DOE_2022_OFFGRID_GENERATION;SRC_PHL_V21_POWER_VALIDATION","assumption_ids":"ASM_PHL_V20_GENERATION_BENCHMARK_ONLY;ASM_PHL_V21_BOUNDARY_ACCOUNTING","input_calculation_ids":"","input_values":"DOE 2020 national and 2021-2024 grid-only benchmarks","input_units":"GWh;PJ","output_value":"annual metrics in power_allocation_v21_validation.json","output_unit":"percent","script_path":"scripts/compare_power_allocation_v21.py","script_version":"v21","notes":"Observed generation never enters a source parameter."},
    ]
    append("CALCULATIONS.csv", calculations, "calculation_id")

    assumptions = [
        {"assumption_id":"ASM_PHL_V21_OFFGRID_DEMAND_PROJECTION","statement":"After observed 2022 sales, off-grid customer sales grow at the PDP national reference-sales growth rate.","central_value":"PDP annual growth ratios","unit":"fraction/year","evidence_source_ids":"SRC_PHL_V21_POWER_BUILD","lower_bound":"","upper_bound":"","rationale":"Maintains a full-horizon service without inventing a separate unsourced island forecast.","notes":"A disclosed aggregation; national final demand is conserved."},
        {"assumption_id":"ASM_PHL_V21_2021_SALES_ESTIMATE","statement":"2021 off-grid sales use the 2020 sales-to-consumption ratio applied to reported 2021 consumption.","central_value":"1352.8615800135044","unit":"GWh","evidence_source_ids":"SRC_PHL_DOE_2020_POWER_SITUATION","lower_bound":"","upper_bound":"","rationale":"The retained 2021 report provides consumption but not the complete sales split.","notes":"Estimated and disclosed."},
        {"assumption_id":"ASM_PHL_V21_SCALED_STOCK_SPLIT","statement":"Inherited residual-retirement profiles are split by the official end-2020 off-grid/national stock fraction.","central_value":"technology-specific","unit":"fraction","evidence_source_ids":"SRC_PHL_DOE_2020_POWER_SITUATION","lower_bound":"","upper_bound":"","rationale":"Preserves every annual national RC total without fabricating plant vintages.","notes":"A plant register remains a gap."},
        {"assumption_id":"ASM_PHL_V21_BUILD_ENVELOPES","statement":"Optional off-grid build ceilings are 0.10 GW/year oil and 0.02 GW/year renewable after a zero-build 2020 initial-condition year.","central_value":"0.10;0.02","unit":"GW/year","evidence_source_ids":"SRC_PHL_DOE_2022_POWER_SITUATION;SRC_PHL_DOE_OFFGRID_PLANTS_2021","lower_bound":"","upper_bound":"","rationale":"Rounded headroom above demonstrated delivery prevents implausible instantaneous island deployment without requiring a build.","notes":"Renewable ceiling binds from 2021 and is material."},
        {"assumption_id":"ASM_PHL_V21_RETAINED_HYDRO_PROFILE","statement":"The retained wet/dry CLEWs design factors are a physical seasonal proxy pending plant-level inflow and reservoir data.","central_value":"wet 0.3834;dry 0.1447","unit":"capacity factor","evidence_source_ids":"SRC_PHL_V21_POWER_BUILD","lower_bound":"","upper_bound":"","rationale":"Restores a documented pre-existing physical profile rather than fitting AF to observed PJ.","notes":"Annual mean is preserved at full precision."},
        {"assumption_id":"ASM_PHL_V21_RESIDUE_AVAILABILITY","statement":"Phil-LiDAR availability factors are applied to crop-derived residues before conversion to the biomass activity ceiling.","central_value":"rice .81;sugar .61;coconut .55","unit":"fraction","evidence_source_ids":"SRC_PHL_DOE_PHILLIDAR2_BIOMASS","lower_bound":"0","upper_bound":"1","rationale":"Represents collection availability independently of observed generation.","notes":"National crop pool; no plant feedstock catchments."},
        {"assumption_id":"ASM_PHL_V21_RESIDUE_COLLECTION_COST","statement":"Residue collection and handling cost is 15.8 MUSD/PJ electricity, anchored to ERC's published biomass fuel component.","central_value":"15.8","unit":"MUSD/PJ electricity","evidence_source_ids":"SRC_PHL_ERC_BIOMASS_FIT","lower_bound":"","upper_bound":"","rationale":"Explicit economic driver, not back-calculated from biomass output.","notes":"Judgmental; FIT credit is separately source-derived."},
        {"assumption_id":"ASM_PHL_V21_BOUNDARY_ACCOUNTING","statement":"DOE 2020 national generation includes off-grid output; 2021-2024 national summary rows are grid-only and exclude modeled off-grid activity in comparison.","central_value":"year-specific boundary","unit":"classification","evidence_source_ids":"SRC_PHL_DOE_POWER_SUMMARY_2024;SRC_PHL_DOE_2022_OFFGRID_GENERATION","lower_bound":"","upper_bound":"","rationale":"Prevents double counting across the documented boundary break.","notes":"Off-grid 2020 and 2022 are also validated separately."},
    ]
    append("ASSUMPTIONS.csv", assumptions, "assumption_id")

    maps = [
        {"map_id":"MAP_PHL_V21_OFFGRID_COMMODITY","model_file":"genData.json;RYC.json;RYCTs.json","parameter":"commodity;SAD;SDP","entity":"COM_v21off / PHL_POW_ELE_OFFGRID_FINAL","mode":"","scenario":"SC_0; others inherit","years":"2020-2053","value_or_expression":"sales PJ series and sector-weighted demand profile","model_unit":"PJ","evidence_ids":"SRC_PHL_DOE_2020_POWER_SITUATION;CALC_PHL_V21_OFFGRID_DEMAND;CALC_PHL_V21_OFFGRID_DELIVERY;ASM_PHL_V21_2021_SALES_ESTIMATE","superseded_by":"","evidence_type":"derived","notes":"Identical PJ removed from existing electricity final demands; E=final demand/accounting, J=2021 sales estimate."},
        {"map_id":"MAP_PHL_V21_OFFGRID_OIL","model_file":"genData.json;RT.json;RYT.json;RYTCM.json;RYTEM.json;RYTM.json","parameter":"technology;OL;RC;AF;TAMaxCI;IAR;OAR;EAR;VC","entity":"TEC_v21oil / PHL_POW_CHP_OIL_OFFGRID","mode":"1-30","scenario":"SC_0; others inherit","years":"2020-2053","value_or_expression":"official stock/dependable capacity; inherited oil performance; TAMaxCI 0 in 2020 then 0.10","model_unit":"GW;fraction;PJ/PJ;MUSD/PJ","evidence_ids":"SRC_PHL_DOE_2020_POWER_SITUATION;SRC_PHL_DOE_2022_POWER_SITUATION;CALC_PHL_V21_STOCK_SPLIT;CALC_PHL_V21_BUILD_LIMITS","superseded_by":"","evidence_type":"derived","notes":"No activity minimum; E=stock/availability, J=construction ceiling."},
        {"map_id":"MAP_PHL_V21_OFFGRID_RE","model_file":"genData.json;RT.json;RYT.json;RYTCM.json;RYTTs.json","parameter":"technology;OL;RC;AF;TAMaxCI;OAR;CF","entity":"TEC_v21ore / PHL_POW_RE_OFFGRID","mode":"1-30","scenario":"SC_0; others inherit","years":"2020-2053","value_or_expression":"aggregate official hydro/solar/wind stock; TAMaxCI 0 in 2020 then 0.02","model_unit":"GW;fraction;PJ/PJ","evidence_ids":"SRC_PHL_DOE_2020_POWER_SITUATION;SRC_PHL_DOE_OFFGRID_PLANTS_2021;CALC_PHL_V21_STOCK_SPLIT;CALC_PHL_V21_BUILD_LIMITS","superseded_by":"","evidence_type":"derived","notes":"Ceiling binds 2021 onward; E=stock/profile, J=aggregation/ceiling."},
        {"map_id":"MAP_PHL_V21_BIOMASS_FIT","model_file":"genData.json;RT.json;RYT.json;RYTCM.json;RYTM.json","parameter":"technology;RC;TAMaxCI;TAU;IAR;OAR;VC","entity":"TEC_v21bio / PHL_POW_CHP_BIOM_FIT_OLD","mode":"1-30","scenario":"SC_0; others inherit","years":"2020-2053","value_or_expression":"0.25 GW closed stock; crop-residue TAU; FIT-adjusted VC","model_unit":"GW;PJ;MUSD/PJ","evidence_ids":"SRC_PHL_ERC_BIOMASS_FIT;SRC_PHL_DOE_PHILLIDAR2_BIOMASS;CALC_PHL_V21_BIOMASS_RESIDUE;CALC_PHL_V21_BIOMASS_FIT_COST","superseded_by":"","evidence_type":"derived","notes":"Resource ceiling slack in 2020; E=stock/resource/contract, J=collection cost."},
        {"map_id":"MAP_PHL_V21_HYDRO_PROFILE","model_file":"RYT.json;RYTTs.json","parameter":"AF;CF","entity":"TEC_p3vu5 / PHL_POW_PP_HY_LA","mode":"all timeslices","scenario":"SC_0; others inherit","years":"2020-2053","value_or_expression":"grid dependable/nameplate AF; rescaled wet/dry CF preserving 0.26438418 mean","model_unit":"fraction","evidence_ids":"SRC_PHL_DOE_2020_POWER_SITUATION;CALC_PHL_V21_HYDRO_PROFILE;ASM_PHL_V21_RETAINED_HYDRO_PROFILE","superseded_by":"","evidence_type":"derived","notes":"Supersedes restrictive v20 profile; E=availability, J=retained profile proxy; no observed hydro PJ used."},
        {"map_id":"MAP_PHL_V21_GENERATION_BENCHMARK","model_file":"data_sources/snapshots/power_allocation_v21_validation.json","parameter":"validation only","entity":"technology groups and total","mode":"","scenario":"BASE comparison","years":"2020-2024","value_or_expression":"WAPE, share and total errors","model_unit":"PJ;percent","evidence_ids":"SRC_PHL_V21_POWER_VALIDATION;CALC_PHL_V21_GENERATION_VALIDATION","superseded_by":"","evidence_type":"derived","notes":"H=benchmark only; not present in solver input."},
        {"map_id":"MAP_PHL_V21_VALIDATION_CHAIN","model_file":"data_sources/snapshots/power_allocation_v21_optimizer_ledger.json","parameter":"audit artifacts","entity":"r1-r4 and live promotion","mode":"","scenario":"BASE","years":"2020-2053","value_or_expression":"source/static/matrix/solve/promotion records","model_unit":"audit identity","evidence_ids":"SRC_PHL_V21_POWER_BUILD;SRC_PHL_V21_POWER_VALIDATION","superseded_by":"","evidence_type":"direct","notes":"A=validation artifact; four optimizer runs, zero sensitivities, and r2 deterministic failure retained."},
    ]
    append("MODEL_MAP.csv", maps, "map_id")

    gaps = [
        {"item":"V21 off-grid renewable technology aggregation","why_absent":"Hydro, solar and wind share one compact technology to protect runtime.","upgrade_source":"Plant-specific off-grid capacity, profiles, costs, batteries and hybrid dispatch.","priority":"medium","notes":"Activity is allocated by capacity-weighted potential only for validation."},
        {"item":"V21 off-grid coal generation route","why_absent":"The compact formulation includes oil and aggregate RE only; DOE reports 89.492 GWh off-grid coal in 2022.","upgrade_source":"Plant register and continuing coal supply/service evidence for isolated systems.","priority":"low","notes":"2022 modeled oil/RE shares sum to 100%."},
        {"item":"V21 hydro inflow, reservoir and outage representation","why_absent":"Retained seasonal design factors are used because a source-complete hydrological dataset was not recovered.","upgrade_source":"Plant inflows, reservoir storage/releases, run-of-river hydrology and outage records.","priority":"high","notes":"29.16 PJ is endogenous under the restored proxy, not a fitted target."},
        {"item":"V21 biomass plant feedstock catchments and cogeneration obligations","why_absent":"National crop residues and a 250 MW FIT tranche are sufficient for compact calibration but do not identify plant steam hosts or transport radii.","upgrade_source":"Plant register, fuel contracts, catchment GIS and host-industry steam demand.","priority":"medium","notes":"National residue ceiling is slack in 2020."},
        {"item":"V21 off-grid sales after 2022","why_absent":"No complete official full-horizon island sales forecast was retained.","upgrade_source":"Missionary Electrification Development Plan service-area demand forecasts.","priority":"medium","notes":"V21 uses national PDP growth ratios and discloses the assumption."},
    ]
    append("GAPS.csv", gaps, "item")

    changes = [{"change_id":"CHG_PHL_V21_POWER_ALLOCATION_20260820","date":"2026-08-20","class":"B","description":"Added compact off-grid oil/renewable service, a physical FIT biomass tranche and restored seasonal hydro profile to improve endogenous historical power allocation without generation or investment forcing.","model_objects":"genData.json;RT.json;RYC.json;RYCTs.json;RYT.json;RYTCM.json;RYTEM.json;RYTM.json;RYTTs.json","evidence_path":"documentation/MODEL_FIXES_POWER_ALLOCATION_V21_2026-08-20.md;data_sources/snapshots/power_allocation_v21_validation.json","map_rows_affected":";".join(row["map_id"] for row in maps),"resolve_status":"resolved","author":"Codex","commit":"","notes":"Four optimizer runs: r1 timeout, r2 timeout and deterministic infeasibility, r3 optimal rejected diagnostic, r4 optimal accepted. Zero sensitivity runs. Candidate/live source and data.txt byte identity passed."}]
    append("CHANGES.csv", changes, "change_id")
    reconcile_v21_rows()


if __name__ == "__main__":
    main()
