#!/usr/bin/env python3
"""Build or install the Philippines v16 irrigated-rice water data repair."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from decimal import Decimal, getcontext
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PACKAGE.parents[0] / "case" / "Philippines_v16"
INPUTS = PACKAGE / "data_sources" / "snapshots" / "irrigation_water_engineering_2026.json"
BASE = "SC_0"
WATER = "COM_sp9qb"
YEARS = tuple(str(year) for year in range(2020, 2054))
GLOBAL_FILES = ("Parameters.json", "Variables.json", "Duals.json", "Indicators.json")

getcontext().prec = 40


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expected_values(inputs: dict) -> dict[tuple[str, int], Decimal]:
    assumptions = inputs["engineering_assumptions"]
    efficiency = Decimal(str(assumptions["irrigation_efficiency_fraction"]))
    cropping = Decimal("3253454.36") / Decimal("2006000")
    paddy = Decimal(str(assumptions["paddy_addition_mm_per_crop"])) / Decimal("1000")
    return {
        (tech, int(mode)): (Decimal(deficit) + paddy) * cropping / efficiency
        for mode, rows in inputs["gaez_water_deficit_m_per_crop"].items()
        for tech, deficit in rows.items()
    }


def prepare_copy(source: Path, target: Path) -> None:
    if target.exists():
        raise FileExistsError(f"refusing to replace target: {target}")
    if target.resolve() == source.resolve():
        raise ValueError("copy target resolves to source")
    target.mkdir(parents=True)
    for path in sorted(source.glob("*.json")):
        shutil.copy2(path, target / path.name)
    if (source / "view" / "resData.json").is_file():
        (target / "view").mkdir()
        shutil.copy2(source / "view" / "resData.json", target / "view" / "resData.json")
    storage = source.parent
    for name in GLOBAL_FILES:
        destination = target.parent / name
        if not destination.exists() and (storage / name).is_file():
            shutil.copy2(storage / name, destination)


def update(source: Path, target: Path, in_place: bool, manifest_out: Path | None) -> dict:
    inputs = read_json(INPUTS)
    values = expected_values(inputs)
    if in_place:
        if target.resolve() != source.resolve():
            raise ValueError("--in-place requires target and source to resolve identically")
    else:
        prepare_copy(source, target)

    before_files = {p.name: read_json(p) for p in sorted(source.glob("*.json"))}
    rytcm_path = target / "RYTCM.json"
    rytcm = read_json(rytcm_path)
    base_rows = rytcm["IAR"][BASE]
    selected = {
        (row["TechId"], int(row["MoId"])): row
        for row in base_rows
        if row["CommId"] == WATER and (row["TechId"], int(row["MoId"])) in values
    }
    if set(selected) != set(values):
        raise AssertionError(f"missing or duplicate rice-water coordinates: expected={len(values)} actual={len(selected)}")

    changed_cells = 0
    before_values = {}
    for key, value in values.items():
        row = selected[key]
        before_values[f"{key[0]}|{key[1]}"] = row["2020"]
        for year in YEARS:
            if Decimal(str(row[year])) != value:
                changed_cells += 1
            row[year] = float(value)
    write_json(rytcm_path, rytcm)

    after_files = {p.name: read_json(p) for p in sorted(target.glob("*.json")) if p.name in before_files}
    changed_files = sorted(name for name in before_files if before_files[name] != after_files.get(name))
    if changed_files not in (["RYTCM.json"], []):
        raise AssertionError(f"unexpected source changes: {changed_files}")

    before_rytcm = before_files["RYTCM.json"]
    after_rytcm = after_files["RYTCM.json"]
    for parameter in before_rytcm:
        if parameter != "IAR" and before_rytcm[parameter] != after_rytcm[parameter]:
            raise AssertionError(f"non-IAR parameter changed: {parameter}")
    for scenario in before_rytcm["IAR"]:
        if scenario != BASE and before_rytcm["IAR"][scenario] != after_rytcm["IAR"][scenario]:
            raise AssertionError(f"policy IAR overlay changed: {scenario}")
    before_keys = [(r["TechId"], r["CommId"], r["MoId"]) for r in before_rytcm["IAR"][BASE]]
    after_keys = [(r["TechId"], r["CommId"], r["MoId"]) for r in after_rytcm["IAR"][BASE]]
    if before_keys != after_keys:
        raise AssertionError("IAR coordinate structure changed")

    cropping = Decimal("3253454.36") / Decimal("2006000")
    efficiency = Decimal("0.38")
    duty = {}
    for mode, rows in inputs["gaez_water_deficit_m_per_crop"].items():
        for tech, deficit in rows.items():
            gross_seasonal_depth_m = (Decimal(deficit) + Decimal("0.450")) / efficiency
            duty[f"{tech}|{mode}"] = float(gross_seasonal_depth_m / Decimal("0.864"))
    if min(duty.values()) < 1 or max(duty.values()) > 5:
        raise AssertionError("computed seasonal duties fall outside the NIA 1-5 L/s/ha range")

    manifest = {
        "schema": "philippines-v16-irrigated-rice-water-manifest-v1",
        "source_case": str(source.resolve()),
        "target_case": str(target.resolve()),
        "in_place": in_place,
        "input_snapshot": str(INPUTS),
        "input_sha256": sha256(INPUTS),
        "changed_source_files": changed_files,
        "changed_cells": changed_cells,
        "expected_cells": len(values) * len(YEARS),
        "cropping_intensity_crops_per_year": float(cropping),
        "formula": "annual gross IAR = (GAEZ WDe + 0.450 m/crop) * (3253454.36 / 2006000 crops/year) / 0.38",
        "before_2020": before_values,
        "after_km3_per_1000km2_year": {f"{tech}|{mode}": float(value) for (tech, mode), value in values.items()},
        "after_m3_per_ha_year": {f"{tech}|{mode}": float(value * Decimal("10000")) for (tech, mode), value in values.items()},
        "seasonal_nia_equivalent_l_per_s_per_ha": duty,
        "nia_range_l_per_s_per_ha": [1, 5],
        "source_rytcm_sha256_before": sha256(source / "RYTCM.json") if not in_place else None,
        "target_rytcm_sha256_after": sha256(target / "RYTCM.json"),
        "non_forcing": {
            "technologies_added": 0,
            "commodities_added": 0,
            "modes_added": 0,
            "demands_changed": False,
            "activity_or_share_bounds_changed": False,
            "user_constraints_changed": False
        }
    }
    if manifest_out:
        write_json(manifest_out, manifest)
    print(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path)
    parser.add_argument("--in-place", action="store_true")
    parser.add_argument("--copy-only", action="store_true", help="Create an unchanged disposable control copy")
    parser.add_argument("--manifest-out", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    target = source if args.in_place else (args.target.resolve() if args.target else None)
    if target is None:
        parser.error("--target is required unless --in-place is used")
    if args.copy_only:
        if args.in_place:
            parser.error("--copy-only cannot be combined with --in-place")
        prepare_copy(source, target)
        report = {
            "schema": "philippines-v16-disposable-control-v1",
            "source_case": str(source),
            "target_case": str(target),
            "source_hashes": {path.name: sha256(path) for path in sorted(source.glob("*.json"))},
            "target_hashes": {path.name: sha256(target / path.name) for path in sorted(source.glob("*.json"))},
        }
        if report["source_hashes"] != report["target_hashes"]:
            raise AssertionError("control copy does not reproduce source JSON files")
        if args.manifest_out:
            write_json(args.manifest_out, report)
        print(json.dumps(report, indent=2))
        return
    update(source, target, args.in_place, args.manifest_out)


if __name__ == "__main__":
    main()
