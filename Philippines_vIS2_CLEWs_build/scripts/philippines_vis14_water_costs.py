#!/usr/bin/env python3
"""Build and validate Philippines vIS1.4 physical water-withdrawal costs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import subprocess
import sys
import time
import types
from datetime import date
from decimal import Decimal, getcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP" / "DataStorage"
SOURCE = STORAGE / ".Philippines_vIS13-water-cap-candidate-20260831"
TARGET = STORAGE / ".Philippines_vIS14-water-infrastructure-candidate-20260831"
BASELINE_RUN = SOURCE / "res" / "BASE_VIS13_WATER_CAP_CLOSURE"
RUN_NAME = "BASE_VIS14_WATER_INFRASTRUCTURE"
MODEL = ROOT / "WebAPP" / "SOLVERs" / "model.v.5.4.txt"
YEARS = tuple(str(year) for year in range(2020, 2054))
BASE = "SC_0"

getcontext().prec = 30

# All monetary inputs are normalized once to constant 2020 USD. Model water
# activity is km3/year, so 1 USD/m3 is exactly 1,000 MUSD/km3.
PHL_CPI_2009 = Decimal("96.3485477178423")
PHL_CPI_2015 = Decimal("115.429504132997")
PHL_CPI_2020 = Decimal("132.7240608691")
USA_CPI_2009 = Decimal("98.3864199710624")
USA_CPI_2020 = Decimal("118.690501577198")
PHP_PER_USD_2020 = Decimal("49.62")
PHP_PER_KWH_2020 = Decimal("8.13")
ACRE_FOOT_M3 = Decimal("1233.48183754752")
SECONDS_PER_YEAR = Decimal("31536000")

PUBLIC_MARGINAL_2009_PHP_M3 = Decimal("7.235")
PUBLIC_ALL_IN_2020_USD_M3 = (
    PUBLIC_MARGINAL_2009_PHP_M3 * PHL_CPI_2020 / PHL_CPI_2009 / PHP_PER_USD_2020
)
REFERENCE_ELECTRICITY_2020_USD_KWH = PHP_PER_KWH_2020 / PHP_PER_USD_2020
GWT_07_ELECTRICITY_USD_M3 = Decimal("0.7") / Decimal("3.6") * REFERENCE_ELECTRICITY_2020_USD_KWH
PUBLIC_GWT_DIRECT_2020_USD_M3 = PUBLIC_ALL_IN_2020_USD_M3 - GWT_07_ELECTRICITY_USD_M3

# NWRB/LLDA annual resource-user fees at >7,000 l/s. Fixed PHP5,000 permit
# components are deliberately excluded from VariableCost. One sustained l/s
# is 31,536 m3/year.
IRRIGATION_FEE_2015_PHP_PER_LPS_YEAR = Decimal("16.80")
POWER_FEE_2015_PHP_PER_LPS_YEAR = Decimal("8.40")
IRRIGATION_FEE_2020_USD_M3 = (
    IRRIGATION_FEE_2015_PHP_PER_LPS_YEAR
    * PHL_CPI_2020 / PHL_CPI_2015
    / (SECONDS_PER_YEAR / Decimal("1000"))
    / PHP_PER_USD_2020
)
POWER_FEE_2020_USD_M3 = (
    POWER_FEE_2015_PHP_PER_LPS_YEAR
    * PHL_CPI_2020 / PHL_CPI_2015
    / (SECONDS_PER_YEAR / Decimal("1000"))
    / PHP_PER_USD_2020
)


def musd_per_km3(usd_per_m3: Decimal) -> float:
    return float(usd_per_m3 * Decimal("1000"))


PUBLIC_SUR_VC = musd_per_km3(PUBLIC_ALL_IN_2020_USD_M3)
PUBLIC_GWT_VC = musd_per_km3(PUBLIC_GWT_DIRECT_2020_USD_M3)
POWER_VC = musd_per_km3(POWER_FEE_2020_USD_M3)
IRRIGATION_VC = musd_per_km3(IRRIGATION_FEE_2020_USD_M3)

# The repository's CCG/CLEWs Demo abstraction technologies provide the model-
# aligned physical asset benchmark. Values are MUSD per km3/year capacity and
# MUSD per km3/year capacity-year; 7/137 and 17/332 are approximately 5%.
SURFACE_CC = 137.0
GROUNDWATER_CC = 332.0
SURFACE_FC = 7.0
GROUNDWATER_FC = 17.0
PUMP_OPERATIONAL_LIFE = 20

TECHNOLOGY_COSTS = {
    "PHL_DEM_PUB_SUR_WAT": PUBLIC_SUR_VC,
    "PHL_DEM_PWR_SUR_WAT": POWER_VC,
    "DEMAGRSURPHL": IRRIGATION_VC,
    "PHL_DEM_PWR_SUR_WAT_LUZ": POWER_VC,
    "PHL_DEM_PWR_SUR_WAT_VIS": POWER_VC,
    "PHL_DEM_PWR_SUR_WAT_MIN": POWER_VC,
    "PHL_DEM_PUB_GWT_WAT": PUBLIC_GWT_VC,
    "PHL_DEM_PWR_GWT_WAT": POWER_VC,
    "DEMAGRGWTPHL": IRRIGATION_VC,
    "PHL_DEM_PWR_GWT_WAT_LUZ": POWER_VC,
    "PHL_DEM_PWR_GWT_WAT_VIS": POWER_VC,
    "PHL_DEM_PWR_GWT_WAT_MIN": POWER_VC,
}

PUBLIC = {"PHL_DEM_PUB_SUR_WAT", "PHL_DEM_PUB_GWT_WAT"}
IRRIGATION = {"DEMAGRSURPHL", "DEMAGRGWTPHL"}
POWER = set(TECHNOLOGY_COSTS) - PUBLIC - IRRIGATION
SURFACE = {name for name in TECHNOLOGY_COSTS if "SUR" in name}
GROUNDWATER = set(TECHNOLOGY_COSTS) - SURFACE

CAPITAL_COSTS = {name: SURFACE_CC if name in SURFACE else GROUNDWATER_CC for name in TECHNOLOGY_COSTS}
FIXED_COSTS = {name: SURFACE_FC if name in SURFACE else GROUNDWATER_FC for name in TECHNOLOGY_COSTS}

CAP_TECHS = {
    "WATER_SUR_AVAIL": tuple(name for name in TECHNOLOGY_COSTS if name in SURFACE),
    "WATER_GWT_POTENTIAL": tuple(name for name in TECHNOLOGY_COSTS if name in GROUNDWATER),
}

SOURCES = [
    {
        "source_id": "SRC_VIS14_WB_WSP_WATER_DISTRICTS",
        "provider": "World Bank Water and Sanitation Program / LWUA",
        "title": "Prospects and Pitfalls in Integrated Water Services in the Philippines",
        "reference_period": "2003-2005 data; August 2009 publication",
        "use": "Marginal public-water production cost from doubled-output cost response",
        "locator": "PDF pp. 3-4: PHP10 to PHP8.20/m3 and PHP9 to PHP8.30/m3; fixed-cost shares 80% and 70%",
        "url": "https://documents1.worldbank.org/curated/en/320351468298445609/pdf/715230BRI0Box30rated0WS0Philippines.pdf",
    },
    {
        "source_id": "SRC_VIS14_CLEWS_DEMO_ABSTRACTION_ASSETS",
        "provider": "Climate Compatible Growth / CLEWs repository benchmark",
        "title": "CLEWs Demo physical surface- and groundwater-abstraction technologies",
        "reference_period": "repository benchmark inspected 2026-08-31",
        "use": "Model-aligned CapitalCost, FixedCost, and OperationalLife for physical abstraction assets",
        "locator": "WebAPP/DataStorage/CLEWs Demo: DEMAGRSURWAT CC=137 FC=7 OL=20; DEMAGRGWTWAT CC=332 FC=17 OL=20",
        "url": "https://www.open.edu/openlearncreate/course/view.php?id=11715",
    },
    {
        "source_id": "SRC_VIS14_US_EPA_ASSET_LIFE",
        "provider": "United States Environmental Protection Agency",
        "title": "Asset Management: A Handbook for Small Water Systems",
        "reference_period": "2003",
        "use": "Independent useful-life cross-check for pumping equipment and exclusion of long-lived wells/intakes",
        "locator": "Table 3: pumping equipment 10 years, wells and springs 25 years, intake structures 35 years",
        "url": "https://www.epa.gov/sites/default/files/2015-04/documents/epa816k03002.pdf",
    },
    {
        "source_id": "SRC_VIS14_ADB_WDDSP",
        "provider": "Asian Development Bank / Local Water Utilities Administration",
        "title": "Water District Development Sector Project (Philippines)",
        "reference_period": "2016-2024 contracts",
        "use": "Philippine scope cross-check that source development and pumping facilities are physical capital packages distinct from distribution pipes",
        "locator": "Project 41665-013 contract packages separately identify source-development/pumping facilities and pipes/fittings",
        "url": "https://www.adb.org/projects/41665-013/main",
    },
    {
        "source_id": "SRC_VIS14_LLDA_NWRB_ANNUAL_WATER_CHARGE",
        "provider": "Laguna Lake Development Authority / National Water Resources Board",
        "title": "2025 Citizen's Charter - annual water charges",
        "reference_period": "NWRB fee schedule adopted 2015 and still published in 2025",
        "use": "Marginal raw-water resource-user charges for national/corporate irrigation and power generation",
        "locator": "At >7,000 l/s: national/corporate irrigation PHP16.80 and power generation PHP8.40 per l/s-year; base cost PHP5,000 excluded",
        "url": "https://www.llda.gov.ph/wp-content/uploads/dox/citizens_charter/2025%20Citizen%27s%20Charter%20%281%29.pdf",
    },
    {
        "source_id": "SRC_VIS14_FAO_IRRIGATION_CHARGING",
        "provider": "Food and Agriculture Organization of the United Nations",
        "title": "Water charging in irrigated agriculture, Water Reports 28",
        "reference_period": "2004 publication",
        "use": "Boundary check only: total irrigation service cost is USD0.02-0.04/m3 and must not be added again to raw-withdrawal routes",
        "locator": "Chapter 3, Cost of water: total irrigation service cost range and distinction between cost and price",
        "url": "https://www.fao.org/4/y5690e/y5690e04.htm",
    },
    {
        "source_id": "SRC_VIS14_NIA_2020_ANNUAL_REPORT",
        "provider": "Philippines National Irrigation Administration",
        "title": "Annual Report 2020",
        "reference_period": "2020",
        "use": "Philippine irrigation-system and O&M cross-check; not used as a volumetric coefficient because expenses are not separable by delivered volume",
        "locator": "Annual report financial and physical-performance tables",
        "url": "https://nia.gov.ph/wp-content/uploads/newsletter/2020-annualreport_0.pdf",
    },
    {
        "source_id": "SRC_VIS14_DOE_EPIRA_RATE",
        "provider": "Philippines Department of Energy",
        "title": "38th Status Report on EPIRA Implementation",
        "reference_period": "December 2020",
        "use": "Reference electricity price used only to remove electricity already represented by model IAR",
        "locator": "Electricity rates: national average system rate PHP8.13/kWh",
        "url": "https://legacy.doe.gov.ph/sites/default/files/pdf/electric_power/38th_epira_report_april-2021.pdf",
    },
    {
        "source_id": "SRC_VIS14_BSP_FX_2020",
        "provider": "Bangko Sentral ng Pilipinas",
        "title": "BSP Annual Report 2020",
        "reference_period": "2020",
        "use": "PHP49.62 per USD annual-average conversion",
        "locator": "Foreign Exchange Market section",
        "url": "https://www.bsp.gov.ph/Media_And_Research/Annual%20Report/annrep2020.pdf",
    },
    {
        "source_id": "SRC_VIS14_WB_CPI",
        "provider": "World Bank World Development Indicators",
        "title": "Consumer price index (2010=100), FP.CPI.TOTL",
        "reference_period": "2009, 2015, 2020",
        "use": "Normalize Philippine-peso and US-dollar source values to 2020 prices",
        "locator": "PHL and USA API observations",
        "url": "https://api.worldbank.org/v2/country/PHL/indicator/FP.CPI.TOTL?format=json",
    },
    {
        "source_id": "SRC_VIS14_MANILA_WATER_ENERGY_CHECK",
        "provider": "Manila Water Company",
        "title": "Integrated Report 2020 - Protecting the Environment",
        "reference_period": "2020",
        "use": "Scope check: water-supply energy intensity 1,150 GJ/MCM billed; flags that vIS1.4 does not recalibrate physical electricity IAR",
        "locator": "Energy Intensity table",
        "url": "https://reports.manilawater.com/2020/sustainability-at-manila-water/protecting-the-environment",
    },
]


dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(ROOT / "API"))

from Classes.Base import Config  # noqa: E402
from Classes.Case.DataFileClass import DataFile  # noqa: E402
from Classes.Case.OsemosysClass import Osemosys  # noqa: E402


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def technology_ids(gen: dict) -> dict[str, str]:
    return {row["Tech"]: row["TechId"] for row in gen["osy-tech"]}


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def append_schema_rows(path: Path, rows: list[dict]) -> None:
    """Append rows using the canonical ledger's existing column order."""
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        header = next(reader)
    for row in rows:
        missing = set(header) - set(row)
        extra = set(row) - set(header)
        if missing or extra:
            raise RuntimeError(f"schema mismatch for {path.name}: missing={sorted(missing)}, extra={sorted(extra)}")
    with path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=header)
        writer.writerows(rows)


