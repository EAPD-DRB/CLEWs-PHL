#!/usr/bin/env python3
"""Build the compact, non-forcing Philippines v21 power-allocation candidate.

The script makes only three connected repairs:

* separates the physical off-grid service and its 2020 legacy stocks;
* links the FIT-eligible legacy biomass tranche to crop-residue co-products; and
* replaces the accidentally restrictive hydro time-slice profile with the
  retained CLEWs seasonal design profile, preserving its original annual mean.

Observed generation is never written to a model parameter.
"""

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


YEARS = [str(year) for year in range(2020, 2054)]
TS_WET = 12
CAPACITY_TO_ACTIVITY = 31.536

TECH = {
    "oil_grid": "TEC_2hnym",
    "hydro_grid": "TEC_p3vu5",
    "solar_grid": "TEC_1k064",
    "wind_grid": "TEC_1wdli",
    "biomass_nonfit": "TEC_gthhk",
    "oil_offgrid": "TEC_v21oil",
    "hydro_offgrid": "TEC_v21hyd",
    "solar_offgrid": "TEC_v21sol",
    "wind_offgrid": "TEC_v21wnd",
    "biomass_fit": "TEC_v21bio",
}
COMM = {
    "grid_power": "COM_o7vja",
    "offgrid_sales": "COM_v21off",
    "residue": "COM_v21res",
    "housing_electricity": "COM_9ncwn",
    "services_electricity": "COM_dyc97",
    "industry_other": "COM_8qscb",
    "rice": "COM_zrfky",
    "sugarcane": "COM_ec7z7",
    "coconut": "COM_vwhhn",
    "water": "COM_viggz",
    "processed_oil": "COM_fbce3",
    "solar_resource": "COM_fxuo5",
}

# December 2020 DOE capacity tables, GW.
STOCKS = {
    "oil_total": 4.2366,
    "oil_offgrid": 0.569224,
    "oil_grid_dependable": 2.650,
    "oil_offgrid_dependable": 0.403166,
    "hydro_total": 3.7793,
    "hydro_offgrid": 0.030595,
    "hydro_grid_dependable": 3.497,
    "hydro_offgrid_dependable": 0.030250,
    "solar_total": 1.0193,
    "solar_offgrid": 0.007230,
    "solar_offgrid_dependable": 0.007125,
    "wind_total": 0.4429,
    "wind_offgrid": 0.016,
    "wind_offgrid_dependable": 0.016,
    "biomass_total": 0.4474,
    "biomass_fit": 0.250,
}

# DOE 2020 report: 1,481 GWh consumption = 1,286 GWh customer sales,
# 3 GWh own use and 192 GWh system loss; gross generation was 1,618 GWh.
# The 2021 sales number is estimated from the retained 2020 sales/consumption
# share because the report gives only total consumption. 2022 is the sum of
# the five reported customer classes (887+332+86+181+2 GWh).
OFFGRID_SALES_GWH = {"2020": 1286.0, "2021": 1558.0 * 1286.0 / 1481.0, "2022": 1488.0}
OFFGRID_GROSS_GWH = {"2020": 1618.0, "2021": 1654.491, "2022": 1769.0}

# DOE PDP 2023-2050 reference-scenario national electricity-sales forecast.
# Only growth ratios are used after the last observed off-grid sales value.
PDP_REFERENCE_GWH = {
    2022: 91333, 2023: 96075, 2024: 100155, 2025: 105220, 2026: 111109,
    2027: 117653, 2028: 124797, 2029: 132399, 2030: 140459, 2031: 149027,
    2032: 158062, 2033: 167588, 2034: 177624, 2035: 188188, 2036: 199260,
    2037: 210870, 2038: 223045, 2039: 235809, 2040: 249186, 2041: 262514,
    2042: 276378, 2043: 290798, 2044: 305794, 2045: 321381, 2046: 337524,
    2047: 354247, 2048: 371567, 2049: 389499, 2050: 408057,
}

# Customer class shares from the same DOE 2020 off-grid figure.
OFFGRID_SECTOR_SHARE = {
    COMM["housing_electricity"]: 785.0 / 1286.0,
    COMM["services_electricity"]: 433.0 / 1286.0,
    COMM["industry_other"]: 68.0 / 1286.0,
}

