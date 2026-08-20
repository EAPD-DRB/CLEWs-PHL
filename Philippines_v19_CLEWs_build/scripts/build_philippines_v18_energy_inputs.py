#!/usr/bin/env python3
"""Create Philippines v18 from v17 with source-traceable energy inputs."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
from decimal import Decimal, getcontext
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parent
DEFAULT_SOURCE = REPO / "case" / "Philippines_v17"
DEFAULT_TARGET = REPO / "case" / "Philippines_v18"
INPUTS = PACKAGE / "data_sources" / "snapshots" / "energy_inputs_v18_2026-08-12.json"
DEFAULT_MANIFEST = PACKAGE / "data_sources" / "snapshots" / "energy_inputs_v18_build_manifest.json"
BASE = "SC_0"
GLOBAL_FILES = ("Parameters.json", "Variables.json", "Duals.json", "Indicators.json")
CHANGED_FILES = ("RT.json", "RYT.json", "RYTM.json", "RYTTs.json", "genData.json")
YEARS = tuple(str(year) for year in range(2020, 2054))

GEO = "TEC_0qr3z"
WIND = "TEC_1wdli"
COAL = "TEC_46nha"
SMR = "TEC_fa6fe"
HYDRO = "TEC_p3vu5"
GAS_IMPORT = "TEC_otz0y"
GAS_DOMESTIC = "TEC_6rwx6"

getcontext().prec = 40


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one(rows: list[dict], **coordinates) -> dict:
    matches = [row for row in rows if all(row.get(key) == value for key, value in coordinates.items())]
    if len(matches) != 1:
        raise AssertionError(f"expected one row for {coordinates}; found {len(matches)}")
    return matches[0]


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


def annual_cf(cf_rows: list[dict], ys_rows: list[dict], tech: str, year: str) -> Decimal:
    cf = {row["TsId"]: Decimal(str(row[year])) for row in cf_rows if row["TechId"] == tech}
    ys = {row["TsId"]: Decimal(str(row[year])) for row in ys_rows}
    if set(cf) != set(ys):
        raise AssertionError("onshore capacity-factor and YearSplit timeslices differ")
    return sum(cf[timeslice] * ys[timeslice] for timeslice in ys)


def update(source: Path, target: Path, manifest_path: Path) -> dict:
    inputs = read_json(INPUTS)
    prepare_copy(source, target)
    before = {path.name: sha256(path) for path in sorted(source.glob("*.json"))}

    gen_path = target / "genData.json"
    gen = read_json(gen_path)
    if gen["osy-casename"] != "Philippines_v17":
        raise AssertionError(f"unexpected source identity: {gen['osy-casename']}")
    source_tech_ids = [item["TechId"] for item in gen["osy-tech"]]
    source_comm_ids = [item["CommId"] for item in gen["osy-comm"]]
    gen["osy-casename"] = "Philippines_v18"
    gen["osy-date"] = "2026-08-12"
    gen["osy-desc"] = (
        "Philippines v18 energy-input successor of Philippines v17. The complete v17 national "
        "land account and safeguards are retained. V18 sets a 0.70 geothermal resource ceiling, "
        "aligns onshore-wind capacity factor with the national restricted resource screen, updates "
        "coal and SMR capital costs, uses a 60-year large-hydro life, and separates the existing "
        "domestic-gas and LNG import routes by observed chronology, prices and annual limits. "
        "No technology or commodity is added.\n\n" + gen["osy-desc"]
    )
    techs = {item["TechId"]: item for item in gen["osy-tech"]}
    techs[GAS_IMPORT]["Desc"] = (
        "Imported LNG route to existing raw natural gas; unavailable before 2023 and bounded by "
        "observed 2023 use and the operating terminal envelope thereafter."
    )
    techs[GAS_DOMESTIC]["Desc"] = (
        "Domestic natural-gas extraction route; historical limits follow DOE production and the "
        "post-2024 interim envelope follows the documented PEP decline proxy."
    )
    write_json(gen_path, gen)

    ryt_path = target / "RYT.json"
    ryt = read_json(ryt_path)
    geo = one(ryt["AF"][BASE], TechId=GEO)
    coal = one(ryt["CC"][BASE], TechId=COAL)
    smr = one(ryt["CC"][BASE], TechId=SMR)
    import_cap = one(ryt["TAU"][BASE], TechId=GAS_IMPORT)
    domestic_cap = one(ryt["TAU"][BASE], TechId=GAS_DOMESTIC)
    gas = inputs["natural_gas"]
    conversion = Decimal(str(gas["mmscf_to_pj"]))
    observed = {year: Decimal(str(value)) for year, value in gas["domestic_production_mmscf"].items()}
    import_2023 = Decimal(str(gas["lng_import_limit"]["2023_pj"]))
    import_terminal = Decimal(str(gas["lng_import_limit"]["2024_2053_pj_per_year"]))
    for year in YEARS:
        geo[year] = inputs["geothermal"]["availability_after"]
        coal[year] = inputs["capital_costs"]["coal_power_musd_per_gw"]
        smr[year] = inputs["capital_costs"]["nuclear_smr_musd_per_gw"]
        year_number = int(year)
        if year_number <= 2022:
            import_cap[year] = 0.0
        elif year_number == 2023:
            import_cap[year] = float(import_2023)
        else:
            import_cap[year] = float(import_terminal)
        if year in observed:
            domestic_cap[year] = float(observed[year] * conversion)
        else:
            domestic_cap[year] = float(observed["2024"] * conversion * Decimal("0.992") ** (year_number - 2024))
    write_json(ryt_path, ryt)

    rytm_path = target / "RYTM.json"
    rytm = read_json(rytm_path)
    import_price = one(rytm["VC"][BASE], TechId=GAS_IMPORT, MoId=1)
    domestic_price = one(rytm["VC"][BASE], TechId=GAS_DOMESTIC, MoId=1)
    inherited_import_2024 = Decimal(str(import_price["2024"]))
    inherited_domestic_2020 = Decimal(str(domestic_price["2020"]))
    domestic_anchor = Decimal(str(gas["domestic_price_2020_usd_per_gj"]))
    lng_2023 = Decimal(str(gas["lng_prices"]["2023_usd_per_gj"]))
    lng_2024 = Decimal(str(gas["lng_prices"]["2024_usd_per_gj"]))
    inherited_import = {year: Decimal(str(import_price[year])) for year in YEARS}
    inherited_domestic = {year: Decimal(str(domestic_price[year])) for year in YEARS}
    for year in YEARS:
        domestic_price[year] = float(inherited_domestic[year] / inherited_domestic_2020 * domestic_anchor)
        if int(year) == 2023:
            import_price[year] = float(lng_2023)
        elif int(year) >= 2024:
            import_price[year] = float(inherited_import[year] / inherited_import_2024 * lng_2024)
    write_json(rytm_path, rytm)

    rytts_path = target / "RYTTs.json"
    rytts = read_json(rytts_path)
    ryts = read_json(target / "RYTs.json")
    target_cf = Decimal(str(inputs["onshore_wind"]["annual_capacity_factor_after"]))
    wind_rows = [row for row in rytts["CF"][BASE] if row["TechId"] == WIND]
    before_cf = {year: annual_cf(rytts["CF"][BASE], ryts["YS"][BASE], WIND, year) for year in YEARS}
    for row in wind_rows:
        for year in YEARS:
            value = Decimal(str(row[year])) * target_cf / before_cf[year]
            if not Decimal("0") <= value <= Decimal("1"):
                raise AssertionError(f"scaled wind CF outside [0,1]: {row['TsId']} {year}")
            row[year] = float(value)
    after_cf = {year: annual_cf(rytts["CF"][BASE], ryts["YS"][BASE], WIND, year) for year in YEARS}
    if any(abs(value - target_cf) > Decimal("1e-12") for value in after_cf.values()):
        raise AssertionError("onshore annual capacity-factor target was not reproduced")
    write_json(rytts_path, rytts)

    rt_path = target / "RT.json"
    rt = read_json(rt_path)
    lives = rt["OL"][BASE][0]
    if lives[HYDRO] != inputs["operating_lives"]["large_hydro_years_before"]:
        raise AssertionError("unexpected inherited large-hydro life")
    if lives[SMR] != inputs["operating_lives"]["nuclear_smr_years_confirmed_unchanged"]:
        raise AssertionError("unexpected inherited SMR life")
    lives[HYDRO] = inputs["operating_lives"]["large_hydro_years_after"]
    write_json(rt_path, rt)

    after = {path.name: sha256(path) for path in sorted(target.glob("*.json"))}
    changed = sorted(name for name in before if before[name] != after[name])
    if changed != sorted(CHANGED_FILES):
        raise AssertionError(f"unexpected changed source files: {changed}")
    final_gen = read_json(gen_path)
    if [item["TechId"] for item in final_gen["osy-tech"]] != source_tech_ids:
        raise AssertionError("technology structure changed")
    if [item["CommId"] for item in final_gen["osy-comm"]] != source_comm_ids:
        raise AssertionError("commodity structure changed")

    manifest = {
        "schema": "philippines-v18-energy-build-manifest-v1",
        "source_case": str(source.resolve()),
        "target_case": str(target.resolve()),
        "source_case_sha256": before,
        "target_case_sha256": after,
        "changed_files": changed,
        "unchanged_file_count": len(before) - len(changed),
        "technology_ids_unchanged": True,
        "commodity_ids_unchanged": True,
        "land_cover_source_files_unchanged": all(
            before[name] == after[name] for name in before if name not in CHANGED_FILES
        ),
        "parameters": {
            "geothermal_af": float(Decimal(str(geo["2020"]))),
            "onshore_wind_annual_cf_before": float(before_cf["2020"]),
            "onshore_wind_annual_cf_after": float(after_cf["2020"]),
            "coal_capital_cost": coal["2020"],
            "smr_capital_cost": smr["2020"],
            "smr_life": lives[SMR],
            "large_hydro_life": lives[HYDRO],
            "gas_import_cap_pj": {year: import_cap[year] for year in ("2020", "2022", "2023", "2024", "2053")},
            "gas_domestic_cap_pj": {year: domestic_cap[year] for year in ("2020", "2021", "2022", "2023", "2024", "2053")},
            "gas_import_price_usd_per_gj": {year: import_price[year] for year in ("2020", "2022", "2023", "2024", "2053")},
            "gas_domestic_price_usd_per_gj": {year: domestic_price[year] for year in ("2020", "2024", "2053")}
        }
    }
    write_json(manifest_path, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    print(json.dumps(update(args.source.resolve(), args.target.resolve(), args.manifest.resolve()), indent=2))


if __name__ == "__main__":
    main()