def write_schema_ledger(calc_rows: list[dict]) -> dict[str, int]:
    ledger = TARGET / "data_sources"
    source_rows = []
    for source in SOURCES:
        source_rows.append({
            "source_id": source["source_id"],
            "provider": source["provider"],
            "product": source["title"],
            "edition": "retained exact web/PDF locator",
            "reference_period": source["reference_period"],
            "geography": "Philippines and/or international engineering benchmark",
            "variable": source["use"],
            "source_unit": "source-specific",
            "exact_locator": source["locator"],
            "url": source["url"],
            "access_date": "2026-08-31",
            "license": "",
            "sha256": "",
            "local_file": "water_cost_vIS14_2026-08-31/SOURCES.csv",
            "notes": "The exact input and transformation are recorded in CALCULATIONS.csv; no source-file hash is required for this web-cited vIS1.4 update.",
        })
    append_schema_rows(ledger / "SOURCES.csv", source_rows)

    assumption_rows = [
        {
            "assumption_id": "ASM_PHL_VIS14_CONSTANT_2020_USD",
            "statement": "Normalize all water-withdrawal VariableCost inputs once to constant 2020 USD and hold them constant in real terms through 2053.",
            "central_value": "2020",
            "unit": "price year",
            "evidence_source_ids": "SRC_VIS14_WB_CPI;SRC_VIS14_BSP_FX_2020",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "Maintains one real price basis across Philippine-peso and US-dollar sources.",
            "notes": "1 USD/m3 equals exactly 1000 MUSD/km3 at the model activity scale.",
        },
        {
            "assumption_id": "ASM_PHL_VIS14_PUBLIC_MARGINAL_COST",
            "statement": "Use the midpoint of the two World Bank/WSP reported doubled-production cost-growth responses as the public-water marginal production cost.",
            "central_value": "7.235",
            "unit": "PHP2009/m3",
            "evidence_source_ids": "SRC_VIS14_WB_WSP_WATER_DISTRICTS",
            "lower_bound": "7.00",
            "upper_bound": "7.47",
            "rationale": "A marginal coefficient belongs in VariableCost; reported average costs contain 70-80 percent fixed cost.",
            "notes": "Groundwater VC removes the reference monetary value of the existing electricity IAR to avoid double counting.",
        },
        {
            "assumption_id": "ASM_PHL_VIS14_POWER_RESOURCE_FEE",
            "statement": "Apply the flow-proportional NWRB power-generation resource-user fee to national and island power-water withdrawal routes.",
            "central_value": "8.40",
            "unit": "PHP2015 per l/s-year",
            "evidence_source_ids": "SRC_VIS14_LLDA_NWRB_ANNUAL_WATER_CHARGE",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "A legal Philippine flow charge is compatible with self-supplied abstraction; the rejected purchased-water proxy would have embedded supplier infrastructure and double counted the new asset costs.",
            "notes": "The fixed PHP5000 permit component is excluded from VC and groundwater pumping electricity remains endogenous.",
        },
        {
            "assumption_id": "ASM_PHL_VIS14_IRRIGATION_RAW_FEE_BOUNDARY",
            "statement": "Apply only the flow-proportional national/corporate NWRB resource-user fee to agriculture withdrawal routes.",
            "central_value": "16.80",
            "unit": "PHP2015 per l/s-year",
            "evidence_source_ids": "SRC_VIS14_LLDA_NWRB_ANNUAL_WATER_CHARGE;SRC_VIS14_FAO_IRRIGATION_CHARGING;SRC_VIS14_NIA_2020_ANNUAL_REPORT",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "PHL_AGR_IRRIGATION already carries scheme capital and O&M; loading total service cost on gross withdrawal would double count it.",
            "notes": "The fixed PHP5000 permit component is excluded from VC.",
        },
        {
            "assumption_id": "ASM_PHL_VIS14_ABSTRACTION_ASSET_COSTS",
            "statement": "Use the repository's CCG/CLEWs Demo source-class benchmark for the physical intake/pump asset carried by every withdrawal technology.",
            "central_value": "surface CC=137 FC=7; groundwater CC=332 FC=17",
            "unit": "MUSD/(km3/year); MUSD/(km3/year)-year",
            "evidence_source_ids": "SRC_VIS14_CLEWS_DEMO_ABSTRACTION_ASSETS;SRC_VIS14_ADB_WDDSP",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "These are the same physical abstraction technology class and model capacity unit; one source-class coefficient avoids unsupported use- or island-specific asset prices.",
            "notes": "Boundary excludes treatment, distribution, irrigation conveyance/on-farm works, and already-modelled electricity.",
        },
        {
            "assumption_id": "ASM_PHL_VIS14_ABSTRACTION_LIFE",
            "statement": "Use the CCG/CLEWs 20-year composite abstraction-asset life for all twelve routes.",
            "central_value": "20",
            "unit": "years",
            "evidence_source_ids": "SRC_VIS14_CLEWS_DEMO_ABSTRACTION_ASSETS;SRC_VIS14_US_EPA_ASSET_LIFE",
            "lower_bound": "10",
            "upper_bound": "35",
            "rationale": "The model technology represents a composite pumping/intake train; 20 years lies between EPA pumping-equipment and civil well/intake component lives.",
            "notes": "No residual capacity is invented because no national asset registry can allocate 2020 installed stock across the twelve routes.",
        },
        {
            "assumption_id": "ASM_PHL_VIS14_ENERGY_BOUNDARY",
            "statement": "Retain existing water-pumping electricity IARs and exclude their electricity from direct infrastructure cost where already represented.",
            "central_value": "unchanged",
            "unit": "model IAR",
            "evidence_source_ids": "SRC_VIS14_MANILA_WATER_ENERGY_CHECK",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "Electricity remains an endogenous input; duplicating it in direct cost would double count.",
            "notes": "The Manila Water 1150 GJ/MCM benchmark remains a documented calibration gap.",
        },
    ]
    append_schema_rows(ledger / "ASSUMPTIONS.csv", assumption_rows)

    calculation_rows = [
        {
            "calculation_id": "CALC_PHL_VIS14_PUBLIC_WATER_VC",
            "formula": "all-in=(7.235*PHL_CPI2020/PHL_CPI2009/49.62)*1000; groundwater direct=all-in-(0.7/3.6*8.13/49.62)*1000",
            "source_ids": "SRC_VIS14_WB_WSP_WATER_DISTRICTS;SRC_VIS14_WB_CPI;SRC_VIS14_BSP_FX_2020;SRC_VIS14_DOE_EPIRA_RATE",
            "assumption_ids": "ASM_PHL_VIS14_CONSTANT_2020_USD;ASM_PHL_VIS14_PUBLIC_MARGINAL_COST;ASM_PHL_VIS14_ENERGY_BOUNDARY",
            "input_calculation_ids": "",
            "input_values": "7.235;96.3485477178423;132.7240608691;49.62;0.7;8.13",
            "input_units": "PHP2009/m3;CPI;CPI;PHP/USD;PJ/km3;PHP/kWh",
            "output_value": f"surface={PUBLIC_SUR_VC:.15g};groundwater_direct={PUBLIC_GWT_VC:.15g}",
            "output_unit": "MUSD/km3",
            "script_path": "scripts/philippines_vis14_water_costs.py",
            "script_version": "vIS1.4",
            "notes": "At the reference tariff, groundwater direct VC plus its existing electricity input reconstructs the same public all-in marginal cost.",
        },
        {
            "calculation_id": "CALC_PHL_VIS14_POWER_WITHDRAWAL_VC",
            "formula": "8.40*PHL_CPI2020/PHL_CPI2015/31536/49.62*1000",
            "source_ids": "SRC_VIS14_LLDA_NWRB_ANNUAL_WATER_CHARGE;SRC_VIS14_WB_CPI;SRC_VIS14_BSP_FX_2020",
            "assumption_ids": "ASM_PHL_VIS14_CONSTANT_2020_USD;ASM_PHL_VIS14_POWER_RESOURCE_FEE;ASM_PHL_VIS14_ENERGY_BOUNDARY",
            "input_calculation_ids": "",
            "input_values": "8.40;132.7240608691;115.429504132997;31536;49.62",
            "input_units": "PHP2015/lps-year;CPI;CPI;m3/lps-year;PHP/USD",
            "output_value": f"{POWER_VC:.15g}",
            "output_unit": "MUSD/km3",
            "script_path": "scripts/philippines_vis14_water_costs.py",
            "script_version": "vIS1.4",
            "notes": "The flow charge is source-neutral; fixed permit cost and endogenous pumping electricity are excluded.",
        },
        {
            "calculation_id": "CALC_PHL_VIS14_IRRIGATION_WITHDRAWAL_VC",
            "formula": "16.80*PHL_CPI2020/PHL_CPI2015/31536/49.62*1000",
            "source_ids": "SRC_VIS14_LLDA_NWRB_ANNUAL_WATER_CHARGE;SRC_VIS14_WB_CPI;SRC_VIS14_BSP_FX_2020",
            "assumption_ids": "ASM_PHL_VIS14_CONSTANT_2020_USD;ASM_PHL_VIS14_IRRIGATION_RAW_FEE_BOUNDARY",
            "input_calculation_ids": "",
            "input_values": "16.80;132.7240608691;115.429504132997;31536;49.62",
            "input_units": "PHP2015/lps-year;CPI;CPI;m3/lps-year;PHP/USD",
            "output_value": f"{IRRIGATION_VC:.15g}",
            "output_unit": "MUSD/km3",
            "script_path": "scripts/philippines_vis14_water_costs.py",
            "script_version": "vIS1.4",
            "notes": "Only the flow-proportional charge is converted; fixed permit and scheme service costs are excluded.",
        },
        {
            "calculation_id": "CALC_PHL_VIS14_DOUBLE_COUNT_GATE",
            "formula": "public groundwater direct+reference modeled electricity=public all-in; power and irrigation use only legal flow fees; abstraction assets exclude downstream infrastructure and modeled electricity",
            "source_ids": "SRC_VIS14_WB_WSP_WATER_DISTRICTS;SRC_VIS14_LLDA_NWRB_ANNUAL_WATER_CHARGE;SRC_VIS14_FAO_IRRIGATION_CHARGING;SRC_VIS14_CLEWS_DEMO_ABSTRACTION_ASSETS",
            "assumption_ids": "ASM_PHL_VIS14_PUBLIC_MARGINAL_COST;ASM_PHL_VIS14_POWER_RESOURCE_FEE;ASM_PHL_VIS14_IRRIGATION_RAW_FEE_BOUNDARY;ASM_PHL_VIS14_ABSTRACTION_ASSET_COSTS;ASM_PHL_VIS14_ENERGY_BOUNDARY",
            "input_calculation_ids": "CALC_PHL_VIS14_PUBLIC_WATER_VC;CALC_PHL_VIS14_POWER_WITHDRAWAL_VC;CALC_PHL_VIS14_IRRIGATION_WITHDRAWAL_VC;CALC_PHL_VIS14_ABSTRACTION_ASSET_COSTS",
            "input_values": "model IAR and existing PHL_AGR_IRRIGATION VC",
            "input_units": "mixed",
            "output_value": "passed if exact boundary checks hold",
            "output_unit": "boolean gate",
            "script_path": "scripts/philippines_vis14_water_costs.py",
            "script_version": "vIS1.4",
            "notes": "Preflight blocks generation on any boundary failure.",
        },
        {
            "calculation_id": "CALC_PHL_VIS14_ABSTRACTION_ASSET_COSTS",
            "formula": "transfer model-aligned source-class benchmark unchanged: surface CC=137 FC=7; groundwater CC=332 FC=17; OL=20",
            "source_ids": "SRC_VIS14_CLEWS_DEMO_ABSTRACTION_ASSETS;SRC_VIS14_US_EPA_ASSET_LIFE;SRC_VIS14_ADB_WDDSP",
            "assumption_ids": "ASM_PHL_VIS14_ABSTRACTION_ASSET_COSTS;ASM_PHL_VIS14_ABSTRACTION_LIFE;ASM_PHL_VIS14_ENERGY_BOUNDARY",
            "input_calculation_ids": "",
            "input_values": "137;7;332;17;20",
            "input_units": "MUSD/(km3/year);MUSD/(km3/year)-year;MUSD/(km3/year);MUSD/(km3/year)-year;years",
            "output_value": "surface=137/7/20;groundwater=332/17/20",
            "output_unit": "CC/FC/OL",
            "script_path": "scripts/philippines_vis14_water_costs.py",
            "script_version": "vIS1.4",
            "notes": "The source-class costs are applied to public, power, agriculture, and island variants without unsupported multipliers.",
        },
    ]
    append_schema_rows(ledger / "CALCULATIONS.csv", calculation_rows)

    model_map_rows = []
    for row in calc_rows:
        sector = row["sector"]
        calc_id = (
            "CALC_PHL_VIS14_PUBLIC_WATER_VC" if sector == "public"
            else "CALC_PHL_VIS14_IRRIGATION_WITHDRAWAL_VC" if sector == "irrigation"
            else "CALC_PHL_VIS14_POWER_WITHDRAWAL_VC"
        )
        model_map_rows.append({
            "map_id": "MAP_PHL_VIS14_WATER_VC_" + re.sub(r"[^A-Z0-9]+", "_", row["technology"].upper()),
            "model_file": "RYTM.json",
            "parameter": "VC",
            "entity": row["technology"],
            "mode": "1",
            "scenario": "SC_0; policy rows inherit",
            "years": "2020-2053",
            "value_or_expression": row["variable_cost_musd_per_km3"],
            "model_unit": "MUSD/km3 gross withdrawal",
            "evidence_ids": calc_id + ";CALC_PHL_VIS14_DOUBLE_COUNT_GATE",
            "superseded_by": "",
            "evidence_type": "source+calculation+assumption",
            "notes": row["boundary"],
        })
        for parameter, value, unit in (
            ("CC", CAPITAL_COSTS[row["technology"]], "MUSD per km3/year capacity"),
            ("FC", FIXED_COSTS[row["technology"]], "MUSD per km3/year capacity-year"),
            ("OL", PUMP_OPERATIONAL_LIFE, "years"),
        ):
            model_map_rows.append({
                "map_id": f"MAP_PHL_VIS14_WATER_{parameter}_" + re.sub(r"[^A-Z0-9]+", "_", row["technology"].upper()),
                "model_file": "RT.json" if parameter == "OL" else "RYT.json",
                "parameter": parameter,
                "entity": row["technology"],
                "mode": "",
                "scenario": "SC_0; policy rows inherit",
                "years": "2020-2053" if parameter != "OL" else "model period",
                "value_or_expression": value,
                "model_unit": unit,
                "evidence_ids": "CALC_PHL_VIS14_ABSTRACTION_ASSET_COSTS;CALC_PHL_VIS14_DOUBLE_COUNT_GATE",
                "superseded_by": "",
                "evidence_type": "model benchmark+official cross-check+assumption",
                "notes": "Physical abstraction asset only; excludes downstream treatment, distribution, irrigation service, and endogenous electricity.",
            })
    append_schema_rows(ledger / "MODEL_MAP.csv", model_map_rows)

    append_schema_rows(ledger / "CHANGES.csv", [{
        "change_id": "CHG_PHL_VIS14_WATER_WITHDRAWAL_COSTS_20260831",
        "date": "2026-08-31",
        "class": "B",
        "description": "Costed all twelve national and island physical water-withdrawal assets with source-class capital, fixed O&M, 20-year life, and direct variable costs under explicit double-count boundaries.",
        "model_objects": "RYT.json CC/FC; RT.json OL; RYTM.json VC: 12 technologies, 2020-2053 where year-indexed",
        "evidence_path": "data_sources/water_cost_vIS14_2026-08-31;documentation/MODEL_FIXES_WATER_INFRASTRUCTURE_VIS14_2026-08-31.md",
        "map_rows_affected": "48 MAP_PHL_VIS14_WATER_{VC,CC,FC,OL}_* rows",
        "resolve_status": "pending_single_BASE_validation",
        "author": "Codex",
        "commit": "",
        "notes": "No outcome constraint, activity floor, share, TAL or TAU added; physical OL changes capacity survival from the placeholder one-year pass-through treatment.",
    }])

    gap_rows = [
        {
            "item": "Philippines abstraction-asset cost and stock by source, use and island",
            "why_absent": "No public national inventory allocates installed pump/intake capacity or comparable capital and fixed O&M across the twelve modeled routes.",
            "upgrade_source": "Plant-level water-supply contracts, audited O&M accounts, NWRB permits and pumping records for Luzon, Visayas and Mindanao.",
            "priority": "high",
            "notes": "vIS1.4 transfers the CCG/CLEWs source-class physical-asset benchmark uniformly and does not invent a 2020 residual-capacity allocation.",
        },
        {
            "item": "Physical electricity intensity of public and irrigation withdrawal routes",
            "why_absent": "Manila Water reports an aggregate billed-water energy intensity, but it cannot be mapped cleanly to raw surface versus groundwater abstraction; NIA does not publish a national volumetric pumping series.",
            "upgrade_source": "Utility and NIA scheme-level kWh, gross abstraction, delivered volume, lift and source-type data.",
            "priority": "high",
            "notes": "vIS1.4 is cost-only and retains existing IARs; its public-groundwater VC removes only the electricity already represented.",
        },
        {
            "item": "Volumetric Philippine irrigation O&M split between abstraction and scheme service",
            "why_absent": "NIA accounts aggregate administrative, maintenance and project expenses and do not provide a clean national PHP/m3 split; FAO's service-cost range includes components already represented by PHL_AGR_IRRIGATION.",
            "upgrade_source": "NIA scheme ledgers linking annual O&M, pumped energy, water diverted/delivered and maintained service area.",
            "priority": "high",
            "notes": "vIS1.4 assigns only the marginal NWRB resource-user fee to DEMAGR withdrawal routes to avoid double counting service O&M.",
        },
    ]
    append_schema_rows(ledger / "GAPS.csv", gap_rows)
    return {
        "SOURCES.csv": len(source_rows),
        "ASSUMPTIONS.csv": len(assumption_rows),
        "CALCULATIONS.csv": len(calculation_rows),
        "MODEL_MAP.csv": len(model_map_rows),
        "CHANGES.csv": 1,
        "GAPS.csv": len(gap_rows),
    }


