#!/usr/bin/env python3
"""Compare overlapping upstream and MUIO result CSVs after an import."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path


ABBREVIATIONS = {
    "REGION": "r",
    "TIMESLICE": "l",
    "TECHNOLOGY": "t",
    "MODE_OF_OPERATION": "m",
    "FUEL": "f",
    "EMISSION": "e",
    "YEAR": "y",
}


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


def source_rows(path: Path) -> tuple[list[str], dict[tuple[str, ...], float]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        indices = [field for field in reader.fieldnames or [] if field != "VALUE"]
        return indices, {
            tuple(normalized(row[field]) for field in indices): float(row["VALUE"])
            for row in reader
        }


def muiogo_rows(
    path: Path, source_indices: list[str]
) -> dict[tuple[str, ...], float]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        value_field = fields[-1]
        rows = {}
        for row in reader:
            key_values = []
            for source_field in source_indices:
                short = ABBREVIATIONS[source_field]
                if short in row:
                    value = row[short]
                elif f"{short}_x" in row:
                    value = row[f"{short}_x"]
                else:
                    raise KeyError(f"{path}: cannot map {source_field} from {fields}")
                key_values.append(normalized(value))
            rows[tuple(key_values)] = float(row[value_field])
        return rows


def objective_from_solution(path: Path) -> float:
    first_line = path.open(encoding="utf-8").readline()
    match = re.search(r"objective value\s+([-+0-9.eE]+)", first_line)
    if not match:
        raise ValueError(f"Cannot read objective from {path}")
    return float(match.group(1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_results", type=Path)
    parser.add_argument("muiogo_results", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--upstream-solution", type=Path, required=True)
    args = parser.parse_args()

    overlap = sorted(
        {path.name for path in args.upstream_results.glob("*.csv")}
        & {path.name for path in args.muiogo_results.glob("*.csv")}
    )
    comparisons = []
    for filename in overlap:
        indices, upstream = source_rows(args.upstream_results / filename)
        muiogo = muiogo_rows(args.muiogo_results / filename, indices)
        matches = 0
        absolute_errors = []
        for key, expected in upstream.items():
            actual = muiogo.get(key, 0.0)
            absolute_errors.append(abs(expected - actual))
            if math.isclose(expected, actual, rel_tol=1e-4, abs_tol=5e-4):
                matches += 1
        extra_nonzero = sum(
            key not in upstream and not math.isclose(value, 0.0, abs_tol=5e-4)
            for key, value in muiogo.items()
        )
        comparisons.append(
            {
                "file": filename,
                "upstream_nonzero_rows": len(upstream),
                "matching_rows": matches,
                "match_fraction": matches / len(upstream) if upstream else 1.0,
                "muiogo_extra_nonzero_rows": extra_nonzero,
                "mean_absolute_error": (
                    sum(absolute_errors) / len(absolute_errors) if absolute_errors else 0.0
                ),
                "max_absolute_error": max(absolute_errors, default=0.0),
            }
        )

    upstream_objective = objective_from_solution(args.upstream_solution)
    with (args.muiogo_results / "ObjectiveValue.csv").open(
        newline="", encoding="utf-8-sig"
    ) as stream:
        muiogo_objective = float(next(csv.DictReader(stream))["ObjectiveValue"])
    report = {
        "upstream_objective": upstream_objective,
        "muiogo_objective": muiogo_objective,
        "objective_difference": muiogo_objective - upstream_objective,
        "objective_ratio": muiogo_objective / upstream_objective,
        "overlapping_result_files": len(comparisons),
        "files": comparisons,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "files"}, indent=2
        )
    )
    for item in comparisons:
        print(
            item["file"],
            {
                key: item[key]
                for key in (
                    "upstream_nonzero_rows",
                    "matching_rows",
                    "match_fraction",
                    "muiogo_extra_nonzero_rows",
                )
            },
        )


if __name__ == "__main__":
    main()
