#!/usr/bin/env python3
"""Validate the cumulative ledger, workbook, and portable v19 delivery."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parent
LEDGER = PACKAGE / "data_sources"
CASE = REPO / "case" / "Philippines_v19"
ARCHIVE = PACKAGE / "muio" / "Philippines_v19_v19.0.0_MUIO.zip"
WORKBOOK = LEDGER / "PHILIPPINES_V19_CANONICAL_SCHEMA_LEDGER.xlsx"
OUTPUT = LEDGER / "snapshots" / "pm25_coverage_v19_delivery_validation.json"
TABLE_KEYS = {
    "SOURCES.csv": "source_id", "CALCULATIONS.csv": "calculation_id",
    "ASSUMPTIONS.csv": "assumption_id", "MODEL_MAP.csv": "map_id",
    "GAPS.csv": "item", "CHANGES.csv": "change_id",
}
GENERATED_NAMES = {"data.txt", "data_processed.txt", "lp.lp", "results.txt"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(filename: str) -> list[dict]:
    with (LEDGER / filename).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    checks: list[dict] = []

    def check(name: str, condition: bool, detail) -> None:
        checks.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})

    tables = {filename: rows(filename) for filename in TABLE_KEYS}
    schema_errors = []
    for filename, key in TABLE_KEYS.items():
        values = [row[key] for row in tables[filename]]
        if not values or any(not value for value in values) or len(values) != len(set(values)):
            schema_errors.append(filename)
    check("six_ledger_tables_unique_nonempty_keys", not schema_errors,
          {filename: len(table) for filename, table in tables.items()} | {"errors": schema_errors})

    expected = {
        "SOURCES.csv": 11, "CALCULATIONS.csv": 7, "ASSUMPTIONS.csv": 5,
        "MODEL_MAP.csv": 54, "GAPS.csv": 5, "CHANGES.csv": 2,
    }
    prefixes = {
        "SOURCES.csv": "SRC_PHL_V19_", "CALCULATIONS.csv": "CALC_PHL_V19_",
        "ASSUMPTIONS.csv": "ASM_PHL_V19_", "MODEL_MAP.csv": "MAP_PHL_V19_",
        "CHANGES.csv": "CHG_PHL_V19_",
    }
    counts = {}
    for filename, prefix in prefixes.items():
        key = TABLE_KEYS[filename]
        counts[filename] = sum(row[key].startswith(prefix) for row in tables[filename])
    counts["SOURCES.csv"] = sum(
        row["source_id"].startswith(("SRC_PHL_V19_", "SRC_EEA_2023_", "SRC_EEA_2025_"))
        or row["source_id"] == "SRC_PHL_FISHERIES_DIESEL_BASIS"
        for row in tables["SOURCES.csv"]
    )
    counts["GAPS.csv"] = sum(
        row["item"] in {
            "Philippines-specific PM2.5 technology factors",
            "Alternative-powertrain road exhaust and road-wear differentiation",
            "Aviation and rail PM2.5 extension", "Agriculture oil and gas stationary heat",
            "PM2.5 sources without explicit model activity",
        } for row in tables["GAPS.csv"]
    )
    check("v19_ledger_record_counts", counts == expected, {"actual": counts, "expected": expected})

    identifiers = set()
    for filename in ("SOURCES.csv", "CALCULATIONS.csv", "ASSUMPTIONS.csv"):
        key = TABLE_KEYS[filename]
        identifiers.update(row[key] for row in tables[filename])
    missing_refs = []
    for row in tables["MODEL_MAP.csv"]:
        if row["map_id"].startswith("MAP_PHL_V19_"):
            for ref in filter(None, row["evidence_ids"].split(";")):
                if ref not in identifiers:
                    missing_refs.append(f"{row['map_id']}:{ref}")
    check("v19_model_map_references_resolve", not missing_refs, missing_refs)

    source_errors = []
    for row in tables["SOURCES.csv"]:
        if not row["source_id"].startswith("SRC_PHL_V19_") and not row["source_id"].startswith("SRC_EEA_"):
            continue
        local = (LEDGER / row["local_file"]).resolve()
        if not local.is_file() or (row["sha256"] and sha256(local) != row["sha256"]):
            source_errors.append(row["source_id"])
    check("v19_ledger_local_evidence_hashes", not source_errors, source_errors)

    archive_manifest = next(csv.DictReader((LEDGER / "V19_MODEL_ARCHIVE_MANIFEST.csv").open(newline="", encoding="utf-8")))
    with zipfile.ZipFile(ARCHIVE) as archive:
        bad_crc = archive.testzip()
        members = [info.filename for info in archive.infolist() if not info.is_dir()]
        result_members = [name for name in members if "/res/" in name or Path(name).name in GENERATED_NAMES]
        identity_errors = []
        for path in CASE.glob("*.json"):
            member = f"Philippines_v19/{path.name}"
            if member not in members or archive.read(member) != path.read_bytes():
                identity_errors.append(path.name)
    archive_ok = (
        bad_crc is None and not result_members and not identity_errors
        and sha256(ARCHIVE) == archive_manifest["sha256"]
        and ARCHIVE.stat().st_size == int(archive_manifest["size_bytes"])
        and len(members) == int(archive_manifest["member_count"])
    )
    check("portable_archive_integrity_identity_and_result_exclusion", archive_ok, {
        "crc_error": bad_crc, "result_members": result_members, "identity_errors": identity_errors,
        "members": len(members), "sha256": sha256(ARCHIVE),
    })

    workbook_ok = WORKBOOK.is_file()
    workbook_error = None
    if workbook_ok:
        try:
            with zipfile.ZipFile(WORKBOOK) as workbook:
                workbook_error = workbook.testzip()
                workbook_ok = workbook_error is None and "xl/workbook.xml" in workbook.namelist()
        except zipfile.BadZipFile as exc:
            workbook_ok = False
            workbook_error = str(exc)
    check("review_workbook_integrity", workbook_ok, {"path": str(WORKBOOK), "error": workbook_error})

    status = "pass" if all(item["status"] == "pass" for item in checks) else "fail"
    report = {"schema": "philippines-v19-delivery-validation-v1", "status": status, "checks": checks}
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