def calculations() -> list[dict]:
    rows = []
    for name, value in TECHNOLOGY_COSTS.items():
        if name == "PHL_DEM_PUB_SUR_WAT":
            formula = "7.235 PHP2009/m3 * PHL_CPI2020/PHL_CPI2009 / 49.62 PHP/USD * 1000"
            boundary = "marginal public-water production cost; no modeled electricity input to subtract"
        elif name == "PHL_DEM_PUB_GWT_WAT":
            formula = "public all-in cost - (0.7 PJ/km3 / 3.6 kWh/MJ * 8.13 PHP/kWh / 49.62 PHP/USD), then *1000"
            boundary = "public-water marginal cost net of electricity already purchased endogenously"
        elif name in POWER:
            formula = "8.40 PHP2015/(l/s-year) * PHL_CPI2020/PHL_CPI2015 / 31536 m3/(l/s-year) / 49.62 PHP/USD * 1000"
            boundary = "marginal NWRB power-generation resource fee only; fixed permit, asset costs and electricity represented separately"
        else:
            formula = "16.80 PHP2015/(l/s-year) * PHL_CPI2020/PHL_CPI2015 / 31536 m3/(l/s-year) / 49.62 PHP/USD * 1000"
            boundary = "marginal NWRB resource-user charge only; fixed permit and irrigation-service O&M excluded"
        rows.append({
            "technology": name,
            "classification": "surface" if name in SURFACE else "groundwater",
            "sector": "public" if name in PUBLIC else "irrigation" if name in IRRIGATION else "power cooling",
            "mode": 1,
            "formula": formula,
            "variable_cost_musd_per_km3": f"{value:.15g}",
            "capital_cost_musd_per_km3_per_year": f"{CAPITAL_COSTS[name]:.15g}",
            "fixed_cost_musd_per_km3_per_year_year": f"{FIXED_COSTS[name]:.15g}",
            "operational_life_years": PUMP_OPERATIONAL_LIFE,
            "boundary": boundary,
        })
    return rows