# DOE Phil-LiDAR 2 residue fraction * net calorific value * availability.
RESIDUE_PJ_PER_MT = {
    COMM["rice"]: 0.225 * 16.5 * 0.81,
    COMM["sugarcane"]: 0.29 * 16.56 * 0.61,
    COMM["coconut"]: (0.35 * 21.75 + 0.15 * 25.32) * 0.55,
}

# ERC FIT and World Bank official exchange-rate series. 2020 is Resolution 06;
# 2021-2025 are the adjusted 2014-2015 entrant rates approved in 2025.
BIOMASS_FIT_PHP_PER_KWH = {
    "2020": 6.63, "2021": 7.0655, "2022": 6.9609,
    "2023": 7.3298, "2024": 7.9363, "2025": 8.1259,
}
PHP_PER_USD = {
    "2020": 49.6240960026328, "2021": 49.2545977288412,
    "2022": 54.477785837205, "2023": 55.630363223193,
    "2024": 57.2906550699734,
}

# Collection/handling is an explicit, inspectable judgement anchored to the
# ERC published biomass fuel component (Php5.50/kWh at 1.7 kg/kWh). It is not
# back-calculated from observed electricity production.
RESIDUE_COLLECTION_MUSD_PER_PJ_ELECTRICITY = 15.8


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".codex-tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row(payload: dict, parameter: str, technology: str, *, scenario: str = "SC_0", **keys: Any) -> dict:
    matches = [
        item for item in payload[parameter][scenario]
        if item.get("TechId") == technology and all(item.get(key) == value for key, value in keys.items())
    ]
    if len(matches) != 1:
        raise AssertionError((parameter, technology, scenario, keys, len(matches)))
    return matches[0]


def commodity_row(payload: dict, parameter: str, commodity: str, *, scenario: str = "SC_0", **keys: Any) -> dict:
    matches = [
        item for item in payload[parameter][scenario]
        if item.get("CommId") == commodity and all(item.get(key) == value for key, value in keys.items())
    ]
    if len(matches) != 1:
        raise AssertionError((parameter, commodity, scenario, keys, len(matches)))
    return matches[0]


def copy_years(source: dict, target: dict) -> None:
    for year in YEARS:
        target[year] = source[year]


def projected_offgrid_sales() -> dict[str, float]:
    result = dict(OFFGRID_SALES_GWH)
    for year in range(2023, 2051):
        result[str(year)] = OFFGRID_SALES_GWH["2022"] * PDP_REFERENCE_GWH[year] / PDP_REFERENCE_GWH[2022]
    for year in range(2051, 2054):
        result[str(year)] = result[str(year - 1)] * 1.054
    return result


