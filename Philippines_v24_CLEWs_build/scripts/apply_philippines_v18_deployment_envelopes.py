#!/usr/bin/env python3
"""Apply the non-forcing Philippines v18 generation deployment envelopes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path


BASE = "SC_0"
FIRST_YEAR = 2026
LAST_YEAR = 2053
YEARS = tuple(range(2020, LAST_YEAR + 1))
ACTIVE_YEARS = tuple(range(FIRST_YEAR, LAST_YEAR + 1))
EXPECTED_RYT_SHA256 = "51b281345d28aa8b40cf9e963c3d07c77cff98b9baa8fb4a8b7aef8351caf97d"
UNBOUNDED = {Decimal("9999"), Decimal("999999")}

EXPANSION_BANDS = {
    "PHL_POW_PP_WON": ((2026, 2029, "1.5"), (2030, 2039, "3.0"), (2040, 2053, "5.0")),
    "PHL_POW_PP_SPV": ((2026, 2029, "4.0"), (2030, 2039, "7.0"), (2040, 2053, "10.0")),
    "PHL_POW_PP_COAL": ((2026, 2029, "2.0"), (2030, 2039, "2.5"), (2040, 2053, "3.0")),
    "PHL_POW_PP_COAL_CCS": ((2026, 2029, "2.0"), (2030, 2039, "2.5"), (2040, 2053, "3.0")),
    "PHL_POW_PP_NGCC": ((2026, 2029, "2.0"), (2030, 2039, "2.5"), (2040, 2053, "3.0")),
    "PHL_POW_PP_NGCC_CCS": ((2026, 2029, "2.0"), (2030, 2039, "2.5"), (2040, 2053, "3.0")),
    "PHL_POW_GEO_OLD": ((2026, 2029, "0.15"), (2030, 2039, "0.25"), (2040, 2053, "0.35")),
    "PHL_POW_PP_HY_LA": ((2026, 2029, "1.0"), (2030, 2039, "1.5"), (2040, 2053, "2.0")),
    "PHL_POW_PP_BIOM_CCS": ((2026, 2029, "0.20"), (2030, 2039, "0.30"), (2040, 2053, "0.40")),
    "PHL_POW_PP_H2": ((2026, 2029, "0"), (2030, 2039, "1.0"), (2040, 2053, "2.0")),
    "PHL_POW_PP_WOF": ((2026, 2027, "0"), (2028, 2030, "1.0"), (2031, 2039, "2.0"), (2040, 2053, "4.0")),
    "PHL_POW_PP_NUSMR": ((2026, 2034, "0"), (2035, 2039, "0.30"), (2040, 2053, "0.60")),
    "PHL_POW_PP_NU": ((2026, 2034, "0"), (2035, 2053, "1.20")),
}

INHERITED_ONLY = (
    "PHL_POW_CHP_COAL_OLD",
    "PHL_POW_CHP_NG_OLD",
    "PHL_POW_CHP_OIL_OLD",
    "PHL_POW_CHP_BIOM_OLD",
)

SOURCE_ROWS = (
    {
        "source_id": "SRC_PHL_DOE_POWER_STATISTICS_2024", "provider": "Philippines Department of Energy",
        "product": "2024 Power Statistics Summary", "edition": "updated 15 June 2025",
        "reference_period": "2003-2024", "geography": "Philippines",
        "variable": "Installed generation capacity by plant type", "source_unit": "MW",
        "exact_locator": "Installed Capacity by Plant Type in MW table, 2003-2024",
        "url": "https://legacy.doe.gov.ph/sites/default/files/pdf/energy_statistics/02_Summary.pdf",
        "access_date": "2026-08-13", "license": "Philippine government publication; provider terms",
        "sha256": "", "local_file": "", "notes": "Primary observed capacity series; annual maxima are calculated, not copied as forecasts.",
    },
    {
        "source_id": "SRC_PHL_PCO_MTERRA_2026", "provider": "Philippine Presidential Communications Office",
        "product": "President Marcos inaugurates world's largest solar farm", "edition": "2026 release",
        "reference_period": "2026 and project completion", "geography": "Philippines",
        "variable": "MTerra solar capacity energized and planned", "source_unit": "MWp",
        "exact_locator": "Phase I and complete two-phase project capacities",
        "url": "https://pco.gov.ph/news_releases/president-marcos-inaugurates-worlds-largest-solar-farm-pushes-expansion-of-clean-energy/",
        "access_date": "2026-08-13", "license": "Philippine government publication; provider terms",
        "sha256": "", "local_file": "", "notes": "Observed/current project scale supports a higher solar construction envelope than the historical net-addition maximum.",
    },
    {
        "source_id": "SRC_PHL_BOI_SAN_JOSE_WIND_2026", "provider": "Philippine Board of Investments",
        "product": "BOI Mobilizes Government to Fast-Track San Jose Wind Power Project", "edition": "2026 release",
        "reference_period": "2026 project development", "geography": "Nueva Ecija, Philippines",
        "variable": "Proposed onshore-wind project capacity", "source_unit": "MW",
        "exact_locator": "San Jose Wind Power Project description (300 MW)",
        "url": "https://boi.gov.ph/boi-mobilizes-government-to-fast-track-san-jose-wind-power-project/",
        "access_date": "2026-08-13", "license": "Philippine government publication; provider terms",
        "sha256": "", "local_file": "", "notes": "Project size is capability evidence, not a committed-project allowance in the model.",
    },
    {
        "source_id": "SRC_VNM_EVN_WIND_2021", "provider": "Vietnam Electricity",
        "product": "The power system and the electricity market have been operated safely, reliably and transparently",
        "edition": "10 January 2022", "reference_period": "2021", "geography": "Vietnam",
        "variable": "Wind capacity commissioned and total system installed capacity", "source_unit": "MW",
        "exact_locator": "Paragraph reporting about 3,600 MW wind commissioned and 76,620 MW total installed capacity",
        "url": "https://en.evn.com.vn/d6/news/The-power-system-and-the-electricity-market-have-been-operated-safely-reliably-and-transparently-66-163-2671.aspx",
        "access_date": "2026-08-13", "license": "Provider copyright; citation permitted",
        "sha256": "", "local_file": "", "notes": "International upper-bound reasonableness check only.",
    },
    {
        "source_id": "SRC_PHL_EDC_GEOTHERMAL_DRILLING_2024", "provider": "Energy Development Corporation",
        "product": "2024 Integrated Report and geothermal drilling programme", "edition": "2024",
        "reference_period": "2024", "geography": "Philippines",
        "variable": "Make-up/replacement wells and annual wells drilled", "source_unit": "wells/year",
        "exact_locator": "Drilling programme discussion and 2024 record of 24 wells",
        "url": "https://energy.com.ph/lopez-led-edc-investing-p25-billion-to-drill-new-geothermal-wells/",
        "access_date": "2026-08-13", "license": "Provider copyright; citation permitted",
        "sha256": "", "local_file": "", "notes": "Supports persistent existing-field maintenance and replacement, not a generation target.",
    },
    {
        "source_id": "SRC_ADB_PHL_GEOTHERMAL_DERISKING_2024", "provider": "Asian Development Bank",
        "product": "Roadmap to Derisking Geothermal in the Philippines", "edition": "May 2024",
        "reference_period": "2024", "geography": "Philippines",
        "variable": "Exploration, drilling-risk and financing barriers", "source_unit": "qualitative study",
        "exact_locator": "Project 55140-001 consultant reports on geothermal potential, drilling and risk sharing",
        "url": "https://www.adb.org/projects/55140-001/main", "access_date": "2026-08-13",
        "license": "ADB terms of use", "sha256": "", "local_file": "",
        "notes": "Supports a conservative greenfield geothermal entry envelope.",
    },
    {
        "source_id": "SRC_HEGGARTY_MAX_INVESTMENT_RATE_2024", "provider": "Heggarty, Bourmaud, Girard and Kariniotakis",
        "product": "Assessing the relative impacts of maximum investment rate and temporal detail in capacity expansion models applied to power systems",
        "edition": "Energy 290 (2024) 130231", "reference_period": "capacity-expansion methodology",
        "geography": "Europe; methodological support", "variable": "Maximum technology investment rates",
        "source_unit": "GW/year and modeled limits", "exact_locator": "doi:10.1016/j.energy.2024.130231",
        "url": "https://doi.org/10.1016/j.energy.2024.130231", "access_date": "2026-08-13",
        "license": "Publisher terms", "sha256": "", "local_file": "",
        "notes": "Methodological support that financing, permitting, manufacturing, construction and grid connection can be represented by maximum investment rates.",
    },
)

HISTORICAL_MAXIMA = {
    "TOTAL_GENERATION": "2.66", "COAL": "1.57", "NATURAL_GAS": "0.57", "SOLAR": "1.06",
    "ONSHORE_WIND": "0.25", "HYDRO": "0.35", "GEOTHERMAL": "0.065", "BIOMASS": "0.12",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def dec(value) -> Decimal:
    return Decimal(str(value))


def clean(value: Decimal):
    if value == value.to_integral():
        return int(value)
    return float(value)


def expansion_for(technology: str, year: int) -> tuple[Decimal, str]:
    for start, end, value in EXPANSION_BANDS[technology]:
        if start <= year <= end:
            assumption_id = f"ASM_PHL_V18_DEPLOY_{technology.removeprefix('PHL_POW_')}_{start}_{end}"
            return Decimal(value), assumption_id
    raise AssertionError((technology, year))


def append_rows(path: Path, rows: list[dict]) -> None:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        existing = list(reader)
    if fieldnames is None:
        raise AssertionError(f"missing header: {path}")
    key = fieldnames[0]
    duplicate = sorted({row[key] for row in existing} & {row[key] for row in rows})
    if duplicate:
        raise AssertionError(f"duplicate ledger IDs in {path.name}: {duplicate[:5]}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(existing)
        writer.writerows(rows)


def source_ids_for(technology: str) -> str:
    common = ["SRC_PHL_DOE_POWER_STATISTICS_2024", "SRC_HEGGARTY_MAX_INVESTMENT_RATE_2024"]
    if technology == "PHL_POW_PP_WON":
        common += ["SRC_PHL_BOI_SAN_JOSE_WIND_2026", "SRC_VNM_EVN_WIND_2021"]
    elif technology == "PHL_POW_PP_SPV":
        common += ["SRC_PHL_PCO_MTERRA_2026"]
    elif technology == "PHL_POW_GEO_OLD":
        common += ["SRC_PHL_EDC_GEOTHERMAL_DRILLING_2024", "SRC_ADB_PHL_GEOTHERMAL_DERISKING_2024"]
    elif technology == "PHL_POW_PP_WOF":
        common += ["SRC_ADB_PHL_GEOTHERMAL_DERISKING_2024"]
    return ";".join(common)


def build_assumptions() -> list[dict]:
    rows = []
    for technology, bands in EXPANSION_BANDS.items():
        for start, end, value in bands:
            rows.append({
                "assumption_id": f"ASM_PHL_V18_DEPLOY_{technology.removeprefix('PHL_POW_')}_{start}_{end}",
                "statement": f"{technology} may commission at most {value} GW/year of expansion headroom during {start}-{end}, before replacement allowances.",
                "central_value": value, "unit": "GW/year", "evidence_source_ids": source_ids_for(technology),
                "lower_bound": "", "upper_bound": "",
                "rationale": "Judgmental, policy-neutral construction/financing/permitting/grid envelope informed by Philippine deployment evidence; it is deliberately generous and is not a forecast or capacity target.",
                "notes": "classification=judgmental; BASE physical envelope inherited by policy scenarios unless an existing scenario override is more restrictive",
            })
    rows.append({
        "assumption_id": "ASM_PHL_V18_DEPLOY_OLD_STOCK_ONLY",
        "statement": "The inherited coal, gas, oil and biomass CHP _OLD technologies receive zero new-capacity entry from 2026; their unchanged residual-capacity paths remain available until retirement.",
        "central_value": "0", "unit": "GW/year", "evidence_source_ids": "SRC_PHL_DOE_POWER_STATISTICS_2024;SRC_MUIO_FORMULATION",
        "lower_bound": "", "upper_bound": "", "rationale": "These are inherited-stock representations; geothermal is the documented exception because the model has no separate geothermal new-build or repowering technology.",
        "notes": "classification=judgmental technology-role rule; no residual capacity value changes",
    })
    rows.append({
        "assumption_id": "ASM_PHL_V18_DEPLOY_RECYCLE_START_2026",
        "statement": "Only allowances established from 2026 onward are recycled at operational life; unbounded pre-2026 defaults are not interpreted as physical permitted capacity.",
        "central_value": "2026", "unit": "first recycled allowance vintage year", "evidence_source_ids": "SRC_MUIO_FORMULATION",
        "lower_bound": "", "upper_bound": "", "rationale": "The deployment envelope starts in 2026 while every source cell through 2025 is preserved; recycling 9999/999999 defaults would defeat the physical bound.",
        "notes": "classification=judgmental implementation boundary following the v14 allowance-recycling method",
    })
    return rows


def apply(case: Path, package: Path) -> dict:
    ryt_path = case / "RYT.json"
    if sha256(ryt_path) != EXPECTED_RYT_SHA256:
        raise AssertionError(f"unexpected v18 RYT source fingerprint: {sha256(ryt_path)}")
    before_hashes = {path.name: sha256(path) for path in sorted(case.glob("*.json"))}
    gen = read_json(case / "genData.json")
    if gen["osy-casename"] != "Philippines_v18" or tuple(gen["osy-years"]) != tuple(str(y) for y in YEARS):
        raise AssertionError("unexpected case identity or horizon")
    tech_id = {row["Tech"]: row["TechId"] for row in gen["osy-tech"]}
    missing = sorted((set(EXPANSION_BANDS) | set(INHERITED_ONLY)) - set(tech_id))
    if missing:
        raise AssertionError(f"missing technologies: {missing}")

    ryt = read_json(ryt_path)
    rt = read_json(case / "RT.json")
    tamax = {row["TechId"]: row for row in ryt["TAMaxCI"][BASE]}
    residual = {row["TechId"]: row for row in ryt["RC"][BASE]}
    lives = rt["OL"][BASE][0]
    preserved = {name: {str(y): tamax[tech_id[name]][str(y)] for y in range(2020, FIRST_YEAR)} for name in set(EXPANSION_BANDS) | set(INHERITED_ONLY)}
    calculations = []
    calc_rows = []
    map_rows = []

    for technology in EXPANSION_BANDS:
        tid = tech_id[technology]
        life = int(lives[tid])
        permitted: dict[int, Decimal] = {}
        for year in ACTIVE_YEARS:
            source_value = dec(tamax[tid][str(year)])
            committed = Decimal("0") if source_value in UNBOUNDED else max(Decimal("0"), source_value)
            expansion, assumption_id = expansion_for(technology, year)
            previous_rc = dec(residual[tid][str(year - 1)])
            current_rc = dec(residual[tid][str(year)])
            residual_retirement = max(Decimal("0"), previous_rc - current_rc)
            recycle_year = year - life
            recycled = permitted.get(recycle_year, Decimal("0")) if recycle_year >= FIRST_YEAR else Decimal("0")
            value = max(committed, expansion) + residual_retirement + recycled
            permitted[year] = value
            before = tamax[tid][str(year)]
            tamax[tid][str(year)] = clean(value)
            calculation_id = f"CALC_PHL_V18_TAMAXCI_{technology.removeprefix('PHL_POW_')}_{year}"
            input_calc = f"CALC_PHL_V18_TAMAXCI_{technology.removeprefix('PHL_POW_')}_{recycle_year}" if recycled and recycle_year >= FIRST_YEAR else ""
            calc_rows.append({
                "calculation_id": calculation_id,
                "formula": "max(existing committed allowance, expansion envelope) + positive residual-capacity retirement + TAMaxCI[y-OperationalLife] for envelope vintages from 2026",
                "source_ids": f"SRC_MUIO_FORMULATION;{source_ids_for(technology)}",
                "assumption_ids": f"{assumption_id};ASM_PHL_V18_DEPLOY_RECYCLE_START_2026",
                "input_calculation_ids": input_calc,
                "input_values": f"committed={committed};expansion={expansion};residual_retirement={residual_retirement};recycled={recycled};life={life}",
                "input_units": "GW/year;GW/year;GW/year;GW/year;years",
                "output_value": str(value), "output_unit": "GW/year",
                "script_path": "scripts/apply_philippines_v18_deployment_envelopes.py", "script_version": "v1",
                "notes": "classification=calculated; upper bound only; capacity and dispatch remain endogenous",
            })
            map_rows.append({
                "map_id": f"MAP_PHL_V18_TAMAXCI_{technology.removeprefix('PHL_POW_')}_{year}",
                "model_file": "case/Philippines_v18/RYT.json", "parameter": "TotalAnnualMaxCapacityInvestment",
                "entity": f"{tid} / {technology}", "mode": "", "scenario": "SC_0; policy rows inherit unless an existing override is more restrictive",
                "years": str(year), "value_or_expression": str(value), "model_unit": "GW/year",
                "evidence_ids": f"{calculation_id};{assumption_id};SRC_MUIO_FORMULATION", "superseded_by": "",
                "evidence_type": "derived", "notes": "NCC1 new-capacity ceiling; no minimum, activity bound, technology share or aggregate construction cap.",
            })
            calculations.append({
                "technology": technology, "technology_id": tid, "year": year, "before": before,
                "existing_committed_allowance_gw": clean(committed), "expansion_envelope_gw": clean(expansion),
                "residual_retirement_allowance_gw": clean(residual_retirement), "recycled_allowance_gw": clean(recycled),
                "operational_life_years": life, "after_tamaxci_gw": clean(value), "classification": "calculated",
                "assumption_id": assumption_id,
            })

    for technology in INHERITED_ONLY:
        tid = tech_id[technology]
        for year in ACTIVE_YEARS:
            before = tamax[tid][str(year)]
            tamax[tid][str(year)] = 0
            calculation_id = f"CALC_PHL_V18_TAMAXCI_{technology.removeprefix('PHL_POW_')}_{year}"
            calc_rows.append({
                "calculation_id": calculation_id, "formula": "inherited-stock-only entry allowance = 0; unchanged ResidualCapacity remains available",
                "source_ids": "SRC_MUIO_FORMULATION;SRC_PHL_DOE_POWER_STATISTICS_2024",
                "assumption_ids": "ASM_PHL_V18_DEPLOY_OLD_STOCK_ONLY", "input_calculation_ids": "",
                "input_values": "expansion=0;replacement=0", "input_units": "GW/year;GW/year",
                "output_value": "0", "output_unit": "GW/year",
                "script_path": "scripts/apply_philippines_v18_deployment_envelopes.py", "script_version": "v1",
                "notes": "classification=calculated from judgmental technology-role rule; residual trajectory unchanged",
            })
            map_rows.append({
                "map_id": f"MAP_PHL_V18_TAMAXCI_{technology.removeprefix('PHL_POW_')}_{year}",
                "model_file": "case/Philippines_v18/RYT.json", "parameter": "TotalAnnualMaxCapacityInvestment",
                "entity": f"{tid} / {technology}", "mode": "", "scenario": "SC_0; policy rows inherit unless an existing override is more restrictive",
                "years": str(year), "value_or_expression": "0", "model_unit": "GW/year",
                "evidence_ids": f"{calculation_id};ASM_PHL_V18_DEPLOY_OLD_STOCK_ONLY;SRC_MUIO_FORMULATION",
                "superseded_by": "", "evidence_type": "derived", "notes": "Inherited physical stock only; residual-capacity path is unchanged.",
            })
            calculations.append({
                "technology": technology, "technology_id": tid, "year": year, "before": before,
                "existing_committed_allowance_gw": 0, "expansion_envelope_gw": 0,
                "residual_retirement_allowance_gw": 0, "recycled_allowance_gw": 0,
                "operational_life_years": int(lives[tid]), "after_tamaxci_gw": 0,
                "classification": "calculated", "assumption_id": "ASM_PHL_V18_DEPLOY_OLD_STOCK_ONLY",
            })

    for technology, annual in preserved.items():
        for year, value in annual.items():
            if tamax[tech_id[technology]][year] != value:
                raise AssertionError(f"historical cell changed: {technology} {year}")
    write_json(ryt_path, ryt)
    after_hashes = {path.name: sha256(path) for path in sorted(case.glob("*.json"))}
    changed = sorted(name for name in before_hashes if before_hashes[name] != after_hashes[name])
    if changed != ["RYT.json"]:
        raise AssertionError(f"source diff outside RYT.json: {changed}")

    data_sources = package / "data_sources"
    append_rows(data_sources / "SOURCES.csv", list(SOURCE_ROWS))
    assumption_rows = build_assumptions()
    append_rows(data_sources / "ASSUMPTIONS.csv", assumption_rows)
    historical_calcs = []
    for technology, value in HISTORICAL_MAXIMA.items():
        historical_calcs.append({
            "calculation_id": f"CALC_PHL_DEPLOY_HIST_MAX_{technology}",
            "formula": "max(InstalledCapacity[y] - InstalledCapacity[y-1]) over 2004-2024; net annual additions",
            "source_ids": "SRC_PHL_DOE_POWER_STATISTICS_2024", "assumption_ids": "", "input_calculation_ids": "",
            "input_values": "DOE 2003-2024 installed-capacity series", "input_units": "MW converted to GW",
            "output_value": value, "output_unit": "GW/year", "script_path": "", "script_version": "",
            "notes": "classification=calculated from observed annual capacity; may understate gross commissioning when retirements occur",
        })
    historical_calcs.append({
        "calculation_id": "CALC_PHL_DEPLOY_VNM_WIND_SCALE",
        "formula": "3.6 GW * 29.706 GW Philippine 2024 system / 76.620 GW Vietnam 2021 system",
        "source_ids": "SRC_VNM_EVN_WIND_2021;SRC_PHL_DOE_POWER_STATISTICS_2024", "assumption_ids": "", "input_calculation_ids": "",
        "input_values": "3.6;29.706;76.620", "input_units": "GW;GW;GW", "output_value": "1.395342", "output_unit": "GW/year",
        "script_path": "", "script_version": "", "notes": "classification=calculated; international upper-bound reasonableness check, not a forecast",
    })
    append_rows(data_sources / "CALCULATIONS.csv", historical_calcs + calc_rows)
    append_rows(data_sources / "MODEL_MAP.csv", map_rows)
    append_rows(data_sources / "GAPS.csv", [
        {
            "item": "Long-term Philippine technology deployment scaling after 2029",
            "why_absent": "The 2030-2053 expansion envelopes are defensible policy-neutral upper bounds rather than forecasts of supply-chain, permitting, finance or grid capability.",
            "upgrade_source": "Annual Philippine project pipeline, interconnection queue, permitting duration, domestic construction capacity, finance closures and transmission commissioning plan by technology.",
            "priority": "high", "notes": "Sensitivity testing is required for policy conclusions that bind on these later-period envelopes.",
        },
        {
            "item": "Distinct geothermal greenfield and existing-field repowering costs",
            "why_absent": "PHL_POW_GEO_OLD is the only geothermal technology, so expansion and replacement allowances share one inherited cost, performance and lifetime representation.",
            "upgrade_source": "Philippine field-specific greenfield exploration/EPC and existing-field make-up drilling, refurbishment, lifetime and performance evidence.",
            "priority": "high", "notes": "No geothermal technology or commodity is added in this implementation.",
        },
    ])
    map_ids = ";".join(row["map_id"] for row in map_rows)
    append_rows(data_sources / "CHANGES.csv", [{
        "change_id": "CHG_PHL_V18_DEPLOYMENT_ENVELOPES_20260813", "date": "2026-08-13", "class": "C",
        "description": "Installed policy-neutral, technology-specific annual generation entry envelopes from 2026 with residual-retirement and operational-life allowance recycling; preserved every 2020-2025 source cell and left capacity choice and dispatch endogenous.",
        "model_objects": "case/Philippines_v18/RYT.json TAMaxCI.SC_0 only",
        "evidence_path": "documentation/MODEL_FIXES_DEPLOYMENT_ENVELOPES_2026-08-13.md;data_sources/snapshots/deployment_envelopes_v18_2026-08-13.json",
        "map_rows_affected": map_ids, "resolve_status": "resolve_required", "author": "Codex", "commit": "",
        "notes": "No capacity minimum generation minimum technology share activity bound aggregate construction cap or PEP capacity total was added.",
    }])

    snapshot = {
        "schema": "philippines-v18-deployment-envelope-calculation-v1",
        "case": "Philippines_v18", "parameter": "TotalAnnualMaxCapacityInvestment", "scenario": BASE,
        "equation": "NCC1: NewCapacity[t,y] <= TotalAnnualMaxCapacityInvestment[t,y]",
        "formula": "max(existing committed allowance, expansion envelope) + positive residual retirement + recycled envelope allowance at operational life",
        "application_start_year": FIRST_YEAR, "preserved_years": [2020, 2021, 2022, 2023, 2024, 2025],
        "observations_classification": {
            "DOE historical additions": "benchmark/evidence for continuing construction constraint",
            "current project sizes": "capability evidence",
            "international record": "upper-bound reasonableness check",
            "envelope values": "judgmental upper bounds, not forecasts or targets",
            "residual capacity": "initial physical stock retirement schedule",
        },
        "technology_roles": {
            "expansion_capable_physical_generation": sorted(name for name in EXPANSION_BANDS if name != "PHL_POW_GEO_OLD"),
            "combined_existing_field_repowering_and_greenfield": ["PHL_POW_GEO_OLD"],
            "inherited_physical_stock_only": list(INHERITED_ONLY),
            "unaffected_pass_throughs_conversions_accounting_and_demands": "all other technologies",
        },
        "calculations": calculations,
    }
    snapshot_path = data_sources / "snapshots" / "deployment_envelopes_v18_2026-08-13.json"
    write_json(snapshot_path, snapshot)
    manifest = {
        "schema": "philippines-v18-deployment-envelope-build-manifest-v1",
        "source_case_ryt_sha256": EXPECTED_RYT_SHA256, "target_case_ryt_sha256": after_hashes["RYT.json"],
        "source_json_sha256": before_hashes, "target_json_sha256": after_hashes, "changed_source_files": changed,
        "changed_parameter_families": ["RYT.TAMaxCI.SC_0"], "unchanged_source_file_count": len(before_hashes) - 1,
        "historical_2020_2025_unchanged": True, "scenario_override_rows_unchanged": True,
        "calculation_count": len(calculations), "model_map_rows_added": len(map_rows),
        "snapshot_sha256": sha256(snapshot_path),
    }
    write_json(data_sources / "snapshots" / "deployment_envelope_build_manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(apply(args.case.resolve(), args.package.resolve()), indent=2))


if __name__ == "__main__":
    main()
