#!/usr/bin/env python3
"""Validate the Philippines v18 source package and result-free MUIO archive."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parent
CASE = REPO / "case" / "Philippines_v18"
ARCHIVE = PACKAGE / "muio" / "Philippines_v18_v18.0.0_MUIO.zip"
ARCHIVE_MANIFEST = PACKAGE / "data_sources" / "V18_MODEL_ARCHIVE_MANIFEST.csv"
ENERGY_VALIDATION = PACKAGE / "data_sources" / "snapshots" / "energy_inputs_v18_validation.json"
PROVENANCE_VALIDATION = PACKAGE / "diagnostics" / "provenance_validation_v18.json"
OUTPUT = PACKAGE / "diagnostics" / "delivery_validation_v18.json"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    checks: list[dict] = []

    def check(name: str, condition: bool, detail) -> None:
        checks.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})

    required = [
        PACKAGE / "README.md",
        PACKAGE / "data_sources" / "SOURCES.csv",
        PACKAGE / "data_sources" / "CALCULATIONS.csv",
        PACKAGE / "data_sources" / "ASSUMPTIONS.csv",
        PACKAGE / "data_sources" / "MODEL_MAP.csv",
        PACKAGE / "data_sources" / "GAPS.csv",
        PACKAGE / "data_sources" / "CHANGES.csv",
        PACKAGE / "data_sources" / "PHILIPPINES_V18_CANONICAL_SCHEMA_LEDGER.xlsx",
        ARCHIVE,
        ENERGY_VALIDATION,
        PROVENANCE_VALIDATION,
    ]
    missing = [str(path.relative_to(PACKAGE)) for path in required if not path.is_file()]
    check("required_package_files", not missing, missing)

    gen = read_json(CASE / "genData.json")
    check("live_case_identity", gen["osy-casename"] == "Philippines_v18", gen["osy-casename"])
    energy_validation = read_json(ENERGY_VALIDATION)
    check("energy_input_validation", energy_validation["status"] == "pass", energy_validation["status"])
    provenance = read_json(PROVENANCE_VALIDATION)
    ledger = provenance.get("ledger", provenance)
    check("provenance_validation", provenance["status"] == "pass", {
        "status": provenance["status"],
        "verified_digests": ledger.get("verified_digests"),
        "input_coverage": ledger.get("model_inputs", {}),
    })

    with ARCHIVE_MANIFEST.open(newline="", encoding="utf-8") as stream:
        manifest = next(csv.DictReader(stream))
    archive_hash = sha256(ARCHIVE)
    check("archive_manifest_hash", archive_hash == manifest["sha256"], {
        "expected": manifest["sha256"], "actual": archive_hash,
    })
    check("archive_manifest_size", ARCHIVE.stat().st_size == int(manifest["size_bytes"]), {
        "expected": int(manifest["size_bytes"]), "actual": ARCHIVE.stat().st_size,
    })

    with zipfile.ZipFile(ARCHIVE) as handle:
        corrupt = handle.testzip()
        names = handle.namelist()
        forbidden = [
            name for name in names
            if "/res/" in name
            or name.rsplit("/", 1)[-1] in {"data.txt", "data_processed.txt", "lp.lp", "results.txt"}
        ]
        check("archive_crc", corrupt is None, corrupt)
        check("archive_member_count", len(names) == int(manifest["member_count"]), {
            "expected": int(manifest["member_count"]), "actual": len(names),
        })
        check("result_free_archive", not forbidden, forbidden)
        source_mismatch = {}
        for path in sorted(CASE.glob("*.json")):
            member = f"Philippines_v18/{path.name}"
            if member not in names:
                source_mismatch[path.name] = "missing"
            elif sha256_bytes(handle.read(member)) != sha256(path):
                source_mismatch[path.name] = "hash mismatch"
        check("archive_live_source_identity", not source_mismatch, source_mismatch)

    checksums = (PACKAGE / "muio" / "SHA256SUMS").read_text(encoding="utf-8")
    check("archive_checksum_published", f"{archive_hash}  {ARCHIVE.name}" in checksums, ARCHIVE.name)

    report = {
        "schema": "philippines-v18-delivery-validation-v1",
        "package": str(PACKAGE),
        "case": str(CASE),
        "archive": str(ARCHIVE),
        "status": "pass" if all(item["status"] == "pass" for item in checks) else "fail",
        "checks": checks,
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
