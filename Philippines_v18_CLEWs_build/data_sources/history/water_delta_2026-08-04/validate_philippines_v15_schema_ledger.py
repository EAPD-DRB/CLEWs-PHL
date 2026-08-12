#!/usr/bin/env python3
"""Validate the Philippines v15 water schema ledger against the live case.

This validator complements the repository's generic six-table provenance
validator.  It verifies retained-evidence hashes, live case/run identity,
full-precision water formulas, the documented model mappings, and the
deterministic source checks used to validate the implemented water model.
It does not generate or solve the model and writes only its JSON report.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REPO = Path(__file__).resolve().parents[3]
DOCS = REPO / "docs" / "philippines_v15"
LEDGER_DIR = DOCS / "data_sources"
CASE = REPO / "WebAPP" / "DataStorage" / "Philippines_v15"
BASELINE = REPO / "WebAPP" / "DataStorage" / "Philippines_v14_STOCK_TURNOVER"
MANIFEST_PATH = CASE / "documentation" / "national_water_manifest.json"
WATER_LEDGER_PATH = CASE / "documentation" / "national_water_ledger.json"
SOURCE_DATA_PATH = REPO / "scripts" / "data" / "philippines_water_precipitation_ssp245.json"
MODEL_PATH = REPO / "WebAPP" / "SOLVERs" / "model.v.5.4.txt"
NOTE_PATH = LEDGER_DIR / "calculation_notes" / "national_water_v15.md"
GENERIC_REPORT_PATH = DOCS / "validation" / "schema_ledger_build.json"
REPORT_PATH = DOCS / "validation" / "schema_ledger_live.json"
MODEL_VALIDATOR_PATH = REPO / "scripts" / "validate_philippines_v15_national_water.py"

EXPECTED_COUNTS = {
    "SOURCES.csv": 21,
    "CALCULATIONS.csv": 13,
    "ASSUMPTIONS.csv": 12,
    "MODEL_MAP.csv": 14,
    "GAPS.csv": 9,
    "CHANGES.csv": 5,
}

EXPECTED_MODEL_MAP_IDS = {
    "MAP_PHL_V15_LINEAGE",
    "MAP_PHL_GWT_IRRIGATION_STRUCTURE",
    "MAP_PHL_GWT_IRRIGATION_IAR",
    "MAP_PHL_CLIMATE_RYTCM",
    "MAP_PHL_SURFACE_CONSTRAINT_STRUCTURE",
    "MAP_PHL_GWT_CONSTRAINT_STRUCTURE",
    "MAP_PHL_SURFACE_UCC",
    "MAP_PHL_GROUNDWATER_UCC",
    "MAP_PHL_SURFACE_CAM",
    "MAP_PHL_GROUNDWATER_CAM",
    "MAP_PHL_WATER_SOURCE_SNAPSHOT",
    "MAP_PHL_WATER_MANIFEST",
    "MAP_PHL_WATER_VALIDATION",
    "MAP_PHL_WATER_LEDGER",
}

REQUIRED_SOURCE_IDS = {
    "SRC_PHL_V14_CASE",
    "SRC_PHL_WATER_SNAPSHOT",
    "SRC_WB_CCKP_ERA5_PHL_TS",
    "SRC_WB_CCKP_ERA5_PHL_NORMAL",
    "SRC_WB_CCKP_CMIP6_PHL_HIST",
    "SRC_WB_CCKP_CMIP6_PHL_SSP245_2030",
    "SRC_WB_CCKP_CMIP6_PHL_SSP245_2050",
    "SRC_WB_CCKP_METADATA",
    "SRC_IPCC_AR6_SSP245",
    "SRC_DEPDEV_WATER_POLICY_NOTE",
    "SRC_PDP_2023_2028_CH12",
    "SRC_PSA_WATER_ACCOUNTS_2020",
    "SRC_PIDS_REGIONAL_WATER",
    "SRC_PIDS_METRO_CEBU_GW",
    "SRC_MGB_REGIONAL_GW",
    "SRC_FAO_AQUASTAT_METHOD",
    "SRC_CLEWS_PHL_GEOSPATIAL",
    "SRC_MUIO_FORMULATION",
    "SRC_PHL_V15_MANIFEST",
    "SRC_PHL_V15_VALIDATION",
    "SRC_PHL_V15_LEDGER",
}

REQUIRED_CALCULATION_IDS = {
    "CALC_PHL_V14_PRECIP_DEPTH",
    "CALC_PHL_ERA5_REBASE",
    "CALC_PHL_SSP245_MULTIPLIER_2030",
    "CALC_PHL_SSP245_MULTIPLIER_2050",
    "CALC_PHL_SSP245_ANNUAL",
    "CALC_PHL_COMBINED_HYDROLOGY_FACTOR",
    "CALC_PHL_PRECIP_ACTIVITY",
    "CALC_PHL_WATER_RESOURCE_TOTAL",
    "CALC_PHL_SURFACE_UCC",
    "CALC_PHL_GROUNDWATER_UCC",
    "CALC_PHL_GWT_IRRIGATION_IAR",
    "CALC_PHL_UDC_EXACTNESS",
    "CALC_PHL_WATER_VALIDATION",
}

REQUIRED_ASSUMPTION_IDS = {
    "ASM_PHL_WATER_NATIONAL_BOUNDARY",
    "ASM_PHL_ERA5_1991_2020_ANCHOR",
    "ASM_PHL_SSP245_MEDIAN_ONLY",
    "ASM_PHL_P10_P90_METADATA_ONLY",
    "ASM_PHL_SSP245_LINEAR_ANNUALISATION",
    "ASM_PHL_HYDROLOGY_UNIFORM_SCALING",
    "ASM_PHL_POTENTIAL_FLOW_CEILINGS",
    "ASM_PHL_CAPS_SCALE_WITH_MEDIAN_PRECIP",
    "ASM_PHL_GWT_IRRIGATION_ONE_TO_ONE",
    "ASM_PHL_POLICY_INHERITANCE",
    "ASM_PHL_NO_GROUNDWATER_STOCK",
    "ASM_PHL_ENV_WATER_LEDGER_AUTHORITY",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def close(actual: float, expected: float, tolerance: float, label: str) -> None:
    require(
        math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance),
        f"{label}: {actual!r} != {expected!r} (absolute tolerance {tolerance})",
    )


def load_model_validator() -> Any:
    spec = importlib.util.spec_from_file_location("phl_water_validator", MODEL_VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODEL_VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_report(value: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT_PATH.with_name(REPORT_PATH.name + ".codex-tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(REPORT_PATH)


def parse_note_rows() -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    for line in NOTE_PATH.read_text(encoding="utf-8").splitlines():
        if not re.match(r"^\| 20\d\d \|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        require(len(cells) == 6, f"unexpected annual calculation-note row: {line}")
        rows.append(
            {
                "year": int(cells[0]),
                "median_multiplier": float(cells[1]),
                "combined_factor": float(cells[2]),
                "precipitation_km3": float(cells[3]),
                "surface_cap_km3": float(cells[4]),
                "groundwater_cap_km3": float(cells[5]),
            }
        )
    return rows


def main() -> int:
    checks: list[dict[str, Any]] = []

    def run_check(name: str, operation: Callable[[], Any]) -> Any:
        try:
            detail = operation()
        except Exception as error:  # report all independent failures
            checks.append(
                {
                    "name": name,
                    "status": "fail",
                    "detail": f"{type(error).__name__}: {error}",
                }
            )
            return None
        checks.append({"name": name, "status": "pass", "detail": detail})
        return detail

    tables: dict[str, list[dict[str, str]]] = {}

    def check_table_counts() -> dict[str, int]:
        for filename, expected in EXPECTED_COUNTS.items():
            rows = read_csv(LEDGER_DIR / filename)
            tables[filename] = rows
            require(len(rows) == expected, f"{filename} has {len(rows)} rows; expected {expected}")
        return {filename: len(rows) for filename, rows in tables.items()}

    run_check("canonical_table_row_counts", check_table_counts)

    def ensure_tables() -> None:
        if not tables:
            for filename in EXPECTED_COUNTS:
                tables[filename] = read_csv(LEDGER_DIR / filename)

    def check_required_ids() -> dict[str, int]:
        ensure_tables()
        identifiers = {
            "source_ids": {row["source_id"] for row in tables["SOURCES.csv"]},
            "calculation_ids": {
                row["calculation_id"] for row in tables["CALCULATIONS.csv"]
            },
            "assumption_ids": {
                row["assumption_id"] for row in tables["ASSUMPTIONS.csv"]
            },
            "model_map_ids": {row["map_id"] for row in tables["MODEL_MAP.csv"]},
        }
        expected = {
            "source_ids": REQUIRED_SOURCE_IDS,
            "calculation_ids": REQUIRED_CALCULATION_IDS,
            "assumption_ids": REQUIRED_ASSUMPTION_IDS,
            "model_map_ids": EXPECTED_MODEL_MAP_IDS,
        }
        for label, expected_ids in expected.items():
            require(
                identifiers[label] == expected_ids,
                f"{label} differs; missing={sorted(expected_ids - identifiers[label])}; "
                f"unexpected={sorted(identifiers[label] - expected_ids)}",
            )
        return {label: len(values) for label, values in identifiers.items()}

    run_check("required_trace_identifiers", check_required_ids)

    def check_snapshot_hashes() -> dict[str, Any]:
        ensure_tables()
        verified: list[dict[str, str]] = []
        for row in tables["SOURCES.csv"]:
            if not row["sha256"]:
                continue
            require(row["local_file"], f"{row['source_id']} has a digest but no local file")
            local_path = LEDGER_DIR / row["local_file"]
            require(local_path.is_file(), f"missing retained evidence {local_path}")
            actual = sha256(local_path)
            require(actual == row["sha256"], f"digest mismatch for {row['source_id']}")
            verified.append(
                {
                    "source_id": row["source_id"],
                    "local_file": row["local_file"],
                    "sha256": actual,
                }
            )
        require(len(verified) == 6, f"verified {len(verified)} digests; expected 6")
        return {"verified_digests": len(verified), "files": verified}

    run_check("retained_evidence_sha256", check_snapshot_hashes)

    manifest = run_check("load_live_manifest", lambda: read_json(MANIFEST_PATH))
    water_ledger = run_check("load_live_water_ledger", lambda: read_json(WATER_LEDGER_PATH))

    def check_live_identity() -> dict[str, Any]:
        gen = read_json(CASE / "genData.json")
        res_data = read_json(CASE / "view" / "resData.json")
        records = [row for row in res_data["osy-cases"] if row["Case"] == "BASE_V15"]
        require(gen["osy-casename"] == "Philippines_v15", "genData case identity differs")
        require(len(records) == 1, "BASE_V15 run metadata is absent or duplicated")
        active = [row["Scenario"] for row in records[0]["Scenarios"] if row["Active"]]
        require(active == ["BASE"], f"active scenarios differ: {active}")
        return {"case": gen["osy-casename"], "run": records[0]["Case"], "active": active}

    run_check("live_case_and_run_identity", check_live_identity)

    def check_manifest_identity_and_hashes() -> dict[str, Any]:
        require(isinstance(manifest, dict), "manifest did not load")
        require(manifest["target_case"] == "Philippines_v15", "manifest target differs")
        require(
            manifest["source_data"]["sha256"] == sha256(SOURCE_DATA_PATH),
            "source-data hash differs from manifest",
        )
        require(
            manifest["model_formulation"]["sha256"] == sha256(MODEL_PATH),
            "model-formulation hash differs from manifest",
        )
        require(manifest["years"] == [str(year) for year in range(2020, 2054)], "year list differs")
        return {
            "target_case": manifest["target_case"],
            "source_data_sha256": manifest["source_data"]["sha256"],
            "model_formulation_sha256": manifest["model_formulation"]["sha256"],
            "years": len(manifest["years"]),
        }

    run_check("manifest_identity_and_live_hashes", check_manifest_identity_and_hashes)

    def check_water_ledger_identity() -> dict[str, Any]:
        require(isinstance(water_ledger, dict), "water ledger did not load")
        require(water_ledger["case"] == "Philippines_v15", "water-ledger case differs")
        require(water_ledger["run"] == "BASE_V15", "water-ledger run differs")
        require(len(water_ledger["annual"]) == 34, "water ledger does not contain 34 annual rows")
        years = [int(row["year"]) for row in water_ledger["annual"]]
        require(years == list(range(2020, 2054)), "water-ledger years are incomplete or unordered")
        return {"case": water_ledger["case"], "run": water_ledger["run"], "annual_rows": 34}

    run_check("live_water_ledger_identity", check_water_ledger_identity)

    note_rows = run_check("calculation_note_annual_rows", parse_note_rows)

    def check_annual_formulas() -> dict[str, Any]:
        require(isinstance(manifest, dict), "manifest did not load")
        require(isinstance(note_rows, list), "annual note rows did not load")
        require(len(note_rows) == 34, f"calculation note has {len(note_rows)} annual rows")
        climate = manifest["climate"]
        rebase = float(climate["era5_rebase_factor"])
        normal = float(climate["era5_1991_2020_normal_mm_per_year"])
        area = float(climate["national_land_area_1000km2"])
        surface = manifest["withdrawal_constraints"]["WATER_SUR_AVAIL"]["annual_UCC_km3"]
        groundwater = manifest["withdrawal_constraints"]["WATER_GWT_POTENTIAL"]["annual_UCC_km3"]
        for row in note_rows:
            year = str(row["year"])
            multiplier = float(climate["ssp245_median_multiplier"][year])
            close(float(row["median_multiplier"]), multiplier, 5e-14, f"{year} median multiplier")
            close(float(row["combined_factor"]), rebase * multiplier, 5e-14, f"{year} combined factor")
            close(float(row["precipitation_km3"]), area * normal / 1000 * multiplier, 5e-10, f"{year} precipitation")
            close(float(surface[year]), 125.79 * multiplier, 5e-13, f"{year} surface UCC")
            close(float(groundwater[year]), 20.2 * multiplier, 5e-13, f"{year} groundwater UCC")
            close(float(row["surface_cap_km3"]), float(surface[year]), 5e-10, f"{year} printed surface UCC")
            close(float(row["groundwater_cap_km3"]), float(groundwater[year]), 5e-10, f"{year} printed groundwater UCC")
        return {
            "years_checked": len(note_rows),
            "formulas": [
                "combined_factor = ERA5_rebase * SSP2-4.5_median_multiplier",
                "precipitation_km3 = national_land_area_1000km2 * ERA5_normal_mm / 1000 * multiplier",
                "surface_UCC_km3 = 125.79 * multiplier",
                "groundwater_UCC_km3 = 20.2 * multiplier",
            ],
        }

    run_check("full_precision_annual_water_formulas", check_annual_formulas)

    source_hashes_before: dict[str, str] = {}
    source_hashes_after: dict[str, str] = {}
    model_source_checks: dict[str, Any] | None = None

    def check_live_model_sources() -> dict[str, Any]:
        nonlocal source_hashes_before, source_hashes_after, model_source_checks
        validator = load_model_validator()
        source_hashes_before = validator.source_parameter_hashes(CASE)
        model_source_checks = validator.source_checks(CASE, BASELINE, completed_run=True)
        source_hashes_after = validator.source_parameter_hashes(CASE)
        require(source_hashes_before == source_hashes_after, "source parameters changed during checking")
        expected_true = (
            "source_data_sha256_matches",
            "candidate_fingerprints_match",
            "baseline_fingerprints_match_generation_source",
            "median_only_installed",
            "irrigation_coefficients_unchanged",
            "exact_withdrawal_proof_repeated",
            "policy_inheritance_repeated",
        )
        for field in expected_true:
            require(model_source_checks.get(field) is True, f"model source check {field} did not pass")
        require(
            model_source_checks.get("p10_p90_model_scenarios_added") is False,
            "p10/p90 model scenarios were unexpectedly added",
        )
        return {
            "source_json_files_checked": len(source_hashes_before),
            "source_parameters_unchanged_during_check": True,
            "deterministic_source_checks": model_source_checks,
        }

    run_check("live_model_deterministic_source_checks", check_live_model_sources)

    def check_generic_report() -> dict[str, Any]:
        report = read_json(GENERIC_REPORT_PATH)
        require(report["status"] == "pass", "generic provenance report did not pass")
        require(report["failure_count"] == 0, "generic provenance report contains failures")
        require(report["verified_digests"] == 6, "generic provenance digest count differs")
        return {
            "status": report["status"],
            "failure_count": report["failure_count"],
            "warning_count": report["warning_count"],
            "verified_digests": report["verified_digests"],
            "warning_interpretation": "blank commit fields in the uncommitted working tree",
        }

    run_check("generic_schema_ledger_validation", check_generic_report)

    failed = [item for item in checks if item["status"] == "fail"]
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "validator": str(Path(__file__).relative_to(REPO)),
        "scope": "Documentation-only validation of the Philippines_v15 national-water schema ledger against live source parameters and retained evidence.",
        "case": "Philippines_v15",
        "run": "BASE_V15",
        "status": "pass" if not failed else "fail",
        "check_count": len(checks),
        "failure_count": len(failed),
        "checks": checks,
    }
    write_report(report)
    print(json.dumps({key: report[key] for key in ("status", "check_count", "failure_count")}, indent=2))
    print(f"report: {REPORT_PATH.relative_to(REPO)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
