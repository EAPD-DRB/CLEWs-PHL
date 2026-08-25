#!/usr/bin/env python3
"""Create Philippines v17 from v16 with national land accounting and safeguards."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PACKAGE.parents[0] / "case" / "Philippines_v16"
DEFAULT_TARGET = PACKAGE.parents[0] / "case" / "Philippines_v17"
INPUTS = PACKAGE / "data_sources" / "snapshots" / "land_cover_2020.json"
SAFEGUARDS = PACKAGE / "data_sources" / "snapshots" / "land_transition_safeguards.json"
BASE_SCENARIO = "SC_0"
YEARS = tuple(str(year) for year in range(2020, 2054))
GLOBAL_FILES = ("Parameters.json", "Variables.json", "Duals.json", "Indicators.json")

LAND_SUPPLY = "TEC_dgw1l"
LAND_TERMINAL = "TEC_envland_v12"
OTHER_LAND = "TEC_zty92"
PHL_LAND = "COM_fxuo5"
LOTHTOT = "COM_26200"
ENV_CROPLAND = "COM_env_lcrp_v12"
PUBLIC_WATER = "COM_n1j3l"

ENV_MODE_CLASS = {
    1: "forest",
    2: "grassland_and_woodland",
    3: "other_agricultural",
    4: "barren",
    5: "built_up",
    6: "water_bodies",
    7: "cropland",
    8: "unallocated",
}


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


def prepare_copy(source: Path, target: Path) -> None:
    if target.exists():
        raise FileExistsError(f"refusing to replace target: {target}")
    target.mkdir(parents=True)
    for path in sorted(source.glob("*.json")):
        shutil.copy2(path, target / path.name)
    if (source / "documentation").is_dir():
        shutil.copytree(source / "documentation", target / "documentation")
    if (source / "view" / "resData.json").is_file():
        (target / "view").mkdir()
        shutil.copy2(source / "view" / "resData.json", target / "view" / "resData.json")
    for name in GLOBAL_FILES:
        destination = target.parent / name
        if not destination.exists() and (source.parent / name).is_file():
            shutil.copy2(source.parent / name, destination)


def row(rows: list[dict], **coordinates) -> dict:
    matches = [candidate for candidate in rows if all(candidate.get(k) == v for k, v in coordinates.items())]
    if len(matches) != 1:
        raise AssertionError(f"expected one row for {coordinates}, found {len(matches)}")
    return matches[0]


def set_all_years(record: dict, value: float) -> int:
    changed = 0
    for year in YEARS:
        if record[year] != value:
            changed += 1
        record[year] = value
    return changed


def update(source: Path, target: Path, manifest_out: Path | None) -> dict:
    inputs = read_json(INPUTS)
    safeguards = read_json(SAFEGUARDS)
    classes = inputs["model_units_1000_km2"]
    if abs(sum(classes[name] for name in ENV_MODE_CLASS.values()) - classes["total"]) > 1e-9:
        raise AssertionError("land classes do not close to the national total")
    rate = safeguards["calculations"]["annual_restoration_rate"]["output_1000_km2_per_year"]
    grass_reserve = safeguards["calculations"]["true_grassland_reserve"]["output_1000_km2"]
    brush_pool = safeguards["calculations"]["mapped_brush_shrub_pool"]["model_output_1000_km2"]
    suitability = safeguards["calculations"]["forest_eligible_brush_shrub_pool"]["suitability_fraction"]
    forest_eligible_pool = safeguards["calculations"]["forest_eligible_brush_shrub_pool"]["output_1000_km2"]
    if abs(classes["grassland_and_woodland"] - grass_reserve - brush_pool) > 1e-9:
        raise AssertionError("grass reserve and eligible brush/shrub pool do not close")
    if abs(brush_pool * suitability - forest_eligible_pool) > 1e-9:
        raise AssertionError("forest-eligible brush/shrub calculation does not close")

    prepare_copy(source, target)
    before = {path.name: sha256(path) for path in sorted(source.glob("*.json"))}
    changed_cells = {"RYT.json": 0, "RYTM.json": 0, "RYTCM.json": 0, "genData.json": 0}

    gen_path = target / "genData.json"
    gen = read_json(gen_path)
    if gen["osy-casename"] != "Philippines_v16":
        raise AssertionError(f"unexpected source identity: {gen['osy-casename']}")
    gen["osy-casename"] = "Philippines_v17"
    gen["osy-date"] = "2026-08-12"
    gen["osy-desc"] = (
        "Philippines v17 land-accounting successor of Philippines v16. The complete v16 model is "
        "retained; v17 initializes the 2020 national PSA/NAMRIA land-cover partition, closes the "
        "annual national land balance, reuses LNDOTHTOT mode 2 as endogenous idle/fallow "
        "cropland, preserves true grassland and 2020 cropland, grows built-up land with the "
        "central population-urbanization pathway, and limits forest expansion to a Philippine "
        "policy-rate envelope over the documented forest-suitable share of brush/shrub. "
        "Forest mode-27 variable cost remains -10.\n\n" + gen["osy-desc"]
    )
    techs = {item["TechId"]: item for item in gen["osy-tech"]}
    other = techs[OTHER_LAND]
    if ENV_CROPLAND not in other["OAR"]:
        other["OAR"].append(ENV_CROPLAND)
        changed_cells["genData.json"] += 1
    other["Desc"] = (
        "National land-accounting adapter. Mode 1 maps PHL_LND to model-defined other land and "
        "LOTHTOT; mode 2 maps PHL_LND to idle/fallow cropland and LOTHTOT. LOTHTOT retains the "
        "inherited mode-29 hydrology proxy."
    )
    techs[LAND_SUPPLY]["Desc"] = (
        "Annual national land endowment fixed to the inherited 295.8131 thousand km2 control total."
    )
    write_json(gen_path, gen)

    ryt_path = target / "RYT.json"
    ryt = read_json(ryt_path)
    for scenario in ryt["TAL"]:
        for parameter in ("TAL", "TAU"):
            supply = row(ryt[parameter][scenario], TechId=LAND_SUPPLY)
            changed_cells["RYT.json"] += set_all_years(supply, classes["total"])
    write_json(ryt_path, ryt)

    rytm_path = target / "RYTM.json"
    rytm = read_json(rytm_path)
    demand = read_json(target / "RYC.json")
    public_water = row(demand["AAD"][BASE_SCENARIO], CommId=PUBLIC_WATER)
    base_public_water = public_water["2020"]
    built_path = safeguards["calculations"]["central_built_up_path"]
    disabled_upper = safeguards["model_rules"]["disabled_mode_upper_sentinel_1000_km2"]
    idle_fallow_ceiling = safeguards["calculations"]["idle_fallow_ceiling"]["output_1000_km2"]
    urban_2020 = built_path["urban_share_2020"]
    urban_2050 = built_path["urban_share_2050"]
    for scenario in rytm["TAMLL"]:
        for mode, class_name in ENV_MODE_CLASS.items():
            lower = row(rytm["TAMLL"][scenario], TechId=LAND_TERMINAL, MoId=mode)
            upper = row(rytm["TAMUL"][scenario], TechId=LAND_TERMINAL, MoId=mode)
            for year_text in YEARS:
                year = int(year_text)
                elapsed = year - 2020
                forest_release = min(rate * elapsed, forest_eligible_pool)
                urban_share = urban_2020 + (urban_2050 - urban_2020) * min(elapsed, 30) / 30
                built_up = classes["built_up"] * (public_water[year_text] / base_public_water) * (urban_share / urban_2020)
                if mode == 1:
                    lower_value = classes[class_name]
                    upper_value = classes[class_name] + forest_release
                elif mode == 2:
                    lower_value = classes[class_name] if year == 2020 else grass_reserve
                    upper_value = classes[class_name]
                elif mode in (3, 4, 6):
                    lower_value = upper_value = classes[class_name]
                elif mode == 5:
                    lower_value = upper_value = built_up
                elif mode == 7:
                    lower_value = classes[class_name]
                    upper_value = classes[class_name] if year == 2020 else upper[year_text]
                elif mode == 8:
                    lower_value = 0.0
                    upper_value = disabled_upper
                else:
                    raise AssertionError(mode)
                if lower[year_text] != lower_value:
                    changed_cells["RYTM.json"] += 1
                if upper[year_text] != upper_value:
                    changed_cells["RYTM.json"] += 1
                lower[year_text] = lower_value
                upper[year_text] = upper_value
    write_json(rytm_path, rytm)

    # Prevent the bookkeeping route from turning unused brush into new idle
    # cropland. Productive crop technologies retain their inherited freedom.
    for scenario in rytm["TAMUL"]:
        idle_upper = row(rytm["TAMUL"][scenario], TechId=OTHER_LAND, MoId=2)
        changed_cells["RYTM.json"] += set_all_years(idle_upper, idle_fallow_ceiling)
    write_json(rytm_path, rytm)

    rytcm_path = target / "RYTCM.json"
    rytcm = read_json(rytcm_path)
    for scenario in rytcm["IAR"]:
        idle_input = row(rytcm["IAR"][scenario], TechId=OTHER_LAND, CommId=PHL_LAND, MoId=2)
        idle_lothtot = row(rytcm["OAR"][scenario], TechId=OTHER_LAND, CommId=LOTHTOT, MoId=2)
        crop_rows = []
        for mode in range(1, 31):
            crop_matches = [
                candidate for candidate in rytcm["OAR"][scenario]
                if candidate.get("TechId") == OTHER_LAND
                and candidate.get("CommId") == ENV_CROPLAND
                and candidate.get("MoId") == mode
            ]
            if crop_matches:
                if len(crop_matches) != 1:
                    raise AssertionError(f"duplicate idle-cropland mode {mode} rows in {scenario}")
                crop_row = crop_matches[0]
            else:
                template = row(
                    rytcm["OAR"][scenario], TechId=OTHER_LAND, CommId=LOTHTOT, MoId=mode
                )
                crop_row = copy.deepcopy(template)
                crop_row["CommId"] = ENV_CROPLAND
                rytcm["OAR"][scenario].append(crop_row)
                changed_cells["RYTCM.json"] += 1
            changed_cells["RYTCM.json"] += set_all_years(crop_row, 1.0 if mode == 2 else 0.0)
            crop_rows.append(crop_row)
        for target_row in (idle_input, idle_lothtot):
            changed_cells["RYTCM.json"] += set_all_years(target_row, 1.0)
    write_json(rytcm_path, rytcm)

    (target / "README.md").write_text(
        """# Philippines_v17 national land-cover case

