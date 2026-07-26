#!/usr/bin/env python3
"""Import the authoritative Philippines v10 Fisheries v2.3 block into v12.

The importer copies Fisheries technology/commodity definitions and every
dimensioned parameter record that references them.  It also imports the
PHL_INDU_OTH SpecifiedAnnualDemand row because the processing-demand carve-out
is part of the Fisheries accounting boundary.  Dimension-expansion records
created by v12's 30-mode nexus integration are retained when v10 has no
corresponding key.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any


ID_FIELDS = (
    "TechId",
    "CommId",
    "EmisId",
    "StgId",
    "ConId",
    "TsId",
    "SeId",
    "DtId",
    "DtbId",
    "MoId",
)

DOCUMENTS = {
    "FSH_CALIBRATION.md": "FSH_CALIBRATION_v2.3.md",
    "FSH_GLOBAL_PARITY.md": "FSH_GLOBAL_PARITY_v2.3.md",
    "FSH_calibration_data.csv": "FSH_calibration_data_v2.3.csv",
    "FSH_industry_carveout.csv": "FSH_industry_carveout_v2.3.csv",
}


def load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def dump(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=4)


def canonical_hash(data: Any) -> str:
    encoded = json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def update_document_links(path: Path, build_copy: bool) -> None:
    """Make copied v2.3 document links match the cleaned folder layout."""
    text = path.read_text(encoding="utf-8")
    if build_copy:
        replacements = {
            "FSH_calibration_data.csv":
                "../../evidence/fisheries/FSH_calibration_data_v2.3.csv",
            "FSH_industry_carveout.csv":
                "../../evidence/fisheries/FSH_industry_carveout_v2.3.csv",
            "FSH_GLOBAL_PARITY.md": "FSH_GLOBAL_PARITY_v2.3.md",
        }
    else:
        replacements = {
            "FSH_calibration_data.csv": "FSH_calibration_data_v2.3.csv",
            "FSH_industry_carveout.csv":
                "FSH_industry_carveout_v2.3.csv",
            "FSH_GLOBAL_PARITY.md": "FSH_GLOBAL_PARITY_v2.3.md",
        }
    for old, new in replacements.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def row_key(row: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple((field, row[field]) for field in ID_FIELDS if field in row)


def is_sector_row(
    row: dict[str, Any],
    filename: str,
    parameter: str,
    fish_tech_ids: set[str],
    fish_comm_ids: set[str],
    industry_comm_id: str,
) -> bool:
    if row.get("TechId") in fish_tech_ids:
        return True
    if row.get("CommId") in fish_comm_ids:
        return True
    return (
        filename == "RYC.json"
        and parameter == "SAD"
        and row.get("CommId") == industry_comm_id
    )


def scalar_sector_keys(
    row: dict[str, Any], fish_tech_ids: set[str], fish_comm_ids: set[str]
) -> set[str]:
    return (set(row) & fish_tech_ids) | (set(row) & fish_comm_ids)


def masked_non_fisheries(
    filename: str,
    data: Any,
    fish_tech_ids: set[str],
    fish_comm_ids: set[str],
    industry_comm_id: str,
) -> Any:
    masked = deepcopy(data)
    if filename == "genData.json":
        masked["osy-tech"] = [
            item
            for item in masked["osy-tech"]
            if item.get("TechId") not in fish_tech_ids
        ]
        masked["osy-comm"] = [
            item
            for item in masked["osy-comm"]
            if item.get("CommId") not in fish_comm_ids
        ]
        return masked

    for parameter, scenarios in masked.items():
        if not isinstance(scenarios, dict):
            continue
        for scenario, rows in scenarios.items():
            if not isinstance(rows, list):
                continue
            kept: list[Any] = []
            for row in rows:
                if not isinstance(row, dict):
                    kept.append(row)
                    continue
                if is_sector_row(
                    row,
                    filename,
                    parameter,
                    fish_tech_ids,
                    fish_comm_ids,
                    industry_comm_id,
                ):
                    continue
                for key in scalar_sector_keys(row, fish_tech_ids, fish_comm_ids):
                    row.pop(key)
                kept.append(row)
            scenarios[scenario] = kept
    return masked


def merge_parameter_file(
    filename: str,
    source_data: dict[str, Any],
    target_data: dict[str, Any],
    fish_tech_ids: set[str],
    fish_comm_ids: set[str],
    industry_comm_id: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    merged = deepcopy(target_data)
    counts = {
        "records_replaced": 0,
        "records_added": 0,
        "records_removed": 0,
        "scalar_values_replaced": 0,
        "v12_dimension_rows_retained": 0,
    }

    for parameter, source_scenarios in source_data.items():
        if parameter not in merged:
            merged[parameter] = {}
        for scenario, source_rows in source_scenarios.items():
            if scenario not in merged[parameter]:
                merged[parameter][scenario] = []
            target_rows = merged[parameter][scenario]

            source_selected = {
                row_key(row): deepcopy(row)
                for row in source_rows
                if isinstance(row, dict)
                and row_key(row)
                and is_sector_row(
                    row,
                    filename,
                    parameter,
                    fish_tech_ids,
                    fish_comm_ids,
                    industry_comm_id,
                )
            }
            remaining = dict(source_selected)
            rebuilt: list[Any] = []

            for target_row in target_rows:
                if not isinstance(target_row, dict):
                    rebuilt.append(target_row)
                    continue

                key = row_key(target_row)
                if key and is_sector_row(
                    target_row,
                    filename,
                    parameter,
                    fish_tech_ids,
                    fish_comm_ids,
                    industry_comm_id,
                ):
                    if key in source_selected:
                        replacement = source_selected[key]
                        rebuilt.append(replacement)
                        remaining.pop(key, None)
                        if replacement != target_row:
                            counts["records_replaced"] += 1
                    else:
                        rebuilt.append(target_row)
                        counts["v12_dimension_rows_retained"] += 1
                    continue

                scalar_keys = scalar_sector_keys(
                    target_row, fish_tech_ids, fish_comm_ids
                )
                if scalar_keys:
                    source_scalar = next(
                        (
                            row
                            for row in source_rows
                            if isinstance(row, dict)
                            and not row_key(row)
                            and scalar_sector_keys(
                                row, fish_tech_ids, fish_comm_ids
                            )
                        ),
                        None,
                    )
                    if source_scalar is None:
                        for scalar_key in scalar_keys:
                            target_row.pop(scalar_key, None)
                            counts["records_removed"] += 1
                    else:
                        for scalar_key in (
                            scalar_sector_keys(
                                source_scalar, fish_tech_ids, fish_comm_ids
                            )
                        ):
                            if target_row.get(scalar_key) != source_scalar[scalar_key]:
                                counts["scalar_values_replaced"] += 1
                            target_row[scalar_key] = deepcopy(
                                source_scalar[scalar_key]
                            )
                rebuilt.append(target_row)

            for source_row in remaining.values():
                rebuilt.append(source_row)
                counts["records_added"] += 1
            merged[parameter][scenario] = rebuilt

    return merged, counts


def verify_parity(
    source: Path,
    target: Path,
    fish_tech_ids: set[str],
    fish_comm_ids: set[str],
    industry_comm_id: str,
) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    checked_records = 0
    checked_scalar_values = 0

    source_gen = load(source / "genData.json")
    target_gen = load(target / "genData.json")
    for group, id_field, selected in (
        ("osy-tech", "TechId", fish_tech_ids),
        ("osy-comm", "CommId", fish_comm_ids),
    ):
        source_items = {
            item[id_field]: item
            for item in source_gen[group]
            if item[id_field] in selected
        }
        target_items = {item[id_field]: item for item in target_gen[group]}
        for item_id, source_item in source_items.items():
            checked_records += 1
            if target_items.get(item_id) != source_item:
                mismatches.append(
                    {
                        "file": "genData.json",
                        "group": group,
                        "id": item_id,
                        "issue": "definition mismatch",
                    }
                )

    for source_path in sorted(source.glob("*.json")):
        if source_path.name == "genData.json":
            continue
        target_path = target / source_path.name
        if not target_path.exists():
            mismatches.append(
                {"file": source_path.name, "issue": "missing target file"}
            )
            continue
        source_data = load(source_path)
        target_data = load(target_path)
        for parameter, source_scenarios in source_data.items():
            for scenario, source_rows in source_scenarios.items():
                target_rows = target_data.get(parameter, {}).get(scenario, [])
                target_by_key = {
                    row_key(row): row
                    for row in target_rows
                    if isinstance(row, dict) and row_key(row)
                }
                for source_row in source_rows:
                    if not isinstance(source_row, dict):
                        continue
                    key = row_key(source_row)
                    if key and is_sector_row(
                        source_row,
                        source_path.name,
                        parameter,
                        fish_tech_ids,
                        fish_comm_ids,
                        industry_comm_id,
                    ):
                        checked_records += 1
                        if target_by_key.get(key) != source_row:
                            mismatches.append(
                                {
                                    "file": source_path.name,
                                    "parameter": parameter,
                                    "scenario": scenario,
                                    "key": list(key),
                                    "issue": "parameter mismatch",
                                }
                            )
                    if not key:
                        for scalar_key in scalar_sector_keys(
                            source_row, fish_tech_ids, fish_comm_ids
                        ):
                            checked_scalar_values += 1
                            target_scalar = next(
                                (
                                    row
                                    for row in target_rows
                                    if isinstance(row, dict) and not row_key(row)
                                ),
                                {},
                            )
                            if target_scalar.get(scalar_key) != source_row[scalar_key]:
                                mismatches.append(
                                    {
                                        "file": source_path.name,
                                        "parameter": parameter,
                                        "scenario": scenario,
                                        "field": scalar_key,
                                        "issue": "scalar mismatch",
                                    }
                                )
    return {
        "status": "PASS" if not mismatches else "FAIL",
        "checked_dimensioned_records_and_definitions": checked_records,
        "checked_scalar_values": checked_scalar_values,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    build = repo / "Philippines_v12_CLEWs_build"
    source = repo / "WebAPP/DataStorage/Philippines_v10"
    target = repo / "WebAPP/DataStorage/Philippines_v12"
    build_notes = build / "data_sources/calculation_notes/fisheries"
    build_evidence = build / "data_sources/evidence/fisheries"
    target_documentation = (
        target / "documentation/data_sources/fisheries"
    )
    diagnostics = build / "diagnostics"

    source_gen = load(source / "genData.json")
    target_gen = load(target / "genData.json")
    fish_tech_ids = {
        item["TechId"]
        for item in source_gen["osy-tech"]
        if item["Tech"].startswith("PHL_FSH_")
        or item["Tech"] == "PHL_POW_TD_FSH"
    }
    fish_comm_ids = {
        item["CommId"]
        for item in source_gen["osy-comm"]
        if item["Comm"].startswith("PHL_FSH_")
    }
    industry_comm_id = next(
        item["CommId"]
        for item in source_gen["osy-comm"]
        if item["Comm"] == "PHL_INDU_OTH"
    )
    source_tech = {
        item["TechId"]: item
        for item in source_gen["osy-tech"]
        if item["TechId"] in fish_tech_ids
    }
    source_comm = {
        item["CommId"]: item
        for item in source_gen["osy-comm"]
        if item["CommId"] in fish_comm_ids
    }
    merged_gen = deepcopy(target_gen)
    for group, id_field, replacements in (
        ("osy-tech", "TechId", source_tech),
        ("osy-comm", "CommId", source_comm),
    ):
        merged_gen[group] = [
            deepcopy(replacements.get(item[id_field], item))
            for item in merged_gen[group]
        ]
        present = {item[id_field] for item in merged_gen[group]}
        merged_gen[group].extend(
            deepcopy(item)
            for item_id, item in replacements.items()
            if item_id not in present
        )

    json_before: dict[str, Any] = {}
    json_after: dict[str, Any] = {}
    changes_by_file: dict[str, Any] = {}
    json_files = sorted(
        path.name
        for path in source.glob("*.json")
        if (target / path.name).exists()
    )
    for filename in json_files:
        target_data = load(target / filename)
        source_data = load(source / filename)
        json_before[filename] = target_data
        if filename == "genData.json":
            merged = merged_gen
            counts = {
                "definitions_replaced": sum(
                    1
                    for group, id_field, selected in (
                        ("osy-tech", "TechId", fish_tech_ids),
                        ("osy-comm", "CommId", fish_comm_ids),
                    )
                    for old, new in zip(target_gen[group], merged_gen[group])
                    if old.get(id_field) in selected and old != new
                )
            }
        else:
            merged, counts = merge_parameter_file(
                filename,
                source_data,
                target_data,
                fish_tech_ids,
                fish_comm_ids,
                industry_comm_id,
            )
        json_after[filename] = merged
        if canonical_hash(target_data) != canonical_hash(merged):
            changes_by_file[filename] = counts

    before_nonfish = {
        filename: canonical_hash(
            masked_non_fisheries(
                filename,
                data,
                fish_tech_ids,
                fish_comm_ids,
                industry_comm_id,
            )
        )
        for filename, data in json_before.items()
    }
    after_nonfish = {
        filename: canonical_hash(
            masked_non_fisheries(
                filename,
                data,
                fish_tech_ids,
                fish_comm_ids,
                industry_comm_id,
            )
        )
        for filename, data in json_after.items()
    }
    nonfish_mismatches = sorted(
        filename
        for filename in before_nonfish
        if before_nonfish[filename] != after_nonfish[filename]
    )
    if nonfish_mismatches:
        raise RuntimeError(
            "Non-Fisheries semantic records changed: "
            + ", ".join(nonfish_mismatches)
        )

    preview = {
        "status": "DRY_RUN" if args.dry_run else "IMPORTED",
        "source": str(source),
        "target": str(target),
        "fisheries_version": "v2.3",
        "fish_technology_ids": sorted(fish_tech_ids),
        "fish_commodity_ids": sorted(fish_comm_ids),
        "industry_boundary_commodity_id": industry_comm_id,
        "changed_json_files": changes_by_file,
        "non_fisheries_preservation": {
            "status": "PASS",
            "changed_files": nonfish_mismatches,
        },
    }
    if args.dry_run:
        print(json.dumps(preview, indent=2))
        return

    for filename, merged in json_after.items():
        if filename in changes_by_file:
            dump(target / filename, merged)

    build_notes.mkdir(parents=True, exist_ok=True)
    build_evidence.mkdir(parents=True, exist_ok=True)
    target_documentation.mkdir(parents=True, exist_ok=True)
    document_hashes: dict[str, str] = {}
    for source_name, destination_name in DOCUMENTS.items():
        build_destination = (
            build_notes / destination_name
            if destination_name.endswith(".md")
            else build_evidence / destination_name
        )
        target_destination = target_documentation / destination_name
        shutil.copy2(source / source_name, build_destination)
        shutil.copy2(source / source_name, target_destination)
        update_document_links(build_destination, build_copy=True)
        update_document_links(target_destination, build_copy=False)
        document_hashes[source_name] = file_hash(source / source_name)

    parity = verify_parity(
        source,
        target,
        fish_tech_ids,
        fish_comm_ids,
        industry_comm_id,
    )
    report = {
        **preview,
        "import_date": date.today().isoformat(),
        "source_documentation": {
            "status": "PASS",
            "files": document_hashes,
            "package_location": str(build / "data_sources"),
        },
        "fisheries_parameter_parity": parity,
        "overall_status": (
            "PASS"
            if parity["status"] == "PASS" and not nonfish_mismatches
            else "FAIL"
        ),
    }
    diagnostics.mkdir(parents=True, exist_ok=True)
    dump(diagnostics / "fisheries_v23_import_audit.json", report)
    print(json.dumps(report, indent=2))
    if report["overall_status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
