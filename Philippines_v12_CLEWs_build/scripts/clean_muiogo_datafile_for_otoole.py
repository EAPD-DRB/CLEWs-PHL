#!/usr/bin/env python3
"""Create an otoole-readable copy of a MUIO data file for parity analysis.

MUIO uses COMMODITY instead of FUEL and writes extra user-defined-constraint
sets/parameters.  The optimization data file itself is not changed.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


TOP_LEVEL_NAME = re.compile(r"^([A-Za-z][A-Za-z0-9_]*):\s*$", re.MULTILINE)
PARAM_START = re.compile(r"^param\s+([^\s:]+)", re.MULTILINE)


def configured_names(config_path: Path) -> set[str]:
    return set(TOP_LEVEL_NAME.findall(config_path.read_text(encoding="utf-8")))


def populated_source_names(inputs: Path) -> set[str]:
    populated: set[str] = set()
    for path in inputs.glob("*.csv"):
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.reader(stream)
            next(reader, None)
            if next(reader, None) is not None:
                populated.add(path.stem)
    return populated


def filter_parameters(text: str, allowed: set[str]) -> tuple[str, list[str]]:
    matches = list(PARAM_START.finditer(text))
    removed: list[str] = []
    pieces: list[str] = []
    cursor = 0
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else text.index("#\nend;", match.start())
        pieces.append(text[cursor : match.start()])
        name = match.group(1)
        if name in allowed:
            pieces.append(text[match.start() : end])
        else:
            removed.append(name)
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces), removed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-inputs", type=Path, required=True)
    args = parser.parse_args()

    configured = configured_names(args.config)
    populated = populated_source_names(args.source_inputs)
    allowed_parameters = configured & populated
    text = args.input.read_text(encoding="utf-8")
    text = re.sub(r"^set COMMODITY\b", "set FUEL", text, flags=re.MULTILINE)

    removed_sets: list[str] = []
    retained_lines: list[str] = []
    for line in text.splitlines(keepends=True):
        match = re.match(r"^set\s+([^\s:]+)", line)
        if match and match.group(1) not in configured:
            removed_sets.append(match.group(1))
            continue
        retained_lines.append(line)
    text, removed_parameters = filter_parameters(
        "".join(retained_lines), allowed_parameters
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"otoole parity copy: {args.output}")
    print(f"Removed MUIO-only sets: {', '.join(removed_sets)}")
    print(f"Removed MUIO-only parameters: {', '.join(removed_parameters)}")


if __name__ == "__main__":
    main()