This is the complete Philippines v16 MUIO source model plus the v17 national
land-account repair and Philippine land-transition safeguards. The 2020
PSA/NAMRIA seven-class partition is initialized through ENV_LAND equalities;
MINLNDTOT is fixed to 295.8131 thousand km2 in every year; existing LNDOTHTOT
mode 2 is the endogenous idle/fallow cropland route; true grassland and 2020
total cropland are preserved; built-up area follows the central population-
urbanization path; and forest expansion follows the documented policy-rate
envelope over the forest-suitable share of brush/shrub. No
technology, commodity, user constraint, or global mode was added. Forest
VC=-10 is unchanged.

See `documentation/MODEL_FIXES_LAND_COVER_2026-08-12.md` and the repository
package `Philippines_v17_CLEWs_build` for the complete cumulative provenance.
Generated solver inputs and results are not model sources and are excluded
from the portable archive.
""",
        encoding="utf-8",
    )

    after = {path.name: sha256(path) for path in sorted(target.glob("*.json"))}
    changed_files = sorted(name for name in before if before[name] != after.get(name))
    expected = ["RYT.json", "RYTCM.json", "RYTM.json", "genData.json"]
    if changed_files != expected:
        raise AssertionError(f"unexpected changed source files: {changed_files}")

    original_forest_vc = read_json(source / "RYTM.json")["VC"]
    candidate_forest_vc = read_json(target / "RYTM.json")["VC"]
    if original_forest_vc != candidate_forest_vc:
        raise AssertionError("VC changed; forest -10 must be retained exactly")

    manifest = {
        "schema": "philippines-v17-land-cover-build-manifest-v1",
        "source_case": str(source.resolve()),
        "target_case": str(target.resolve()),
        "input_snapshot": str(INPUTS),
        "input_sha256": sha256(INPUTS),
        "safeguards_snapshot": str(SAFEGUARDS),
        "safeguards_sha256": sha256(SAFEGUARDS),
        "changed_source_files": changed_files,
        "changed_cells": changed_cells,
        "class_totals_1000_km2": {name: classes[name] for name in ENV_MODE_CLASS.values()},
        "national_total_1000_km2": classes["total"],
        "base_year": 2020,
        "land_supply_equality_years": [2020, 2053],
        "transition_safeguards": {
            "annual_forest_expansion_envelope_1000_km2_per_year": rate,
            "mapped_brush_shrub_pool_1000_km2": brush_pool,
            "forest_suitability_fraction": suitability,
            "forest_eligible_brush_shrub_pool_1000_km2": forest_eligible_pool,
            "true_grassland_reserve_1000_km2": grass_reserve,
            "forest_floor_1000_km2": classes["forest"],
            "maximum_forest_1000_km2": classes["forest"] + forest_eligible_pool,
            "central_built_up_1000_km2": {
                year: classes["built_up"]
                * (public_water[year] / base_public_water)
                * ((urban_2020 + (urban_2050 - urban_2020) * min(int(year) - 2020, 30) / 30) / urban_2020)
                for year in YEARS
            },
            "fixed_classes_1000_km2": {
                name: classes[name] for name in ("other_agricultural", "barren", "water_bodies")
            },
            "cropland_floor_1000_km2": classes["cropland"],
            "idle_fallow_ceiling_1000_km2": idle_fallow_ceiling,
            "unallocated_upper_sentinel_1000_km2": disabled_upper,
        },
        "idle_fallow_adapter": {"technology": OTHER_LAND, "mode": 2},
        "forest_variable_cost_changed": False,
        "new_technologies": 0,
        "new_commodities": 0,
        "new_global_modes": 0,
        "source_hashes_before": before,
        "target_hashes_after": after,
    }
    if manifest_out:
        write_json(manifest_out, manifest)
    print(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--manifest-out", type=Path)
    args = parser.parse_args()
    update(args.source.resolve(), args.target.resolve(), args.manifest_out)


if __name__ == "__main__":
    main()
