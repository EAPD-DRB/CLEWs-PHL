#!/usr/bin/env python3
"""Build or promote the non-forcing Philippines v16 energy-input repair.

The repair corrects three physical inputs and removes a misleading import
suffix from the three affected renewable technology labels.  Stable TechId
values are preserved, no commodity is renamed, and no output is prescribed.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
import types
from decimal import Decimal, getcontext
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
STORAGE = REPO / "WebAPP" / "DataStorage"
SOURCE_CASE = (STORAGE / "Philippines_v16").resolve()
INPUTS = REPO / "scripts" / "data" / "philippines_v16_energy_inputs.json"
GLOBAL_FILES = ("Parameters.json", "Variables.json", "Duals.json", "Indicators.json")
PROMOTED_FILES = ("genData.json", "RYT.json", "RYTTs.json")
BASE_SCENARIO = "SC_0"

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(REPO / "API"))

from Classes.Base import Config  # noqa: E402
from Classes.Case.UpdateCaseClass import UpdateCase  # noqa: E402


getcontext().prec = 40


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + ".codex-tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def keyed_rows(rows: list[dict], keys: tuple[str, ...]) -> dict[tuple, dict]:
    return {tuple(row.get(key) for key in keys): row for row in rows}


def snapshot(case: Path) -> dict[str, object]:
    return {path.name: read_json(path) for path in sorted(case.glob("*.json"))}


def prepare_target(target: Path) -> None:
    if target.exists():
        raise FileExistsError(f"refusing to replace target: {target}")
    if target.resolve() == SOURCE_CASE:
        raise ValueError("target resolves to the live case")
    for name in GLOBAL_FILES:
        destination = target.parent / name
        if not destination.exists():
            shutil.copy2(STORAGE / name, destination)
    target.mkdir(parents=True)
    for source in sorted(SOURCE_CASE.glob("*.json")):
        shutil.copy2(source, target / source.name)
    (target / "view").mkdir()
    shutil.copy2(SOURCE_CASE / "view" / "resData.json", target / "view" / "resData.json")


def weighted_offshore_cf(inputs: dict) -> Decimal:
    numerator = Decimal("0")
    denominator = Decimal("0")
    for zone in inputs["offshore_wind"]["zones"]:
        capacity = Decimal(str(zone["fixed_mw"])) + Decimal(str(zone["floating_mw"]))
        numerator += capacity * Decimal(str(zone["capacity_factor_percent"])) / Decimal("100")
        denominator += capacity
    expected_capacity = Decimal(str(inputs["offshore_wind"]["expected_total_capacity_mw"]))
    if denominator != expected_capacity:
        raise AssertionError(f"offshore zone capacity sum {denominator} != {expected_capacity}")
    value = numerator / denominator
    expected = Decimal(str(inputs["offshore_wind"]["expected_weighted_capacity_factor"]))
    if abs(value - expected) > Decimal("1e-15"):
        raise AssertionError(f"offshore weighted CF {value} != {expected}")
    return value


def rename_technologies(gen: dict, inputs: dict) -> list[dict]:
    technologies = {item["TechId"]: item for item in gen["osy-tech"]}
    changes = []
    for spec in inputs["technology_renames"]:
        item = technologies[spec["tech_id"]]
        if item["Tech"] != spec["before"]:
            raise AssertionError(f"unexpected technology name for {spec['tech_id']}: {item['Tech']}")
        changes.append({"tech_id": spec["tech_id"], "before": item["Tech"], "after": spec["after"]})
        item["Tech"] = spec["after"]
        item["Desc"] = spec["description"]
    return changes


def annual_cf(rows: list[dict], year_split_rows: list[dict], tech_id: str, year: str) -> Decimal:
    cf = {row["TsId"]: Decimal(str(row[year])) for row in rows if row["TechId"] == tech_id}
    ys = {row["TsId"]: Decimal(str(row[year])) for row in year_split_rows}
    if set(cf) != set(ys):
        raise AssertionError(f"capacity-factor/year-split timeslices differ for {tech_id}")
    return sum(cf[timeslice] * ys[timeslice] for timeslice in ys)


def apply_parameters(case: Path, inputs: dict) -> dict:
    gen = read_json(case / "genData.json")
    years = [str(year) for year in gen["osy-years"]]
    scenarios = [scenario["ScenarioId"] for scenario in gen["osy-scenarios"]]

    ryt = read_json(case / "RYT.json")
    geothermal = inputs["geothermal"]
    onshore = inputs["onshore_wind"]
    af = keyed_rows(ryt["AF"][BASE_SCENARIO], ("TechId",))[(geothermal["tech_id"],)]
    tau = keyed_rows(ryt["TAU"][BASE_SCENARIO], ("TechId",))[(onshore["tech_id"],)]
    for year in years:
        if Decimal(str(af[year])) != Decimal(str(geothermal["availability_factor_before"])):
            raise AssertionError(f"unexpected geothermal AF in {BASE_SCENARIO} {year}: {af[year]}")
        if Decimal(str(tau[year])) != Decimal(str(onshore["annual_activity_upper_limit_before_pj"])):
            raise AssertionError(f"unexpected onshore TAU in {BASE_SCENARIO} {year}: {tau[year]}")
        af[year] = geothermal["availability_factor_after"]
        tau[year] = onshore["annual_activity_upper_limit_after_pj"]
    write_json(case / "RYT.json", ryt)

    target_cf = weighted_offshore_cf(inputs)
    rytts = read_json(case / "RYTTs.json")
    ryts = read_json(case / "RYTs.json")
    offshore_id = inputs["offshore_wind"]["tech_id"]
    scenario_summary = {}
    for scenario in (BASE_SCENARIO,):
        before_means = {
            year: annual_cf(rytts["CF"][scenario], ryts["YS"][scenario], offshore_id, year)
            for year in years
        }
        scales = {year: target_cf / before_means[year] for year in years}
        offshore_rows = [row for row in rytts["CF"][scenario] if row["TechId"] == offshore_id]
        if len(offshore_rows) != len(ryts["YS"][scenario]):
            raise AssertionError(f"unexpected offshore CF row count in {scenario}")
        for row in offshore_rows:
            for year in years:
                value = Decimal(str(row[year])) * scales[year]
                if not Decimal("0") <= value <= Decimal("1"):
                    raise AssertionError(f"scaled offshore CF outside [0,1]: {scenario} {row['TsId']} {year}")
                row[year] = float(value)
        after_means = {
            year: annual_cf(rytts["CF"][scenario], ryts["YS"][scenario], offshore_id, year)
            for year in years
        }
        for year, value in after_means.items():
            if abs(value - target_cf) > Decimal("1e-12"):
                raise AssertionError(f"offshore annual CF mismatch in {scenario} {year}: {value}")
        scenario_summary[scenario] = {
            "before_annual_cf": float(before_means[years[0]]),
            "after_annual_cf": float(after_means[years[0]]),
            "scale_factor": float(scales[years[0]]),
            "timeslice_rows": len(offshore_rows),
        }
    write_json(case / "RYTTs.json", rytts)
    return {
        "years": years,
        "scenarios": scenarios,
        "physical_input_scenario": BASE_SCENARIO,
        "policy_scenario_treatment": "null overrides preserved; policy scenarios inherit SC_0 physical inputs",
        "offshore": scenario_summary,
        "geothermal_availability": geothermal["availability_factor_after"],
        "onshore_tau_pj": onshore["annual_activity_upper_limit_after_pj"],
    }


def assert_allowed_diff(before: dict, after: dict, inputs: dict) -> list[str]:
    changed_files = sorted(name for name in before if before[name] != after[name])
    if changed_files != sorted(PROMOTED_FILES):
        raise AssertionError(f"unexpected semantic source changes: {changed_files}")

    before_gen = before["genData.json"]
    after_gen = after["genData.json"]
    if [item["TechId"] for item in before_gen["osy-tech"]] != [item["TechId"] for item in after_gen["osy-tech"]]:
        raise AssertionError("technology IDs changed")
    expected_names = {row["tech_id"]: row for row in inputs["technology_renames"]}
    for old, new in zip(before_gen["osy-tech"], after_gen["osy-tech"], strict=True):
        if old["TechId"] in expected_names:
            spec = expected_names[old["TechId"]]
            expected = copy.deepcopy(old)
            expected["Tech"] = spec["after"]
            expected["Desc"] = spec["description"]
            if new != expected:
                raise AssertionError(f"unapproved technology metadata change: {old['TechId']}")
        elif new != old:
            raise AssertionError(f"unapproved technology change: {old['TechId']}")
    if before_gen["osy-comm"] != after_gen["osy-comm"]:
        raise AssertionError("commodity structure or metadata changed")
    if before_gen["osy-constraints"] != after_gen["osy-constraints"]:
        raise AssertionError("user-defined constraints changed")

    before_ryt = copy.deepcopy(before["RYT.json"])
    after_ryt = copy.deepcopy(after["RYT.json"])
    geo_id = inputs["geothermal"]["tech_id"]
    won_id = inputs["onshore_wind"]["tech_id"]
    for scenario in after_ryt["AF"]:
        old = keyed_rows(before_ryt["AF"][scenario], ("TechId",))[(geo_id,)]
        new = keyed_rows(after_ryt["AF"][scenario], ("TechId",))[(geo_id,)]
        old.update(new)
        tau_old = keyed_rows(before_ryt["TAU"][scenario], ("TechId",))[(won_id,)]
        tau_new = keyed_rows(after_ryt["TAU"][scenario], ("TechId",))[(won_id,)]
        tau_old.update(tau_new)
    if before_ryt != after_ryt:
        raise AssertionError("RYT contains changes outside geothermal AF and onshore TAU")

    before_cf = copy.deepcopy(before["RYTTs.json"])
    after_cf = copy.deepcopy(after["RYTTs.json"])
    offshore_id = inputs["offshore_wind"]["tech_id"]
    for scenario in after_cf["CF"]:
        old_rows = keyed_rows(before_cf["CF"][scenario], ("TechId", "TsId"))
        new_rows = keyed_rows(after_cf["CF"][scenario], ("TechId", "TsId"))
        for key, new in new_rows.items():
            if key[0] == offshore_id:
                old_rows[key].update(new)
    if before_cf != after_cf:
        raise AssertionError("RYTTs contains changes outside offshore-wind CF")
    return changed_files


def build_candidate(target: Path) -> dict:
    prepare_target(target)
    inputs = read_json(INPUTS)
    before = snapshot(target)
    source_hashes = {name: sha256(SOURCE_CASE / name) for name in PROMOTED_FILES}

    gen = copy.deepcopy(before["genData.json"])
    renames = rename_technologies(gen, inputs)
    write_json(target / "genData.json", gen)
    Config.DATA_STORAGE = target.parent
    UpdateCase(target.name, gen).updateCase()
    write_json(target / "genData.json", gen)

    parameters = apply_parameters(target, inputs)
    after = snapshot(target)
    changed_files = assert_allowed_diff(before, after, inputs)

    manifest = {
        "schema": "philippines-v16-energy-input-candidate-v1",
        "source_case": str(SOURCE_CASE),
        "target_case": str(target),
        "input_file": str(INPUTS),
        "input_sha256": sha256(INPUTS),
        "source_hashes": source_hashes,
        "candidate_hashes": {name: sha256(target / name) for name in PROMOTED_FILES},
        "changed_source_files": changed_files,
        "technology_renames": renames,
        "parameter_summary": parameters,
        "classification": {
            "initial_stock": "unchanged",
            "final_demand": "unchanged",
            "continuing_constraints": "onshore screened technical resource ceiling; unchanged geothermal 4 GW capacity ceiling",
            "benchmark_only": "DOE 2020 geothermal generation and utilization",
        },
        "non_forcing_assertions": {
            "technology_ids_changed": False,
            "commodity_changed": False,
            "final_demand_changed": False,
            "activity_target_or_lower_bound_added": False,
            "user_constraint_changed": False,
            "wind_construction_required": False,
        },
    }
    write_json(target / "energy_input_calibration_manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    return manifest


def promote(candidate: Path, backup: Path) -> dict:
    manifest = read_json(candidate / "energy_input_calibration_manifest.json")
    if backup.exists():
        raise FileExistsError(f"refusing to replace backup: {backup}")
    backup.mkdir(parents=True)
    for name in PROMOTED_FILES:
        if sha256(SOURCE_CASE / name) != manifest["source_hashes"][name]:
            raise AssertionError(f"live source changed since candidate creation: {name}")
        if sha256(candidate / name) != manifest["candidate_hashes"][name]:
            raise AssertionError(f"candidate changed since manifest creation: {name}")
        shutil.copy2(SOURCE_CASE / name, backup / name)
    for name in PROMOTED_FILES:
        temporary = SOURCE_CASE / f".{name}.energy-input-candidate"
        shutil.copy2(candidate / name, temporary)
        temporary.replace(SOURCE_CASE / name)
    result = {
        "source_case": str(SOURCE_CASE),
        "candidate": str(candidate),
        "backup": str(backup),
        "promoted_files": list(PROMOTED_FILES),
        "promoted_hashes": {name: sha256(SOURCE_CASE / name) for name in PROMOTED_FILES},
    }
    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--target", type=Path)
    group.add_argument("--promote-from", type=Path)
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    if args.target:
        build_candidate(args.target.resolve())
    else:
        if args.backup is None:
            parser.error("--backup is required with --promote-from")
        promote(args.promote_from.resolve(), args.backup.resolve())


if __name__ == "__main__":
    main()
