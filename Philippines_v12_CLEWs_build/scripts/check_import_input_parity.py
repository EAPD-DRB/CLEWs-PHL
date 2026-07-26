#!/usr/bin/env python3
"""Compare source CLEWs CSV rows with an otoole round-trip of MUIO data."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path


def normalized(value: str) -> str:
    value = value.strip()
    if value in {"GLOBAL", "RE1"}:
        return "<REGION>"
    try:
        number = float(value)
    except ValueError:
        return value
    if number.is_integer():
        return str(int(number))
    return format(number, ".15g")


def read_rows(path: Path) -> tuple[list[str], dict[tuple[str, ...], float | None]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        rows: dict[tuple[str, ...], float | None] = {}
        if fields == ["VALUE"]:
            for row in reader:
                rows[(normalized(row["VALUE"]),)] = None
            return fields, rows
        indices = [field for field in fields if field != "VALUE"]
        for row in reader:
            key = tuple(normalized(row[field]) for field in indices)
            rows[key] = float(row["VALUE"])
        return fields, rows


def config_defaults(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    starts = list(re.finditer(r"^([A-Za-z][A-Za-z0-9_]*):\s*$", text, re.MULTILINE))
    defaults: dict[str, float] = {}
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[match.end() : end]
        default = re.search(r"^\s+default:\s+([-+0-9.eE]+)\s*$", block, re.MULTILINE)
        if default:
            defaults[match.group(1)] = float(default.group(1))
    return defaults


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("roundtrip", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    defaults = config_defaults(args.config)
    files = []
    total_source_rows = 0
    total_matching_rows = 0
    for source_path in sorted(args.source.glob("*.csv")):
        fields, source_rows = read_rows(source_path)
        total_source_rows += len(source_rows)
        roundtrip_path = args.roundtrip / source_path.name
        if not roundtrip_path.exists():
            files.append(
                {
                    "file": source_path.name,
                    "source_rows": len(source_rows),
                    "status": "not_generated",
                    "missing_rows": len(source_rows),
                }
            )
            continue
        roundtrip_fields, roundtrip_rows = read_rows(roundtrip_path)
        missing = []
        differing = []
        matching = 0
        implicit_default = 0
        for key, expected in source_rows.items():
            if key not in roundtrip_rows:
                default = defaults.get(source_path.stem)
                if (
                    expected is not None
                    and default is not None
                    and math.isclose(expected, default, rel_tol=1e-9, abs_tol=1e-10)
                ):
                    matching += 1
                    implicit_default += 1
                    continue
                missing.append(key)
                continue
            actual = roundtrip_rows[key]
            if expected is None or math.isclose(expected, actual, rel_tol=1e-9, abs_tol=1e-10):
                matching += 1
            else:
                differing.append({"key": key, "source": expected, "muiogo": actual})
        total_matching_rows += matching
        files.append(
            {
                "file": source_path.name,
                "source_rows": len(source_rows),
                "matching_rows": matching,
                "implicit_default_rows": implicit_default,
                "missing_rows": len(missing),
                "differing_rows": len(differing),
                "extra_generated_rows": len(set(roundtrip_rows) - set(source_rows)),
                "status": "exact" if matching == len(source_rows) else "mismatch",
                "missing_examples": missing[:5],
                "difference_examples": differing[:5],
                "source_fields": fields,
                "roundtrip_fields": roundtrip_fields,
            }
        )

    report = {
        "source_rows": total_source_rows,
        "matching_rows": total_matching_rows,
        "match_fraction": total_matching_rows / total_source_rows,
        "files_exact": sum(item["status"] == "exact" for item in files),
        "files_mismatch": sum(item["status"] == "mismatch" for item in files),
        "files_not_generated": sum(item["status"] == "not_generated" for item in files),
        "files": files,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "files"}, indent=2))
    for item in files:
        if item["source_rows"] and item["status"] != "exact":
            print(
                item["file"],
                {
                    key: item[key]
                    for key in ("source_rows", "matching_rows", "missing_rows", "differing_rows", "status")
                    if key in item
                },
            )


if __name__ == "__main__":
    main()
