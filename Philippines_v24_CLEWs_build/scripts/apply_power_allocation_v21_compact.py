#!/usr/bin/env python3
"""Build the runtime-minimal Philippines v21 power-allocation candidate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import types
from datetime import date
from pathlib import Path
from typing import Any

from apply_power_allocation_v21 import (
    BIOMASS_FIT_PHP_PER_KWH, COMM as BASE_COMM, OFFGRID_GROSS_GWH,
    OFFGRID_SALES_GWH, OFFGRID_SECTOR_SHARE, PDP_REFERENCE_GWH, PHP_PER_USD,
    RESIDUE_COLLECTION_MUSD_PER_PJ_ELECTRICITY, RESIDUE_PJ_PER_MT, STOCKS, YEARS,
)


TECH = {
    "oil_grid": "TEC_2hnym", "hydro_grid": "TEC_p3vu5", "solar_grid": "TEC_1k064",
    "wind_grid": "TEC_1wdli", "biomass_nonfit": "TEC_gthhk", "biomass_supply": "TEC_telf6",
    "oil_offgrid": "TEC_v21oil", "renewable_offgrid": "TEC_v21ore", "biomass_fit": "TEC_v21bio",
}
COMM = {**BASE_COMM, "offgrid_sales": "COM_v21off"}
OFFGRID_BUILD_LIMIT_GW = {
    # The end-2020 plant register is the initial condition, so same-year new
    # capacity is zero.  Later optional ceilings are deliberately above the
    # demonstrated additions: DOE reports 31 MW of new off-grid diesel in 2022
    # and the retained recent off-grid RE register includes a 16 MW wind entry.
    # These are construction envelopes, not generation or build requirements.
    TECH["oil_offgrid"]: {year: (0.0 if year == "2020" else 0.1) for year in YEARS},
    TECH["renewable_offgrid"]: {year: (0.0 if year == "2020" else 0.02) for year in YEARS},
}


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".codex-tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row(payload: dict, parameter: str, technology: str | None = None, commodity: str | None = None,
        *, scenario: str = "SC_0", **keys: Any) -> dict:
    matches = [item for item in payload[parameter][scenario]
               if (technology is None or item.get("TechId") == technology)
               and (commodity is None or item.get("CommId") == commodity)
               and all(item.get(key) == value for key, value in keys.items())]
    if len(matches) != 1:
        raise AssertionError((parameter, technology, commodity, scenario, keys, len(matches)))
    return matches[0]


def copy_years(source: dict, target: dict) -> None:
    for year in YEARS:
        target[year] = source[year]


def projected_sales() -> dict[str, float]:
    result = dict(OFFGRID_SALES_GWH)
    for year in range(2023, 2051):
        result[str(year)] = OFFGRID_SALES_GWH["2022"] * PDP_REFERENCE_GWH[year] / PDP_REFERENCE_GWH[2022]
    for year in range(2051, 2054):
        result[str(year)] = result[str(year - 1)] * 1.054
    return result


def add_structure(gen: dict) -> None:
    assert gen["osy-casename"] == "Philippines_v20"
    gen["osy-comm"].append({
        "CommId": COMM["offgrid_sales"], "Comm": "PHL_POW_ELE_OFFGRID_FINAL",
        "Desc": "Electricity sold to customers in small-island and isolated grids; excludes own use and system loss.",
        "UnitId": "PJ",
    })
    old = {item["TechId"]: item for item in gen["osy-tech"]}

    def clone(source: str, target: str, name: str, desc: str, inputs: list[str], output: str) -> dict:
        item = copy.deepcopy(old[source])
        item.update({"TechId": target, "Tech": name, "Desc": desc, "IAR": inputs, "OAR": [output]})
        return item

    gen["osy-tech"].extend([
        clone(TECH["oil_grid"], TECH["oil_offgrid"], "PHL_POW_CHP_OIL_OFFGRID",
              "2020 oil stock and optional replacement generation in small-island and isolated grids.",
              [COMM["water"], COMM["processed_oil"]], COMM["offgrid_sales"]),
        clone(TECH["hydro_grid"], TECH["renewable_offgrid"], "PHL_POW_RE_OFFGRID",
              "Aggregate 2020 off-grid hydro, solar, and wind stock with an optional renewable replacement route.",
              [], COMM["offgrid_sales"]),
        clone(TECH["biomass_nonfit"], TECH["biomass_fit"], "PHL_POW_CHP_BIOM_FIT_OLD",
              "Closed 250 MW DOE FIT-eligible biomass tranche using crop-derived residue ceiling.",
              [COMM["water"], "COM_0"], COMM["grid_power"]),
    ])
    gen["osy-casename"] = "Philippines_v21"
    gen["osy-date"] = date.today().isoformat()
    gen["osy-desc"] = (
        "Philippines v21 compact endogenous power-allocation repair. It separates official off-grid "
        "customer service and legacy oil/renewable stocks, separates the 250 MW FIT biomass tranche "
        "with a crop-derived physical residue ceiling, and restores the retained seasonal hydro "
        "design envelope at DOE dependable capacity. No generation/share/activity target or realized "
        "investment equality is used.\n\n" + gen.get("osy-desc", "")
    )


def clone_parameters(case: Path) -> dict[str, Any]:
    analog = {TECH["oil_offgrid"]: TECH["oil_grid"],
              TECH["renewable_offgrid"]: TECH["hydro_grid"],
              TECH["biomass_fit"]: TECH["biomass_nonfit"]}
    rt = read(case / "RT.json")
    for parameter in rt:
        for scenario, rows in rt[parameter].items():
            for item in rows:
                for target, source in analog.items():
                    item[target] = item[source] if scenario == "SC_0" else None
    write(case / "RT.json", rt)

    ryt = read(case / "RYT.json")
    for parameter in ryt:
        for target, source in analog.items():
            copy_years(row(ryt, parameter, source), row(ryt, parameter, target))
    originals = {name: copy.deepcopy(row(ryt, "RC", technology)) for name, technology in {
        "oil": TECH["oil_grid"], "hydro": TECH["hydro_grid"], "solar": TECH["solar_grid"],
        "wind": TECH["wind_grid"], "biomass": TECH["biomass_nonfit"]}.items()}
    fractions = {
        "oil": STOCKS["oil_offgrid"] / STOCKS["oil_total"],
        "hydro": STOCKS["hydro_offgrid"] / STOCKS["hydro_total"],
        "solar": STOCKS["solar_offgrid"] / STOCKS["solar_total"],
        "wind": STOCKS["wind_offgrid"] / STOCKS["wind_total"],
        "biomass": STOCKS["biomass_fit"] / STOCKS["biomass_total"],
    }
    for family, technology in (("oil", TECH["oil_grid"]), ("hydro", TECH["hydro_grid"]),
                               ("solar", TECH["solar_grid"]), ("wind", TECH["wind_grid"]),
                               ("biomass", TECH["biomass_nonfit"])):
        for year in YEARS:
            row(ryt, "RC", technology)[year] = originals[family][year] * (1 - fractions[family])
    for year in YEARS:
        row(ryt, "RC", TECH["oil_offgrid"])[year] = originals["oil"][year] * fractions["oil"]
        row(ryt, "RC", TECH["renewable_offgrid"])[year] = sum(
            originals[family][year] * fractions[family] for family in ("hydro", "solar", "wind"))
        row(ryt, "RC", TECH["biomass_fit"])[year] = originals["biomass"][year] * fractions["biomass"]

    af_values = {
        TECH["oil_grid"]: STOCKS["oil_grid_dependable"] / (STOCKS["oil_total"] - STOCKS["oil_offgrid"]),
        TECH["oil_offgrid"]: STOCKS["oil_offgrid_dependable"] / STOCKS["oil_offgrid"],
        TECH["hydro_grid"]: STOCKS["hydro_grid_dependable"] / (STOCKS["hydro_total"] - STOCKS["hydro_offgrid"]),
        TECH["renewable_offgrid"]: ((STOCKS["hydro_offgrid_dependable"] + STOCKS["solar_offgrid_dependable"]
                                     + STOCKS["wind_offgrid_dependable"])
                                    / (STOCKS["hydro_offgrid"] + STOCKS["solar_offgrid"] + STOCKS["wind_offgrid"])),
    }
    for technology, value in af_values.items():
        for year in YEARS:
            row(ryt, "AF", technology)[year] = value
    for technology, limits in OFFGRID_BUILD_LIMIT_GW.items():
        for year in YEARS:
            row(ryt, "TAMaxCI", technology)[year] = limits[year]
            row(ryt, "TAMinCI", technology)[year] = 0
    for year in YEARS:
        row(ryt, "TAMaxCI", TECH["biomass_fit"])[year] = 0
        row(ryt, "TAMinCI", TECH["biomass_fit"])[year] = 0

    crop_demand = read(case / "RYC.json")
    biomass_iar = row(read(case / "RYTCM.json"), "IAR", TECH["biomass_nonfit"], "COM_0", MoId=1)
    residue_ceiling = {}
    for year in YEARS:
        residue = sum(row(crop_demand, "AAD", commodity=crop)[year] * factor
                      for crop, factor in RESIDUE_PJ_PER_MT.items())
        residue_ceiling[year] = residue
        row(ryt, "TAU", TECH["biomass_fit"])[year] = residue / biomass_iar[year]
    write(case / "RYT.json", ryt)

    rytm = read(case / "RYTM.json")
    for target, source in analog.items():
        for mode in range(1, 31):
            copy_years(row(rytm, "VC", source, MoId=mode), row(rytm, "VC", target, MoId=mode))
    supply_vc = row(rytm, "VC", TECH["biomass_supply"], MoId=1)
    fit_vc = row(rytm, "VC", TECH["biomass_fit"], MoId=1)
    for year in YEARS:
        if int(year) <= 2034:
            rate_year = year if year in BIOMASS_FIT_PHP_PER_KWH else "2025"
            fx_year = year if year in PHP_PER_USD else "2024"
            fit_credit = BIOMASS_FIT_PHP_PER_KWH[rate_year] * (1000 / 3.6) / PHP_PER_USD[fx_year]
        else:
            fit_credit = 0
        fit_vc[year] = (RESIDUE_COLLECTION_MUSD_PER_PJ_ELECTRICITY - fit_credit
                        - supply_vc[year] * biomass_iar[year] + 0.0001)
    write(case / "RYTM.json", rytm)

    rytts = read(case / "RYTTs.json")
    for target, source in analog.items():
        for source_row in [item for item in rytts["CF"]["SC_0"] if item["TechId"] == source]:
            copy_years(source_row, row(rytts, "CF", target, TsId=source_row["TsId"]))
    gen = read(case / "genData.json")
    ts_order = [item["TsId"] for item in gen["osy-ts"]]
    ys_rows = {item["TsId"]: item for item in read(case / "RYTs.json")["YS"]["SC_0"]}
    wet_share = sum(ys_rows[ts]["2020"] for ts in ts_order[:12])
    original_mean = 0.3834 * (2 * 0.2507) + 0.1447 * (2 * 0.2493)
    scale = original_mean / (0.3834 * wet_share + 0.1447 * (1 - wet_share))
    for index, ts in enumerate(ts_order):
        hydro = row(rytts, "CF", TECH["hydro_grid"], TsId=ts)
        offgrid = row(rytts, "CF", TECH["renewable_offgrid"], TsId=ts)
        solar = row(rytts, "CF", TECH["solar_grid"], TsId=ts)
        wind = row(rytts, "CF", TECH["wind_grid"], TsId=ts)
        for year in YEARS:
            hydro[year] = (0.3834 if index < 12 else 0.1447) * scale
            offgrid[year] = (STOCKS["hydro_offgrid"] * hydro[year] + STOCKS["solar_offgrid"] * solar[year]
                             + STOCKS["wind_offgrid"] * wind[year]) / (
                                 STOCKS["hydro_offgrid"] + STOCKS["solar_offgrid"] + STOCKS["wind_offgrid"])
    write(case / "RYTTs.json", rytts)

    rytcm = read(case / "RYTCM.json")
    for target, source, mappings in (
        (TECH["oil_offgrid"], TECH["oil_grid"], [(COMM["water"], COMM["water"]),
                                                  (COMM["processed_oil"], COMM["processed_oil"])]),
        (TECH["biomass_fit"], TECH["biomass_nonfit"], [(COMM["water"], COMM["water"]), ("COM_0", "COM_0")]),
    ):
        for target_comm, source_comm in mappings:
            for mode in range(1, 31):
                copy_years(row(rytcm, "IAR", source, source_comm, MoId=mode),
                           row(rytcm, "IAR", target, target_comm, MoId=mode))
    delivery = {year: (OFFGRID_SALES_GWH[year] / OFFGRID_GROSS_GWH[year]
                       if year in OFFGRID_GROSS_GWH else OFFGRID_SALES_GWH["2022"] / OFFGRID_GROSS_GWH["2022"])
                for year in YEARS}
    for technology, source in analog.items():
        output = COMM["grid_power"] if technology == TECH["biomass_fit"] else COMM["offgrid_sales"]
        for mode in range(1, 31):
            source_row = row(rytcm, "OAR", source, COMM["grid_power"], MoId=mode)
            target = row(rytcm, "OAR", technology, output, MoId=mode)
            for year in YEARS:
                target[year] = source_row[year] if technology == TECH["biomass_fit"] else source_row[year] * delivery[year]
    write(case / "RYTCM.json", rytcm)

    rytem = read(case / "RYTEM.json")
    for target, source in ((TECH["oil_offgrid"], TECH["oil_grid"]), (TECH["biomass_fit"], TECH["biomass_nonfit"])):
        emissions = {item["EmisId"] for item in rytem["EAR"]["SC_0"] if item["TechId"] == source}
        for emission in emissions:
            for mode in range(1, 31):
                copy_years(row(rytem, "EAR", source, EmisId=emission, MoId=mode),
                           row(rytem, "EAR", target, EmisId=emission, MoId=mode))
    write(case / "RYTEM.json", rytem)
    return {"residue_ceiling_pj": residue_ceiling, "hydro_raw_cf": original_mean,
            "offgrid_re_af": af_values[TECH["renewable_offgrid"]],
            "offgrid_build_limits_gw_per_year": OFFGRID_BUILD_LIMIT_GW}


def reallocate_demand(case: Path) -> dict[str, float]:
    sales = projected_sales()
    ryc = read(case / "RYC.json")
    target = row(ryc, "SAD", commodity=COMM["offgrid_sales"])
    for year in YEARS:
        value = sales[year] * 0.0036
        target[year] = value
        for commodity, share in OFFGRID_SECTOR_SHARE.items():
            row(ryc, "SAD", commodity=commodity)[year] -= value * share
    write(case / "RYC.json", ryc)
    rycts = read(case / "RYCTs.json")
    profiles = {commodity: {item["TsId"]: item for item in rycts["SDP"]["SC_0"] if item["CommId"] == commodity}
                for commodity in OFFGRID_SECTOR_SHARE}
    for target in [item for item in rycts["SDP"]["SC_0"] if item["CommId"] == COMM["offgrid_sales"]]:
        for year in YEARS:
            target[year] = sum(share * profiles[commodity][target["TsId"]][year]
                               for commodity, share in OFFGRID_SECTOR_SHARE.items())
    write(case / "RYCTs.json", rycts)
    return sales


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("--muiogo", type=Path, required=True)
    args = parser.parse_args()
    case, muiogo = args.case.resolve(), args.muiogo.resolve()
    files = sorted(path for path in case.glob("*.json") if path.name != "water_demand_validation_summary.json")
    before = {path.name: digest(path) for path in files}
    gen = read(case / "genData.json")
    add_structure(gen)
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *unused_args, **unused_kwargs: None
    sys.modules.setdefault("dotenv", dotenv_stub)
    sys.path.insert(0, str(muiogo / "API"))
    from Classes.Base.FileClass import File
    from Classes.Case.UpdateCaseClass import UpdateCase
    UpdateCase(case.name, gen).updateCase()
    File.writeFile(gen, case / "genData.json")
    physical = clone_parameters(case)
    sales = reallocate_demand(case)
    after = {path.name: digest(path) for path in files}
    changed = sorted(name for name in before if before[name] != after[name])
    expected = {"RT.json", "RYC.json", "RYCTs.json", "RYT.json", "RYTCM.json", "RYTEM.json",
                "RYTM.json", "RYTTs.json", "genData.json"}
    assert set(changed) == expected, changed
    manifest = {
        "case": str(case), "date": date.today().isoformat(), "formulation": "compact_r4",
        "changed_source_files": changed, "before_sha256": before, "after_sha256": after,
        "classification": {
            "offgrid_sales": "genuine exogenous final demand reallocated from existing national end-use totals",
            "2020_capacity": "initial stock", "dependable_capacity_and_losses": "physical driver",
            "crop_demands_and_residue_factors": "physical resource ceiling",
            "fit_eligibility_and_tariff": "continuing contractual/economic driver",
            "offgrid_build_limits": "judgmental continuing physical construction ceilings; optional and deliberately generous",
            "technology_generation": "benchmark only",
        },
        "objects_added": {"technologies": 3, "commodities": 1, "constraints": 0},
        "offgrid_sales_gwh": sales, "physical": physical,
        "no_forcing": ["no generation TAL", "no fixed share", "no realized investment equality", "no deviation penalty"],
    }
    write(case / "documentation" / "power_allocation_v21_build_manifest.json", manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