def documentation_text() -> str:
    return f"""# Philippines vIS1.4 physical water-withdrawal cost methodology

Date: 2026-08-31
Parent: Philippines vIS1.3 water-cap candidate
Status: BASE-only candidate; not promoted

## Equation-first classification

All twelve affected technologies are physical abstraction assets: source intake/pump-and-motor trains that convert gross surface water or groundwater into sector water. They are not accounting devices. Cost observations are economic drivers, never activity targets. `RYT.json / CC` enters discounted capital investment, `RYT.json / FC` enters fixed operating cost on total installed capacity, `RT.json / OL` governs vintage survival, and `RYTM.json / VC` multiplies endogenous activity. No demand, activity floor, source share, `TAL`, `TAU`, resource cap, or model equation is added.

The asset boundary excludes treatment, distribution networks, irrigation conveyance/on-farm works, and electricity already purchased through input-activity ratios. ADB Philippine project packages independently confirm that source-development/pumping facilities and pipes/fittings are separable capital scopes. No 2020 residual capacity is invented: a public asset registry capable of allocating installed capacity among these twelve routes was not found, so the existing zero `ResidualCapacity` remains and the model endogenously builds physical capacity.

## Capital, fixed O&M, and lifetime

The repository's CCG/CLEWs Demo contains the same physical abstraction class and capacity unit. Its surface route has `CapitalCost=137`, `FixedCost=7`, `OperationalLife=20`; its groundwater route has `CapitalCost=332`, `FixedCost=17`, `OperationalLife=20`. vIS1.4 transfers these source-class coefficients to every national and island route: surface CC/FC are {SURFACE_CC:g}/{SURFACE_FC:g}; groundwater CC/FC are {GROUNDWATER_CC:g}/{GROUNDWATER_FC:g}; all have a {PUMP_OPERATIONAL_LIFE}-year life. The fixed O&M ratios are approximately 5% of capital. EPA's component guide brackets a composite abstraction train with 10 years for pumping equipment, 25 for wells/springs, and 35 for intake structures, supporting the retained 20-year composite benchmark. The original cost-year metadata are not exposed in the demo; the coefficients are therefore transferred unchanged and disclosed as a model benchmark, not falsely escalated.

## Constant-2020-USD method

The model coefficient is MUSD/km3. Because one km3 is 1 billion m3, `1 USD/m3 = 1,000 MUSD/km3`. Historical peso costs use World Bank Philippine CPI and the BSP 2020 average of PHP49.62/USD. Historical US-dollar costs use World Bank US CPI. Values remain constant in real 2020 dollars through 2053.

### Public supply

The World Bank/WSP-LWUA study reports pump-fed Philippine water-district cost responses when production doubles: average production cost moves from PHP10.00 to PHP8.20/m3 for integrated systems and PHP9.00 to PHP8.30/m3 for non-integrated systems. Its reported cost-growth rates imply incremental costs of PHP7.00 and PHP7.47/m3; their midpoint, PHP7.235/m3 in 2009 prices, is used. This marginal value is preferred to average operating cost because the same study reports fixed-cost shares of 80% and 70%.

Surface public-water VC is {PUBLIC_SUR_VC:.12f} MUSD/km3. Groundwater public-water VC is {PUBLIC_GWT_VC:.12f} MUSD/km3 after subtracting {musd_per_km3(GWT_07_ELECTRICITY_USD_M3):.12f} MUSD/km3: the monetary value, at the DOE 2020 national reference rate, of the existing 0.7 PJ/km3 electricity IAR. This prevents the sourced all-in marginal cost and endogenous electricity purchase from charging the same pumping energy twice. The subtraction is a boundary adjustment, not a fixed model electricity price; the actual solve still prices electricity endogenously.

### Power water

The NWRB/LLDA schedule charges power generators PHP8.40 per l/s-year above 7,000 l/s plus a PHP5,000 base charge. Only the marginal flow charge becomes VC: {POWER_VC:.12f} MUSD/km3. This replaces the rejected purchased-water proxy, which could embed a supplier's infrastructure and double count the new physical asset costs. The fixed permit charge and endogenous groundwater electricity are excluded. National and LUZ/VIS/MIN routes use the same legal rate; no island differential is invented.

### Irrigation

The current NWRB/LLDA schedule charges national/corporate irrigation users PHP16.80 per l/s-year above 7,000 l/s plus a fixed PHP5,000 base charge. Only the marginal flow charge is converted to VC: {IRRIGATION_VC:.12f} MUSD/km3. The fixed permit component is excluded because it is not activity-proportional.

FAO reports total irrigation service costs around USD0.02-0.04/m3, and NIA publishes system O&M accounts, but neither is loaded on `DEMAGRSURPHL` or `DEMAGRGWTPHL`. The model already charges irrigation infrastructure through `PHL_AGR_IRRIGATION` (capital cost plus 0.609137055838 MUSD per 1000 km2-year service), and crop costs explicitly exclude separately represented irrigation charges. Adding FAO's full-service cost to gross-withdrawal activity would double count scheme O&M. The two withdrawal routes therefore carry only the sourced marginal raw-water charge; groundwater pumping electricity remains separate through its existing IAR.

## Scope and limitations

This is a physical-cost calibration, not an installed-stock calibration. Manila Water's 2020 energy benchmark is retained as a check, but electricity IARs are unchanged. NWRB annual charges are assessed on permitted flow rather than metered abstraction; treating the flow-proportional part as VC is an approximation. Surface routes still lack explicit electricity inputs, so their transferred asset costs cover intake/pump equipment but do not fabricate an energy coefficient. The schema ledger records the missing Philippine asset-stock, island-cost, and source-specific energy data as gaps.

## Source and calculation files

- Canonical schema ledger: `data_sources/SOURCES.csv`, `ASSUMPTIONS.csv`, `CALCULATIONS.csv`, `MODEL_MAP.csv`, `CHANGES.csv`, and `GAPS.csv`
- `data_sources/water_cost_vIS14_2026-08-31/SOURCES.csv`
- `data_sources/water_cost_vIS14_2026-08-31/CALCULATIONS.csv`
- `data_sources/water_cost_vIS14_2026-08-31/MODEL_MAP.csv`
- `documentation/vis14_water_cost_preflight.json`
- `res/{RUN_NAME}/generation_matrix_report.json`
- `res/{RUN_NAME}/optimization_record.json`
- `res/{RUN_NAME}/result_comparison_vs_vis13.json`
"""


