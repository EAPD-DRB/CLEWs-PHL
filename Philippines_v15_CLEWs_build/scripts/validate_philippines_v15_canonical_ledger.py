#!/usr/bin/env python3
"""Validate the cumulative Philippines v15 ledger without earlier live cases."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


PACKAGE = Path(__file__).resolve().parents[1]
LEDGER = PACKAGE / "data_sources"
EVIDENCE = LEDGER / "evidence"
ARCHIVE = PACKAGE / "muio" / "Philippines_v15_v15.0.0_MUIO.zip"
REPORT = PACKAGE / "diagnostics" / "canonical_schema_ledger_validation.json"
GENERIC_REPORT = PACKAGE / "diagnostics" / "schema_ledger_build.json"

EXPECTED_COUNTS = {
    "SOURCES.csv": 76,
    "CALCULATIONS.csv": 67,
    "ASSUMPTIONS.csv": 38,
    "MODEL_MAP.csv": 71946,
    "GAPS.csv": 17,
    "CHANGES.csv": 10,
}

REQUIRED_V15_MAPS = {
    "MAP_PHL_V15_LINEAGE",
    "MAP_PHL_GWT_IRRIGATION_STRUCTURE",
    "MAP_PHL_GWT_IRRIGATION_IAR",
    "MAP_PHL_CLIMATE_RYTCM",
    "MAP_PHL_SURFACE_UCC",
    "MAP_PHL_GROUNDWATER_UCC",
    "MAP_PHL_WATER_MANIFEST",
    "MAP_PHL_WATER_VALIDATION",
    "MAP_PHL_WATER_LEDGER",
    "MAP_PHL_V15_CANONICAL_PACKAGE",
}


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


def main() -> int:
    checks: list[dict[str, object]] = []

    def check(name: str, operation: Callable[[], object]) -> object | None:
        try:
            detail = operation()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "detail": f"{type(error).__name__}: {error}"})
            return None
        checks.append({"name": name, "status": "pass", "detail": detail})
        return detail

    tables = {name: read_csv(LEDGER / name) for name in EXPECTED_COUNTS}

    def table_counts() -> dict[str, int]:
        actual = {name: len(rows) for name, rows in tables.items()}
        require(actual == EXPECTED_COUNTS, f"row counts differ: {actual}")
        return actual

    check("canonical_table_counts", table_counts)

    def generic_schema() -> dict[str, object]:
        result = subprocess.run(
            [sys.executable, str(PACKAGE / "scripts" / "provenance.py"), str(LEDGER), "--stage", "build", "--json", str(GENERIC_REPORT)],
            cwd=PACKAGE.parent,
            text=True,
            capture_output=True,
            check=False,
        )
        report = json.loads(GENERIC_REPORT.read_text(encoding="utf-8"))
        require(result.returncode == 0 and report["failure_count"] == 0, result.stdout + result.stderr)
        return {"failure_count": report["failure_count"], "warning_count": report["warning_count"], "verified_digests": report["verified_digests"]}

    check("generic_six_table_schema", generic_schema)

    def retained_manifest() -> dict[str, int]:
        manifest_path = EVIDENCE / "RETAINED_EVIDENCE_MANIFEST.csv"
        rows = read_csv(manifest_path)
        listed = set()
        for row in rows:
            relative = row["relative_path"]
            require(not Path(relative).is_absolute() and ".." not in Path(relative).parts, f"unsafe evidence path {relative}")
            path = LEDGER / relative
            require(path.is_file(), f"missing retained evidence {relative}")
            require(path.stat().st_size == int(row["size_bytes"]), f"size mismatch {relative}")
            require(sha256(path) == row["sha256"], f"digest mismatch {relative}")
            listed.add(relative)
        actual = {
            path.relative_to(LEDGER).as_posix()
            for path in EVIDENCE.rglob("*")
            if path.is_file() and path.name not in {"RETAINED_EVIDENCE_MANIFEST.csv", "CURRENT_MODEL_ARCHIVE_MANIFEST.csv"}
        }
        require(actual == listed, f"manifest coverage differs; unlisted={sorted(actual-listed)} missing={sorted(listed-actual)}")
        return {"files": len(rows), "bytes": sum(int(row["size_bytes"]) for row in rows)}

    check("retained_evidence_manifest", retained_manifest)

    def current_archive() -> dict[str, object]:
        rows = read_csv(EVIDENCE / "CURRENT_MODEL_ARCHIVE_MANIFEST.csv")
        require(len(rows) == 1, "archive manifest must have one row")
        row = rows[0]
        require((PACKAGE / row["package_relative_path"]).resolve() == ARCHIVE.resolve(), "archive manifest points elsewhere")
        require(ARCHIVE.stat().st_size == int(row["size_bytes"]), "archive size mismatch")
        require(sha256(ARCHIVE) == row["sha256"], "archive digest mismatch")
        with zipfile.ZipFile(ARCHIVE) as archive:
            members = {name for name in archive.namelist() if not name.endswith("/")}
        require(len(members) == int(row["zip_member_count"]), "archive member count mismatch")
        required = {
            "Philippines_v15/genData.json", "Philippines_v15/RYT.json",
            "Philippines_v15/RYTEM.json", "Philippines_v15/RYTCM.json",
            "Philippines_v15/RYTCn.json", "Philippines_v15/RYCn.json",
            "Philippines_v15/documentation/national_water_manifest.json",
            "Philippines_v15/documentation/national_water_validation.json",
        }
        require(required <= members, f"archive lacks {sorted(required-members)}")
        return {"sha256": row["sha256"], "members": len(members), "bytes": ARCHIVE.stat().st_size}

    check("current_v15_model_archive", current_archive)

    def lineage_coverage() -> dict[str, int]:
        maps = tables["MODEL_MAP.csv"]
        inherited = sum(row.get("notes", "").startswith("Retained inherited-base mapping") for row in maps)
        v13_factors = sum(bool(re.fullmatch(r"MAP_PHL_V13_PM25_\d{2}", row["map_id"])) for row in maps)
        v14_cells = sum(row["map_id"].startswith("MAP_PHL_V14_CHANGE_") for row in maps)
        ids = {row["map_id"] for row in maps}
        require(inherited == 68624, f"expected 68,624 inherited rows, found {inherited}")
        require(v13_factors == 18, f"expected 18 v13 PM2.5 factors, found {v13_factors}")
        require(v14_cells == 3253, f"expected 3,253 v14 cell changes, found {v14_cells}")
        require(REQUIRED_V15_MAPS <= ids, f"missing v15 maps {sorted(REQUIRED_V15_MAPS-ids)}")
        return {"inherited_base_rows": inherited, "v13_pm25_factor_rows": v13_factors, "v14_cell_change_rows": v14_cells, "v15_required_rows": len(REQUIRED_V15_MAPS)}

    check("cumulative_lineage_mapping", lineage_coverage)

    def no_external_version_dependency() -> dict[str, int]:
        banned = (
            "Philippines_v12_CLEWs_build",
            "WebAPP/DataStorage/Philippines_v14_STOCK_TURNOVER",
            "docs/philippines_v14_stock_turnover",
        )
        inspected = 0
        for row in tables["SOURCES.csv"]:
            for column in ("local_file", "exact_locator"):
                value = row.get(column, "")
                require(not any(token in value for token in banned), f"{row['source_id']} {column} depends on another version: {value}")
                if column == "local_file" and value:
                    require(not Path(value).is_absolute() and ".." not in Path(value).parts, f"unsafe local_file {value}")
                    require((LEDGER / value).is_file(), f"missing local_file {value}")
                inspected += 1
        for row in tables["MODEL_MAP.csv"]:
            value = row["model_file"]
            require(not any(token in value for token in banned), f"{row['map_id']} depends on another version: {value}")
            inspected += 1
        allowed = (
            "config/config.yaml",
            "model/inputs/",
            "evidence/inherited_base/",
            "muio/Philippines_v15_v15.0.0_MUIO.zip",
        )
        require(
            all(
                row["model_file"] == allowed[0]
                or row["model_file"].startswith(allowed[1:3])
                or row["model_file"] == allowed[3]
                for row in tables["MODEL_MAP.csv"]
            ),
            "model maps point outside the active raw base, retained evidence, or current archive",
        )

        promoted = [PACKAGE / "config" / "config.yaml"] + sorted(
            (PACKAGE / "model" / "inputs").rglob("*.csv")
        )
        for active in promoted:
            relative = active.relative_to(PACKAGE)
            retained = EVIDENCE / "inherited_base" / "build_snapshot" / relative
            require(active.is_file(), f"missing active raw-build file {relative}")
            require(retained.is_file(), f"missing retained counterpart {relative}")
            require(sha256(active) == sha256(retained), f"active raw-build copy differs from retained evidence: {relative}")

        narrative_files = [
            PACKAGE / "README.md",
            LEDGER / "DATA_SOURCES.md",
            *(LEDGER / "calculation_notes").glob("*.md"),
            *(PACKAGE / "documentation").glob("*.md"),
            PACKAGE / "scripts" / "README.md",
        ]
        obsolete_narrative_pointers = (
            "docs/philippines_v14_stock_turnover",
            "docs/philippines_v15/data_sources",
        )
        for path in narrative_files:
            text = path.read_text(encoding="utf-8")
            require(
                not any(token in text for token in obsolete_narrative_pointers),
                f"active narrative contains an obsolete provenance pointer: {path.relative_to(PACKAGE)}",
            )
        return {
            "fields_inspected": inspected,
            "promoted_raw_files_verified": len(promoted),
            "active_narrative_files_verified": len(narrative_files),
        }

    check("no_external_version_dependency", no_external_version_dependency)

    def no_blanket_inheritance() -> dict[str, int]:
        maps = tables["MODEL_MAP.csv"]
        blanket = [row for row in maps if row["map_id"] == "MAP_PHL_V15_LINEAGE"]
        require(len(blanket) == 1, "lineage summary missing or duplicated")
        require(len(maps) > 70000, "lineage summary is still substituting for detailed mappings")
        require("SRC_PHL_INHERITED_BASE_SNAPSHOT" in blanket[0]["evidence_ids"], "lineage summary lacks retained base evidence")
        require("SRC_PHL_V15_RETAINED_EVIDENCE" in blanket[0]["evidence_ids"], "lineage summary lacks retained-evidence manifest")
        return {"summary_rows": 1, "detailed_rows": len(maps) - 1}

    check("blanket_parent_reference_is_not_the_ledger", no_blanket_inheritance)

    status = "pass" if all(item["status"] == "pass" for item in checks) else "fail"
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "validator": "Philippines_v15_CLEWs_build/scripts/validate_philippines_v15_canonical_ledger.py",
        "ledger_dir": "Philippines_v15_CLEWs_build/data_sources",
        "model_archive": "Philippines_v15_CLEWs_build/muio/Philippines_v15_v15.0.0_MUIO.zip",
        "requires_earlier_live_case": False,
        "status": status,
        "checks": checks,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