def add_structure(gen: dict) -> None:
    if gen["osy-casename"] != "Philippines_v20":
        raise AssertionError(gen["osy-casename"])
    if any(item["CommId"] in {COMM["offgrid_sales"], COMM["residue"]} for item in gen["osy-comm"]):
        raise AssertionError("v21 commodities already exist")
    if any(item["TechId"] in set(TECH.values()) - {TECH[k] for k in ("oil_grid", "hydro_grid", "solar_grid", "wind_grid", "biomass_nonfit")} for item in gen["osy-tech"]):
        raise AssertionError("v21 technologies already exist")

    gen["osy-comm"].extend([
        {"CommId": COMM["offgrid_sales"], "Comm": "PHL_POW_ELE_OFFGRID_FINAL",
         "Desc": "Electricity sold to customers in small-island and isolated grids; excludes own use and system loss.", "UnitId": "PJ"},
        {"CommId": COMM["residue"], "Comm": "PHL_PRO_AGR_RESIDUE",
         "Desc": "Recoverable energy in rice husk, bagasse, and coconut husk/shell co-produced with modeled crops.", "UnitId": "PJ"},
    ])

    old = {item["TechId"]: item for item in gen["osy-tech"]}

    def clone(analog: str, new_id: str, name: str, desc: str, inputs: list[str], output: str) -> dict:
        item = copy.deepcopy(old[analog])
        item.update({"TechId": new_id, "Tech": name, "Desc": desc, "IAR": inputs, "OAR": [output]})
        return item

    gen["osy-tech"].extend([
        clone(TECH["oil_grid"], TECH["oil_offgrid"], "PHL_POW_CHP_OIL_OFFGRID_OLD",
              "Closed 2020 off-grid oil stock serving small-island and isolated grids.",
              [COMM["water"], COMM["processed_oil"]], COMM["offgrid_sales"]),
        clone(TECH["hydro_grid"], TECH["hydro_offgrid"], "PHL_POW_PP_HY_OFFGRID_OLD",
              "Closed 2020 off-grid hydropower stock.", [], COMM["offgrid_sales"]),
        clone(TECH["solar_grid"], TECH["solar_offgrid"], "PHL_POW_PP_SPV_OFFGRID_OLD",
              "Closed 2020 off-grid solar photovoltaic stock.", [COMM["solar_resource"]], COMM["offgrid_sales"]),
        clone(TECH["wind_grid"], TECH["wind_offgrid"], "PHL_POW_PP_WON_OFFGRID_OLD",
              "Closed 2020 off-grid wind stock.", [], COMM["offgrid_sales"]),
        clone(TECH["biomass_nonfit"], TECH["biomass_fit"], "PHL_POW_CHP_BIOM_FIT_OLD",
              "Closed legacy biomass tranche with DOE FIT eligibility and crop-residue fuel.",
              [COMM["water"], COMM["residue"]], COMM["grid_power"]),
    ])

    crop_ids = set(RESIDUE_PJ_PER_MT)
    crop_techs = [item for item in gen["osy-tech"] if crop_ids.intersection(item.get("OAR", []))]
    if len(crop_techs) != 8:
        raise AssertionError(f"expected eight land clusters, found {len(crop_techs)}")
    for item in crop_techs:
        if COMM["residue"] not in item["OAR"]:
            item["OAR"].append(COMM["residue"])

    gen["osy-casename"] = "Philippines_v21"
    gen["osy-date"] = date.today().isoformat()
    gen["osy-desc"] = (
        "Philippines v21 compact endogenous power-allocation repair. It separates the official "
        "off-grid customer service and 2020 oil/renewable stocks, links the closed FIT-eligible "
        "biomass tranche to recoverable crop residues, and restores the retained seasonal hydro "
        "design envelope at the DOE dependable-capacity ratio. Generation observations remain "
        "benchmarks; no generation/share/activity target or realized investment equality is used.\n\n"
        + gen.get("osy-desc", "")
    )