def build() -> None:
    if TARGET.exists():
        raise FileExistsError(f"refusing to replace candidate: {TARGET}")
    shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("res", ".DS_Store"))

    gen = read_json(TARGET / "genData.json")
    gen["osy-casename"] = "Philippines_vIS1.4"
    gen["osy-date"] = "2026-08-31"
    gen["osy-desc"] = (
        "Philippines vIS1.4: vIS1.3 plus source-traceable physical asset and "
        "operating costs for all twelve surface- and groundwater-withdrawal routes."
    )
    write_json(TARGET / "genData.json", gen)

    ids = technology_ids(gen)
    ryt = read_json(TARGET / "RYT.json")
    rt = read_json(TARGET / "RT.json")
    rytm = read_json(TARGET / "RYTM.json")
    for name, value in TECHNOLOGY_COSTS.items():
        for parameter, expected in (("CC", CAPITAL_COSTS[name]), ("FC", FIXED_COSTS[name])):
            rows = [row for row in ryt[parameter][BASE] if row["TechId"] == ids[name]]
            if len(rows) != 1:
                raise RuntimeError(f"expected exactly one BASE {parameter} row for {name}, found {len(rows)}")
            for year in YEARS:
                rows[0][year] = expected
        life_rows = [row for row in rt["OL"][BASE] if ids[name] in row]
        if len(life_rows) != 1:
            raise RuntimeError(f"expected exactly one BASE OL row for {name}, found {len(life_rows)}")
        life_rows[0][ids[name]] = PUMP_OPERATIONAL_LIFE
        rows = [row for row in rytm["VC"][BASE] if row["TechId"] == ids[name] and row["MoId"] == 1]
        if len(rows) != 1:
            raise RuntimeError(f"expected exactly one BASE VC row for {name}/mode 1, found {len(rows)}")
        for year in YEARS:
            rows[0][year] = value
    write_json(TARGET / "RYT.json", ryt)
    write_json(TARGET / "RT.json", rt)
    write_json(TARGET / "RYTM.json", rytm)

    source_dir = TARGET / "data_sources" / "water_cost_vIS14_2026-08-31"
    write_csv(source_dir / "SOURCES.csv", SOURCES)
    calc_rows = calculations()
    write_csv(source_dir / "CALCULATIONS.csv", calc_rows)
    write_csv(source_dir / "MODEL_MAP.csv", [
        {
            "model_file": "RYTM.json",
            "parameter": "VC",
            "scenario": BASE,
            "technology": row["technology"],
            "mode": 1,
            "years": "2020-2053",
            "value_musd_per_km3": row["variable_cost_musd_per_km3"],
            "capital_cost_musd_per_km3_per_year": row["capital_cost_musd_per_km3_per_year"],
            "fixed_cost_musd_per_km3_per_year_year": row["fixed_cost_musd_per_km3_per_year_year"],
            "operational_life_years": row["operational_life_years"],
            "inheritance": "non-BASE rows remain null and inherit BASE",
        }
        for row in calc_rows
    ])
    ledger_additions = write_schema_ledger(calc_rows)
    (source_dir / "README.md").write_text(documentation_text(), encoding="utf-8")
    (TARGET / "documentation" / "MODEL_FIXES_WATER_INFRASTRUCTURE_VIS14_2026-08-31.md").write_text(
        documentation_text(), encoding="utf-8"
    )
    write_json(TARGET / "documentation" / "vis14_water_cost_build_manifest.json", {
        "schema": "philippines-vis14-water-cost-build-v1",
        "source_case": str(SOURCE),
        "candidate_case": str(TARGET),
        "source_parameter_changed": "RYT.json CC/FC, RT.json OL, RYTM.json VC / SC_0 / 12 technologies / 2020-2053 where year-indexed",
        "structural_changes": 0,
        "capacity_survival_change": "OL 1 to 20 years for 12 physical assets",
        "constraint_changes": 0,
        "optimizer_runs": 0,
        "costs_musd_per_km3": TECHNOLOGY_COSTS,
        "capital_costs_musd_per_km3_per_year": CAPITAL_COSTS,
        "fixed_costs_musd_per_km3_per_year_year": FIXED_COSTS,
        "operational_life_years": PUMP_OPERATIONAL_LIFE,
        "canonical_schema_ledger_additions": ledger_additions,
    })
    print(json.dumps({
        "candidate": str(TARGET),
        "costs_musd_per_km3": TECHNOLOGY_COSTS,
        "capital_costs_musd_per_km3_per_year": CAPITAL_COSTS,
        "fixed_costs_musd_per_km3_per_year_year": FIXED_COSTS,
        "operational_life_years": PUMP_OPERATIONAL_LIFE,
        "canonical_schema_ledger_additions": ledger_additions,
    }, indent=2))


def energy_iar(case: Path, ids: dict[str, str]) -> dict[str, float]:
    gen = read_json(case / "genData.json")
    commodities = {row["CommId"]: row["Comm"] for row in gen["osy-comm"]}
    rows = read_json(case / "RYTCM.json")["IAR"][BASE]
    result = {}
    for name in TECHNOLOGY_COSTS:
        total = 0.0
        for row in rows:
            if row["TechId"] == ids[name] and "ELE" in commodities.get(row["CommId"], ""):
                if row["MoId"] == 1:
                    total += float(row["2020"])
        result[name] = total
    return result


