#!/usr/bin/env python3
"""Build Philippines_v12 by grafting the raw CLEWs nexus onto v10.

The script deliberately preserves every inherited v10 technology and parameter
record except the explicitly retired placeholder land/precipitation block.  It
does not calibrate or otherwise tune the upstream land, crop, or water data.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any


RETIRED_TECH_NAMES = {
    "PHL_MIN_PRC",
    "PHL_LND_OTH",
    "PHL_LND_GRS",
    "PHL_LND_BLT",
    "PHL_LND_WAT",
    "PHL_LND_FOR",
    "PHL_LND_CRP",
    "PHL_LND",
}

RETIRED_COMM_NAMES = {
    "PHL_LND_LOTH",
    "PHL_LND_LGRS",
    "PHL_LND_LBLT",
    "PHL_LND_LWAT",
    "PHL_LND_LFOR",
    "PHL_LND_LCRP",
}

# These connections make the new nexus part of the inherited system instead
# of creating parallel, disconnected energy/water/land commodities.
RAW_TO_V10_COMMODITY = {
    "AGRELCPHLXX02": "PHL_AGR_ELE",
    "LTOT": "PHL_LND",
    "WTREVTPHL": "PHL_WTR_EVT",
    "WTRGRCPHL": "PHL_WTR_GWT",
    "WTRPRCPHL": "PHL_WTR_PRC",
    "WTRSURPHL": "PHL_WTR_SUR",
}

SCENARIO_NAMES = {
    "SC_0": "BASE",
    "SC_3hgjb": "COAL_PHASEOUT",
    "SC_w03qj": "RE",
    "SC_huc7i": "EV",
}

RT_CSV = {
    "TMPAU": "TotalTechnologyModelPeriodActivityUpperLimit.csv",
    "TMPAL": "TotalTechnologyModelPeriodActivityLowerLimit.csv",
    "OL": "OperationalLife.csv",
    "CAU": "CapacityToActivityUnit.csv",
    "DRI": "DiscountRateIdv.csv",
}

RYT_CSV = {
    "COTU": "CapacityOfOneTechnologyUnit.csv",
    "TAU": "TotalTechnologyAnnualActivityUpperLimit.csv",
    "TAL": "TotalTechnologyAnnualActivityLowerLimit.csv",
    "TAMinCI": "TotalAnnualMinCapacityInvestment.csv",
    "TAMinC": "TotalAnnualMinCapacity.csv",
    "TAMaxCI": "TotalAnnualMaxCapacityInvestment.csv",
    "TAMaxC": "TotalAnnualMaxCapacity.csv",
    "RC": "ResidualCapacity.csv",
    "FC": "FixedCost.csv",
    "CC": "CapitalCost.csv",
    "AF": "AvailabilityFactor.csv",
}

RYTM_CSV = {
    "TAIML": "TechnologyActivityIncreaseByModeLimit.csv",
    "TADML": "TechnologyActivityDecreaseByModeLimit.csv",
    "TAMUL": "TechnologyActivityByModeUpperLimit.csv",
    "TAMLL": "TechnologyActivityByModeLowerLimit.csv",
    "VC": "VariableCost.csv",
}

RYC_CSV = {
    "SAD": "SpecifiedAnnualDemand.csv",
    "AAD": "AccumulatedAnnualDemand.csv",
}

CROP_NAMES = {
    "CON": "coconuts",
    "MZE": "maize",
    "OTH": "other crops",
    "RCP": "rice",
    "SGC": "sugar cane",
    "TOM": "vegetables (tomato GAEZ proxy)",
}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=4)


def parse_number(value: str) -> int | float:
    number = float(value)
    if number.is_integer() and "." not in value and "e" not in value.lower():
        return int(number)
    return number


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def raw_tech_selected(name: str) -> bool:
    return name.startswith("LND") or name in {
        "MINLNDTOT",
        "MINPRCPHL",
        "DEMAGRGWTPHL",
        "DEMAGRSURPHL",
    }


def parameter_defaults(path: Path) -> dict[str, Any]:
    groups = read_json(path)
    return {
        parameter["id"]: parameter["default"]
        for parameters in groups.values()
        for parameter in parameters
    }


def index_csv(
    csv_dir: Path,
    filename: str,
    dimensions: tuple[str, ...],
    tech_names: set[str] | None = None,
    fuel_names: set[str] | None = None,
) -> dict[tuple[str, ...], int | float]:
    indexed: dict[tuple[str, ...], int | float] = {}
    for row in read_csv_rows(csv_dir / filename):
        if tech_names is not None and row.get("TECHNOLOGY") not in tech_names:
            continue
        if fuel_names is not None and row.get("FUEL") not in fuel_names:
            continue
        key = tuple(row[dimension] for dimension in dimensions)
        indexed[key] = parse_number(row["VALUE"])
    return indexed


def tech_description(name: str) -> str:
    if name == "MINLNDTOT":
        return "National land endowment supply from the raw Philippines CLEWs Global build."
    if name == "MINPRCPHL":
        return "National precipitation supply from clustered Philippines geospatial data."
    if name == "DEMAGRGWTPHL":
        return "Groundwater irrigation supply using existing agricultural electricity."
    if name == "DEMAGRSURPHL":
        return "Surface-water irrigation supply."
    if name.startswith("LNDAGRPHLC"):
        return (
            f"Spatial land, crop, and water allocation for Philippines cluster "
            f"{int(name[-2:])}."
        )
    land_cover = {
        "LNDBARTOT": "Bare land accounting",
        "LNDBLTTOT": "Built-up land accounting",
        "LNDFORTOT": "Forest land accounting",
        "LNDGRSTOT": "Grassland accounting",
        "LNDOTHTOT": "Other land accounting",
        "LNDWATTOT": "Water-body land accounting",
    }
    if name in land_cover:
        return f"{land_cover[name]} from the raw Philippines CLEWs Global build."
    match = re.fullmatch(r"LND(CON|MZE|OTH|RCP|SGC|TOM)(H|L)(I|R)TOT", name)
    if match:
        crop, inputs, water = match.groups()
        return (
            f"{CROP_NAMES[crop].capitalize()} land option: "
            f"{'high' if inputs == 'H' else 'low'} inputs, "
            f"{'irrigated' if water == 'I' else 'rainfed'}."
        )
    return f"{name} from the raw Philippines CLEWs Global build."


def commodity_description(name: str) -> str:
    fixed = {
        "AGRWATPHL": "Irrigation water available to crop production.",
        "CRPCON": "Coconut production.",
        "CRPMZE": "Maize production.",
        "CRPOTH": "Other crop production.",
        "CRPRCP": "Rice production.",
        "CRPSGC": "Sugar-cane production.",
        "CRPTOM": "Vegetable production represented by the GAEZ tomato proxy.",
        "LBARTOT": "Bare land.",
        "LBLTTOT": "Built-up land.",
        "LFORTOT": "Forest land.",
        "LGRSTOT": "Grassland.",
        "LOTHTOT": "Other land.",
        "LWATTOT": "Water-body land.",
    }
    if name in fixed:
        return fixed[name]
    match = re.fullmatch(r"L(CON|MZE|OTH|RCP|SGC|TOM)(H|L)(I|R)TOT", name)
    if match:
        crop, inputs, water = match.groups()
        return (
            f"Land allocated to {CROP_NAMES[crop]}, "
            f"{'high' if inputs == 'H' else 'low'} inputs, "
            f"{'irrigated' if water == 'I' else 'rainfed'}."
        )
    return f"{name} nexus commodity from the raw Philippines CLEWs Global build."


def commodity_unit(name: str) -> str:
    if name.startswith("CRP"):
        return "Mt"
    if name == "AGRWATPHL":
        return "10<sup>9</sup>m<sup>3</sup>"
    return "10<sup>3</sup>km<sup>2</sup>"


def tech_units(name: str) -> tuple[str, str]:
    if name in {"MINPRCPHL", "DEMAGRGWTPHL", "DEMAGRSURPHL"}:
        water = "10<sup>9</sup>m<sup>3</sup>"
        return water, water
    land = "10<sup>3</sup>km<sup>2</sup>"
    return land, land


def null_year_row(years: list[int], **dimensions: Any) -> dict[str, Any]:
    row = dict(dimensions)
    row.update({str(year): None for year in years})
    return row


def valued_year_row(
    years: list[int],
    values: dict[tuple[str, ...], int | float],
    key_prefix: tuple[str, ...],
    default: Any,
    **dimensions: Any,
) -> dict[str, Any]:
    row = dict(dimensions)
    for year in years:
        row[str(year)] = values.get((*key_prefix, str(year)), default)
    return row


def remove_references(
    case_dir: Path, retired_tech_ids: set[str], retired_comm_ids: set[str]
) -> None:
    for path in case_dir.glob("*.json"):
        if path.name == "genData.json":
            continue
        data = read_json(path)
        changed = False
        for parameter in data.values():
            if not isinstance(parameter, dict):
                continue
            for scenario, rows in parameter.items():
                if not isinstance(rows, list):
                    continue
                new_rows = []
                for row in rows:
                    if not isinstance(row, dict):
                        new_rows.append(row)
                        continue
                    if row.get("TechId") in retired_tech_ids:
                        changed = True
                        continue
                    if row.get("CommId") in retired_comm_ids:
                        changed = True
                        continue
                    if len(rows) == 1 and not any(
                        key in row
                        for key in (
                            "TechId",
                            "CommId",
                            "EmisId",
                            "StgId",
                            "ConId",
                            "TsId",
                            "SeId",
                            "DtId",
                            "DtbId",
                            "MoId",
                        )
                    ):
                        for tech_id in retired_tech_ids:
                            if tech_id in row:
                                del row[tech_id]
                                changed = True
                    new_rows.append(row)
                parameter[scenario] = new_rows
        if changed:
            write_json(path, data)


def ensure_mode_rows(
    data: dict[str, dict[str, list[dict[str, Any]]]],
    parameter: str,
    scenarios: list[str],
    years: list[int],
    dimensions: list[dict[str, Any]],
    default: Any,
    raw_values: dict[tuple[str, ...], int | float] | None = None,
    new_tech_ids: set[str] | None = None,
    tech_name_by_id: dict[str, str] | None = None,
    comm_name_by_id: dict[str, str] | None = None,
) -> None:
    raw_values = raw_values or {}
    new_tech_ids = new_tech_ids or set()
    tech_name_by_id = tech_name_by_id or {}
    comm_name_by_id = comm_name_by_id or {}

    for scenario in scenarios:
        rows = data[parameter][scenario]
        key_fields = list(dimensions[0]) if dimensions else []
        existing = {tuple(row[field] for field in key_fields): row for row in rows}
        for dims in dimensions:
            key = tuple(dims[field] for field in key_fields)
            if key in existing:
                continue
            if scenario != "SC_0":
                rows.append(null_year_row(years, **dims))
                continue
            tech_id = dims.get("TechId")
            if tech_id not in new_tech_ids:
                rows.append(
                    {
                        **dims,
                        **{str(year): default for year in years},
                    }
                )
                continue
            tech_name = tech_name_by_id[tech_id]
            prefix: tuple[str, ...]
            if "CommId" in dims:
                prefix = (
                    tech_name,
                    comm_name_by_id[dims["CommId"]],
                    str(dims["MoId"]),
                )
            elif "EmisId" in dims:
                prefix = ()
            else:
                prefix = (tech_name, str(dims["MoId"]))
            rows.append(
                valued_year_row(years, raw_values, prefix, default, **dims)
            )


def build(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo.resolve()
    source_case = repo / "WebAPP/DataStorage/Philippines_v10"
    raw_case = repo / "WebAPP/DataStorage/Philippines_v12_raw_CLEWs"
    destination = repo / "WebAPP/DataStorage/Philippines_v12"
    csv_dir = (
        repo / "Philippines_v12_CLEWs_build/model/inputs/clewsy"
        if args.csv_dir is None
        else args.csv_dir.resolve()
    )

    if destination.exists():
        raise FileExistsError(
            f"{destination} already exists; move it aside before rebuilding."
        )
    if not source_case.is_dir() or not raw_case.is_dir() or not csv_dir.is_dir():
        raise FileNotFoundError("Required v10, raw import, or raw CSV directory is missing.")

    shutil.copytree(source_case, destination)
    shutil.rmtree(destination / "res", ignore_errors=True)
    shutil.rmtree(destination / "view", ignore_errors=True)
    (destination / "view").mkdir()
    write_json(destination / "view/resData.json", {"osy-cases": []})
    shutil.copy2(
        raw_case / "view/viewDefinitions.json",
        destination / "view/viewDefinitions.json",
    )
    for stale in ("export.csv",):
        (destination / stale).unlink(missing_ok=True)

    gen = read_json(destination / "genData.json")
    raw_gen = read_json(raw_case / "genData.json")
    years = [int(year) for year in gen["osy-years"]]
    scenarios = [item["ScenarioId"] for item in gen["osy-scenarios"]]
    defaults = parameter_defaults(repo / "WebAPP/DataStorage/Parameters.json")

    old_tech_by_name = {item["Tech"]: item for item in gen["osy-tech"]}
    old_comm_by_name = {item["Comm"]: item for item in gen["osy-comm"]}
    retired_tech_ids = {
        old_tech_by_name[name]["TechId"] for name in RETIRED_TECH_NAMES
    }
    retired_comm_ids = {
        old_comm_by_name[name]["CommId"] for name in RETIRED_COMM_NAMES
    }

    raw_tech_by_name = {item["Tech"]: item for item in raw_gen["osy-tech"]}
    raw_comm_by_name = {item["Comm"]: item for item in raw_gen["osy-comm"]}
    selected_names = {
        name for name in raw_tech_by_name if raw_tech_selected(name)
    }
    selected_raw_techs = [
        item for item in raw_gen["osy-tech"] if item["Tech"] in selected_names
    ]
    if len(selected_raw_techs) != 42:
        raise ValueError(f"Expected 42 nexus technologies, found {len(selected_raw_techs)}")

    iar_rows = [
        row
        for row in read_csv_rows(csv_dir / "InputActivityRatio.csv")
        if row["TECHNOLOGY"] in selected_names
    ]
    oar_rows = [
        row
        for row in read_csv_rows(csv_dir / "OutputActivityRatio.csv")
        if row["TECHNOLOGY"] in selected_names
    ]
    relevant_fuels = {row["FUEL"] for row in iar_rows + oar_rows}

    raw_comm_id_to_final: dict[str, str] = {}
    raw_comm_name_to_final: dict[str, str] = {}
    for name in relevant_fuels:
        raw_id = raw_comm_by_name[name]["CommId"]
        if name in RAW_TO_V10_COMMODITY:
            final_id = old_comm_by_name[RAW_TO_V10_COMMODITY[name]]["CommId"]
        else:
            final_id = raw_id
        raw_comm_id_to_final[raw_id] = final_id
        raw_comm_name_to_final[name] = final_id

    remaining_tech_ids = {
        item["TechId"] for item in gen["osy-tech"] if item["TechId"] not in retired_tech_ids
    }
    new_tech_ids = {item["TechId"] for item in selected_raw_techs}
    collision = remaining_tech_ids & new_tech_ids
    if collision:
        raise ValueError(f"Technology ID collision: {sorted(collision)}")

    remaining_comm_ids = {
        item["CommId"] for item in gen["osy-comm"] if item["CommId"] not in retired_comm_ids
    }
    new_comm_items = [
        item
        for item in raw_gen["osy-comm"]
        if item["Comm"] in relevant_fuels
        and item["Comm"] not in RAW_TO_V10_COMMODITY
    ]
    new_comm_ids = {item["CommId"] for item in new_comm_items}
    collision = remaining_comm_ids & new_comm_ids
    if collision:
        raise ValueError(f"Commodity ID collision: {sorted(collision)}")

    iar_by_tech: dict[str, set[str]] = {name: set() for name in selected_names}
    oar_by_tech: dict[str, set[str]] = {name: set() for name in selected_names}
    for row in iar_rows:
        iar_by_tech[row["TECHNOLOGY"]].add(raw_comm_name_to_final[row["FUEL"]])
    for row in oar_rows:
        oar_by_tech[row["TECHNOLOGY"]].add(raw_comm_name_to_final[row["FUEL"]])

    new_tech_definitions = []
    for raw_item in selected_raw_techs:
        name = raw_item["Tech"]
        cap_unit, act_unit = tech_units(name)
        new_tech_definitions.append(
            {
                "TechId": raw_item["TechId"],
                "Tech": name,
                "Desc": tech_description(name),
                "CapUnitId": cap_unit,
                "ActUnitId": act_unit,
                "TG": [],
                "IAR": sorted(iar_by_tech[name]),
                "OAR": sorted(oar_by_tech[name]),
                "INCR": [],
                "ITCR": [],
                "EAR": [],
            }
        )

    new_comm_definitions = [
        {
            "CommId": item["CommId"],
            "Comm": item["Comm"],
            "Desc": commodity_description(item["Comm"]),
            "UnitId": commodity_unit(item["Comm"]),
        }
        for item in new_comm_items
    ]

    gen["osy-casename"] = "Philippines_v12"
    gen["osy-date"] = date.today().strftime("%a %b %d %Y")
    gen["osy-mo"] = "30"
    for scenario in gen["osy-scenarios"]:
        scenario["Scenario"] = SCENARIO_NAMES.get(
            scenario["ScenarioId"], scenario["Scenario"]
        )
    gen["osy-desc"] = (
        gen["osy-desc"].rstrip()
        + "\n\nv12\n"
        + "* preserves the v10 energy and fisheries systems\n"
        + "* replaces the placeholder land block with an uncalibrated, "
        + "eight-cluster CLEWs Global land-agriculture-water system\n"
        + "* connects irrigation pumping to PHL_AGR_ELE and connects raw "
        + "surface/groundwater flows to the inherited water system\n"
        + "* retains raw crop demands, land availability, precipitation, "
        + "technology options, and costs without historical tuning"
    )
    gen["osy-tech"] = [
        item for item in gen["osy-tech"] if item["TechId"] not in retired_tech_ids
    ] + new_tech_definitions
    gen["osy-comm"] = [
        item for item in gen["osy-comm"] if item["CommId"] not in retired_comm_ids
    ] + new_comm_definitions
    for constraint in gen["osy-constraints"]:
        constraint["CM"] = [
            tech_id for tech_id in constraint["CM"] if tech_id not in retired_tech_ids
        ]
    write_json(destination / "genData.json", gen)
    remove_references(destination, retired_tech_ids, retired_comm_ids)

    tech_name_by_id = {item["TechId"]: item["Tech"] for item in gen["osy-tech"]}
    comm_name_by_id = {item["CommId"]: item["Comm"] for item in gen["osy-comm"]}
    # The reused v10 commodity IDs must point back to raw names for CSV lookup.
    for raw_name, final_id in raw_comm_name_to_final.items():
        comm_name_by_id[final_id] = raw_name

    # RT: one object per scenario, with technology IDs as keys.
    rt = read_json(destination / "RT.json")
    for parameter, filename in RT_CSV.items():
        values = index_csv(csv_dir, filename, ("TECHNOLOGY",), selected_names)
        for scenario in scenarios:
            target = rt[parameter][scenario][0]
            for tech in new_tech_definitions:
                target[tech["TechId"]] = (
                    values.get((tech["Tech"],), defaults[parameter])
                    if scenario == "SC_0"
                    else None
                )
    write_json(destination / "RT.json", rt)

    # RYT: one year-vector row per technology.
    ryt = read_json(destination / "RYT.json")
    for parameter, filename in RYT_CSV.items():
        values = index_csv(
            csv_dir, filename, ("TECHNOLOGY", "YEAR"), selected_names
        )
        for scenario in scenarios:
            for tech in new_tech_definitions:
                if scenario == "SC_0":
                    row = valued_year_row(
                        years,
                        values,
                        (tech["Tech"],),
                        defaults[parameter],
                        TechId=tech["TechId"],
                    )
                else:
                    row = null_year_row(years, TechId=tech["TechId"])
                ryt[parameter][scenario].append(row)
    write_json(destination / "RYT.json", ryt)

    # All RYTM records must cover the global 1..30 mode range because MUIO's
    # data generator directly indexes every technology/mode pair.
    rytm = read_json(destination / "RYTM.json")
    all_tech_ids = [item["TechId"] for item in gen["osy-tech"]]
    tech_mode_dims = [
        {"TechId": tech_id, "MoId": mode}
        for tech_id in all_tech_ids
        for mode in range(1, 31)
    ]
    for parameter, filename in RYTM_CSV.items():
        values = index_csv(
            csv_dir,
            filename,
            ("TECHNOLOGY", "MODE_OF_OPERATION", "YEAR"),
            selected_names,
        )
        ensure_mode_rows(
            rytm,
            parameter,
            scenarios,
            years,
            tech_mode_dims,
            defaults[parameter],
            values,
            new_tech_ids,
            tech_name_by_id,
            comm_name_by_id,
        )
    write_json(destination / "RYTM.json", rytm)

    # IAR/OAR: retain inherited records, fill inherited higher modes with
    # defaults, and insert raw nexus coefficients for all selected modes.
    rytcm = read_json(destination / "RYTCM.json")
    for parameter, filename in {
        "IAR": "InputActivityRatio.csv",
        "OAR": "OutputActivityRatio.csv",
    }.items():
        values = index_csv(
            csv_dir,
            filename,
            ("TECHNOLOGY", "FUEL", "MODE_OF_OPERATION", "YEAR"),
            selected_names,
            relevant_fuels,
        )
        dims = []
        association_field = parameter
        for tech in gen["osy-tech"]:
            for comm_id in tech[association_field]:
                for mode in range(1, 31):
                    dims.append(
                        {
                            "TechId": tech["TechId"],
                            "CommId": comm_id,
                            "MoId": mode,
                        }
                    )
        ensure_mode_rows(
            rytcm,
            parameter,
            scenarios,
            years,
            dims,
            defaults[parameter],
            values,
            new_tech_ids,
            tech_name_by_id,
            comm_name_by_id,
        )
    write_json(destination / "RYTCM.json", rytcm)

    # Existing emission technologies also require explicit default rows for
    # modes 3..30 after increasing the global mode count.
    rytem = read_json(destination / "RYTEM.json")
    emission_dims = [
        {"TechId": tech["TechId"], "EmisId": emis_id, "MoId": mode}
        for tech in gen["osy-tech"]
        for emis_id in tech["EAR"]
        for mode in range(1, 31)
    ]
    for parameter in ("EACR", "EAR"):
        ensure_mode_rows(
            rytem,
            parameter,
            scenarios,
            years,
            emission_dims,
            defaults[parameter],
        )
    write_json(destination / "RYTEM.json", rytem)

    # Annual demand rows are added only for genuinely new commodities. Reused
    # v10 commodities keep their inherited demand records unchanged.
    ryc = read_json(destination / "RYC.json")
    new_comm_names = {item["Comm"] for item in new_comm_items}
    for parameter, filename in RYC_CSV.items():
        values = index_csv(
            csv_dir, filename, ("FUEL", "YEAR"), fuel_names=new_comm_names
        )
        for scenario in scenarios:
            for comm in new_comm_definitions:
                if scenario == "SC_0":
                    row = valued_year_row(
                        years,
                        values,
                        (comm["Comm"],),
                        defaults[parameter],
                        CommId=comm["CommId"],
                    )
                else:
                    row = null_year_row(years, CommId=comm["CommId"])
                ryc[parameter][scenario].append(row)
    write_json(destination / "RYC.json", ryc)

    # New commodities receive the default zero demand profile over all 30 v10
    # timeslices. Crop demand is accumulated annual demand, so no profile is
    # imposed.
    rycts = read_json(destination / "RYCTs.json")
    timeslice_ids = [item["TsId"] for item in gen["osy-ts"]]
    for scenario in scenarios:
        for comm in new_comm_definitions:
            for timeslice_id in timeslice_ids:
                if scenario == "SC_0":
                    row = {
                        "CommId": comm["CommId"],
                        "TsId": timeslice_id,
                        **{str(year): defaults["SDP"] for year in years},
                    }
                else:
                    row = null_year_row(
                        years, CommId=comm["CommId"], TsId=timeslice_id
                    )
                rycts["SDP"][scenario].append(row)
    write_json(destination / "RYCTs.json", rycts)

    # Capacity factors are one for all new annual land/water technologies and
    # all inherited v10 timeslices.
    rytts = read_json(destination / "RYTTs.json")
    for scenario in scenarios:
        for tech in new_tech_definitions:
            for timeslice_id in timeslice_ids:
                if scenario == "SC_0":
                    row = {
                        "TechId": tech["TechId"],
                        "TsId": timeslice_id,
                        **{str(year): defaults["CF"] for year in years},
                    }
                else:
                    row = null_year_row(
                        years, TechId=tech["TechId"], TsId=timeslice_id
                    )
                rytts["CF"][scenario].append(row)
    write_json(destination / "RYTTs.json", rytts)

    summary = {
        "case": "Philippines_v12",
        "source_case": "Philippines_v10",
        "raw_nexus_source": "PhilippinesV12Raw",
        "retired_technologies": sorted(RETIRED_TECH_NAMES),
        "retired_commodities": sorted(RETIRED_COMM_NAMES),
        "added_technology_count": len(new_tech_definitions),
        "added_commodity_count": len(new_comm_definitions),
        "final_technology_count": len(gen["osy-tech"]),
        "final_commodity_count": len(gen["osy-comm"]),
        "modes": 30,
        "years": [years[0], years[-1]],
        "timeslices": len(timeslice_ids),
        "commodity_connections": RAW_TO_V10_COMMODITY,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument("--csv-dir", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    summary = build(args)
    if args.summary:
        write_json(args.summary, summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
