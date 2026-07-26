#!/usr/bin/env python3
"""One-off Philippines timeslice repair after MUIO's unmodified template importer.

ImportTemplate assigns every imported timeslice to the first season, day type,
and daily time bracket. This script reads the authoritative CLEWs Global
Conversionls/Conversionld/Conversionlh CSVs and repairs only those references
in the generated MUIO genData.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from pathlib import Path


DIMENSIONS = (
    ("SEASON", "Conversionls.csv", "osy-se", "Se", "SeId", "SE"),
    ("DAYTYPE", "Conversionld.csv", "osy-dt", "Dt", "DtId", "DT"),
    (
        "DAILYTIMEBRACKET",
        "Conversionlh.csv",
        "osy-dtb",
        "Dtb",
        "DtbId",
        "DTB",
    ),
)


def normalized(value) -> str:
    text = str(value).strip()
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer():
        return str(int(number))
    return format(number, ".15g")


def active_membership(path: Path, dimension: str) -> dict[str, str]:
    candidates: dict[str, list[str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            value = float(row["VALUE"])
            if math.isclose(value, 1.0, abs_tol=1e-12):
                candidates.setdefault(normalized(row["TIMESLICE"]), []).append(
                    normalized(row[dimension])
                )
            elif not math.isclose(value, 0.0, abs_tol=1e-12):
                raise ValueError(f"{path}: membership must be binary, found {value}")
    invalid = {key: values for key, values in candidates.items() if len(values) != 1}
    if invalid:
        raise ValueError(f"{path}: timeslices must have exactly one active member: {invalid}")
    return {key: values[0] for key, values in candidates.items()}


def day_split(path: Path) -> dict[str, dict[str, float]]:
    values: dict[str, dict[str, float]] = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            bracket = normalized(row["DAILYTIMEBRACKET"])
            values.setdefault(bracket, {})[normalized(row["YEAR"])] = float(row["VALUE"])
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_folder", type=Path)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--rydtb-backup", type=Path, required=True)
    args = parser.parse_args()

    gen_data_path = args.case_folder / "genData.json"
    with gen_data_path.open(encoding="utf-8") as stream:
        gen_data = json.load(stream)

    mappings: dict[str, dict[str, str]] = {}
    for dimension, filename, set_key, name_key, id_key, target_key in DIMENSIONS:
        set_ids = {normalized(item[name_key]): item[id_key] for item in gen_data[set_key]}
        memberships = active_membership(args.inputs / filename, dimension)
        mappings[target_key] = {
            timeslice: set_ids[member] for timeslice, member in memberships.items()
        }

    imported_timeslices = {normalized(item["Ts"]) for item in gen_data["osy-ts"]}
    for target_key, membership in mappings.items():
        if set(membership) != imported_timeslices:
            raise ValueError(
                f"{target_key} conversion timeslices do not match imported TIMESLICE set"
            )

    args.backup.parent.mkdir(parents=True, exist_ok=True)
    if not args.backup.exists():
        shutil.copy2(gen_data_path, args.backup)
    for item in gen_data["osy-ts"]:
        name = normalized(item["Ts"])
        for target_key, membership in mappings.items():
            item[target_key] = membership[name]

    temporary = gen_data_path.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(gen_data, stream, ensure_ascii=False, indent=4)
        stream.write("\n")
    temporary.replace(gen_data_path)

    rydtb_path = args.case_folder / "RYDtb.json"
    with rydtb_path.open(encoding="utf-8") as stream:
        rydtb = json.load(stream)
    if not args.rydtb_backup.exists():
        args.rydtb_backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(rydtb_path, args.rydtb_backup)

    dtb_names = {
        item["DtbId"]: normalized(item["Dtb"]) for item in gen_data["osy-dtb"]
    }
    split = day_split(args.inputs / "DaySplit.csv")
    imported_years = {normalized(year) for year in gen_data["osy-years"]}
    if any(set(year_values) != imported_years for year_values in split.values()):
        raise ValueError("DaySplit years do not match the imported YEAR set")
    for scenario, rows in rydtb["DS"].items():
        for row in rows:
            bracket = dtb_names[row["DtbId"]]
            for year, value in split[bracket].items():
                row[year] = value
    temporary = rydtb_path.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(rydtb, stream, ensure_ascii=False, indent=4)
        stream.write("\n")
    temporary.replace(rydtb_path)

    report = {
        item["Ts"]: {"SE": item["SE"], "DT": item["DT"], "DTB": item["DTB"]}
        for item in gen_data["osy-ts"]
    }
    print(json.dumps({"timeslices": report, "DaySplit": split}, indent=2))


if __name__ == "__main__":
    main()