def preflight() -> None:
    failures = []
    checks = []

    def check(condition: bool, name: str, detail=None):
        checks.append({"check": name, "passed": bool(condition), "detail": detail})
        if not condition:
            failures.append(name)

    gen = read_json(TARGET / "genData.json")
    ids = technology_ids(gen)
    check(gen["osy-casename"] == "Philippines_vIS1.4", "case identity")
    check(set(TECHNOLOGY_COSTS) <= set(ids), "all twelve technologies exist")
    check(len(TECHNOLOGY_COSTS) == 12, "exactly twelve costed technologies")
    check(len(SURFACE) == 6 and len(GROUNDWATER) == 6, "six surface and six groundwater routes")

    rytm = read_json(TARGET / "RYTM.json")["VC"]
    ryt_all = read_json(TARGET / "RYT.json")
    rt_all = read_json(TARGET / "RT.json")
    for name, expected in TECHNOLOGY_COSTS.items():
        rows = [row for row in rytm[BASE] if row["TechId"] == ids[name] and row["MoId"] == 1]
        check(len(rows) == 1, f"one active BASE VC row: {name}")
        if rows:
            check(all(math.isclose(float(rows[0][year]), expected, rel_tol=0, abs_tol=1e-12) for year in YEARS),
                  f"full-horizon VC value: {name}", expected)
            check(expected > 0 and math.isfinite(expected), f"positive finite VC: {name}")
        for parameter, asset_expected in (("CC", CAPITAL_COSTS[name]), ("FC", FIXED_COSTS[name])):
            asset_rows = [row for row in ryt_all[parameter][BASE] if row["TechId"] == ids[name]]
            check(len(asset_rows) == 1, f"one active BASE {parameter} row: {name}")
            if asset_rows:
                check(all(math.isclose(float(asset_rows[0][year]), asset_expected, rel_tol=0, abs_tol=1e-12) for year in YEARS),
                      f"full-horizon {parameter} value: {name}", asset_expected)
                check(asset_expected > 0 and math.isfinite(asset_expected), f"positive finite {parameter}: {name}")
            for scenario, scenario_rows in ryt_all[parameter].items():
                if scenario == BASE:
                    continue
                overlay = [row for row in scenario_rows if row["TechId"] == ids[name]]
                check(len(overlay) == 1 and all(overlay[0][year] is None for year in YEARS),
                      f"{parameter} policy inheritance remains null: {scenario}/{name}")
        life_rows = [row for row in rt_all["OL"][BASE] if ids[name] in row]
        check(len(life_rows) == 1 and life_rows[0][ids[name]] == PUMP_OPERATIONAL_LIFE,
              f"physical operational life: {name}", PUMP_OPERATIONAL_LIFE)
        rc_rows = [row for row in ryt_all["RC"][BASE] if row["TechId"] == ids[name]]
        check(len(rc_rows) == 1 and all(float(rc_rows[0][year]) == 0 for year in YEARS),
              f"no invented residual stock: {name}")
        for scenario, scenario_rows in rytm.items():
            if scenario == BASE:
                continue
            overlay = [row for row in scenario_rows if row["TechId"] == ids[name] and row["MoId"] == 1]
            check(len(overlay) == 1 and all(overlay[0][year] is None for year in YEARS),
                  f"policy inheritance remains null: {scenario}/{name}")

    iars = energy_iar(TARGET, ids)
    expected_iars = {name: 0.0 for name in TECHNOLOGY_COSTS}
    expected_iars.update({name: 0.7 for name in GROUNDWATER if name not in IRRIGATION})
    expected_iars["DEMAGRGWTPHL"] = 0.0173
    for name, expected in expected_iars.items():
        check(math.isclose(iars[name], expected, rel_tol=0, abs_tol=1e-12), f"existing electricity IAR: {name}", expected)

    reconstructed_public = PUBLIC_GWT_VC + musd_per_km3(GWT_07_ELECTRICITY_USD_M3)
    check(math.isclose(reconstructed_public, PUBLIC_SUR_VC, rel_tol=0, abs_tol=1e-9),
          "public groundwater all-in cost reconstructs without energy double count",
          {"direct": PUBLIC_GWT_VC, "reference_energy": musd_per_km3(GWT_07_ELECTRICITY_USD_M3), "all_in": reconstructed_public})

    irrigation_id = ids.get("PHL_AGR_IRRIGATION")
    irrigation_rows = [row for row in rytm[BASE] if row["TechId"] == irrigation_id and row["MoId"] == 1]
    irrigation_service_vc = irrigation_rows[0]["2020"] if len(irrigation_rows) == 1 else None
    check(len(irrigation_rows) == 1 and math.isclose(float(irrigation_service_vc), 0.6091370558375635, rel_tol=0, abs_tol=1e-12),
          "separate irrigation-service O&M remains present", irrigation_service_vc)
    check(IRRIGATION_VC < 0.1, "irrigation withdrawal cost limited to raw-water fee, not duplicated full-service cost", IRRIGATION_VC)
    check(PUBLIC_SUR_VC > PUBLIC_GWT_VC > IRRIGATION_VC > POWER_VC > 0,
          "direct-cost magnitudes follow the documented sector boundaries")
    check(all(CAPITAL_COSTS[name] > FIXED_COSTS[name] > 0 for name in TECHNOLOGY_COSTS),
          "all physical assets have non-zero capital and fixed costs")

    # Constructive feasibility gate: retain the solved vIS1.3 activity schedule,
    # and build enough 20-year-lived capacity to cover its largest timeslice
    # rate. With zero minimum investment and all candidate maxima above that
    # rate, extending asset life cannot invalidate that schedule.
    baseline_peak = {name: 0.0 for name in TECHNOLOGY_COSTS}
    with (BASELINE_RUN / "csv" / "RateOfActivity.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["t"] in baseline_peak:
                baseline_peak[row["t"]] = max(baseline_peak[row["t"]], float(row["RateOfActivity"]))
    for name, peak in baseline_peak.items():
        max_rows = [row for row in ryt_all["TAMaxC"][BASE] if row["TechId"] == ids[name]]
        min_rows = [row for row in ryt_all["TAMinCI"][BASE] if row["TechId"] == ids[name]]
        minimum_investment = max(float(min_rows[0][year]) for year in YEARS) if min_rows else math.inf
        available_ceiling = min(float(max_rows[0][year]) for year in YEARS) if max_rows else -math.inf
        check(peak <= available_ceiling + 1e-9 and minimum_investment == 0,
              f"constructive baseline activity capacity envelope: {name}",
              {"baseline_peak_rate": peak, "minimum_total_capacity_ceiling": available_ceiling, "maximum_minimum_investment": minimum_investment})

    record = read_json(BASELINE_RUN / "optimization_record.json")
    check(str(record.get("status", "")).startswith("Optimal"), "retained vIS1.3 BASE feasible witness is optimal")
    check((BASELINE_RUN / "results.txt").is_file(), "retained vIS1.3 BASE witness results exist")

    report = {
        "schema": "philippines-vis14-water-cost-preflight-v1",
        "status": "passed" if not failures else "failed",
        "optimizer_runs": 0,
        "generation_runs": 0,
        "physical_classification": "twelve physical source-intake/pump abstraction assets",
        "observation_classification": "economic-driver costs, engineering/model asset benchmark, and legal fees; no observed activity is imposed",
        "equation_map": {
            "source": "RYT.json CC/FC; RT.json OL; RYTM.json VC / SC_0",
            "generated": "CapitalCost, FixedCost, OperationalLife, VariableCost",
            "equation": "CAa1/CAa2 capacity accumulation and OC1/OC2/CI1 discounted costs in SOLVERs/model.v.5.4.txt",
            "effect": "physical capacity survives 20 years and incurs capital, fixed, and direct variable costs",
        },
        "feasibility_proof": (
            "The retained vIS1.3 activity schedule is constructive: each affected technology has zero minimum investment, "
            "its maximum capacity exceeds the schedule's maximum timeslice rate, and a 20-year life permits capacity to be "
            "built no later than needed. Costs do not constrain activity and no demand/resource equation changes."
        ),
        "double_counting_boundary": {
            "public": "groundwater direct VC is sourced all-in marginal cost less the existing 0.7 PJ/km3 electricity input valued at the DOE reference rate",
            "power": "only the Philippine legal flow fee is variable; the purchased-water proxy was rejected because it could embed supplier infrastructure",
            "irrigation": "withdrawal VC is only the marginal NWRB resource-user fee; scheme capital/O&M remains solely on PHL_AGR_IRRIGATION and electricity remains in IAR",
            "assets": "CC/FC cover source intake/pump assets only; treatment, distribution, irrigation service, and modeled electricity are excluded",
            "excluded_fixed_costs": "public average/fixed cost and the NWRB PHP5,000 permit charge",
        },
        "costs_musd_per_km3": TECHNOLOGY_COSTS,
        "capital_costs_musd_per_km3_per_year": CAPITAL_COSTS,
        "fixed_costs_musd_per_km3_per_year_year": FIXED_COSTS,
        "operational_life_years": PUMP_OPERATIONAL_LIFE,
        "checks": checks,
        "failures": failures,
    }
    write_json(TARGET / "documentation" / "vis14_water_cost_preflight.json", report)
    print(json.dumps({k: report[k] for k in ("status", "optimizer_runs", "generation_runs", "costs_musd_per_km3", "failures")}, indent=2))
    if failures:
        raise RuntimeError(f"preflight failed: {failures}")


def datafile() -> DataFile:
    Config.DATA_STORAGE = STORAGE
    return DataFile(TARGET.name)


def matrix_metrics(log: str) -> dict[str, int]:
    patterns = {
        "rows": r"Number of rows\s*=\s*(\d+)",
        "columns": r"Number of columns\s*=\s*(\d+)",
        "matrix_nonzeros": r"Number of non-zeros \(matrix\)\s*=\s*(\d+)",
        "objective_nonzeros": r"Number of non-zeros \(objrow\)\s*=\s*(\d+)",
    }
    result = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, log)
        if match:
            result[key] = int(match.group(1))
    return result


