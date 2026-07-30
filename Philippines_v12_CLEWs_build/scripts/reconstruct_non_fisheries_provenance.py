#!/usr/bin/env python3
"""Reconstruct canonical non-Fisheries provenance ledgers for Philippines v12.

The script never writes under ``model/inputs`` or ``config``. It snapshots the
legacy ledgers, writes the six canonical ledgers, and proves that every model
and configuration input has the same SHA-256 before and after reconstruction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from provenance import LEDGER_TABLES, REQUIRED_COLUMNS


ACCESS_DATE = "2026-07-30"
PHL_COMMIT = "4690597ac3511f402990b03ecfc4182f70b3850b"
MUIOGO_COMMIT = "e9f3823d11537655c9f7ddfd1b36a14f290eac56"
CLEWS_GLOBAL_COMMIT = "8df78c66be104e446f84a7dbb0df1c0a4fda4080"
CLEWS_GAEZ_COMMIT = "30ec12e6524dc9c8ce474ffe1a467508f992007f"
CLEWSY_COMMIT = "6eefaf2abc6d91917c0fddfeea373db37443a8dd"
OSEMOSYS_GLOBAL_COMMIT = "036fdd07cc0dc31df1649cdc1689a8aa35a83a36"

PHL_REPO = "https://github.com/EAPD-DRB/CLEWs-PHL"
MUIOGO_REPO = "https://github.com/EAPD-DRB/MUIOGO"

LEGACY_TABLES = (
    "ASSUMPTIONS.csv",
    "CALCULATIONS.csv",
    "MODEL_DATA_MAP.csv",
)

SET_PARAMETERS = {
    "CROP",
    "DAILYTIMEBRACKET",
    "DAYTYPE",
    "EMISSION",
    "FUEL",
    "MODE_OF_OPERATION",
    "REGION",
    "SEASON",
    "STORAGE",
    "TECHNOLOGY",
    "TIMESLICE",
    "YEAR",
}

TIME_PARAMETERS = {
    "Conversionld",
    "Conversionlh",
    "Conversionls",
    "DAILYTIMEBRACKET",
    "DAYTYPE",
    "DaysInDayType",
    "DaySplit",
    "MODE_OF_OPERATION",
    "REGION",
    "SEASON",
    "TIMESLICE",
    "YEAR",
    "YearSplit",
}

CAPACITY_PARAMETERS = {
    "CapacityOfOneTechnologyUnit",
    "ResidualCapacity",
    "ResidualStorageCapacity",
    "StorageMaxChargeRate",
    "StorageMaxDischargeRate",
    "TotalAnnualMaxCapacity",
    "TotalAnnualMaxCapacityInvestment",
    "TotalAnnualMinCapacity",
    "TotalAnnualMinCapacityInvestment",
}

ACTIVITY_LIMIT_PARAMETERS = {
    "TechnologyActivityByModeLowerLimit",
    "TechnologyActivityByModeUpperLimit",
    "TechnologyActivityDecreaseByModeLimit",
    "TechnologyActivityIncreaseByModeLimit",
    "TotalTechnologyAnnualActivityLowerLimit",
    "TotalTechnologyAnnualActivityUpperLimit",
    "TotalTechnologyModelPeriodActivityLowerLimit",
    "TotalTechnologyModelPeriodActivityUpperLimit",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protected_hashes(root: Path) -> Dict[str, str]:
    files = sorted(
        path
        for base in (root / "model" / "inputs", root / "config")
        for path in base.rglob("*")
        if path.is_file()
    )
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in files
    }


def aggregate_hash(hashes: Dict[str, str]) -> str:
    digest = hashlib.sha256()
    for relative, file_hash in sorted(hashes.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(file_hash))
    return digest.hexdigest()


def blank_row(table: str) -> Dict[str, str]:
    return {column: "" for column in REQUIRED_COLUMNS[table]}


def source(
    source_id: str,
    provider: str,
    product: str,
    edition: str,
    reference_period: str,
    geography: str,
    variable: str,
    source_unit: str,
    exact_locator: str,
    url: str,
    license_name: str,
) -> Dict[str, str]:
    row = blank_row("SOURCES.csv")
    row.update(
        {
            "source_id": source_id,
            "provider": provider,
            "product": product,
            "edition": edition,
            "reference_period": reference_period,
            "geography": geography,
            "variable": variable,
            "source_unit": source_unit,
            "exact_locator": exact_locator,
            "url": url,
            "access_date": ACCESS_DATE,
            "license": license_name,
        }
    )
    return row


def assumption(
    assumption_id: str,
    statement: str,
    central_value: str,
    unit: str,
    evidence_source_ids: str,
    lower_bound: str = "",
    upper_bound: str = "",
) -> Dict[str, str]:
    row = blank_row("ASSUMPTIONS.csv")
    row.update(
        {
            "assumption_id": assumption_id,
            "statement": statement,
            "central_value": central_value,
            "unit": unit,
            "evidence_source_ids": evidence_source_ids,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
        }
    )
    return row


def calculation(
    calculation_id: str,
    formula: str,
    source_ids: str,
    assumption_ids: str,
    input_calculation_ids: str,
    input_values: str,
    input_units: str,
    output_value: str,
    output_unit: str,
    script_path: str = "",
    script_version: str = "",
) -> Dict[str, str]:
    row = blank_row("CALCULATIONS.csv")
    row.update(
        {
            "calculation_id": calculation_id,
            "formula": formula,
            "source_ids": source_ids,
            "assumption_ids": assumption_ids,
            "input_calculation_ids": input_calculation_ids,
            "input_values": input_values,
            "input_units": input_units,
            "output_value": output_value,
            "output_unit": output_unit,
            "script_path": script_path,
            "script_version": script_version,
        }
    )
    return row


def write_table(root: Path, table: str, rows: Iterable[Dict[str, str]]) -> int:
    rows = list(rows)
    path = root / "data_sources" / table
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(REQUIRED_COLUMNS[table]),
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def unique_ids(*values: str) -> str:
    seen = set()
    ordered: List[str] = []
    for value in values:
        for item in re.split(r"[;,\s]+", value):
            item = item.strip()
            if item and item not in seen:
                seen.add(item)
                ordered.append(item)
    return ";".join(ordered)


def is_fisheries_row(row: Dict[str, str]) -> bool:
    return any("FSH" in value.upper() for value in row.values())


def is_nexus_row(row: Dict[str, str]) -> bool:
    text = " ".join(row.values()).upper()
    markers = (
        "AGRWAT",
        "CRP",
        "DEMAGR",
        "LND",
        "LTOM",
        "LCON",
        "LSGC",
        "LMZE",
        "LRCP",
        "LOTH",
        "WTR",
    )
    return any(marker in text for marker in markers)


def commodity_unit(fuel: str) -> str:
    fuel = (fuel or "").upper()
    if fuel.startswith(("WTR", "AGRWAT")):
        return "10^9 m3"
    if fuel.startswith("CRP"):
        return "Mt crop"
    if "LND" in fuel or re.match(r"^L(?:TOM|CON|SGC|MZE|RCP|OTH).+TOT$", fuel):
        return "10^3 km2"
    return "PJ"


def activity_unit(technology: str) -> str:
    technology = (technology or "").upper()
    if technology.startswith(("LND", "MINLND")):
        return "10^3 km2"
    if technology.startswith(("DEMAGR", "MINWTR")):
        return "10^9 m3"
    if "CRP" in technology and technology.startswith("DEM"):
        return "Mt crop"
    return "PJ"


def model_unit(parameter: str, row: Dict[str, str]) -> str:
    fuel = row.get("FUEL", "")
    technology = row.get("TECHNOLOGY", "")
    activity = activity_unit(technology)
    if parameter in SET_PARAMETERS:
        return "set membership"
    if parameter in {"SpecifiedAnnualDemand", "AccumulatedAnnualDemand"}:
        return commodity_unit(fuel)
    if parameter == "SpecifiedDemandProfile":
        return "fraction of annual demand"
    if parameter in {"InputActivityRatio", "OutputActivityRatio"}:
        return f"{commodity_unit(fuel)} per {activity}"
    if parameter == "EmissionActivityRatio":
        return f"MT per {activity}"
    if parameter in {"AnnualEmissionLimit", "AnnualExogenousEmission"}:
        return "MT/year"
    if parameter in {"ModelPeriodEmissionLimit", "ModelPeriodExogenousEmission"}:
        return "MT/model period"
    if parameter == "EmissionsPenalty":
        return "M$/MT"
    if parameter in {"CapacityFactor", "AvailabilityFactor"}:
        return "fraction"
    if parameter in {
        "ReserveMargin",
        "REMinProductionTarget",
        "RETagFuel",
        "RETagTechnology",
        "ReserveMarginTagFuel",
        "ReserveMarginTagTechnology",
    }:
        return "fraction"
    if parameter in {"DiscountRate", "DiscountRateStorage"}:
        return "fraction"
    if parameter in {"YearSplit", "DaySplit"}:
        return "fraction"
    if parameter.startswith("Conversion"):
        return "binary mapping"
    if parameter == "DaysInDayType":
        return "days"
    if parameter in {"OperationalLife", "OperationalLifeStorage"}:
        return "years"
    if parameter == "CapacityToActivityUnit":
        return "activity-unit per capacity-unit-year"
    if parameter in CAPACITY_PARAMETERS:
        return "capacity unit (GW for energy technologies)"
    if parameter == "CapitalCost":
        return "M$/capacity unit"
    if parameter == "CapitalCostStorage":
        return "M$/storage-capacity unit"
    if parameter == "FixedCost":
        return "M$/capacity unit/year"
    if parameter == "VariableCost":
        return f"M$ per {activity}"
    if parameter in ACTIVITY_LIMIT_PARAMETERS:
        return activity
    if parameter in {
        "TechnologyFromStorage",
        "TechnologyToStorage",
        "TradeRoute",
        "DepreciationMethod",
    }:
        return "dimensionless"
    if parameter in {
        "MinStorageCharge",
        "StorageLevelStart",
    }:
        return "fraction of storage capacity"
    return "model-native unit; unresolved at row level"


def row_evidence(parameter: str, row: Dict[str, str]) -> str:
    evidence = [
        "SRC_PHL_V12_REPOSITORY",
        "SRC_OSEMOSYS_GLOBAL_PINNED",
        "SRC_OSEMOSYS_GLOBAL_UNITS",
    ]
    text = " ".join(row.values()).upper()
    if parameter == "CROP":
        evidence.extend(
            [
                "SRC_CROP_CODE_MAPPING",
                "SRC_FAOSTAT_2020",
                "SRC_GAEZ_V4",
                "ASM_LAW_TOMATO_PROXY",
                "ASM_LAW_OTHER_AGGREGATION",
            ]
        )
    elif is_nexus_row(row):
        evidence.extend(
            [
                "SRC_CLEWS_GLOBAL_PINNED",
                "SRC_CLEWS_GAEZ_PINNED",
                "SRC_CLEWSY_PINNED",
                "SRC_GAEZ_V4",
                "SRC_PHL_GEOSPATIAL_SUMMARIES",
            ]
        )
        if "LNDAGR" in text:
            evidence.append("CALC_LAW_CLUSTER_COEFFICIENTS")
        if "AGRWAT" in text:
            evidence.extend(
                [
                    "ASM_LAW_POOLED_WATER",
                    "CALC_LAW_IRRIGATION_DEMAND",
                ]
            )
        if "DEMAGRGWT" in text:
            evidence.append("CALC_LAW_GROUNDWATER_ELECTRICITY")
        if "CRP" in text and parameter == "SpecifiedAnnualDemand":
            evidence.extend(
                [
                    "SRC_FAOSTAT_2020",
                    "ASM_LAW_SSP2_GROWTH",
                    "CALC_LAW_CROP_DEMAND_GROWTH",
                ]
            )
        if "TOM" in text:
            evidence.append("ASM_LAW_TOMATO_PROXY")
        if "OTH" in text:
            evidence.append("ASM_LAW_OTHER_AGGREGATION")
    if parameter in TIME_PARAMETERS:
        evidence.append("SRC_CLEWS_GLOBAL_PINNED")
    return unique_ids(*evidence)


def safe_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return token or "ROW"


def input_map_rows(root: Path) -> tuple[List[Dict[str, str]], int, int]:
    rows: List[Dict[str, str]] = []
    excluded_fisheries = 0
    populated_files = 0
    inputs = root / "model" / "inputs"
    for path in sorted(inputs.rglob("*.csv")):
        relative = path.relative_to(root).as_posix()
        parameter = path.stem
        file_rows = 0
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for line, raw in enumerate(reader, start=2):
                row = {key: (value or "").strip() for key, value in raw.items()}
                if not any(row.values()):
                    continue
                file_rows += 1
                if is_fisheries_row(row):
                    excluded_fisheries += 1
                    continue
                entity_parts = [f"csv_line={line}"]
                for key, value in row.items():
                    if key not in {"VALUE", "YEAR", "MODE_OF_OPERATION"} and value:
                        entity_parts.append(f"{key}={value}")
                value = row.get("VALUE", "")
                if not value:
                    nonblank = [item for item in row.values() if item]
                    value = nonblank[0] if len(nonblank) == 1 else "present"
                mapped = blank_row("MODEL_MAP.csv")
                mapped.update(
                    {
                        "map_id": f"MAP_{safe_token(parameter.upper())}_L{line}",
                        "model_file": relative,
                        "parameter": parameter,
                        "entity": ";".join(entity_parts),
                        "mode": row.get("MODE_OF_OPERATION", ""),
                        "scenario": "raw",
                        "years": row.get("YEAR", "all"),
                        "value_or_expression": value,
                        "model_unit": model_unit(parameter, row),
                        "evidence_ids": row_evidence(parameter, row),
                    }
                )
                rows.append(mapped)
        if file_rows:
            populated_files += 1
    return rows, excluded_fisheries, populated_files


def manual_map(
    map_id: str,
    model_file: str,
    parameter: str,
    entity: str,
    mode: str,
    years: str,
    value_or_expression: str,
    model_unit_value: str,
    evidence_ids: str,
) -> Dict[str, str]:
    row = blank_row("MODEL_MAP.csv")
    row.update(
        {
            "map_id": map_id,
            "model_file": model_file,
            "parameter": parameter,
            "entity": entity,
            "mode": mode,
            "scenario": "raw",
            "years": years,
            "value_or_expression": value_or_expression,
            "model_unit": model_unit_value,
            "evidence_ids": evidence_ids,
        }
    )
    return row


def source_rows() -> List[Dict[str, str]]:
    return [
        source(
            "SRC_PHL_V12_REPOSITORY",
            "EAPD-DRB",
            "CLEWs-PHL Philippines v12 package",
            PHL_COMMIT,
            "2020-2053",
            "Philippines",
            "Retained configuration, raw inputs, documentation and artifacts",
            "model-native; row-specific units are in MODEL_MAP.csv",
            "Philippines_v12_CLEWs_build at the named Git commit; every map row adds an exact file and CSV line",
            f"{PHL_REPO}/tree/{PHL_COMMIT}/Philippines_v12_CLEWs_build",
            "Apache-2.0; third-party data retain provider terms",
        ),
        source(
            "SRC_CLEWS_GLOBAL_PINNED",
            "Climate Compatible Growth",
            "CLEWs Global workflow",
            CLEWS_GLOBAL_COMMIT,
            "build executed in 2026",
            "Philippines",
            "Workflow orchestration and country configuration",
            "software",
            "config/upstream_versions.json workflow.commit; local patches and overrides preserve changed files",
            f"https://github.com/ClimateCompatibleGrowth/clews-global/tree/{CLEWS_GLOBAL_COMMIT}",
            "MIT; see retained license",
        ),
        source(
            "SRC_CLEWS_GAEZ_PINNED",
            "Climate Compatible Growth",
            "CLEWs GAEZ workflow",
            CLEWS_GAEZ_COMMIT,
            "GAEZ v4 / 2010 land-cover baseline",
            "Philippines",
            "Boundary processing, raster extraction and clustering",
            "software",
            "config/upstream_versions.json submodules.CLEWs_GAEZ.commit; overrides/workflow/submodules/CLEWs_GAEZ",
            f"https://github.com/ClimateCompatibleGrowth/CLEWs_GAEZ/tree/{CLEWS_GAEZ_COMMIT}",
            "MIT; see retained license",
        ),
        source(
            "SRC_CLEWSY_PINNED",
            "Climate Compatible Growth",
            "clewsy nexus integration",
            CLEWSY_COMMIT,
            "build executed in 2026",
            "Philippines",
            "Land, crop and water conversion into OSeMOSYS inputs",
            "software",
            "config/upstream_versions.json submodules.clewsy.commit; overrides/workflow/submodules/clewsy",
            f"https://github.com/ClimateCompatibleGrowth/clewsy/tree/{CLEWSY_COMMIT}",
            "See retained clewsy license",
        ),
        source(
            "SRC_OSEMOSYS_GLOBAL_PINNED",
            "OSeMOSYS community",
            "OSeMOSYS Global",
            OSEMOSYS_GLOBAL_COMMIT,
            "workflow data vintages embedded at pinned commit",
            "Philippines",
            "Raw energy-system input generation",
            "PJ, GW, M$, MT and parameter-specific ratios",
            "config/upstream_versions.json submodules.osemosys_global.commit",
            f"https://github.com/OSeMOSYS/osemosys_global/tree/{OSEMOSYS_GLOBAL_COMMIT}",
            "AGPL-3.0; see retained license",
        ),
        source(
            "SRC_OSEMOSYS_GLOBAL_UNITS",
            "OSeMOSYS community",
            "OSeMOSYS Global unit table",
            OSEMOSYS_GLOBAL_COMMIT,
            "unit convention at pinned commit",
            "Global",
            "Energy, capacity, cost and emissions model-unit convention",
            "Energy=PJ; Capacity=GW; Cost=M$; Emissions=MT",
            "docs/data_tables/units.csv at the pinned commit",
            f"https://github.com/OSeMOSYS/osemosys_global/blob/{OSEMOSYS_GLOBAL_COMMIT}/docs/data_tables/units.csv",
            "AGPL-3.0",
        ),
        source(
            "SRC_GADM41_PHL0",
            "GADM",
            "GADM administrative boundaries",
            "4.1",
            "version 4.1",
            "Philippines, administrative level 0",
            "National polygon used for clipping and land-cell construction",
            "EPSG:4326 polygon geometry",
            "Country=Philippines (PHL), level=0; retained components geospatial/boundary/gadm41_PHL_0.{shp,shx,dbf,prj}",
            "https://gadm.org/download_country.html",
            "GADM license and provider terms",
        ),
        source(
            "SRC_GAEZ_V4",
            "FAO and IIASA",
            "Global Agro-Ecological Zones version 4",
            "GAEZ v4 (2021 release)",
            "1961-2010 climate; 2010 land-cover baseline",
            "Philippines",
            "Potential yield, crop water deficit, evapotranspiration, precipitation and land cover",
            "yield and water raster units; converted model units recorded in MODEL_MAP.csv",
            "GAEZ v4 agro-climatic potential-yield and land/water modules; retained summary headers enumerate yld, cwd, evt, precipitation and LCType variables",
            "https://www.fao.org/gaez/gaezv4/en",
            "FAO/IIASA provider terms",
        ),
        source(
            "SRC_FAOSTAT_2020",
            "FAO",
            "FAOSTAT Crop and livestock products",
            "release containing 2020 data",
            "2020",
            "Philippines",
            "Crop harvested area and production used for crop selection and demand anchors",
            "ha and tonnes",
            "Crop and livestock products domain; Area harvested and Production; Philippines; 2020; crop names mapped in retained Crop_code.csv",
            "https://www.fao.org/faostat/en/#data/QCL",
            "FAOSTAT terms of use",
        ),
        source(
            "SRC_PAGASA_SEASONS",
            "DOST-PAGASA",
            "Climate of the Philippines",
            "web page accessed 2026-07-30",
            "climatological description",
            "Philippines",
            "Rainy and dry season month definitions",
            "calendar months",
            "Section 'The Seasons': rainy June-November; dry December-May",
            "https://www.pagasa.dost.gov.ph/information/climate-philippines",
            "Philippine government information; provider terms apply",
        ),
        source(
            "SRC_CROP_CODE_MAPPING",
            "CLEWs GAEZ / Philippines v12 build",
            "Crop-code mapping",
            PHL_COMMIT,
            "2020 crop selection",
            "Philippines",
            "FAOSTAT item names to GAEZ crop codes",
            "categorical crop codes",
            "overrides/workflow/submodules/CLEWs_GAEZ/GAEZ_Processing/Data/Crop_code.csv; rows for RCP, CON, MZE, TOM and SGC",
            f"{PHL_REPO}/blob/{PHL_COMMIT}/Philippines_v12_CLEWs_build/overrides/workflow/submodules/CLEWs_GAEZ/GAEZ_Processing/Data/Crop_code.csv",
            "Apache-2.0 package; upstream/provider terms apply",
        ),
        source(
            "SRC_PHL_GEOSPATIAL_SUMMARIES",
            "Philippines v12 build",
            "Cluster and land-cover summaries",
            PHL_COMMIT,
            "GAEZ v4 / 2020 build configuration",
            "Philippines, eight clusters",
            "Cluster means for yield, water, precipitation and land-cover area",
            "model coefficients; 10^3 km2 and 10^9 m3 conversions",
            "geospatial/summary_stats/PHL_Parameter_byCluster_summary.csv and PHL_LandCover_byCluster_summary.csv",
            f"{PHL_REPO}/tree/{PHL_COMMIT}/Philippines_v12_CLEWs_build/geospatial/summary_stats",
            "Apache-2.0 package; source data retain provider terms",
        ),
        source(
            "SRC_V10_ENERGY_DONOR",
            "Philippines MUIO project",
            "Philippines v10 donor energy system",
            "v10 inherited into v12",
            "2020-2053",
            "Philippines",
            "Historical v10 energy representation retained in the v12 MUIO archive",
            "model-native",
            "muio/Philippines_v12_v12.0.0_MUIO.zip; preservation counts in diagnostics/v12_hybrid_audit.json",
            f"{PHL_REPO}/blob/{PHL_COMMIT}/Philippines_v12_CLEWs_build/diagnostics/v12_hybrid_audit.json",
            "Apache-2.0 package; original data retain provider terms",
        ),
        source(
            "SRC_V10_MODEL_FIXES",
            "MUIOGO Philippines case history",
            "Model fixes — 17 July 2026",
            MUIOGO_COMMIT,
            "v10 fixes recorded 2026-07-17",
            "Philippines",
            "PM2.5, transport, orphan-technology and policy-constraint corrections",
            "model-native; individual sections state converted units",
            "WebAPP/DataStorage/Philippines_v10/MODEL_FIXES_2026-07-17.md, Fixes 1-6",
            f"{MUIOGO_REPO}/blob/{MUIOGO_COMMIT}/WebAPP/DataStorage/Philippines_v10/MODEL_FIXES_2026-07-17.md",
            "MUIOGO repository license",
        ),
        source(
            "SRC_ENV_ARTIFACTS",
            "Philippines v12 build",
            "Environmental accounting artifacts",
            PHL_COMMIT,
            "Base and PEP saved runs, 2026-07-25 to 2026-07-26",
            "Philippines",
            "Land terminal, water reporting residuals and native emissions",
            "10^3 km2, 10^9 m3 and MT",
            "diagnostics/environmental_accounting/ and the ENV_LAND / diagnostic MUIO archives named in README.md",
            f"{PHL_REPO}/tree/{PHL_COMMIT}/Philippines_v12_CLEWs_build/diagnostics/environmental_accounting",
            "Apache-2.0 package",
        ),
        source(
            "SRC_ENV_METHOD_RECORD",
            "Philippines v12 build",
            "Environmental accounting calculation note",
            PHL_COMMIT,
            "implementation recorded 2026-07-25 to 2026-07-26",
            "Philippines",
            "Accounting boundary, formulas, exactness tests and reporting-only fallback",
            "method",
            "data_sources/calculation_notes/ENVIRONMENTAL_ACCOUNTING.md",
            f"{PHL_REPO}/blob/{PHL_COMMIT}/Philippines_v12_CLEWs_build/data_sources/calculation_notes/ENVIRONMENTAL_ACCOUNTING.md",
            "Apache-2.0 package",
        ),
    ]


def assumption_rows() -> List[Dict[str, str]]:
    return [
        assumption(
            "ASM_LAW_TOMATO_PROXY",
            "Vegetables are represented by the GAEZ tomato proxy.",
            "TOM",
            "GAEZ crop code",
            "SRC_CROP_CODE_MAPPING;SRC_GAEZ_V4",
        ),
        assumption(
            "ASM_LAW_OTHER_AGGREGATION",
            "Selected crops outside rice, coconuts, maize, vegetables and sugar cane are aggregated as OTH.",
            "OTH",
            "model crop group",
            "SRC_CROP_CODE_MAPPING;SRC_PHL_V12_REPOSITORY",
        ),
        assumption(
            "ASM_LAW_SSP2_GROWTH",
            "Crop-output demand after 2020 grows only with the retained SSP2 population index.",
            "population_y / population_2020",
            "relative population index (2020=1)",
            "SRC_PHL_V12_REPOSITORY",
        ),
        assumption(
            "ASM_LAW_POOLED_WATER",
            "All irrigated crops draw from one pooled agricultural-water commodity.",
            "1",
            "pooled AGRWATPHL commodity",
            "SRC_CLEWS_GLOBAL_PINNED;SRC_CLEWSY_PINNED",
        ),
        assumption(
            "ASM_LAW_NO_DIRECT_LIQUID",
            "Direct on-farm liquid fuel is not assigned to individual crop technologies.",
            "0",
            "PJ direct liquid fuel per crop-technology activity",
            "SRC_PHL_V12_REPOSITORY",
        ),
        assumption(
            "ASM_ENE_DONOR_PRESERVATION",
            "The v10 energy formulation is inherited as the donor system.",
            "Philippines_v10",
            "donor model version",
            "SRC_V10_ENERGY_DONOR;SRC_V10_MODEL_FIXES",
        ),
        assumption(
            "ASM_ENV_ARCHITECTURE",
            "ENV_LAND is enforced in-model in the derived case while ENV_WATER remains reporting-only.",
            "ENV_LAND=in-model;ENV_WATER=reporting-only",
            "accounting architecture",
            "SRC_ENV_ARTIFACTS;SRC_ENV_METHOD_RECORD",
        ),
        assumption(
            "ASM_ENV_COMMODITY_TOLERANCE",
            "Commodity-result reconciliation accepts the source CSV rounding tolerance.",
            "0.002",
            "commodity unit",
            "SRC_ENV_ARTIFACTS;SRC_ENV_METHOD_RECORD",
        ),
        assumption(
            "ASM_ENV_LAND_TOLERANCE",
            "Land terminal/source closure accepts the source CSV rounding tolerance.",
            "0.005",
            "10^3 km2",
            "SRC_ENV_ARTIFACTS;SRC_ENV_METHOD_RECORD",
        ),
        assumption(
            "ASM_ENV_STOCK_FLOW_TOLERANCE",
            "Parallel-stock flow aggregation accepts accumulated source CSV rounding.",
            "0.05",
            "10^3 km2",
            "SRC_ENV_ARTIFACTS;SRC_ENV_METHOD_RECORD",
        ),
    ]


def calculation_rows() -> List[Dict[str, str]]:
    env_sources = "SRC_ENV_ARTIFACTS;SRC_ENV_METHOD_RECORD"
    env_assumptions = (
        "ASM_ENV_ARCHITECTURE;ASM_ENV_COMMODITY_TOLERANCE;"
        "ASM_ENV_LAND_TOLERANCE;ASM_ENV_STOCK_FLOW_TOLERANCE"
    )
    env_script_version = PHL_COMMIT
    return [
        calculation(
            "CALC_LAW_GROUNDWATER_ELECTRICITY",
            "electricity = groundwater delivered * 0.0173",
            "SRC_CLEWS_GLOBAL_PINNED;SRC_CLEWSY_PINNED",
            "ASM_LAW_POOLED_WATER",
            "",
            "groundwater delivered;0.0173",
            "10^9 m3;PJ/(10^9 m3)",
            "0.0173 * groundwater delivered",
            "PJ",
            "overrides/workflow/submodules/clewsy/src/build/clewsy.py",
            f"{CLEWSY_COMMIT} + patches/clewsy_changes.patch",
        ),
        calculation(
            "CALC_LAW_IRRIGATION_DEMAND",
            "agricultural water = irrigated crop-land activity * cluster/mode AGRWATPHL coefficient",
            "SRC_GAEZ_V4;SRC_PHL_GEOSPATIAL_SUMMARIES;SRC_CLEWSY_PINNED",
            "ASM_LAW_POOLED_WATER",
            "CALC_LAW_CLUSTER_COEFFICIENTS",
            "crop-land activity;cluster/mode water coefficient",
            "10^3 km2;10^9 m3 per 10^3 km2",
            "row-specific AGRWATPHL demand in InputActivityRatio.csv",
            "10^9 m3",
            "overrides/workflow/submodules/clewsy/src/build/clewsy.py",
            f"{CLEWSY_COMMIT} + patches/clewsy_changes.patch",
        ),
        calculation(
            "CALC_LAW_CLUSTER_COEFFICIENTS",
            "cluster coefficient = arithmetic mean of retained GAEZ raster values assigned to each cluster, with documented nearest-covered-cell fill for missing island pixels",
            "SRC_GAEZ_V4;SRC_GADM41_PHL0;SRC_CLEWS_GAEZ_PINNED",
            "",
            "",
            "GAEZ yld/cwd/evt/precipitation/LCType pixels;8 clusters",
            "raw raster units;cluster identifier",
            "geospatial/summary_stats cluster means and converted clewsy coefficients",
            "parameter-specific model units",
            "overrides/workflow/submodules/CLEWs_GAEZ/GAEZ_Processing/libs/spatial_clustering.py",
            f"{CLEWS_GAEZ_COMMIT} + patches/CLEWs_GAEZ_changes.patch",
        ),
        calculation(
            "CALC_LAW_CROP_DEMAND_GROWTH",
            "demand_y = demand_2020 * SSP2_population_y / SSP2_population_2020",
            "SRC_FAOSTAT_2020;SRC_PHL_V12_REPOSITORY",
            "ASM_LAW_SSP2_GROWTH",
            "",
            "2020 crop production anchor;retained SSP2 relative population series",
            "Mt crop;relative index",
            "row-specific annual crop demand in SpecifiedAnnualDemand.csv",
            "Mt crop",
            "overrides/workflow/submodules/clewsy/src/build/clewsy.py",
            f"{CLEWSY_COMMIT} + patches/clewsy_changes.patch",
        ),
        calculation(
            "CALC_ENV_WATER_VAPOR",
            "production(PHL_WTR_EVT) - ordinary use(PHL_WTR_EVT)",
            env_sources,
            "ASM_ENV_ARCHITECTURE;ASM_ENV_COMMODITY_TOLERANCE",
            "",
            "saved production;ordinary use",
            "10^9 m3;10^9 m3",
            "ENV_WATER mode 1",
            "10^9 m3",
            "scripts/report_environmental_accounting.py",
            env_script_version,
        ),
        calculation(
            "CALC_ENV_GROUNDWATER_REMAINING",
            "production(PHL_WTR_GWT) - ordinary use(PHL_WTR_GWT)",
            env_sources,
            "ASM_ENV_ARCHITECTURE;ASM_ENV_COMMODITY_TOLERANCE",
            "",
            "saved production;ordinary use",
            "10^9 m3;10^9 m3",
            "ENV_WATER mode 2",
            "10^9 m3",
            "scripts/report_environmental_accounting.py",
            env_script_version,
        ),
        calculation(
            "CALC_ENV_SURFACE_WATER_REMAINING",
            "production(PHL_WTR_SUR) - ordinary use(PHL_WTR_SUR)",
            env_sources,
            "ASM_ENV_ARCHITECTURE;ASM_ENV_COMMODITY_TOLERANCE",
            "",
            "saved production;ordinary use",
            "10^9 m3;10^9 m3",
            "ENV_WATER mode 3",
            "10^9 m3",
            "scripts/report_environmental_accounting.py",
            env_script_version,
        ),
        calculation(
            "CALC_ENV_LIQUID_WATER_REMAINING",
            "ENV_WATER mode 2 + ENV_WATER mode 3",
            env_sources,
            "ASM_ENV_ARCHITECTURE;ASM_ENV_COMMODITY_TOLERANCE",
            "CALC_ENV_GROUNDWATER_REMAINING;CALC_ENV_SURFACE_WATER_REMAINING",
            "groundwater remaining;surface-water remaining",
            "10^9 m3;10^9 m3",
            "combined modeled raw liquid-water remaining",
            "10^9 m3",
            "scripts/report_environmental_accounting.py",
            env_script_version,
        ),
        calculation(
            "CALC_ENV_NONCROP_LAND",
            "source land activity * parallel output ratio 1 = matching ENV_LAND stock use",
            env_sources,
            env_assumptions,
            "",
            "six non-crop land activities;parallel OAR=1",
            "10^3 km2;dimensionless",
            "ENV_LAND modes 1-6",
            "10^3 km2",
            "scripts/generate_environmental_land_case.py",
            env_script_version,
        ),
        calculation(
            "CALC_ENV_CROPLAND",
            "sum of 24 crop-land option activities * parallel output ratio 1",
            env_sources,
            env_assumptions,
            "",
            "24 crop-land activities;parallel OAR=1",
            "10^3 km2;dimensionless",
            "ENV_LAND mode 7",
            "10^3 km2",
            "scripts/generate_environmental_land_case.py",
            env_script_version,
        ),
        calculation(
            "CALC_ENV_UNALLOCATED_LAND",
            "production(PHL_LND) - ordinary use(PHL_LND)",
            env_sources,
            env_assumptions,
            "",
            "MINLNDTOT production;original land use",
            "10^3 km2;10^3 km2",
            "ENV_LAND mode 8",
            "10^3 km2",
            "scripts/generate_environmental_land_case.py",
            env_script_version,
        ),
        calculation(
            "CALC_ENV_NATIVE_EMISSIONS",
            "sum AnnualTechnologyEmission over technologies by region, emission and year",
            env_sources,
            "ASM_ENV_ARCHITECTURE",
            "",
            "native AnnualTechnologyEmission rows",
            "MT",
            "annual CO2e and PM2_5 totals",
            "MT",
            "scripts/report_environmental_accounting.py",
            env_script_version,
        ),
        calculation(
            "CALC_ENV_LAND_CLOSURE",
            "TotalTechnologyAnnualActivity(MINLNDTOT) - TotalTechnologyAnnualActivity(ENV_LAND) = 0",
            env_sources,
            env_assumptions,
            "CALC_ENV_NONCROP_LAND;CALC_ENV_CROPLAND;CALC_ENV_UNALLOCATED_LAND",
            "land supply activity;ENV_LAND activity",
            "10^3 km2;10^3 km2",
            "0",
            "10^3 km2",
            "scripts/validate_environmental_land_case.py",
            env_script_version,
        ),
    ]


def manual_map_rows() -> List[Dict[str, str]]:
    config_file = "config/config.yaml"
    rows = [
        manual_map(
            "MAP_CONFIG_IDENTITY",
            config_file,
            "scenario/country/geographic_scope",
            "Philippines;PHL",
            "",
            "2020-2053",
            "scenario=PhilippinesV12Raw;country_full_name=Philippines;geographic_scope=[PHL]",
            "configuration",
            "SRC_PHL_V12_REPOSITORY;SRC_CLEWS_GLOBAL_PINNED",
        ),
        manual_map(
            "MAP_CONFIG_HORIZON",
            config_file,
            "startYear/endYear",
            "national model",
            "",
            "2020-2053",
            "startYear=2020;endYear=2053",
            "calendar year",
            "SRC_PHL_V12_REPOSITORY;SRC_CLEWS_GLOBAL_PINNED",
        ),
        manual_map(
            "MAP_CONFIG_SEASONS",
            config_file,
            "seasons/timeslices/dayparts",
            "Philippines",
            "",
            "all",
            "S1=June-November;S2=December-May;D1=hours 1-12;D2=hours 13-24",
            "calendar months and hours",
            "SRC_PAGASA_SEASONS;SRC_PHL_V12_REPOSITORY",
        ),
        manual_map(
            "MAP_CONFIG_TIMEZONE",
            config_file,
            "timeshift",
            "Philippines",
            "",
            "all",
            "8",
            "hours from UTC",
            "SRC_PHL_V12_REPOSITORY",
        ),
        manual_map(
            "MAP_CONFIG_SPATIAL",
            config_file,
            "admin_level/number_of_clusters/region_codes",
            "PHL",
            "",
            "all",
            "admin_level=0;number_of_clusters=8;region_code=PHLXX",
            "configuration",
            "SRC_GADM41_PHL0;SRC_PHL_V12_REPOSITORY;SRC_CLEWS_GAEZ_PINNED",
        ),
        manual_map(
            "MAP_CONFIG_CLIMATE",
            config_file,
            "rcp",
            "Philippines",
            "",
            "all",
            "RCP4.5",
            "scenario label",
            "SRC_GAEZ_V4;SRC_PHL_V12_REPOSITORY",
        ),
        manual_map(
            "MAP_CONFIG_STORAGE",
            config_file,
            "storage_existing/storage_planned",
            "Philippines",
            "",
            "all",
            "storage_existing=true;storage_planned=true",
            "boolean configuration",
            "SRC_PHL_V12_REPOSITORY;SRC_OSEMOSYS_GLOBAL_PINNED",
        ),
        manual_map(
            "MAP_CONFIG_RESERVE_TAGS",
            config_file,
            "reserve_margin_technologies",
            "BIO,CCG,COA,COG,CSP,GEO,HYD,OCG,OIL,OTH,PET,SPV,URN,WAS,WAV,WOF,WON",
            "",
            "all",
            "technology shares exactly as listed in config/config.yaml",
            "percent",
            "SRC_PHL_V12_REPOSITORY;SRC_OSEMOSYS_GLOBAL_PINNED",
        ),
        manual_map(
            "MAP_BOUNDARY_NO_CROP_LIQUID",
            "documentation/MODEL_STRUCTURE.md",
            "crop direct liquid-fuel boundary",
            "crop technologies",
            "",
            "2020-2053",
            "0",
            "PJ direct liquid fuel per crop-technology activity",
            "SRC_PHL_V12_REPOSITORY;ASM_LAW_NO_DIRECT_LIQUID",
        ),
        manual_map(
            "MAP_MUIO_V10_ENERGY_DONOR",
            "muio/Philippines_v12_v12.0.0_MUIO.zip",
            "inherited v10 energy representation",
            "power, fuels, transport, households, industry and other energy",
            "technology-specific",
            "2020-2053",
            "retained donor definitions and parameter records",
            "model-native; original row units remain incomplete",
            "SRC_V10_ENERGY_DONOR;SRC_V10_MODEL_FIXES;ASM_ENE_DONOR_PRESERVATION",
        ),
        manual_map(
            "MAP_MUIO_CROP_DEMAND_GROWTH",
            "muio/Philippines_v12_v12.0.0_MUIO.zip",
            "SpecifiedAnnualDemand",
            "crop-output demand records in Philippines_v12/RYC.json",
            "",
            "2020-2053",
            "demand_2020 * SSP2_population_y / SSP2_population_2020",
            "Mt crop",
            (
                "SRC_PHL_V12_REPOSITORY;SRC_FAOSTAT_2020;"
                "ASM_LAW_SSP2_GROWTH;CALC_LAW_CROP_DEMAND_GROWTH"
            ),
        ),
        manual_map(
            "MAP_ENV_ACCOUNTING",
            "muio/Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC_v12.0.0_MUIO.zip",
            "ENV_LAND/ENV_WATER/native emissions",
            "derived environmental-accounting case",
            "ENV_LAND 1-8;ENV_WATER 1-3",
            "2020-2053",
            "exact land terminal; reporting-only water residual; native emissions",
            "10^3 km2;10^9 m3;MT",
            (
                "SRC_ENV_ARTIFACTS;SRC_ENV_METHOD_RECORD;ASM_ENV_ARCHITECTURE;"
                "CALC_ENV_WATER_VAPOR;CALC_ENV_GROUNDWATER_REMAINING;"
                "CALC_ENV_SURFACE_WATER_REMAINING;CALC_ENV_LIQUID_WATER_REMAINING;"
                "CALC_ENV_NONCROP_LAND;CALC_ENV_CROPLAND;"
                "CALC_ENV_UNALLOCATED_LAND;CALC_ENV_NATIVE_EMISSIONS;"
                "CALC_ENV_LAND_CLOSURE"
            ),
        ),
    ]
    return rows


def gap_rows() -> List[Dict[str, str]]:
    items = [
        (
            "Inherited v10 energy row-level original bibliography",
            "The donor model and dated fixes survive, but the publications and calculation chain behind every inherited energy parameter were not retained.",
            "Recover the original v7-v10 source package or rebuild a row-level register from authoritative DOE, PSA and technology-cost datasets.",
        ),
        (
            "Original model units for technology-specific activity and capacity rows",
            "The raw CSVs retain values and OSeMOSYS coordinates, but several non-energy CLEWs technologies use land, water or crop activity units rather than GW/PJ conventions and no complete unit dictionary survived.",
            "Export the FUEL/TECHNOLOGY unit metadata from the exact pinned clewsy build and reconcile it against InputActivityRatio, OutputActivityRatio and CapacityToActivityUnit.",
        ),
        (
            "GAEZ v4 raw raster filenames, download query and checksums",
            "Cluster summaries and selected variables survive, but the raw cache/download manifest is absent and the pinned CLEWs GAEZ repository URL was not publicly retrievable on 2026-07-30.",
            "Recover the original raster cache or rerun the pinned workflow with a machine-readable GAEZ download manifest recording module, variable, crop, water regime, input level, climate period and SHA-256.",
        ),
        (
            "FAOSTAT 2020 exact export and item/element codes",
            "The crop names, year, domain and model mapping survive, but the original query export and its checksum do not.",
            "Download and retain the Philippines 2020 Crop and livestock products extract with item codes, Area harvested and Production element codes, flags, units and SHA-256.",
        ),
        (
            "SSP2 population input filename, vintage and variable",
            "The demand-growth rule and resulting values survive, but the exact bundled IIASA-WiC file/version and original access date were not retained.",
            "Recover the pinned workflow data bundle and record filename, scenario identifier, population unit, country code, years and checksum.",
        ),
        (
            "GADM 4.1 source archive checksum and original access date",
            "The extracted level-0 shapefile components survive, but the downloaded archive and acquisition log do not.",
            "Retain the original or re-downloaded GADM 4.1 PHL archive with provider metadata, access date and SHA-256, then verify geometry equality.",
        ),
        (
            "Original download access dates",
            "The package was consolidated on 2026-07-25 but did not retain acquisition logs for GADM, GAEZ, FAOSTAT or SSP2. The new SOURCES access_date records reconstruction access, not an invented historical date.",
            "Recover workflow logs, browser/download records or immutable source-package manifests.",
        ),
        (
            "Pinned CLEWs Global, CLEWs GAEZ and clewsy repository snapshots",
            "Commit hashes and local patches/overrides survive, but the recorded public URLs returned repository-not-found during reconstruction.",
            "Restore authorized repository access or publish immutable archives for the three exact commits and verify patches apply cleanly.",
        ),
    ]
    return [
        {
            "item": item,
            "why_absent": why_absent,
            "upgrade_source": upgrade_source,
        }
        for item, why_absent, upgrade_source in items
    ]


def write_reconstruction_note(
    root: Path,
    counts: Dict[str, int],
    before_hash: str,
    protected_file_count: int,
    excluded_fisheries: int,
    populated_files: int,
) -> None:
    note = root / "data_sources" / "calculation_notes" / (
        "PROVENANCE_RECONSTRUCTION_2026-07-30.md"
    )
    note.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Non-Fisheries provenance reconstruction — 30 July 2026

## Scope

This migration converts the active Philippines v12 provenance records to the
canonical six-ledger schema. Fisheries is explicitly out of scope. Its legacy
files were neither interpreted nor changed.

## Evidence policy

- Each populated non-Fisheries raw-input CSV row has one exact `MODEL_MAP`
  record carrying the package-relative file, physical CSV line, coordinates,
  value and best recoverable model unit.
- The Philippines repository snapshot is the immediate source of every
  retained value. External sources are added only where the package or an
  authoritative provider supplies a defensible product/variable locator.
- Missing original files, queries, units, access dates and bibliographic
  links are recorded in `GAPS.csv`; no locator or date was invented.
- Existing legacy ledgers were copied to
  `documentation/history/provenance_legacy_2026-07-30/` before replacement.

## Mechanical checks

- Protected input files hashed: {protected_file_count}
- Protected input aggregate SHA-256 before and after:
  `{before_hash}`
- Populated raw-input CSV files mapped: {populated_files}
- Fisheries raw-input rows excluded: {excluded_fisheries}
- Canonical ledger rows:
"""
    for table in LEDGER_TABLES:
        text += f"  - `{table}`: {counts.get(table, 0)}\n"
    text += """
The reconstruction script aborts if any file under `model/inputs/` or
`config/` changes. Passing ledger validation proves schema, reference and raw
input-file coverage; it does not prove that unresolved historical citations
have been recovered.
"""
    note.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("package_root", type=Path)
    args = parser.parse_args()
    root = args.package_root.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Package root does not exist: {root}")

    before = protected_hashes(root)
    before_aggregate = aggregate_hash(before)

    legacy = root / "documentation" / "history" / (
        "provenance_legacy_2026-07-30"
    )
    legacy.mkdir(parents=True, exist_ok=True)
    for table in LEGACY_TABLES:
        source_path = root / "data_sources" / table
        destination = legacy / table
        if source_path.is_file() and not destination.exists():
            shutil.copy2(source_path, destination)

    counts: Dict[str, int] = {}
    counts["SOURCES.csv"] = write_table(root, "SOURCES.csv", source_rows())
    counts["ASSUMPTIONS.csv"] = write_table(
        root, "ASSUMPTIONS.csv", assumption_rows()
    )
    counts["CALCULATIONS.csv"] = write_table(
        root, "CALCULATIONS.csv", calculation_rows()
    )

    generated_maps, excluded_fisheries, populated_files = input_map_rows(root)
    all_maps = manual_map_rows() + generated_maps
    counts["MODEL_MAP.csv"] = write_table(root, "MODEL_MAP.csv", all_maps)
    counts["GAPS.csv"] = write_table(root, "GAPS.csv", gap_rows())

    change = blank_row("CHANGES.csv")
    change.update(
        {
            "change_id": "CHG_PROVENANCE_RECON_20260730",
            "date": str(date(2026, 7, 30)),
            "class": "A",
            "description": "Reconstructed canonical energy, land, water and environmental-accounting provenance ledgers without changing model or configuration inputs.",
            "model_objects": "SOURCES.csv;CALCULATIONS.csv;ASSUMPTIONS.csv;MODEL_MAP.csv;GAPS.csv;CHANGES.csv",
            "evidence_path": "calculation_notes/PROVENANCE_RECONSTRUCTION_2026-07-30.md",
            "map_rows_affected": "",
            "resolve_status": "objective_unchanged",
            "author": "Codex",
            "commit": PHL_COMMIT,
        }
    )
    counts["CHANGES.csv"] = write_table(root, "CHANGES.csv", [change])
    legacy_map = root / "data_sources" / "MODEL_DATA_MAP.csv"
    if legacy_map.is_file():
        legacy_map.unlink()

    write_reconstruction_note(
        root,
        counts,
        before_aggregate,
        len(before),
        excluded_fisheries,
        populated_files,
    )

    after = protected_hashes(root)
    if before != after:
        changed = sorted(
            {
                *[key for key in before if before.get(key) != after.get(key)],
                *[key for key in after if before.get(key) != after.get(key)],
            }
        )
        raise SystemExit(
            "Protected model/config inputs changed during reconstruction: "
            + ", ".join(changed)
        )

    report = {
        "package_root": str(root),
        "scope": "energy, land, water and environmental accounting",
        "base_commit": PHL_COMMIT,
        "protected_file_count": len(before),
        "protected_input_sha256": before_aggregate,
        "protected_files": before,
        "protected_inputs_unchanged": True,
        "populated_input_files": populated_files,
        "excluded_fisheries_input_rows": excluded_fisheries,
        "ledger_row_counts": counts,
        "legacy_snapshot": legacy.relative_to(root).as_posix(),
    }
    report_path = (
        root / "diagnostics" / "provenance_reconstruction_2026-07-30.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
