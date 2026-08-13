#!/usr/bin/env python3
"""Close promotion lineage and build the result-free Philippines v18.0.1 archive."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import zipfile
from pathlib import Path


ARCHIVE_NAME = "Philippines_v18_v18.0.1_MUIO.zip"
FORBIDDEN = {"data.txt", "data_processed.txt", "lp.lp", "results.txt"}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def write_table(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)


def append_unique(path: Path, row: dict) -> None:
    fields, rows = table(path)
    key = fields[0]
    if any(existing[key] == row[key] for existing in rows):
        raise AssertionError(f"duplicate {key}: {row[key]}")
    write_table(path, fields, rows + [row])


def update_source_digest(package: Path, source_id: str, digest: str) -> None:
    path = package / "data_sources" / "SOURCES.csv"
    fields, rows = table(path)
    found = 0
    for row in rows:
        if row["source_id"] == source_id:
            row["sha256"] = digest
            found += 1
    if found != 1:
        raise AssertionError(f"expected one source row {source_id}, found {found}")
    write_table(path, fields, rows)


def build_archive(live: Path, archive: Path) -> int:
    files = []
    for path in sorted(live.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(live)
        if "res" in relative.parts or path.name in FORBIDDEN or path.name == ".DS_Store":
            continue
        files.append(path)
    temporary = archive.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as handle:
        for path in files:
            handle.write(path, (Path("Philippines_v18") / path.relative_to(live)).as_posix())
    with zipfile.ZipFile(temporary) as handle:
        if handle.testzip() is not None:
            raise AssertionError("archive CRC failed")
    temporary.replace(archive)
    return len(files)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    live = args.live.resolve()
    package = args.package.resolve()
    repo = args.repo.resolve()
    snapshots = package / "data_sources" / "snapshots"
    promotion_path = snapshots / "land_water_closure_promotion_identity.json"
    validation_path = snapshots / "land_water_closure_validation.json"
    build_path = snapshots / "land_water_closure_build_manifest.json"
    promotion = read_json(promotion_path)
    validation = read_json(validation_path)
    build = read_json(build_path)
    if promotion["status"] != "pass" or validation["status"] != "pass":
        raise AssertionError("promotion or candidate validation is not pass")

    validation["validation_status"]["promotion_identity"] = "passed"
    validation["promotion_identity_sha256"] = sha256(promotion_path)
    validation["post_promotion_optimizer_runs"] = 0
    write_json(validation_path, validation)
    build["validation_status"]["promotion_identity"] = "passed"
    build["promotion_identity_sha256"] = sha256(promotion_path)
    build["validation_report_sha256"] = sha256(validation_path)
    write_json(build_path, build)
    for path in (build_path, validation_path, promotion_path):
        shutil.copy2(path, live / "documentation" / path.name)

    append_unique(
        package / "data_sources" / "SOURCES.csv",
        {
            "source_id": "SRC_PHL_V18_LAND_WATER_PROMOTION", "provider": "MUIOGO Philippines v18 workflow",
            "product": "Land-water promotion identity report", "edition": "2026-08-13", "reference_period": "promotion",
            "geography": "Philippines", "variable": "Live/candidate source, generated input, normalized preprocessing and matrix identity",
            "source_unit": "hashes and status", "exact_locator": "snapshots/land_water_closure_promotion_identity.json",
            "url": "", "access_date": "2026-08-13", "license": "Repository license", "sha256": sha256(promotion_path),
            "local_file": "snapshots/land_water_closure_promotion_identity.json", "notes": "No post-promotion CBC; data.txt is byte-identical and preprocessing differs only by unordered set declaration order.",
        },
    )
    update_source_digest(package, "SRC_PHL_V18_LAND_WATER_BUILD", sha256(build_path))
    update_source_digest(package, "SRC_PHL_V18_LAND_WATER_VALIDATION", sha256(validation_path))

    append_unique(
        package / "data_sources" / "CALCULATIONS.csv",
        {
            "calculation_id": "CALC_PHL_V18_LAND_WATER_PROMOTION",
            "formula": "compare all root source JSON + data.txt hashes; canonicalize unordered processed sets; generate/check live LP; compare matrix",
            "source_ids": "SRC_PHL_V18_LAND_WATER_PROMOTION;SRC_PHL_V18_LAND_WATER_VALIDATION",
            "assumption_ids": "ASM_PHL_V18_ALL_LAND_THROUGH_HYDROLOGY;ASM_PHL_V18_CLUSTER_WATER_CONSERVATION",
            "input_calculation_ids": "CALC_PHL_V18_LAND_WATER_RUN",
            "input_values": f"source_json=22; data={promotion['hashes']['data_txt']}; matrix={promotion['matrix']}",
            "input_units": "count; sha256; dimensions",
            "output_value": "pass; no post-promotion optimizer run",
            "output_unit": "status",
            "script_path": "scripts/verify_philippines_v18_land_water_promotion.py",
            "script_version": "v1",
            "notes": "Processed text is non-byte-identical only because derived AMPL sets are unordered; canonical membership and GLPK dimensions match.",
        },
    )

    map_path = package / "data_sources" / "MODEL_MAP.csv"
    fields, rows = table(map_path)
    for row in rows:
        if row["map_id"] in {"MAP_PHL_V18_LAND_HYDROLOGY_BOUNDS", "MAP_PHL_V18_WATER_COEFFICIENT_CLOSURE"}:
            if "SRC_PHL_V18_LAND_WATER_PROMOTION" not in row["evidence_ids"].split(";"):
                row["evidence_ids"] += ";SRC_PHL_V18_LAND_WATER_PROMOTION"
    write_table(map_path, fields, rows)

    changes = package / "data_sources" / "CHANGES.csv"
    fields, rows = table(changes)
    for row in rows:
        if row["change_id"] == "CHG_PHL_V18_LAND_WATER_CLOSURE_20260813":
            row["notes"] += " Promotion passed for 22 source JSON files, byte-identical data.txt, canonicalized processed-set membership and matching GLPK dimensions; no live CBC rerun."
    write_table(changes, fields, rows)

    promotion_note = """