def generated_costs(path: Path) -> dict[str, list[float]]:
    text = path.read_text(encoding="utf-8")
    found = {}
    for name in TECHNOLOGY_COSTS:
        pattern = re.compile(
            rf"\[RE1,{re.escape(name)},\*,\*\]:\s*\n[^\n]+:=\s*\n1\s+([^\n]+)", re.MULTILINE
        )
        match = pattern.search(text)
        if match:
            found[name] = [float(value) for value in match.group(1).split()]
    return found


def generated_asset_values(path: Path, parameter: str) -> dict[str, list[float]]:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"param {re.escape(parameter)}\b.*?;\n", text, re.DOTALL)
    if not match:
        return {}
    if parameter == "OperationalLife":
        lines = [line.split() for line in match.group(0).splitlines() if line.strip()]
        for index, parts in enumerate(lines):
            if parts and parts[-1] == ":=" and index + 1 < len(lines) and lines[index + 1][0] == "RE1":
                names = parts[:-1]
                values = [float(value) for value in lines[index + 1][1:]]
                return {name: [value] for name, value in zip(names, values) if name in TECHNOLOGY_COSTS}
        return {}
    found = {}
    for line in match.group(0).splitlines():
        parts = line.split()
        if parts and parts[0] in TECHNOLOGY_COSTS:
            try:
                found[parts[0]] = [float(value) for value in parts[1:]]
            except ValueError:
                continue
    return found


def recheck_generated() -> None:
    run = TARGET / "res" / RUN_NAME
    report = read_json(run / "generation_matrix_report.json")
    generated_ol = generated_asset_values(run / "data_processed.txt", "OperationalLife")
    ol_ok = set(generated_ol) == set(TECHNOLOGY_COSTS) and all(
        generated_ol[name] == [float(PUMP_OPERATIONAL_LIFE)] for name in generated_ol
    )
    report["all_twelve_generated_operational_lives_landed"] = ol_ok
    report["generated_operational_lives"] = {name: values[0] for name, values in generated_ol.items()}
    report["status"] = "passed" if (
        report.get("all_twelve_generated_costs_landed")
        and report.get("all_twelve_generated_capital_costs_landed")
        and report.get("all_twelve_generated_fixed_costs_landed")
        and ol_ok
        and report.get("glpsol_returncode") == 0
    ) else "failed"
    write_json(run / "generation_matrix_report.json", report)
    print(json.dumps(report, indent=2))
    if report["status"] != "passed":
        raise RuntimeError("existing generated-data/matrix gate remains failed")


def generate_check() -> None:
    preflight_report = read_json(TARGET / "documentation" / "vis14_water_cost_preflight.json")
    if preflight_report.get("status") != "passed" or preflight_report.get("optimizer_runs") != 0:
        raise RuntimeError("blocking source preflight has not passed cleanly")
    run = TARGET / "res" / RUN_NAME
    if run.exists():
        raise FileExistsError(f"refusing to replace run: {run}")

    df = datafile()
    scenarios = [{
        "ScenarioId": item["ScenarioId"],
        "Scenario": item["Scenario"],
        "Desc": item.get("Desc", ""),
        "Active": item["Scenario"] == "BASE",
    } for item in df.genData["osy-scenarios"]]
    created = df.createCaseRun(RUN_NAME, {
        "Case": RUN_NAME,
        "CaseId": "CS_PHL_VIS14_WATER_COST_BASE",
        "Desc": "Philippines vIS1.4 sourced water-withdrawal costs BASE",
        "Runtime": str(date.today()),
        "Scenarios": scenarios,
    })
    if created.get("status_code") != "success":
        raise RuntimeError(json.dumps(created, indent=2))

    timings = {}
    started = time.monotonic()
    df.generateDatafile(RUN_NAME)
    timings["generate"] = time.monotonic() - started
    started = time.monotonic()
    df.preprocessData(run / "data.txt", run / "data_processed.txt")
    timings["preprocess"] = time.monotonic() - started

    landed = generated_costs(run / "data_processed.txt")
    landed_ok = set(landed) == set(TECHNOLOGY_COSTS) and all(
        len(landed[name]) == len(YEARS)
        and all(math.isclose(value, TECHNOLOGY_COSTS[name], rel_tol=0, abs_tol=1e-10) for value in landed[name])
        for name in landed
    )
    generated_cc = generated_asset_values(run / "data_processed.txt", "CapitalCost")
    generated_fc = generated_asset_values(run / "data_processed.txt", "FixedCost")
    generated_ol = generated_asset_values(run / "data_processed.txt", "OperationalLife")
    cc_ok = set(generated_cc) == set(TECHNOLOGY_COSTS) and all(
        len(generated_cc[name]) == len(YEARS)
        and all(math.isclose(value, CAPITAL_COSTS[name], rel_tol=0, abs_tol=1e-10) for value in generated_cc[name])
        for name in generated_cc
    )
    fc_ok = set(generated_fc) == set(TECHNOLOGY_COSTS) and all(
        len(generated_fc[name]) == len(YEARS)
        and all(math.isclose(value, FIXED_COSTS[name], rel_tol=0, abs_tol=1e-10) for value in generated_fc[name])
        for name in generated_fc
    )
    ol_ok = set(generated_ol) == set(TECHNOLOGY_COSTS) and all(
        generated_ol[name] == [float(PUMP_OPERATIONAL_LIFE)] for name in generated_ol
    )

    glpsol = Osemosys._find_solver_binary(df.glpkFolder.resolve(), "glpsol", recursive=False)
    if glpsol is None:
        raise RuntimeError("GLPK solver unavailable")
    started = time.monotonic()
    checked = subprocess.run(
        [str(glpsol), "--check", "-m", str(MODEL), "-d", str(run / "data_processed.txt"), "--wlp", str(run / "lp.lp")],
        cwd=df.glpkFolder.resolve() if df.glpsol_is_bundled else None,
        capture_output=True,
        text=True,
        timeout=300,
    )
    timings["glpsol_check_and_lp"] = time.monotonic() - started
    log = checked.stdout + "\n" + checked.stderr
    (run / "glpsol_check.log").write_text(log, encoding="utf-8")
    matrix_ok = checked.returncode == 0 and "Model has been successfully generated" in log
    report = {
        "schema": "philippines-vis14-water-cost-generation-gate-v1",
        "status": "passed" if landed_ok and cc_ok and fc_ok and ol_ok and matrix_ok else "failed",
        "optimizer_runs": 0,
        "active_scenarios": ["BASE"],
        "timings_seconds": timings,
        "matrix_dimensions": matrix_metrics(log),
        "all_twelve_generated_costs_landed": landed_ok,
        "all_twelve_generated_capital_costs_landed": cc_ok,
        "all_twelve_generated_fixed_costs_landed": fc_ok,
        "all_twelve_generated_operational_lives_landed": ol_ok,
        "generated_costs": {name: values[0] for name, values in landed.items()},
        "generated_capital_costs": {name: values[0] for name, values in generated_cc.items()},
        "generated_fixed_costs": {name: values[0] for name, values in generated_fc.items()},
        "generated_operational_lives": {name: values[0] for name, values in generated_ol.items()},
        "glpsol_returncode": checked.returncode,
    }
    write_json(run / "generation_matrix_report.json", report)
    print(json.dumps(report, indent=2))
    if report["status"] != "passed":
        raise RuntimeError("generated-data/matrix gate failed; optimizer blocked")


def read_activity(path: Path) -> dict[tuple[str, str], float]:
    values = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            key = (row["t"], row["y"])
            values[key] = values.get(key, 0.0) + float(row["TotalAnnualTechnologyActivityByMode"])
    return values


def read_technology_year_metric(path: Path, metric: str) -> dict[tuple[str, str], float]:
    values = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row.get("t") in TECHNOLOGY_COSTS:
                values[(row["t"], row["y"])] = float(row[metric])
    return values


