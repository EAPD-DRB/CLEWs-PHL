#!/usr/bin/env python3
"""Finalize the validated v18 package and rebuild its result-free archive."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import zipfile
from pathlib import Path


ARCHIVE_NAME = "Philippines_v18_v18.0.0_MUIO.zip"
FORBIDDEN_NAMES = {"data.txt", "data_processed.txt", "lp.lp", "results.txt"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        # Preserve the canonical ledgers' existing CRLF convention so a
        # one-row metadata update does not normalize every inherited row.
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)


def update_source_digests(package: Path) -> None:
    sources = package / "data_sources" / "SOURCES.csv"
    with sources.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    local_files = {
        "evidence/CURRENT_MODEL_ARCHIVE_MANIFEST.csv",
        "V18_MODEL_ARCHIVE_MANIFEST.csv",
    }
    updated = 0
    for row in rows:
        if row["local_file"] in local_files:
            row["sha256"] = sha256(package / "data_sources" / row["local_file"])
            updated += 1
    if updated != 3:
        raise RuntimeError(f"Expected three archive-manifest source rows, found {updated}")
    write_csv(sources, fieldnames, rows)


def finalize_change_record(package: Path) -> None:
    changes = package / "data_sources" / "CHANGES.csv"
    with changes.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    target = "CHG_PHL_V18_DEPLOYMENT_ENVELOPES_20260813"
    found = 0
    for row in rows:
        if row["change_id"] == target:
            row["resolve_status"] = "resolved"
            row["notes"] = (
                "Only TAMaxCI.SC_0 changed. Static checks, application generation, "
                "preprocessing, glpsol matrix validation, full CBC control/candidate "
                "solves, comparison, live regeneration and delivery checks passed; "
                "no minimum, share, activity bound, aggregate cap or PEP total was added."
            )
            found += 1
    if found != 1:
        raise RuntimeError(f"Expected one {target} record, found {found}")
    write_csv(changes, fieldnames, rows)


def copy_validation_records(case: Path, package: Path) -> None:
    documentation = case / "documentation"
    documentation.mkdir(parents=True, exist_ok=True)
    sources = {
        package / "documentation" / "MODEL_FIXES_DEPLOYMENT_ENVELOPES_2026-08-13.md":
            documentation / "MODEL_FIXES_DEPLOYMENT_ENVELOPES_2026-08-13.md",
        package / "data_sources" / "snapshots" / "deployment_envelopes_v18_2026-08-13.json":
            documentation / "deployment_envelopes_v18_2026-08-13.json",
        package / "data_sources" / "snapshots" / "deployment_envelope_build_manifest.json":
            documentation / "deployment_envelope_build_manifest.json",
        package / "data_sources" / "snapshots" / "deployment_envelope_static_validation.json":
            documentation / "deployment_envelope_static_validation.json",
        package / "data_sources" / "snapshots" / "deployment_envelope_validation.json":
            documentation / "deployment_envelope_validation.json",
    }
    for source, target in sources.items():
        shutil.copy2(source, target)


def build_archive(case: Path, archive: Path) -> int:
    files = []
    for path in sorted(case.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(case)
        if "res" in relative.parts or path.name in FORBIDDEN_NAMES or path.name == ".DS_Store":
            continue
        files.append(path)
    temporary = archive.with_suffix(".zip.tmp")
    if temporary.exists():
        temporary.unlink()
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as handle:
        for path in files:
            member = Path("Philippines_v18") / path.relative_to(case)
            handle.write(path, member.as_posix())
    with zipfile.ZipFile(temporary) as handle:
        if handle.testzip() is not None:
            raise RuntimeError("Archive CRC validation failed")
    temporary.replace(archive)
    return len(files)


def update_archive_records(package: Path, archive: Path, member_count: int) -> None:
    digest = sha256(archive)
    size = archive.stat().st_size
    manifest_fields = [
        "archive", "sha256", "size_bytes", "member_count", "internal_root",
        "result_files_included", "notes",
    ]
    manifest_row = {
        "archive": archive.name,
        "sha256": digest,
        "size_bytes": str(size),
        "member_count": str(member_count),
        "internal_root": "Philippines_v18/",
        "result_files_included": "false",
        "notes": (
            "Complete editable v18 source JSON, regenerated view files, inherited local "
            "documentation, v18 energy-input records, and deployment-envelope build and "
            "validation records; res/, data.txt, data_processed.txt, lp.lp, and results.txt excluded."
        ),
    }
    write_csv(package / "data_sources" / "V18_MODEL_ARCHIVE_MANIFEST.csv", manifest_fields, [manifest_row])

    current_fields = ["package_relative_path", "size_bytes", "sha256", "zip_member_count", "internal_root"]
    current_row = {
        "package_relative_path": f"muio/{archive.name}",
        "size_bytes": str(size),
        "sha256": digest,
        "zip_member_count": str(member_count),
        "internal_root": "Philippines_v18/",
    }
    write_csv(
        package / "data_sources" / "evidence" / "CURRENT_MODEL_ARCHIVE_MANIFEST.csv",
        current_fields,
        [current_row],
    )

    checksum_path = package / "muio" / "SHA256SUMS"
    lines = [line for line in checksum_path.read_text(encoding="utf-8").splitlines() if archive.name not in line]
    checksum_path.write_text(f"{digest}  {archive.name}\n" + "\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    case = args.case.resolve()
    package = args.package.resolve()

    for name in ("deployment_envelope_static_validation.json", "deployment_envelope_validation.json"):
        report = read_json(package / "data_sources" / "snapshots" / name)
        if report.get("status") != "pass":
            raise RuntimeError(f"Cannot publish: {name} status is {report.get('status')!r}")

    copy_validation_records(case, package)
    finalize_change_record(package)
    archive = package / "muio" / ARCHIVE_NAME
    member_count = build_archive(case, archive)
    update_archive_records(package, archive, member_count)
    update_source_digests(package)

    result = {
        "status": "pass",
        "case": str(case),
        "archive": str(archive),
        "archive_sha256": sha256(archive),
        "archive_size_bytes": archive.stat().st_size,
        "archive_member_count": member_count,
        "result_files_included": False,
    }
    output = package / "data_sources" / "snapshots" / "deployment_envelope_publication.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