def clone_technology_parameters(case: Path) -> None:
    analog = {
        TECH["oil_offgrid"]: TECH["oil_grid"],
        TECH["hydro_offgrid"]: TECH["hydro_grid"],
        TECH["solar_offgrid"]: TECH["solar_grid"],
        TECH["wind_offgrid"]: TECH["wind_grid"],
        TECH["biomass_fit"]: TECH["biomass_nonfit"],
    }

    rt = read(case / "RT.json")
    for parameter, scenarios in rt.items():
        for scenario, rows in scenarios.items():
            for item in rows:
                for target, source in analog.items():
                    item[target] = item[source] if scenario == "SC_0" else None
    write(case / "RT.json", rt)

    ryt = read(case / "RYT.json")
    for parameter in ryt:
        for target, source in analog.items():
            copy_years(row(ryt, parameter, source), row(ryt, parameter, target))

    split = {
        TECH["oil_grid"]: (STOCKS["oil_total"] - STOCKS["oil_offgrid"]) / STOCKS["oil_total"],
        TECH["oil_offgrid"]: STOCKS["oil_offgrid"] / STOCKS["oil_total"],
        TECH["hydro_grid"]: (STOCKS["hydro_total"] - STOCKS["hydro_offgrid"]) / STOCKS["hydro_total"],
        TECH["hydro_offgrid"]: STOCKS["hydro_offgrid"] / STOCKS["hydro_total"],
        TECH["solar_grid"]: (STOCKS["solar_total"] - STOCKS["solar_offgrid"]) / STOCKS["solar_total"],
        TECH["solar_offgrid"]: STOCKS["solar_offgrid"] / STOCKS["solar_total"],
        TECH["wind_grid"]: (STOCKS["wind_total"] - STOCKS["wind_offgrid"]) / STOCKS["wind_total"],
        TECH["wind_offgrid"]: STOCKS["wind_offgrid"] / STOCKS["wind_total"],
        TECH["biomass_nonfit"]: (STOCKS["biomass_total"] - STOCKS["biomass_fit"]) / STOCKS["biomass_total"],
        TECH["biomass_fit"]: STOCKS["biomass_fit"] / STOCKS["biomass_total"],
    }
    original_rc = {
        name: copy.deepcopy(row(ryt, "RC", source))
        for name, source in {
            "oil": TECH["oil_grid"], "hydro": TECH["hydro_grid"],
            "solar": TECH["solar_grid"], "wind": TECH["wind_grid"],
            "biomass": TECH["biomass_nonfit"],
        }.items()
    }
    family = {
        TECH["oil_grid"]: "oil", TECH["oil_offgrid"]: "oil",
        TECH["hydro_grid"]: "hydro", TECH["hydro_offgrid"]: "hydro",
        TECH["solar_grid"]: "solar", TECH["solar_offgrid"]: "solar",
        TECH["wind_grid"]: "wind", TECH["wind_offgrid"]: "wind",
        TECH["biomass_nonfit"]: "biomass", TECH["biomass_fit"]: "biomass",
    }
    for technology, group in family.items():
        target = row(ryt, "RC", technology)
        for year in YEARS:
            target[year] = original_rc[group][year] * split[technology]

    af = {
        TECH["oil_grid"]: STOCKS["oil_grid_dependable"] / (STOCKS["oil_total"] - STOCKS["oil_offgrid"]),
        TECH["oil_offgrid"]: STOCKS["oil_offgrid_dependable"] / STOCKS["oil_offgrid"],
        TECH["hydro_grid"]: STOCKS["hydro_grid_dependable"] / (STOCKS["hydro_total"] - STOCKS["hydro_offgrid"]),
        TECH["hydro_offgrid"]: STOCKS["hydro_offgrid_dependable"] / STOCKS["hydro_offgrid"],
        TECH["solar_offgrid"]: STOCKS["solar_offgrid_dependable"] / STOCKS["solar_offgrid"],
        TECH["wind_offgrid"]: STOCKS["wind_offgrid_dependable"] / STOCKS["wind_offgrid"],
    }
    for technology, value in af.items():
        target = row(ryt, "AF", technology)
        for year in YEARS:
            target[year] = value

    # These are closed initial stocks, not investment options.
    for technology in (TECH["oil_offgrid"], TECH["hydro_offgrid"], TECH["solar_offgrid"],
                       TECH["wind_offgrid"], TECH["biomass_fit"]):
        for year in YEARS:
            row(ryt, "TAMaxCI", technology)[year] = 0
            row(ryt, "TAMinCI", technology)[year] = 0
    write(case / "RYT.json", ryt)

    rytm = read(case / "RYTM.json")
    for target, source in analog.items():
        for mode in range(1, 31):
            copy_years(row(rytm, "VC", source, MoId=mode), row(rytm, "VC", target, MoId=mode))

    # FIT credit converts Php/kWh to MUSD/PJ: rate * 277.777... / Php per USD.
    fit_vc = row(rytm, "VC", TECH["biomass_fit"], MoId=1)
    for year in YEARS:
        if int(year) <= 2034:
            rate_year = year if year in BIOMASS_FIT_PHP_PER_KWH else "2025"
            fx_year = year if year in PHP_PER_USD else "2024"
            credit = BIOMASS_FIT_PHP_PER_KWH[rate_year] * (1000.0 / 3.6) / PHP_PER_USD[fx_year]
            fit_vc[year] = RESIDUE_COLLECTION_MUSD_PER_PJ_ELECTRICITY - credit + 0.0001
        else:
            fit_vc[year] = RESIDUE_COLLECTION_MUSD_PER_PJ_ELECTRICITY + 0.0001
    write(case / "RYTM.json", rytm)

    rytts = read(case / "RYTTs.json")
    for target, source in analog.items():
        source_rows = [item for item in rytts["CF"]["SC_0"] if item.get("TechId") == source]
        for source_row in source_rows:
            copy_years(source_row, row(rytts, "CF", target, TsId=source_row["TsId"]))

    # Preserve the retained CLEWs annual mean (0.26438418) under the current
    # 30-slice YearSplit while retaining its wet/dry ratio 0.3834/0.1447.
    ysplit = read(case / "RYTs.json")
    ts_order = [item["TsId"] for item in read(case / "genData.json")["osy-ts"]]
    ys_rows = {item["TsId"]: item for item in ysplit["YS"]["SC_0"]}
    wet_share = sum(ys_rows[ts]["2020"] for ts in ts_order[:TS_WET])
    original_mean = 0.3834 * (2 * 0.2507) + 0.1447 * (2 * 0.2493)
    scale = original_mean / (0.3834 * wet_share + 0.1447 * (1 - wet_share))
    wet_cf, dry_cf = 0.3834 * scale, 0.1447 * scale
    for technology in (TECH["hydro_grid"], TECH["hydro_offgrid"]):
        for index, ts in enumerate(ts_order):
            target = row(rytts, "CF", technology, TsId=ts)
            for year in YEARS:
                target[year] = wet_cf if index < TS_WET else dry_cf
    write(case / "RYTTs.json", rytts)

    rytcm = read(case / "RYTCM.json")
    # Copy matching inputs and emissions for off-grid technologies.
    input_map = {
        TECH["oil_offgrid"]: [(COMM["water"], TECH["oil_grid"], COMM["water"]),
                              (COMM["processed_oil"], TECH["oil_grid"], COMM["processed_oil"])],
        TECH["solar_offgrid"]: [(COMM["solar_resource"], TECH["solar_grid"], COMM["solar_resource"])],
        TECH["biomass_fit"]: [(COMM["water"], TECH["biomass_nonfit"], COMM["water"]),
                              (COMM["residue"], TECH["biomass_nonfit"], "COM_0")],
    }
    for target, mappings in input_map.items():
        for target_comm, source_tech, source_comm in mappings:
            for mode in range(1, 31):
                source = row(rytcm, "IAR", source_tech, CommId=source_comm, MoId=mode)
                copy_years(source, row(rytcm, "IAR", target, CommId=target_comm, MoId=mode))

    delivery_efficiency = {}
    for year in YEARS:
        if year in OFFGRID_GROSS_GWH:
            delivery_efficiency[year] = OFFGRID_SALES_GWH[year] / OFFGRID_GROSS_GWH[year]
        else:
            delivery_efficiency[year] = OFFGRID_SALES_GWH["2022"] / OFFGRID_GROSS_GWH["2022"]
    for technology, source_technology in analog.items():
        source_output = COMM["grid_power"]
        target_output = COMM["grid_power"] if technology == TECH["biomass_fit"] else COMM["offgrid_sales"]
        for mode in range(1, 31):
            source_row = row(rytcm, "OAR", source_technology, CommId=source_output, MoId=mode)
            target = row(rytcm, "OAR", technology, CommId=target_output, MoId=mode)
            for year in YEARS:
                target[year] = (source_row[year] if technology == TECH["biomass_fit"]
                                else source_row[year] * delivery_efficiency[year])

    # Crop residue is a co-product, calculated directly from each crop OAR.
    crop_techs = [item["TechId"] for item in read(case / "genData.json")["osy-tech"]
                  if set(RESIDUE_PJ_PER_MT).intersection(item.get("OAR", []))]
    for technology in crop_techs:
        for mode in range(1, 31):
            target = row(rytcm, "OAR", technology, CommId=COMM["residue"], MoId=mode)
            for year in YEARS:
                target[year] = sum(
                    row(rytcm, "OAR", technology, CommId=crop, MoId=mode)[year] * factor
                    for crop, factor in RESIDUE_PJ_PER_MT.items()
                )
    write(case / "RYTCM.json", rytcm)

    rytem = read(case / "RYTEM.json")
    for target, source in ((TECH["oil_offgrid"], TECH["oil_grid"]),
                           (TECH["biomass_fit"], TECH["biomass_nonfit"])):
        for emission in [item["EmisId"] for item in rytem["EAR"]["SC_0"] if item.get("TechId") == source]:
            for mode in range(1, 31):
                copy_years(row(rytem, "EAR", source, EmisId=emission, MoId=mode),
                           row(rytem, "EAR", target, EmisId=emission, MoId=mode))
    write(case / "RYTEM.json", rytem)