def csv_value_map(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    header = rows[0]
    value_index = len(header) - 2 if header[-1] == "DiscountRate" else len(header) - 1
    ignored = {value_index}
    if header[-1] == "DiscountRate":
        ignored.add(len(header) - 1)
    key_indexes = [index for index in range(len(header)) if index not in ignored]
    values = {}
    for row in rows[1:]:
        key = tuple(row[index] for index in key_indexes)
        values[key] = float(row[value_index])
    key_headers = [header[index] for index in key_indexes]
    return key_headers, header[value_index], values


def compare_results(baseline_csv: Path, candidate_csv: Path) -> dict:
    baseline_files = {path.name: path for path in baseline_csv.glob("*.csv")}
    candidate_files = {path.name: path for path in candidate_csv.glob("*.csv")}
    tables = {}
    global_top = []
    for name in sorted(set(baseline_files) | set(candidate_files)):
        if name not in baseline_files or name not in candidate_files:
            tables[name] = {"status": "missing", "baseline_present": name in baseline_files, "candidate_present": name in candidate_files}
            continue
        key_headers, metric, baseline = csv_value_map(baseline_files[name])
        candidate_headers, candidate_metric, candidate = csv_value_map(candidate_files[name])
        if key_headers != candidate_headers or metric != candidate_metric:
            tables[name] = {"status": "schema_changed", "baseline_metric": metric, "candidate_metric": candidate_metric}
            continue
        changes = []
        for key in set(baseline) | set(candidate):
            old = baseline.get(key, 0.0)
            new = candidate.get(key, 0.0)
            delta = new - old
            tolerance = 1e-8 + 1e-10 * max(abs(old), abs(new))
            if abs(delta) > tolerance:
                record = {
                    "key": dict(zip(key_headers, key)),
                    "baseline": old,
                    "candidate": new,
                    "delta": delta,
                    "absolute_delta": abs(delta),
                }
                changes.append(record)
                global_top.append({"table": name, **record})
        changes.sort(key=lambda row: row["absolute_delta"], reverse=True)
        tables[name] = {
            "status": "changed" if changes else "unchanged",
            "metric": metric,
            "baseline_rows": len(baseline),
            "candidate_rows": len(candidate),
            "changed_rows": len(changes),
            "maximum_absolute_delta": changes[0]["absolute_delta"] if changes else 0.0,
            "top_changes": changes[:10],
        }
    global_top.sort(key=lambda row: row["absolute_delta"], reverse=True)
    return {
        "schema": "philippines-vis14-result-comparison-v1",
        "baseline": str(baseline_csv.parent),
        "candidate": str(candidate_csv.parent),
        "table_count": len(tables),
        "changed_table_count": sum(row.get("status") == "changed" for row in tables.values()),
        "unchanged_table_count": sum(row.get("status") == "unchanged" for row in tables.values()),
        "tables": tables,
        "largest_changes_anywhere": global_top[:30],
    }


def water_caps(activity: dict[tuple[str, str], float]) -> dict:
    gen = read_json(TARGET / "genData.json")
    constraints = {row["Con"]: row for row in gen["osy-constraints"]}
    cap_rows = {row["ConId"]: row for row in read_json(TARGET / "RYCn.json")["UCC"][BASE]}
    result = {}
    for constraint, names in CAP_TECHS.items():
        cap = cap_rows[constraints[constraint]["ConId"]]
        records = []
        for year in YEARS:
            withdrawal = sum(activity.get((name, year), 0.0) for name in names)
            records.append({"year": year, "withdrawal": withdrawal, "cap": cap[year], "headroom": cap[year] - withdrawal})
        binding = min(records, key=lambda row: row["headroom"])
        result[constraint] = {
            "minimum_headroom": binding["headroom"],
            "binding_year": binding["year"],
            "2020_withdrawal": records[0]["withdrawal"],
            "2020_cap": records[0]["cap"],
        }
    return result


def solve(timeout: int) -> None:
    run = TARGET / "res" / RUN_NAME
    gate = read_json(run / "generation_matrix_report.json")
    if gate.get("status") != "passed" or gate.get("optimizer_runs") != 0:
        raise RuntimeError("generation/matrix gate is not a clean zero-optimizer pass")

    df = datafile()
    cbc = Osemosys._find_solver_binary(df.cbcFolder.resolve(), "cbc", recursive=False)
    if cbc is None:
        raise RuntimeError("CBC solver unavailable")
    command = [str(cbc), str(run / "lp.lp"), "solve", "-printing", "all", "-solu", str(run / "results.txt")]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=df.cbcFolder.resolve() if df.cbc_is_bundled else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - started
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        (run / "cbc.log").write_text(stdout + "\n" + stderr, encoding="utf-8")
        report = {
            "status": "timed_out",
            "optimizer_runs": 1,
            "timeout_seconds": timeout,
            "solve_seconds": elapsed,
            "csv_exported": False,
            "promotion_attempted": False,
        }
        write_json(run / "optimization_record.json", report)
        write_json(TARGET / "documentation" / "vis14_base_validation.json", report)
        print(json.dumps(report, indent=2))
        return

    log = completed.stdout + "\n" + completed.stderr
    (run / "cbc.log").write_text(log, encoding="utf-8")
    if completed.returncode != 0 or not (run / "results.txt").is_file():
        raise RuntimeError(log[-12000:])
    status = (run / "results.txt").read_text(encoding="utf-8").splitlines()[0]
    objective_match = re.search(r"objective value\s+([-+0-9.eE]+)", status)
    objective = float(objective_match.group(1)) if objective_match else None
    baseline_record = read_json(BASELINE_RUN / "optimization_record.json")
    baseline_objective = float(baseline_record["objective"])

    export_started = time.monotonic()
    df.generateCSVfromCBC(run / "data.txt", run / "results.txt", run)
    export_seconds = time.monotonic() - export_started
    activity = read_activity(run / "csv" / "TotalAnnualTechnologyActivityByMode.csv")
    baseline_activity = read_activity(BASELINE_RUN / "csv" / "TotalAnnualTechnologyActivityByMode.csv")
    new_capacity = read_technology_year_metric(run / "csv" / "NewCapacity.csv", "NewCapacity")
    total_capacity = read_technology_year_metric(run / "csv" / "TotalCapacityAnnual.csv", "TotalCapacityAnnual")

    by_technology = {}
    for name, cost in TECHNOLOGY_COSTS.items():
        annual = {year: activity.get((name, year), 0.0) for year in YEARS}
        baseline_annual = {year: baseline_activity.get((name, year), 0.0) for year in YEARS}
        by_technology[name] = {
            "vc_musd_per_km3": cost,
            "capital_cost_musd_per_km3_per_year": CAPITAL_COSTS[name],
            "fixed_cost_musd_per_km3_per_year_year": FIXED_COSTS[name],
            "operational_life_years": PUMP_OPERATIONAL_LIFE,
            "2020_activity_km3": annual["2020"],
            "2020_baseline_activity_km3": baseline_annual["2020"],
            "2020_activity_change_km3": annual["2020"] - baseline_annual["2020"],
            "model_horizon_activity_km3": sum(annual.values()),
            "undiscounted_direct_cost_musd": sum(annual.values()) * cost,
            "2020_new_capacity_km3_per_year": new_capacity.get((name, "2020"), 0.0),
            "maximum_new_capacity_km3_per_year": max(new_capacity.get((name, year), 0.0) for year in YEARS),
            "maximum_total_capacity_km3_per_year": max(total_capacity.get((name, year), 0.0) for year in YEARS),
            "inactive_giant_capacity_flag": (
                max(total_capacity.get((name, year), 0.0) for year in YEARS) > 10000
                and sum(annual.values()) < 1e-8
            ),
        }

    comparison = compare_results(BASELINE_RUN / "csv", run / "csv")
    write_json(run / "result_comparison_vs_vis13.json", comparison)
    caps = water_caps(activity)
    report = {
        "schema": "philippines-vis14-water-cost-base-validation-v1",
        "status": status,
        "optimizer_runs": 1,
        "timeout_seconds": timeout,
        "solve_seconds": elapsed,
        "baseline_solve_seconds": baseline_record.get("solve_seconds"),
        "solve_time_change_seconds": elapsed - float(baseline_record.get("solve_seconds", 0)),
        "solve_time_ratio": elapsed / float(baseline_record.get("solve_seconds")),
        "csv_export_seconds": export_seconds,
        "objective": objective,
        "baseline_objective": baseline_objective,
        "objective_change": objective - baseline_objective if objective is not None else None,
        "objective_change_percent": 100 * (objective / baseline_objective - 1) if objective is not None else None,
        "water_caps": caps,
        "water_technology_results": by_technology,
        "result_comparison": {
            "table_count": comparison["table_count"],
            "changed_table_count": comparison["changed_table_count"],
            "unchanged_table_count": comparison["unchanged_table_count"],
            "changed_tables": [name for name, row in comparison["tables"].items() if row.get("status") == "changed"],
        },
        "promotion_attempted": False,
        "stop_point": "BASE finished; no policy scenario, seal, promotion, or second optimization was run",
        "cbc_tail": log[-3000:],
    }
    write_json(run / "optimization_record.json", report)
    write_json(TARGET / "documentation" / "vis14_base_validation.json", report)
    with (TARGET / "documentation" / "MODEL_FIXES_WATER_INFRASTRUCTURE_VIS14_2026-08-31.md").open("a", encoding="utf-8") as stream:
        stream.write(
            "\n## BASE validation\n\n"
            f"CBC status: `{status}`. Runtime: {elapsed:.3f} seconds under a {timeout}-second timeout. "
            f"Objective: {objective:.8f} MUSD, a change of {objective - baseline_objective:.8f} MUSD "
            f"({100 * (objective / baseline_objective - 1):.6f}%) from vIS1.3. "
            f"The all-output CSV comparison found {comparison['changed_table_count']} changed and "
            f"{comparison['unchanged_table_count']} unchanged tables. No other scenario was run and the candidate was not promoted.\n"
        )
    print(json.dumps({
        "status": report["status"],
        "optimizer_runs": report["optimizer_runs"],
        "timeout_seconds": timeout,
        "solve_seconds": elapsed,
        "baseline_solve_seconds": report["baseline_solve_seconds"],
        "solve_time_ratio": report["solve_time_ratio"],
        "objective": objective,
        "objective_change": report["objective_change"],
        "objective_change_percent": report["objective_change_percent"],
        "water_caps": caps,
        "result_comparison": report["result_comparison"],
        "stop_point": report["stop_point"],
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("build", "preflight", "generate-check", "recheck-generated", "solve"))
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    phases = {"build": build, "preflight": preflight, "generate-check": generate_check, "recheck-generated": recheck_generated}
    if args.phase == "solve":
        solve(args.timeout)
    else:
        phases[args.phase]()


if __name__ == "__main__":
    main()
