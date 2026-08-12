#!/usr/bin/env python3
"""Build the cumulative, self-contained Philippines v15 provenance ledger.

The inputs to this script are retained inside the v15 package.  It does not
read a live v12, v13, or v14 case.  The historical version labels identify
lineage only; every evidentiary path resolves inside Philippines_v15_CLEWs_build.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Iterable


PACKAGE = Path(__file__).resolve().parents[1]
LEDGER = PACKAGE / "data_sources"
BASE = LEDGER / "evidence" / "inherited_base"
BASE_LEDGER = BASE / "ledger_snapshot"
STOCK = LEDGER / "evidence" / "stock_turnover"
STOCK_TABLES = STOCK / "legacy_tables"
STOCK_DOCS = STOCK / "documentation"
DELTA = LEDGER / "history" / "water_delta_2026-08-04"
ARCHIVE = PACKAGE / "muio" / "Philippines_v15_v15.0.0_MUIO.zip"
ARCHIVE_REL = "muio/Philippines_v15_v15.0.0_MUIO.zip"
MANIFEST = LEDGER / "evidence" / "RETAINED_EVIDENCE_MANIFEST.csv"
ARCHIVE_MANIFEST = LEDGER / "evidence" / "CURRENT_MODEL_ARCHIVE_MANIFEST.csv"

SOURCE_FIELDS = [
    "source_id", "provider", "product", "edition", "reference_period",
    "geography", "variable", "source_unit", "exact_locator", "url",
    "access_date", "license", "sha256", "local_file", "notes",
]
CALC_FIELDS = [
    "calculation_id", "formula", "source_ids", "assumption_ids",
    "input_calculation_ids", "input_values", "input_units", "output_value",
    "output_unit", "script_path", "script_version", "notes",
]
ASSUMPTION_FIELDS = [
    "assumption_id", "statement", "central_value", "unit",
    "evidence_source_ids", "lower_bound", "upper_bound", "rationale", "notes",
]
MAP_FIELDS = [
    "map_id", "model_file", "parameter", "entity", "mode", "scenario",
    "years", "value_or_expression", "model_unit", "evidence_ids",
    "superseded_by", "evidence_type", "notes",
]
GAP_FIELDS = ["item", "why_absent", "upgrade_source", "priority", "notes"]
CHANGE_FIELDS = [
    "change_id", "date", "class", "description", "model_objects",
    "evidence_path", "map_rows_affected", "resolve_status", "author", "commit",
    "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local_sha(relative: str) -> str:
    return sha256(LEDGER / relative)


def unique(rows: Iterable[dict[str, str]], key: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        value = row.get(key, "")
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(row)
    return result


def split_ids(value: str) -> list[str]:
    return [part for part in re.split(r"[;,\s]+", value or "") if part]


def join_ids(values: Iterable[str]) -> str:
    return ";".join(dict.fromkeys(value for value in values if value))


def normalize_base_source(source_id: str) -> str:
    if source_id == "SRC_PHL_V12_REPOSITORY":
        return "SRC_PHL_INHERITED_BASE_SNAPSHOT"
    return source_id


SPECIAL_STOCK_SOURCES = {
    "DS-MODEL-V13": "SRC_PHL_V13_CALIBRATION_RECORD",
    "DS-V13-BASE-CAPACITY": "SRC_PHL_V13_BASE_CAPACITY_RECORD",
    "DS-EDGAR-WB-V5": "SRC_PHL_V13_EDGAR_WORKBOOK_RECORD",
}


def normalize_stock_source(source_id: str) -> str:
    if source_id in SPECIAL_STOCK_SOURCES:
        return SPECIAL_STOCK_SOURCES[source_id]
    token = source_id.removeprefix("DS-").replace("-", "_")
    return f"SRC_PHL_V14_{token}"


def normalize_stock_assumption(assumption_id: str) -> str:
    token = assumption_id.removeprefix("AS-").replace("-", "_")
    return f"ASM_PHL_V14_{token}"


def normalize_stock_calculation(calculation_id: str) -> str:
    if calculation_id == "CAL-COOK-TURN":
        return "CALC_PHL_V14_TURN_HOU_COOK_TURN"
    token = calculation_id.removeprefix("CAL-").replace("-", "_")
    return f"CALC_PHL_V14_{token}"


def normalize_stock_map(map_id: str) -> str:
    token = map_id.removeprefix("MAP-").replace("-", "_")
    return f"MAP_PHL_V14_{token}"


def replace_id_list(value: str, replacement) -> str:
    return join_ids(replacement(item) for item in split_ids(value))


def evidence_path_for_base(model_file: str) -> str:
    if model_file == "config/config.yaml" or model_file.startswith("model/inputs/"):
        return model_file
    if model_file.startswith(("config/", "model/", "geospatial/", "overrides/", "patches/")):
        return f"evidence/inherited_base/build_snapshot/{model_file}"
    if model_file.startswith("documentation/"):
        return f"evidence/inherited_base/{model_file}"
    if model_file.startswith("muio/"):
        return ARCHIVE_REL
    return model_file


def write_manifests() -> None:
    evidence_root = LEDGER / "evidence"
    files = [
        path for path in sorted(evidence_root.rglob("*"))
        if path.is_file() and path not in {MANIFEST, ARCHIVE_MANIFEST}
    ]
    rows = []
    for path in files:
        relative = path.relative_to(LEDGER).as_posix()
        if "/inherited_base/" in f"/{relative}":
            role = "inherited base source, calculation, build, or validation evidence"
        elif "/stock_turnover/" in f"/{relative}":
            role = "v13 calibration or v14 stock-turnover evidence"
        else:
            role = "v15 water evidence"
        rows.append({
            "relative_path": relative,
            "size_bytes": str(path.stat().st_size),
            "sha256": sha256(path),
            "role": role,
        })
    write_csv(MANIFEST, ["relative_path", "size_bytes", "sha256", "role"], rows)

    with zipfile.ZipFile(ARCHIVE) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
    write_csv(
        ARCHIVE_MANIFEST,
        ["package_relative_path", "size_bytes", "sha256", "zip_member_count", "internal_root"],
        [{
            "package_relative_path": ARCHIVE_REL,
            "size_bytes": str(ARCHIVE.stat().st_size),
            "sha256": sha256(ARCHIVE),
            "zip_member_count": str(len(members)),
            "internal_root": "Philippines_v15/",
        }],
    )


def build_sources() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    base_sources = read_csv(BASE_LEDGER / "SOURCES.csv")
    for old in base_sources:
        row = {field: old.get(field, "") for field in SOURCE_FIELDS}
        row["source_id"] = normalize_base_source(old["source_id"])
        local_file = old.get("local_file", "") or ""
        if local_file.startswith("evidence/"):
            local_file = "evidence/inherited_base/external_sources/" + local_file.removeprefix("evidence/")
        row["local_file"] = local_file

        if row["source_id"] == "SRC_PHL_INHERITED_BASE_SNAPSHOT":
            row.update({
                "provider": "Philippines v15 retained evidence",
                "product": "Inherited base build snapshot and 68,624-row source map",
                "edition": "frozen in Philippines v15 on 2026-08-05",
                "exact_locator": "evidence/inherited_base/ contains the ledger snapshot, build inputs, geospatial outputs, calculations, source files, and validation evidence",
                "url": "",
                "local_file": "evidence/RETAINED_EVIDENCE_MANIFEST.csv",
                "notes": "This is an internal v15 evidence bundle, not a dependency on an installed earlier case.",
            })
        elif row["source_id"] in {
            "SRC_CLEWS_GLOBAL_PINNED", "SRC_CLEWS_GAEZ_PINNED",
            "SRC_CLEWSY_PINNED", "SRC_OSEMOSYS_GLOBAL_PINNED",
        }:
            row["exact_locator"] = "evidence/inherited_base/build_snapshot/config/upstream_versions.json; retained patches and overrides are in the same build snapshot"
            row["local_file"] = "evidence/inherited_base/build_snapshot/config/upstream_versions.json"
        elif row["source_id"] == "SRC_GADM41_PHL0":
            row["exact_locator"] = "evidence/inherited_base/build_snapshot/geospatial/boundary/gadm41_PHL_0.{shp,shx,dbf,prj}"
            row["local_file"] = "evidence/inherited_base/build_snapshot/geospatial/boundary/gadm41_PHL_0.shp"
        elif row["source_id"] == "SRC_CROP_CODE_MAPPING":
            row["exact_locator"] = "evidence/inherited_base/build_snapshot/overrides/workflow/submodules/CLEWs_GAEZ/GAEZ_Processing/Data/Crop_code.csv"
            row["local_file"] = row["exact_locator"]
            row["url"] = ""
        elif row["source_id"] == "SRC_PHL_GEOSPATIAL_SUMMARIES":
            row["exact_locator"] = "evidence/inherited_base/build_snapshot/geospatial/summary_stats/PHL_Parameter_byCluster_summary.csv and PHL_LandCover_byCluster_summary.csv"
            row["local_file"] = "evidence/inherited_base/build_snapshot/geospatial/summary_stats/PHL_Parameter_byCluster_summary.csv"
            row["url"] = ""
        elif row["source_id"] == "SRC_V10_ENERGY_DONOR":
            row["exact_locator"] = f"{ARCHIVE_REL}; inherited energy values are present in the current model; retained dated correction notes are under evidence/inherited_base/v10/"
            row["local_file"] = "evidence/CURRENT_MODEL_ARCHIVE_MANIFEST.csv"
            row["url"] = ""
            row["notes"] = "Current values are preserved, but the original row-level bibliography remains an explicit gap."
        elif row["source_id"] == "SRC_V10_MODEL_FIXES":
            row["exact_locator"] = "evidence/inherited_base/v10/MODEL_FIXES_2026-07-17.md"
            row["local_file"] = row["exact_locator"]
            row["url"] = ""
        elif row["source_id"] == "SRC_ENV_ARTIFACTS":
            row["exact_locator"] = "evidence/inherited_base/environmental_accounting/; solver-generated pivot backups are omitted because the final v15 archive retains the active source model"
            row["local_file"] = "evidence/inherited_base/environmental_accounting/2026-07-25_env_land_final/validation.json"
            row["url"] = ""
        elif row["source_id"] == "SRC_ENV_METHOD_RECORD":
            row["exact_locator"] = "evidence/inherited_base/calculation_notes/ENVIRONMENTAL_ACCOUNTING.md"
            row["local_file"] = row["exact_locator"]
            row["url"] = ""

        if row["local_file"]:
            row["sha256"] = local_sha(row["local_file"])
        rows.append(row)

    delta_sources = read_csv(DELTA / "SOURCES.csv")
    for old in delta_sources:
        row = {field: old.get(field, "") for field in SOURCE_FIELDS}
        if row["source_id"] == "SRC_PHL_V14_CASE":
            row.update({
                "provider": "Philippines v15 retained evidence",
                "product": "Retained v13 calibration and v14 stock-turnover record",
                "edition": "records frozen in v15 on 2026-08-05",
                "variable": "Exact v13 calibration specification, v14 calculation and assumption tables, 3,253 cell changes, and validation records",
                "exact_locator": "evidence/stock_turnover/legacy_tables/ and evidence/stock_turnover/documentation/",
                "url": "",
                "local_file": "evidence/stock_turnover/documentation/stock_turnover_generation.json",
                "notes": "Historical label retained for compatibility; no live v14 folder or external version package is required.",
            })
        elif row["source_id"] == "SRC_CLEWS_PHL_GEOSPATIAL":
            row.update({
                "provider": "Philippines v15 retained evidence",
                "product": "Retained Philippines geospatial build outputs",
                "edition": "frozen inside v15 on 2026-08-05",
                "exact_locator": "evidence/inherited_base/build_snapshot/geospatial/ contains the national boundary, cluster image, and summary tables",
                "url": "",
                "local_file": "evidence/inherited_base/build_snapshot/geospatial/summary_stats/PHL_Parameter_byCluster_summary.csv",
                "notes": "Internal v15 evidence copy. Cell-level cluster membership geometry remains an explicit gap.",
            })
        if row.get("local_file"):
            row["sha256"] = local_sha(row["local_file"])
        rows.append(row)

    stock_source_rows = read_csv(STOCK_TABLES / "DATA_SOURCE_REGISTER.csv")
    for old in stock_source_rows:
        source_id = normalize_stock_source(old["SourceId"])
        row = {
            "source_id": source_id,
            "provider": old["Institution"],
            "product": old["Title"],
            "edition": old["ReferenceDate"],
            "reference_period": old["ReferenceDate"],
            "geography": old["Geography"],
            "variable": old["Variables"],
            "source_unit": "model-native or publication-specific; see retained register and calculations",
            "exact_locator": f"evidence/stock_turnover/legacy_tables/DATA_SOURCE_REGISTER.csv row {old['SourceId']}; {old['ModelUse']}",
            "url": old["URL"],
            "access_date": old["RetrievedDate"],
            "license": old["License"],
            "sha256": "",
            "local_file": "",
            "notes": f"Quality: {old['Quality']}. {old['Notes']}",
        }
        if old["SourceId"] == "DS-MODEL-V13":
            row.update({
                "provider": "Philippines v15 retained evidence",
                "product": "v13 calibration generation record",
                "exact_locator": "evidence/stock_turnover/documentation/calibration_generation.json and MODEL_FIXES_2026-07-27.md",
                "url": "",
                "local_file": "evidence/stock_turnover/documentation/calibration_generation.json",
            })
        elif old["SourceId"] == "DS-V13-BASE-CAPACITY":
            row.update({
                "provider": "Philippines v15 retained evidence",
                "product": "v13 BASE capacity extraction retained inside v14 generation record",
                "exact_locator": "evidence/stock_turnover/documentation/stock_turnover_generation.json keys validated_v13_baseline_capacity_source and stock_groups",
                "url": "",
                "local_file": "evidence/stock_turnover/documentation/stock_turnover_generation.json",
            })
        elif old["SourceId"] == "DS-EDGAR-WB-V5":
            row.update({
                "provider": "Philippines v15 retained evidence",
                "product": "Retained record of EDGAR PM2.5 calibration workbook v5",
                "exact_locator": "evidence/stock_turnover/documentation/calibration_generation.json records workbook hash, factors, formulas, and selected values; original workbook bytes were not retained",
                "url": "",
                "local_file": "evidence/stock_turnover/documentation/calibration_generation.json",
            })
        if row["local_file"]:
            row["sha256"] = local_sha(row["local_file"])
        rows.append(row)

    extra = [
        ("SRC_PHL_V14_PARAMETER_CHANGE_LOG", "v14 cell-level parameter change log", "evidence/stock_turnover/legacy_tables/PARAMETER_CHANGE_LOG.csv", "3,253 exact before/after cells with source, calculation, and assumption IDs"),
        ("SRC_PHL_V14_MODEL_DATA_MAP", "v14 stock-turnover model-data map", "evidence/stock_turnover/legacy_tables/MODEL_DATA_MAP.csv", "33 implemented source-to-model mappings"),
        ("SRC_PHL_V13_FIXES_RECORD", "v13 calibration change record", "evidence/stock_turnover/documentation/MODEL_FIXES_2026-07-27.md", "PM2.5 and CO2e calibration scope, values, formulas, and limitations"),
        ("SRC_PHL_V13_VALIDATION_RECORD", "v13 calibration validation record", "evidence/stock_turnover/documentation/VALIDATION_2026-07-27.md", "solver status, scenarios, comparisons, and limitations"),
        ("SRC_PHL_V14_FIXES_RECORD", "v14 stock-turnover change record", "evidence/stock_turnover/documentation/MODEL_FIXES_V14_2026-07-27.md", "stock initialization, turnover, adoption, and structural corrections"),
        ("SRC_PHL_V14_VALIDATION_RECORD", "v14 stock-turnover validation record", "evidence/stock_turnover/documentation/validation_results.json", "machine-readable solve and regression validation"),
        ("SRC_PHL_V15_MODEL_ARCHIVE", "Philippines v15 portable source-model archive manifest", "evidence/CURRENT_MODEL_ARCHIVE_MANIFEST.csv", "hash, size, member count, and internal root for the current v15 model archive"),
        ("SRC_PHL_V15_RETAINED_EVIDENCE", "Philippines v15 retained-evidence manifest", "evidence/RETAINED_EVIDENCE_MANIFEST.csv", "path, size, role, and SHA-256 for every retained evidence file"),
    ]
    for source_id, product, local_file, variable in extra:
        rows.append({
            "source_id": source_id,
            "provider": "Philippines v15 retained evidence",
            "product": product,
            "edition": "2026-08-05 cumulative package",
            "reference_period": "2020-2053 model lineage",
            "geography": "Philippines",
            "variable": variable,
            "source_unit": "record",
            "exact_locator": local_file,
            "url": "",
            "access_date": "2026-08-05",
            "license": "MUIOGO repository terms; third-party evidence retains provider terms",
            "sha256": local_sha(local_file),
            "local_file": local_file,
            "notes": "Retained inside the canonical v15 package.",
        })
    return unique(rows, "source_id")


def stock_links() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    calc_sources: dict[str, set[str]] = {}
    assumption_sources: dict[str, set[str]] = {}
    for filename in ("MODEL_DATA_MAP.csv", "PARAMETER_CHANGE_LOG.csv"):
        for row in read_csv(STOCK_TABLES / filename):
            sources = set(split_ids(row.get("SourceIds", "")))
            for calc in split_ids(row.get("CalculationIds", "")):
                calc_sources.setdefault(calc, set()).update(sources)
            for assumption in split_ids(row.get("AssumptionIds", "")):
                assumption_sources.setdefault(assumption, set()).update(sources)
    return calc_sources, assumption_sources


def build_calculations() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for old in read_csv(BASE_LEDGER / "CALCULATIONS.csv"):
        row = {field: old.get(field, "") for field in CALC_FIELDS}
        row["source_ids"] = replace_id_list(old.get("source_ids", ""), normalize_base_source)
        rows.append(row)

    calc_sources, _ = stock_links()
    for old in read_csv(STOCK_TABLES / "CALCULATIONS.csv"):
        source_tokens = set(re.findall(r"DS-[A-Z0-9-]+", old.get("Inputs", "")))
        source_tokens.update(calc_sources.get(old["CalculationId"], set()))
        rows.append({
            "calculation_id": normalize_stock_calculation(old["CalculationId"]),
            "formula": old["Formula"] or old["Question"],
            "source_ids": join_ids(normalize_stock_source(item) for item in sorted(source_tokens)) or "SRC_PHL_V14_MODEL_DATA_MAP",
            "assumption_ids": "",
            "input_calculation_ids": "",
            "input_values": old["Inputs"],
            "input_units": "model-native or source-specific; see retained v14 calculation row",
            "output_value": old["Output"] or "implemented result documented in retained v14 calculation row",
            "output_unit": "model-native or source-specific; see retained v14 calculation row",
            "script_path": "",
            "script_version": "",
            "notes": f"Question: {old['Question']} Implementation: {old['Implementation']} Checks: {old['Checks']}",
        })

    rows.extend([
        {
            "calculation_id": "CALC_PHL_V13_PM25_UNIT_CONVERSION",
            "formula": "PM2.5_kt = PM2.5_MTon * 1000; penalties_per_kt = penalties_per_MTon / 1000",
            "source_ids": "SRC_PHL_V13_CALIBRATION_RECORD;SRC_PHL_V13_FIXES_RECORD",
            "assumption_ids": "", "input_calculation_ids": "",
            "input_values": "all inherited PM2.5 EAR, EACR, AEL, MPEL, and penalty records",
            "input_units": "MTon and cost/MTon", "output_value": "coherent PM2.5 kt parameterization",
            "output_unit": "kt and cost/kt", "script_path": "", "script_version": "",
            "notes": "Exact fingerprints and validation are retained in the v13 generation and validation records.",
        },
        {
            "calculation_id": "CALC_PHL_V13_PM25_FACTOR_INSTALL",
            "formula": "EAR[t,y] = selected workbook-v5 factor for technology t; constant for 2020-2053",
            "source_ids": "SRC_PHL_V13_EDGAR_WORKBOOK_RECORD;SRC_PHL_V13_CALIBRATION_RECORD",
            "assumption_ids": "ASM_PHL_V13_PM25_FACTOR_SELECTION", "input_calculation_ids": "CALC_PHL_V13_PM25_UNIT_CONVERSION",
            "input_values": "18 exact technology factors retained in calibration_generation.json",
            "input_units": "kt per activity unit", "output_value": "18 installed PM2.5 factor series",
            "output_unit": "kt per activity unit", "script_path": "", "script_version": "",
            "notes": "Workbook bytes are missing; its hash and every selected value survive in the retained record.",
        },
        {
            "calculation_id": "CALC_PHL_V13_COOK_OIL_CO2_CORRECTION",
            "formula": "0.0631 - 0.0733 = -0.0102",
            "source_ids": "SRC_PHL_V13_CALIBRATION_RECORD;SRC_PHL_V13_FIXES_RECORD",
            "assumption_ids": "", "input_calculation_ids": "",
            "input_values": "IPCC LPG default 0.0631; inherited processed-oil upstream charge 0.0733",
            "input_units": "MTon CO2e/PJ", "output_value": "-0.0102",
            "output_unit": "MTon CO2e/PJ", "script_path": "", "script_version": "", "notes": "Nets the upstream charge; not a second combustion charge.",
        },
        {
            "calculation_id": "CALC_PHL_V13_BLUE_HYDROGEN_CO2",
            "formula": "EAR_CO2e[y] = -0.70 * IAR_NG[y] * 0.055",
            "source_ids": "SRC_PHL_V13_CALIBRATION_RECORD;SRC_PHL_V13_FIXES_RECORD",
            "assumption_ids": "ASM_PHL_V13_BLUE_H2_CAPTURE", "input_calculation_ids": "",
            "input_values": "annual inherited natural-gas IAR; capture=0.70; upstream factor=0.055",
            "input_units": "PJ/PJ; fraction; MTon/PJ", "output_value": "annual series -0.055797101437 in 2020 to -0.0538461538615 in 2053",
            "output_unit": "MTon CO2e per activity unit", "script_path": "", "script_version": "", "notes": "All 34 annual values survive in calibration_generation.json.",
        },
    ])

    inherited = "SRC_PHL_INHERITED_BASE_SNAPSHOT;SRC_GAEZ_PRC_RASTER;SRC_PHL_GEOSPATIAL_SUMMARIES;SRC_PHL_V14_CASE"
    for old in read_csv(DELTA / "CALCULATIONS.csv"):
        row = {field: old.get(field, "") for field in CALC_FIELDS}
        row["source_ids"] = old.get("source_ids", "").replace("SRC_PHL_V14_CASE", inherited)
        rows.append(row)
    return unique(rows, "calculation_id")


def build_assumptions() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for old in read_csv(BASE_LEDGER / "ASSUMPTIONS.csv"):
        row = {field: old.get(field, "") for field in ASSUMPTION_FIELDS}
        row["evidence_source_ids"] = replace_id_list(old.get("evidence_source_ids", ""), normalize_base_source)
        rows.append(row)

    _, assumption_sources = stock_links()
    for old in read_csv(STOCK_TABLES / "ASSUMPTIONS.csv"):
        source_ids = assumption_sources.get(old["AssumptionId"], set())
        rows.append({
            "assumption_id": normalize_stock_assumption(old["AssumptionId"]),
            "statement": old["Statement"],
            "central_value": old["Status"],
            "unit": "modeling rule/status",
            "evidence_source_ids": join_ids(normalize_stock_source(item) for item in sorted(source_ids)) or "SRC_PHL_V14_MODEL_DATA_MAP",
            "lower_bound": "", "upper_bound": "", "rationale": old["Rationale"],
            "notes": f"Sector: {old['Sector']}. Affects: {old['Affects']}. Replacement evidence: {old['ReplacementEvidence']}",
        })

    rows.extend([
        {
            "assumption_id": "ASM_PHL_V13_PM25_FACTOR_SELECTION",
            "statement": "Use the workbook-v5 recommended PM2.5 technology factors, with EDGAR as a benchmark rather than unquestioned national ground truth.",
            "central_value": "workbook-v5 selected factors", "unit": "calibration choice",
            "evidence_source_ids": "SRC_PHL_V13_EDGAR_WORKBOOK_RECORD;SRC_PHL_V13_CALIBRATION_RECORD", "lower_bound": "", "upper_bound": "",
            "rationale": "The retained v13 record documents the provisional hierarchy and selected values.", "notes": "Power and navigation remain provisional.",
        },
        {
            "assumption_id": "ASM_PHL_V13_BLUE_H2_CAPTURE",
            "statement": "Blue hydrogen captures 70% of the CO2 associated with its natural-gas input.",
            "central_value": "0.70", "unit": "fraction",
            "evidence_source_ids": "SRC_PHL_V13_CALIBRATION_RECORD", "lower_bound": "", "upper_bound": "",
            "rationale": "Exact implementation and annual values are retained in the calibration record.", "notes": "A source-specific capture study was not retained.",
        },
    ])

    inherited = "SRC_PHL_INHERITED_BASE_SNAPSHOT SRC_PHL_V14_CASE"
    for old in read_csv(DELTA / "ASSUMPTIONS.csv"):
        row = {field: old.get(field, "") for field in ASSUMPTION_FIELDS}
        row["evidence_source_ids"] = old.get("evidence_source_ids", "").replace("SRC_PHL_V14_CASE", inherited)
        rows.append(row)
    return unique(rows, "assumption_id")


def build_v13_maps() -> list[dict[str, str]]:
    generation = json.loads((STOCK_DOCS / "calibration_generation.json").read_text(encoding="utf-8"))
    rows: list[dict[str, str]] = []
    for index, factor in enumerate(generation["calibration"]["pm25"]["updated_rows"], start=1):
        rows.append({
            "map_id": f"MAP_PHL_V13_PM25_{index:02d}", "model_file": ARCHIVE_REL,
            "parameter": "Philippines_v15/RYTEM.json:EmissionActivityRatio",
            "entity": f"{factor['technology']};EMI_PM25", "mode": str(factor["mode"]),
            "scenario": factor["scenario"], "years": "2020-2053",
            "value_or_expression": str(factor["factor_kt_per_activity"]),
            "model_unit": "kt PM2.5 per activity unit",
            "evidence_ids": "SRC_PHL_V13_CALIBRATION_RECORD;SRC_PHL_V13_EDGAR_WORKBOOK_RECORD;CALC_PHL_V13_PM25_FACTOR_INSTALL;ASM_PHL_V13_PM25_FACTOR_SELECTION",
            "superseded_by": "", "evidence_type": "", "notes": "Installed in v13 and retained in current v15 model archive.",
        })
    blue = generation["calibration"]["blue_hydrogen_co2e"]
    rows.append({
        "map_id": "MAP_PHL_V13_BLUE_H2_CO2", "model_file": ARCHIVE_REL,
        "parameter": "Philippines_v15/RYTEM.json:EmissionActivityRatio", "entity": "PHL_POW_BH2_NG;EMI_CO2e", "mode": "1", "scenario": "SC_0", "years": "2020-2053",
        "value_or_expression": json.dumps(blue, separators=(",", ":")), "model_unit": "MTon CO2e per activity unit",
        "evidence_ids": "SRC_PHL_V13_CALIBRATION_RECORD;CALC_PHL_V13_BLUE_HYDROGEN_CO2;ASM_PHL_V13_BLUE_H2_CAPTURE",
        "superseded_by": "", "evidence_type": "", "notes": "Exact 34-value annual series retained in the v13 generation record and current archive.",
    })
    rows.extend([
        {
            "map_id": "MAP_PHL_V13_COOK_OIL_CO2", "model_file": ARCHIVE_REL,
            "parameter": "Philippines_v15/RYTEM.json:EmissionActivityRatio", "entity": "PHL_HOU_COOK_OIL;EMI_CO2e", "mode": "1", "scenario": "SC_0", "years": "2020-2053",
            "value_or_expression": "-0.0102", "model_unit": "MTon CO2e/PJ",
            "evidence_ids": "SRC_PHL_V13_CALIBRATION_RECORD;CALC_PHL_V13_COOK_OIL_CO2_CORRECTION", "superseded_by": "", "evidence_type": "", "notes": "Retained in current model archive.",
        },
        {
            "map_id": "MAP_PHL_V13_PM25_UNIT_SYSTEM", "model_file": ARCHIVE_REL,
            "parameter": "Philippines_v15/genData.json, RYE.json, RE.json, and RYTEM.json:PM2.5 unit-linked records", "entity": "EMI_PM25", "mode": "", "scenario": "all", "years": "2020-2053",
            "value_or_expression": "MTon quantities * 1000; penalties / 1000; emission unit=kt", "model_unit": "kt and cost/kt",
            "evidence_ids": "SRC_PHL_V13_CALIBRATION_RECORD;SRC_PHL_V13_FIXES_RECORD;SRC_PHL_V13_VALIDATION_RECORD;CALC_PHL_V13_PM25_UNIT_CONVERSION", "superseded_by": "", "evidence_type": "", "notes": "Broad unit-system mapping supplements the exact technology factor rows.",
        },
    ])
    return rows


def build_maps() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for old in read_csv(BASE_LEDGER / "MODEL_MAP.csv"):
        row = {field: old.get(field, "") for field in MAP_FIELDS}
        row["model_file"] = evidence_path_for_base(old["model_file"])
        row["evidence_ids"] = replace_id_list(old.get("evidence_ids", ""), normalize_base_source)
        row["evidence_type"] = ""
        row["notes"] = "Retained inherited-base mapping. Later v13, v14, and v15 rows in this same table document every known override."
        rows.append(row)

    rows.extend(build_v13_maps())

    for old in read_csv(STOCK_TABLES / "MODEL_DATA_MAP.csv"):
        evidence = [normalize_stock_source(item) for item in split_ids(old["SourceIds"])]
        evidence += [normalize_stock_assumption(item) for item in split_ids(old["AssumptionIds"])]
        evidence += [normalize_stock_calculation(item) for item in split_ids(old["CalculationIds"])]
        evidence.append("SRC_PHL_V14_MODEL_DATA_MAP")
        rows.append({
            "map_id": normalize_stock_map(old["MapId"]), "model_file": ARCHIVE_REL,
            "parameter": old["Parameter"], "entity": old["ModelElement"], "mode": "",
            "scenario": "SC_0 and applicable inherited policy scenarios", "years": old["Years"],
            "value_or_expression": old["Meaning"], "model_unit": "model-native; exact cells and values are in the retained change log",
            "evidence_ids": join_ids(evidence), "superseded_by": "", "evidence_type": "",
            "notes": f"Sector: {old['Sector']}. Archive members: {old['File']}. Status: {old['Status']}. {old['Notes']}",
        })

    for index, old in enumerate(read_csv(STOCK_TABLES / "PARAMETER_CHANGE_LOG.csv"), start=1):
        evidence = [normalize_stock_source(item) for item in split_ids(old["SourceIds"])]
        evidence += [normalize_stock_assumption(item) for item in split_ids(old["AssumptionIds"])]
        evidence += [normalize_stock_calculation(item) for item in split_ids(old["CalculationIds"])]
        evidence.append("SRC_PHL_V14_PARAMETER_CHANGE_LOG")
        rows.append({
            "map_id": f"MAP_PHL_V14_CHANGE_{index:04d}", "model_file": ARCHIVE_REL,
            "parameter": f"Philippines_v15/{old['File']}:{old['Parameter']}", "entity": old["Element"], "mode": "",
            "scenario": old["Scenario"], "years": old["Year"], "value_or_expression": old["After"],
            "model_unit": "model-native; parameter-specific", "evidence_ids": join_ids(evidence),
            "superseded_by": "", "evidence_type": "",
            "notes": f"Before={old['Before']}. {old['Reason']}",
        })

    inherited = "SRC_PHL_INHERITED_BASE_SNAPSHOT SRC_PHL_V14_CASE SRC_PHL_V15_RETAINED_EVIDENCE"
    for old in read_csv(DELTA / "MODEL_MAP.csv"):
        row = {field: old.get(field, "") for field in MAP_FIELDS}
        member = old["model_file"]
        row["model_file"] = ARCHIVE_REL
        row["parameter"] = f"Philippines_v15/{member}:{old['parameter']}"
        row["evidence_ids"] = old.get("evidence_ids", "").replace("SRC_PHL_V14_CASE", inherited)
        row["evidence_ids"] = join_ids(split_ids(row["evidence_ids"]) + ["SRC_PHL_V15_MODEL_ARCHIVE"])
        row["evidence_type"] = ""
        row["notes"] = f"Archive member Philippines_v15/{member}. {old.get('notes', '')}"
        rows.append(row)

    rows.append({
        "map_id": "MAP_PHL_V15_CANONICAL_PACKAGE", "model_file": ARCHIVE_REL,
        "parameter": "complete current source-model package", "entity": "Philippines_v15", "mode": "all",
        "scenario": "all packaged scenarios", "years": "2020-2053",
        "value_or_expression": "The archive is the current model; inherited-base, v13, v14, and v15 provenance are all indexed in this ledger.",
        "model_unit": "package", "evidence_ids": "SRC_PHL_V15_MODEL_ARCHIVE;SRC_PHL_V15_RETAINED_EVIDENCE",
        "superseded_by": "", "evidence_type": "", "notes": "No earlier installed case or ledger is required to interpret this package.",
    })
    return unique(rows, "map_id")


def build_gaps() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for source in (BASE_LEDGER / "GAPS.csv", DELTA / "GAPS.csv"):
        for old in read_csv(source):
            row = {field: old.get(field, "") for field in GAP_FIELDS}
            row["priority"] = row["priority"] or "medium"
            rows.append(row)
    rows.extend([
        {
            "item": "Original v13 calibration workbook bytes",
            "why_absent": "The workbook file was not retained, although its SHA-256, selected factors, formulas, source hierarchy, and all installed values survive in calibration_generation.json and the current model.",
            "upgrade_source": "Recover the workbook whose recorded SHA-256 is c8601bf26acce39d6e661a9f5bcb4801c4de401a5b73ce212f9115cca5ba63f8 and verify it against the retained values.",
            "priority": "medium", "notes": "This is an evidence-byte gap, not a missing model-value or calculation gap.",
        },
        {
            "item": "Original v13 source-case and full CBC result bytes",
            "why_absent": "The installed v13 folder and BASE_V13 result files were not frozen. Their hashes, solve identity, exact extracted 2020 capacities, fingerprints, formulas, and validation narrative survive inside the v15-retained v14 records.",
            "upgrade_source": "Recover files matching the retained hashes and store them under evidence/stock_turnover without replacing the current records.",
            "priority": "medium", "notes": "All v14 stock values derived from them are retained exactly in stock_turnover_generation.json and PARAMETER_CHANGE_LOG.csv.",
        },
        {
            "item": "Local copies and checksums of some v14 official publications",
            "why_absent": "The v14 source register retained exact public URLs and selections but did not freeze every DOE, LTO, PSA, NTRC, WGC, and IRENA publication byte.",
            "upgrade_source": "Download the exact cited editions, retain them without replacing the register, and append verified checksums.",
            "priority": "low", "notes": "The citations, model use, formulas, assumptions, and every changed parameter value are already retained.",
        },
    ])
    return unique(rows, "item")


def build_changes() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for old in read_csv(BASE_LEDGER / "CHANGES.csv"):
        rows.append({field: old.get(field, "") for field in CHANGE_FIELDS})
    rows.extend([
        {
            "change_id": "CHG_PHL_V13_CALIBRATION", "date": "2026-07-27", "class": "B",
            "description": "Converted PM2.5 accounting coherently to kt, installed retained workbook-v5 factors, added navigation PM2.5, corrected cooking-oil CO2e, and linked blue-hydrogen capture to annual natural-gas input.",
            "model_objects": "genData.json; RYTEM.json; RYE.json; RE.json",
            "evidence_path": "evidence/stock_turnover/documentation/MODEL_FIXES_2026-07-27.md",
            "map_rows_affected": "", "resolve_status": "resolved", "author": "Philippines model team", "commit": "",
            "notes": "Exact values, fingerprints, formulas, and validation are retained inside v15; missing workbook bytes are in GAPS.csv.",
        },
        {
            "change_id": "CHG_PHL_V14_STOCK_TURNOVER", "date": "2026-07-28", "class": "B",
            "description": "Replaced historical activity pins with documented initial stocks and full-horizon adoption ceilings, updated official power/road/cooking stocks, and removed the stranded geothermal heat branch.",
            "model_objects": "genData.json; RYT.json; RT.json; RYC.json; RYCTs.json; RYTCM.json",
            "evidence_path": "evidence/stock_turnover/legacy_tables/PARAMETER_CHANGE_LOG.csv",
            "map_rows_affected": "", "resolve_status": "resolved", "author": "Philippines model team", "commit": "",
            "notes": "All 3,253 before/after cells are expanded into MODEL_MAP.csv and retained verbatim in the source log.",
        },
    ])
    for old in read_csv(DELTA / "CHANGES.csv"):
        rows.append({field: old.get(field, "") for field in CHANGE_FIELDS})
    rows.append({
        "change_id": "CHG_PHL_V15_CUMULATIVE_LEDGER", "date": "2026-08-05", "class": "A",
        "description": "Replaced the delta-only filing convention with a cumulative, self-contained v15 ledger carrying inherited-base mappings, v13 calibration, v14 stock turnover, v15 water additions, retained evidence, and explicit gaps.",
        "model_objects": "SOURCES.csv; CALCULATIONS.csv; ASSUMPTIONS.csv; MODEL_MAP.csv; GAPS.csv; CHANGES.csv",
        "evidence_path": "calculation_notes/CANONICAL_LEDGER_RECONSTRUCTION_2026-08-05.md",
        "map_rows_affected": "", "resolve_status": "objective_unchanged", "author": "Codex", "commit": "",
        "notes": "Documentation and packaging only. The previous v15 water-only ledger is preserved under history/water_delta_2026-08-04/.",
    })
    return unique(rows, "change_id")


def main() -> None:
    write_manifests()
    sources = build_sources()
    calculations = build_calculations()
    assumptions = build_assumptions()
    maps = build_maps()
    gaps = build_gaps()
    changes = build_changes()
    write_csv(LEDGER / "SOURCES.csv", SOURCE_FIELDS, sources)
    write_csv(LEDGER / "CALCULATIONS.csv", CALC_FIELDS, calculations)
    write_csv(LEDGER / "ASSUMPTIONS.csv", ASSUMPTION_FIELDS, assumptions)
    write_csv(LEDGER / "MODEL_MAP.csv", MAP_FIELDS, maps)
    write_csv(LEDGER / "GAPS.csv", GAP_FIELDS, gaps)
    write_csv(LEDGER / "CHANGES.csv", CHANGE_FIELDS, changes)
    print(json.dumps({
        "SOURCES.csv": len(sources), "CALCULATIONS.csv": len(calculations),
        "ASSUMPTIONS.csv": len(assumptions), "MODEL_MAP.csv": len(maps),
        "GAPS.csv": len(gaps), "CHANGES.csv": len(changes),
    }, indent=2))


if __name__ == "__main__":
    main()