## Promotion identity

The promoted companion live case passed identity checks for all 22 root source
JSON files. Live `data.txt` is byte-identical to the solved candidate. The
processed files differ only in unordered derived set declarations and become
byte-identical after canonical sorting. GLPK reproduced 791,517 rows, 886,010
columns, 12,817,475 matrix nonzeros and 423,240 objective nonzeros. No
post-promotion CBC optimization was run.
"""
    for path in (
        live / "documentation" / "MODEL_FIXES_LAND_WATER_CLOSURE_2026-08-13.md",
        package / "documentation" / "MODEL_FIXES_LAND_WATER_CLOSURE_2026-08-13.md",
        package / "data_sources" / "calculation_notes" / "land_water_closure_v18_2026-08-13.md",
    ):
        text = path.read_text(encoding="utf-8")
        if "## Promotion identity" not in text:
            path.write_text(text.rstrip() + promotion_note + "\n", encoding="utf-8")

    for script in (
        "verify_philippines_v18_land_water_promotion.py",
        "complete_philippines_v18_land_water_delivery.py",
    ):
        shutil.copy2(repo / "scripts" / script, package / "scripts" / script)

    muio = package / "muio"
    muio.mkdir(exist_ok=True)
    old_archive = muio / "Philippines_v18_v18.0.0_MUIO.zip"
    if old_archive.exists():
        old_archive.unlink()
    archive = muio / ARCHIVE_NAME
    member_count = build_archive(live, archive)
    digest = sha256(archive)
    size = archive.stat().st_size
    write_table(
        package / "data_sources" / "V18_MODEL_ARCHIVE_MANIFEST.csv",
        ["archive", "sha256", "size_bytes", "member_count", "internal_root", "result_files_included", "notes"],
        [{
            "archive": archive.name, "sha256": digest, "size_bytes": str(size),
            "member_count": str(member_count), "internal_root": "Philippines_v18/",
            "result_files_included": "false",
            "notes": "Complete editable v18.0.1 source and documentation; all res/ and generated solver/result files excluded.",
        }],
    )
    write_table(
        package / "data_sources" / "evidence" / "CURRENT_MODEL_ARCHIVE_MANIFEST.csv",
        ["package_relative_path", "size_bytes", "sha256", "zip_member_count", "internal_root"],
        [{
            "package_relative_path": f"muio/{archive.name}", "size_bytes": str(size), "sha256": digest,
            "zip_member_count": str(member_count), "internal_root": "Philippines_v18/",
        }],
    )
    checksum = muio / "SHA256SUMS"
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")

    sources = package / "data_sources" / "SOURCES.csv"
    fields, rows = table(sources)
    manifest_files = {
        "V18_MODEL_ARCHIVE_MANIFEST.csv": package / "data_sources" / "V18_MODEL_ARCHIVE_MANIFEST.csv",
        "evidence/CURRENT_MODEL_ARCHIVE_MANIFEST.csv": package / "data_sources" / "evidence" / "CURRENT_MODEL_ARCHIVE_MANIFEST.csv",
    }
    updated = 0
    for row in rows:
        if row["local_file"] in manifest_files:
            row["sha256"] = sha256(manifest_files[row["local_file"]])
            updated += 1
    if updated != 3:
        raise AssertionError(f"expected three archive-manifest source rows, updated {updated}")
    write_table(sources, fields, rows)

    report = {
        "schema": "philippines-v18-land-water-delivery-build-v1",
        "status": "pass",
        "live_case": str(live),
        "archive": str(archive),
        "archive_sha256": digest,
        "archive_size_bytes": size,
        "archive_member_count": member_count,
        "result_files_included": False,
        "optimizer_runs_total": 2,
        "post_promotion_optimizer_runs": 0,
    }
    write_json(snapshots / "land_water_closure_delivery_build.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