def apply_demand_reallocation(case: Path) -> dict[str, Any]:
    sales = projected_offgrid_sales()
    ryc = read(case / "RYC.json")
    offgrid = commodity_row(ryc, "SAD", COMM["offgrid_sales"])
    reductions: list[dict[str, Any]] = []
    for year in YEARS:
        pj = sales[year] * 0.0036
        offgrid[year] = pj
        for commodity, share in OFFGRID_SECTOR_SHARE.items():
            target = commodity_row(ryc, "SAD", commodity)
            before = target[year]
            after = before - pj * share
            if after <= 0:
                raise AssertionError((commodity, year, before, pj * share))
            target[year] = after
            if year in {"2020", "2021", "2022", "2023", "2024"}:
                reductions.append({"year": int(year), "commodity": commodity, "before_pj": before,
                                   "reallocated_pj": pj * share, "after_pj": after})
    write(case / "RYC.json", ryc)

    rycts = read(case / "RYCTs.json")
    profile_rows = {
        commodity: {item["TsId"]: item for item in rycts["SDP"]["SC_0"] if item["CommId"] == commodity}
        for commodity in OFFGRID_SECTOR_SHARE
    }
    targets = {item["TsId"]: item for item in rycts["SDP"]["SC_0"] if item["CommId"] == COMM["offgrid_sales"]}
    if len(targets) != 30:
        raise AssertionError(len(targets))
    for ts, target in targets.items():
        for year in YEARS:
            target[year] = sum(OFFGRID_SECTOR_SHARE[commodity] * profile_rows[commodity][ts][year]
                               for commodity in OFFGRID_SECTOR_SHARE)
    write(case / "RYCTs.json", rycts)
    return {"sales_gwh": sales, "historical_sector_reductions": reductions}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("--muiogo", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    case, muiogo = args.case.resolve(), args.muiogo.resolve()
    if not case.is_dir():
        raise FileNotFoundError(case)

    source_files = sorted(path for path in case.glob("*.json") if path.name != "water_demand_validation_summary.json")
    before = {path.name: digest(path) for path in source_files}
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
    clone_technology_parameters(case)
    demand = apply_demand_reallocation(case)

    after = {path.name: digest(path) for path in source_files}
    changed = sorted(name for name in before if before[name] != after[name])
    expected = {"RT.json", "RYC.json", "RYCTs.json", "RYT.json", "RYTCM.json", "RYTEM.json",
                "RYTM.json", "RYTTs.json", "genData.json"}
    if set(changed) != expected:
        raise AssertionError({"changed": changed, "expected": sorted(expected)})

    sales = demand["sales_gwh"]
    manifest = {
        "case": str(case), "date": date.today().isoformat(),
        "observation_classification": {
            "doe_2020_offgrid_installed_and_dependable_capacity": "initial stock and continuing physical availability",
            "doe_2020_2022_offgrid_customer_sales": "genuine exogenous final demand",
            "doe_offgrid_gross_generation": "loss-accounting input and validation benchmark, never a technology target",
            "doe_2020_2024_generation_by_technology": "benchmark only",
            "doe_biomass_fit_eligible_capacity": "initial contractual stock classification",
            "doe_phil_lidar_crop_residue_factors": "physical co-product driver",
            "inherited_clews_hydro_profile": "engineering design envelope with missing original row bibliography",
        },
        "changed_source_files": changed,
        "before_sha256": before, "after_sha256": after,
        "offgrid": {
            "sales_gwh": sales,
            "delivery_efficiency": {year: OFFGRID_SALES_GWH[year] / OFFGRID_GROSS_GWH[year]
                                    for year in OFFGRID_GROSS_GWH},
            "stocks_gw": {key: value for key, value in STOCKS.items() if "offgrid" in key},
            "sector_shares": OFFGRID_SECTOR_SHARE,
            "historical_sector_reductions": demand["historical_sector_reductions"],
        },
        "biomass": {
            "fit_stock_gw": STOCKS["biomass_fit"],
            "residue_pj_per_mt_crop": RESIDUE_PJ_PER_MT,
            "collection_cost_musd_per_pj_electricity": RESIDUE_COLLECTION_MUSD_PER_PJ_ELECTRICITY,
            "fit_php_per_kwh": BIOMASS_FIT_PHP_PER_KWH,
            "fit_credit_end_year": 2034,
        },
        "hydro": {
            "retained_original_wet_cf": 0.3834, "retained_original_dry_cf": 0.1447,
            "retained_original_annual_mean": 0.3834 * (2 * 0.2507) + 0.1447 * (2 * 0.2493),
            "grid_af": STOCKS["hydro_grid_dependable"] / (STOCKS["hydro_total"] - STOCKS["hydro_offgrid"]),
            "offgrid_af": STOCKS["hydro_offgrid_dependable"] / STOCKS["hydro_offgrid"],
            "note": "No observed hydro PJ was used; NASA precipitation-only scaling was rejected before optimization because precipitation is not a defensible inflow-to-generation transform.",
        },
        "prohibited_changes_confirmed_absent": [
            "generation TAL/TAU bounds", "fixed technology shares", "realized capacity-addition equalities",
            "generation-deviation penalties", "sensitivity runs",
        ],
    }
    manifest_path = args.manifest or case / "documentation" / "power_allocation_v21_build_manifest.json"
    write(manifest_path, manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
