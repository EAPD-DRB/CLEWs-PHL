#!/usr/bin/env python3
"""Validate the final Philippines v18.0.1 package and result-free archive."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from pathlib import Path


ARCHIVE_NAME = "Philippines_v18_v18.0.1_MUIO.zip"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    live = args.live.resolve()
    package = args.package.resolve()
    archive = package / "muio" / ARCHIVE_NAME
    checks = []

    def check(name: str, condition: bool, detail) -> None:
        checks.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})

    required = [
        package / "README.md",
        *(package / "data_sources" / name for name in (
            "SOURCES.csv", "CALCULATIONS.csv", "ASSUMPTIONS.csv", "MODEL_MAP.csv", "GAPS.csv", "CHANGES.csv",
            "PHILIPPINES_V18_CANONICAL_SCHEMA_LEDGER.xlsx", "V18_MODEL_ARCHIVE_MANIFEST.csv",
        )),
        *(package / "data_sources" / "snapshots" / name for name in (
            "land_water_closure_build_manifest.json", "land_water_closure_validation.json",
            "land_water_closure_runtime_incident.json", "land_water_closure_promotion_identity.json",
            "land_water_closure_delivery_build.json",
        )),
        package / "diagnostics" / "provenance_validation_v18.json",
        archive,
    ]
    missing = [str(path.relative_to(package)) for path in required if not path.is_file()]
    check("required_files", not missing, missing)

    for name in (
        "land_water_closure_build_manifest.json",
        "land_water_closure_validation.json",
        "land_water_closure_promotion_identity.json",
        "land_water_closure_delivery_build.json",
    ):
        payload = read_json(package / "data_sources" / "snapshots" / name)
        check(name.removesuffix(".json"), payload.get("status") == "pass", payload.get("status"))
    incident = read_json(package / "data_sources" / "snapshots" / "land_water_closure_runtime_incident.json")
    check("aggregate_udc_rejected", incident["status"] == "rejected_timeout", incident["status"])
    provenance = read_json(package / "diagnostics" / "provenance_validation_v18.json")
    check("provenance", provenance["status"] == "pass", {
        "status": provenance["status"], "failures": provenance.get("failures", [])
    })

    with (package / "data_sources" / "V18_MODEL_ARCHIVE_MANIFEST.csv").open(newline="", encoding="utf-8-sig") as stream:
        manifest = next(csv.DictReader(stream))
    digest = sha256(archive)
    check("archive_hash", digest == manifest["sha256"], {"actual": digest, "expected": manifest["sha256"]})
    check("archive_size", archive.stat().st_size == int(manifest["size_bytes"]), archive.stat().st_size)
    with zipfile.ZipFile(archive) as handle:
        names = handle.namelist()
        corrupt = handle.testzip()
        forbidden = [
            name for name in names
            if "/res/" in name or name.rsplit("/", 1)[-1] in {"data.txt", "data_processed.txt", "lp.lp", "results.txt"}
        ]
        check("archive_crc", corrupt is None, corrupt)
        check("archive_member_count", len(names) == int(manifest["member_count"]), len(names))
        check("result_free", not forbidden, forbidden)
        mismatch = {}
        for path in sorted(live.glob("*.json")):
            member = f"Philippines_v18/{path.name}"
            if member not in names:
                mismatch[path.name] = "missing"
            elif sha256_bytes(handle.read(member)) != sha256(path):
                mismatch[path.name] = "hash mismatch"
        check("archive_live_source_identity", not mismatch, mismatch)
    checksums = (package / "muio" / "SHA256SUMS").read_text(encoding="utf-8")
    check("published_checksum", f"{digest}  {archive.name}" in checksums, archive.name)

    report = {
        "schema": "philippines-v18-land-water-delivery-validation-v1",
        "status": "pass" if all(item["status"] == "pass" for item in checks) else "fail",
        "live_case": str(live),
        "package": str(package),
        "archive": str(archive),
        "checks": checks,
    }
    output = package / "diagnostics" / "delivery_validation_v18_0_1.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
