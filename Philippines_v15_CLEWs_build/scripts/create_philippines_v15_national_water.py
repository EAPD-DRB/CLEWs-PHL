#!/usr/bin/env python3
"""Build the Philippines v15 national-water case from the v14 CLEWs baseline.

The live source is never edited unless ``--promote`` is supplied explicitly.
Every target is assembled in a sibling staging directory, passed through
``UpdateCase``, checked for an allowlisted semantic source diff, and installed
atomically.  Solver outputs are never copied.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
import types
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
STORAGE = REPO / "WebAPP" / "DataStorage"
SOURCE_NAME = "Philippines_v14_STOCK_TURNOVER"
SOURCE = STORAGE / SOURCE_NAME
LIVE_NAME = "Philippines_v15"
DEFAULT_TARGET = "Philippines_v15_WATER_TEST"
SOURCE_DATA = REPO / "scripts" / "data" / "philippines_water_precipitation_ssp245.json"
MODEL_FILE = REPO / "WebAPP" / "SOLVERs" / "model.v.5.4.txt"
MANIFEST = "national_water_manifest.json"
SOURCE_COPY = "philippines_water_precipitation_ssp245.json"
MODEL_FIXES = "MODEL_FIXES_WATER_2026-08-04.md"
VIEW_INPUTS = ("resData.json", "viewDefinitions.json")
YEARS_EXPECTED = [str(year) for year in range(2020, 2054)]
REGION = "RE1"

PRECIPITATION = "PHL_WTR_PRC"
SURFACE_WATER = "PHL_WTR_SUR"
GROUNDWATER = "PHL_WTR_GWT"
EVAPOTRANSPIRATION = "PHL_WTR_EVT"
IRRIGATION_WATER = "AGRWATPHL"

CLUSTER_NAMES = tuple(f"LNDAGRPHLC{number:02d}" for number in range(1, 9))
WATER_RATIO_TARGETS = (
    ("IAR", PRECIPITATION),
    ("OAR", SURFACE_WATER),
    ("OAR", GROUNDWATER),
    ("OAR", EVAPOTRANSPIRATION),
)
GROUNDWATER_IRRIGATION = "DEMAGRGWTPHL"
MIN_PRECIPITATION = "MINPRCPHL"

CONSTRAINTS = {
    "WATER_SUR_AVAIL": {
        "id": "CO_wsur_v14",
        "description": (
            "National annual surface-water withdrawal cannot exceed the sourced "
            "potential-flow sensitivity; not environmental-flow adjusted."
        ),
        "base_key": "surface_water_potential_km3_per_year",
        "members": (
            "PHL_DEM_PUB_SUR_WAT",
            "PHL_DEM_PWR_SUR_WAT",
            "DEMAGRSURPHL",
        ),
        "raw_commodity": SURFACE_WATER,
    },
    "WATER_GWT_POTENTIAL": {
        "id": "CO_wgwt_v14",
        "description": (
            "National annual groundwater withdrawal cannot exceed the sourced "
            "potential-flow sensitivity; not aquifer safe yield or stock."
        ),
        "base_key": "groundwater_potential_km3_per_year",
        "members": (
            "PHL_DEM_PUB_GWT_WAT",
            "PHL_DEM_PWR_GWT_WAT",
            GROUNDWATER_IRRIGATION,
        ),
        "raw_commodity": GROUNDWATER,
    },
}

ALLOWED_PARAMETER_FILES = {"genData.json", "RYTCM.json", "RYTCn.json", "RYCn.json"}
getcontext().prec = 40


# The application imports dotenv unconditionally, although model generation does
# not use it.  Keep the repository's established no-op fallback for validators.
dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(REPO / "API"))

from Classes.Base import Config  # noqa: E402
from Classes.Case.UpdateCaseClass import UpdateCase  # noqa: E402


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".codex-tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".codex-tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean_number(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def safe_target_name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ValueError("target must be one case-directory name")
    if value in {".", ".."} or value.startswith("."):
        raise ValueError("target cannot be hidden or relative")
    return value


def keyed(rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    result = {str(row[field]): row for row in rows}
    if len(result) != len(rows):
        raise AssertionError(f"duplicate {field} in structural data")
    return result


def row_key(parameter: str, row: dict[str, Any]) -> tuple[Any, ...]:
    fields = {
        "RYTCM": ("TechId", "CommId", "MoId"),
        "RYTCn": ("TechId", "ConId"),
        "RYCn": ("ConId",),
    }[parameter]
    return tuple(row[field] for field in fields)


def rows_by_key(
    payload: dict[str, Any], parameter: str, scenario: str
) -> dict[tuple[Any, ...], dict[str, Any]]:
    result: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in payload[parameter][scenario]:
        key = row_key(
            "RYTCM" if parameter in {"IAR", "OAR"} else (
                "RYTCn" if parameter in {"CAM", "CNCM", "CCM"} else "RYCn"
            ),
            row,
        )
        if key in result:
            raise AssertionError(f"duplicate {parameter}/{scenario} row: {key}")
        result[key] = row
    return result


def matching_row(
    payload: dict[str, Any], parameter: str, scenario: str = "SC_0", **keys: Any
) -> dict[str, Any]:
    matches = [
        row
        for row in payload[parameter][scenario]
        if all(row.get(field) == value for field, value in keys.items())
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"expected one {parameter}/{scenario} row for {keys}, found {len(matches)}"
        )
    return matches[0]


def source_inputs(case: Path) -> list[Path]:
    paths = sorted(case.glob("*.json"))
    paths.extend(case / "view" / name for name in VIEW_INPUTS)
    return [path for path in paths if path.is_file()]


def fingerprints(case: Path) -> dict[str, str]:
    return {
        str(path.relative_to(case)): sha256(path)
        for path in source_inputs(case)
    }


def copy_case_inputs(source: Path, target: Path) -> None:
    for path in sorted(source.glob("*.json")):
        shutil.copy2(path, target / path.name)
    if (source / "README.md").is_file():
        shutil.copy2(source / "README.md", target / "README.md")
    if (source / "documentation").is_dir():
        shutil.copytree(source / "documentation", target / "documentation")
    (target / "view").mkdir()
    for name in VIEW_INPUTS:
        path = source / "view" / name
        if path.is_file():
            shutil.copy2(path, target / "view" / name)


def annual_pathway(source: dict[str, Any], years: list[str]) -> dict[str, Decimal]:
    projection = source["projections_ssp245"]
    historical = Decimal(
        str(projection["historical_climatology_median_mm_per_year"]["value"])
    )
    anchors = {2020: Decimal(1)}
    for period in ("2020-2039", "2040-2059"):
        item = projection["annual_anomaly_mm_per_year"][period]
        anchors[int(item["midpoint_model_year"])] = (
            Decimal(1) + Decimal(str(item["median"])) / historical
        )

    result: dict[str, Decimal] = {}
    for year_text in years:
        year = int(year_text)
        if year <= 2030:
            fraction = Decimal(year - 2020) / Decimal(10)
            value = anchors[2020] + fraction * (anchors[2030] - anchors[2020])
        else:
            # The same 2030-2050 slope is deliberately extended to 2053.
            fraction = Decimal(year - 2030) / Decimal(20)
            value = anchors[2030] + fraction * (anchors[2050] - anchors[2030])
        result[year_text] = value
    return result


def add_structure(gen: dict[str, Any], target_name: str) -> dict[str, Any]:
    tech = keyed(gen["osy-tech"], "Tech")
    comm = keyed(gen["osy-comm"], "Comm")
    existing_names = {row["Con"] for row in gen["osy-constraints"]}
    existing_ids = {row["ConId"] for row in gen["osy-constraints"]}
    if existing_names & set(CONSTRAINTS):
        raise AssertionError("national water constraints already exist")
    requested_ids = {item["id"] for item in CONSTRAINTS.values()}
    if existing_ids & requested_ids:
        raise AssertionError("national water constraint ID collision")

    groundwater_id = comm[GROUNDWATER]["CommId"]
    irrigation = tech[GROUNDWATER_IRRIGATION]
    if groundwater_id in irrigation["IAR"]:
        raise AssertionError("groundwater irrigation link already exists")
    irrigation["IAR"].append(groundwater_id)

    for name, item in CONSTRAINTS.items():
        members = [tech[member]["TechId"] for member in item["members"]]
        gen["osy-constraints"].append(
            {
                "ConId": item["id"],
                "Con": name,
                "Desc": item["description"],
                "Tag": 0,
                "CM": members,
            }
        )

    gen["osy-casename"] = target_name
    gen["osy-date"] = "2026-08-04"
    addition = (
        "\n\nNational water envelope: groundwater irrigation is connected to "
        "the raw groundwater commodity; the inherited land hydrology is rebased "
        "to the ERA5 1991-2020 normal and follows one SSP2-4.5 ensemble-median "
        "path; annual national surface-water and groundwater withdrawal ceilings "
        "are solver enforced. See documentation/national_water_manifest.json."
    )
    if "National water envelope:" not in gen.get("osy-desc", ""):
        gen["osy-desc"] = gen.get("osy-desc", "").rstrip() + addition
    return gen


def land_and_precipitation_baseline(
    gen: dict[str, Any], ryt: dict[str, Any], ratio: dict[str, Any], years: list[str]
) -> dict[str, Any]:
    tech = keyed(gen["osy-tech"], "Tech")
    comm = keyed(gen["osy-comm"], "Comm")
    precip_id = comm[PRECIPITATION]["CommId"]
    cluster_area: dict[str, Decimal] = {}
    cluster_precip: dict[str, Decimal] = {}

    for name in CLUSTER_NAMES:
        tech_id = tech[name]["TechId"]
        tau = matching_row(ryt, "TAU", TechId=tech_id)
        area = Decimal(str(tau["2020"]))
        if area <= 0 or any(Decimal(str(tau[year])) != area for year in years):
            raise AssertionError(f"cluster land envelope is not constant and positive: {name}")
        cluster_area[name] = area

        values: list[Decimal] = []
        for mode in range(1, int(gen["osy-mo"]) + 1):
            row = matching_row(
                ratio, "IAR", TechId=tech_id, CommId=precip_id, MoId=mode
            )
            value = Decimal(str(row["2020"]))
            if value <= 0 or any(Decimal(str(row[year])) != value for year in years):
                raise AssertionError(f"precipitation IAR is not constant and positive: {name}/m{mode}")
            values.append(value)
        if len(set(values)) != 1:
            raise AssertionError(f"precipitation IAR is mode-varying for {name}")
        cluster_precip[name] = values[0]

    land_area = sum(cluster_area.values(), Decimal(0))
    volume = sum(
        cluster_area[name] * cluster_precip[name]
        for name in CLUSTER_NAMES
    )
    depth_mm = volume / land_area * Decimal(1000)
    return {
        "cluster_area_1000km2": cluster_area,
        "cluster_precipitation_km3_per_1000km2": cluster_precip,
        "national_land_area_1000km2": land_area,
        "model_precipitation_volume_km3": volume,
        "model_precipitation_depth_mm": depth_mm,
    }


def closure_ratios(
    gen: dict[str, Any], ratio: dict[str, Any], years: list[str]
) -> dict[tuple[str, int, str], Decimal]:
    tech = keyed(gen["osy-tech"], "Tech")
    comm = keyed(gen["osy-comm"], "Comm")
    ids = {name: comm[name]["CommId"] for name in (
        PRECIPITATION, SURFACE_WATER, GROUNDWATER, EVAPOTRANSPIRATION
    )}
    result: dict[tuple[str, int, str], Decimal] = {}
    for name in CLUSTER_NAMES:
        tech_id = tech[name]["TechId"]
        for mode in range(1, int(gen["osy-mo"]) + 1):
            rows = {
                PRECIPITATION: matching_row(
                    ratio, "IAR", TechId=tech_id, CommId=ids[PRECIPITATION], MoId=mode
                ),
                SURFACE_WATER: matching_row(
                    ratio, "OAR", TechId=tech_id, CommId=ids[SURFACE_WATER], MoId=mode
                ),
                GROUNDWATER: matching_row(
                    ratio, "OAR", TechId=tech_id, CommId=ids[GROUNDWATER], MoId=mode
                ),
                EVAPOTRANSPIRATION: matching_row(
                    ratio, "OAR", TechId=tech_id, CommId=ids[EVAPOTRANSPIRATION], MoId=mode
                ),
            }
            for year in years:
                precipitation = Decimal(str(rows[PRECIPITATION][year]))
                output = sum(
                    Decimal(str(rows[commodity][year]))
                    for commodity in (SURFACE_WATER, GROUNDWATER, EVAPOTRANSPIRATION)
                )
                result[(name, mode, year)] = (output - precipitation) / precipitation
    return result


def apply_values(
    case: Path,
    source: dict[str, Any],
    gen: dict[str, Any],
    before_payloads: dict[str, Any],
) -> dict[str, Any]:
    years = [str(year) for year in gen["osy-years"]]
    if years != YEARS_EXPECTED:
        raise AssertionError("Philippines model years are not exactly 2020-2053")
    scenarios = [row["ScenarioId"] for row in gen["osy-scenarios"]]
    if scenarios[0] != "SC_0":
        raise AssertionError("SC_0 is not the first scenario")

    ratio = read_json(case / "RYTCM.json")
    constraint_ratio = read_json(case / "RYTCn.json")
    constraint_constant = read_json(case / "RYCn.json")
    ryt = read_json(case / "RYT.json")
    tech = keyed(gen["osy-tech"], "Tech")
    comm = keyed(gen["osy-comm"], "Comm")
    pathway = annual_pathway(source, years)
    baseline = land_and_precipitation_baseline(gen, ryt, ratio, years)
    era5 = Decimal(
        str(
            source["observed_annual_mm_per_year"]
            ["era5_climatology_1991_2020_mm_per_year"]["value"]
        )
    )
    rebase = era5 / baseline["model_precipitation_depth_mm"]
    closure_before = closure_ratios(gen, ratio, years)

    changed_rows: list[dict[str, Any]] = []
    for tech_name in CLUSTER_NAMES:
        tech_id = tech[tech_name]["TechId"]
        for parameter, commodity_name in WATER_RATIO_TARGETS:
            commodity_id = comm[commodity_name]["CommId"]
            for mode in range(1, int(gen["osy-mo"]) + 1):
                row = matching_row(
                    ratio,
                    parameter,
                    TechId=tech_id,
                    CommId=commodity_id,
                    MoId=mode,
                )
                base = Decimal(str(row["2020"]))
                if base <= 0 or any(Decimal(str(row[year])) != base for year in years):
                    raise AssertionError(
                        f"climate-linked source ratio is not constant and positive: "
                        f"{tech_name}/{commodity_name}/m{mode}"
                    )
                for year in years:
                    row[year] = clean_number(base * rebase * pathway[year])
                changed_rows.append(
                    {
                        "parameter": parameter,
                        "technology": tech_name,
                        "commodity": commodity_name,
                        "mode": mode,
                        "source_2020_value": clean_number(base),
                    }
                )

    if len(changed_rows) != 8 * 30 * 4:
        raise AssertionError(f"expected 960 hydrology rows, found {len(changed_rows)}")

    groundwater_row = matching_row(
        ratio,
        "IAR",
        TechId=tech[GROUNDWATER_IRRIGATION]["TechId"],
        CommId=comm[GROUNDWATER]["CommId"],
        MoId=1,
    )
    for year in years:
        groundwater_row[year] = 1
    for mode in range(2, int(gen["osy-mo"]) + 1):
        row = matching_row(
            ratio,
            "IAR",
            TechId=tech[GROUNDWATER_IRRIGATION]["TechId"],
            CommId=comm[GROUNDWATER]["CommId"],
            MoId=mode,
        )
        if any(Decimal(str(row[year])) != 0 for year in years):
            raise AssertionError("new groundwater irrigation input leaked beyond mode 1")

    caps: dict[str, dict[str, Decimal]] = {}
    base_resources = source["national_water_resources"]
    for constraint_name, item in CONSTRAINTS.items():
        cap_base = Decimal(str(base_resources[item["base_key"]]))
        caps[constraint_name] = {
            year: cap_base * pathway[year] for year in years
        }
        for member in item["members"]:
            row = matching_row(
                constraint_ratio,
                "CAM",
                TechId=tech[member]["TechId"],
                ConId=item["id"],
            )
            for year in years:
                row[year] = 1
        constant = matching_row(
            constraint_constant, "UCC", ConId=item["id"]
        )
        for year in years:
            constant[year] = clean_number(caps[constraint_name][year])

    write_json(case / "RYTCM.json", ratio)
    write_json(case / "RYTCn.json", constraint_ratio)
    write_json(case / "RYCn.json", constraint_constant)

    closure_after = closure_ratios(gen, ratio, years)
    maximum_closure_delta = max(
        abs(closure_after[key] - value) for key, value in closure_before.items()
    )
    if maximum_closure_delta > Decimal("1e-15"):
        raise AssertionError("hydrological closure ratio was not preserved")

    return {
        "pathway": pathway,
        "rebase": rebase,
        "era5_normal_mm": era5,
        "baseline": baseline,
        "caps": caps,
        "changed_rows": changed_rows,
        "maximum_hydrological_closure_ratio_delta": maximum_closure_delta,
        "before_payloads": before_payloads,
    }


def prove_withdrawal_accounting(case: Path, gen: dict[str, Any]) -> dict[str, Any]:
    years = [str(year) for year in gen["osy-years"]]
    ratio = read_json(case / "RYTCM.json")
    constraint_ratio = read_json(case / "RYTCn.json")
    constraint_constant = read_json(case / "RYCn.json")
    tech = keyed(gen["osy-tech"], "Tech")
    comm = keyed(gen["osy-comm"], "Comm")
    details: dict[str, Any] = {}

    for constraint_name, item in CONSTRAINTS.items():
        raw_id = comm[item["raw_commodity"]]["CommId"]
        member_details = {}
        for member in item["members"]:
            tech_id = tech[member]["TechId"]
            active_modes: set[int] = set()
            for parameter in ("IAR", "OAR"):
                for row in ratio[parameter]["SC_0"]:
                    if row["TechId"] != tech_id:
                        continue
                    if any(Decimal(str(row[year])) != 0 for year in years):
                        active_modes.add(int(row["MoId"]))
            if active_modes != {1}:
                raise AssertionError(f"{member} is not exactly single-mode: {active_modes}")
            raw = matching_row(
                ratio, "IAR", TechId=tech_id, CommId=raw_id, MoId=1
            )
            if any(Decimal(str(raw[year])) != 1 for year in years):
                raise AssertionError(f"{member} raw-water IAR is not 1.0")
            cam = matching_row(
                constraint_ratio,
                "CAM",
                TechId=tech_id,
                ConId=item["id"],
            )
            if any(Decimal(str(cam[year])) != 1 for year in years):
                raise AssertionError(f"{member} CAM is not 1.0")
            member_details[member] = {
                "active_modes": [1],
                "raw_water_IAR": 1,
                "UDC_CAM": 1,
            }
        constant = matching_row(constraint_constant, "UCC", ConId=item["id"])
        if any(Decimal(str(constant[year])) <= 0 for year in years):
            raise AssertionError(f"{constraint_name} has a non-positive ceiling")
        details[constraint_name] = {
            "tag": 0,
            "members": member_details,
            "proof": (
                "Each member has active mode {1}, raw-water IAR 1.0, and CAM 1.0; "
                "therefore the UDC activity sum equals gross annual withdrawal."
            ),
        }
    return details


def assert_policy_inheritance(case: Path, gen: dict[str, Any]) -> None:
    scenarios = [row["ScenarioId"] for row in gen["osy-scenarios"] if row["ScenarioId"] != "SC_0"]
    ratio = read_json(case / "RYTCM.json")
    constraint_ratio = read_json(case / "RYTCn.json")
    constraint_constant = read_json(case / "RYCn.json")
    constraint_ids = {item["id"] for item in CONSTRAINTS.values()}
    tech = keyed(gen["osy-tech"], "Tech")
    groundwater_key = (
        tech[GROUNDWATER_IRRIGATION]["TechId"],
        keyed(gen["osy-comm"], "Comm")[GROUNDWATER]["CommId"],
    )
    for scenario in scenarios:
        for parameter in ("IAR", "OAR"):
            for row in ratio[parameter][scenario]:
                is_groundwater_link = (
                    parameter == "IAR"
                    and row["TechId"] == groundwater_key[0]
                    and row["CommId"] == groundwater_key[1]
                )
                if is_groundwater_link and any(row[year] is not None for year in YEARS_EXPECTED):
                    raise AssertionError(f"groundwater link does not inherit in {scenario}")
        for parameter in ("CAM", "CNCM", "CCM"):
            for row in constraint_ratio[parameter][scenario]:
                if row["ConId"] in constraint_ids and any(
                    row[year] is not None for year in YEARS_EXPECTED
                ):
                    raise AssertionError(f"new {parameter} does not inherit in {scenario}")
        for row in constraint_constant["UCC"][scenario]:
            if row["ConId"] in constraint_ids and any(
                row[year] is not None for year in YEARS_EXPECTED
            ):
                raise AssertionError(f"new UCC does not inherit in {scenario}")


def assert_model_equations() -> dict[str, Any]:
    text = MODEL_FILE.read_text(encoding="utf-8")
    required = {
        "annual_commodity_balance": "s.t. EBb4_EnergyBalanceEachYear4",
        "annual_activity_identity": "s.t. AAC1_TotalAnnualTechnologyActivity",
        "tag_0_udc": "s.t. UDC1_UserDefinedConstraintInequality",
        "udc_activity_term": (
            "UDCMultiplierActivity[r,t,u,y]*TotalTechnologyAnnualActivity[r,t,y] "
            "<= UDCConstant[r,u,y]"
        ),
    }
    missing = [name for name, token in required.items() if token not in text]
    if missing:
        raise AssertionError(f"active solver formulation lacks {missing}")
    return {
        name: {"token": token, "present": True}
        for name, token in required.items()
    }


def assert_allowed_semantic_diff(
    before: dict[str, Any], after: dict[str, Any], gen_before: dict[str, Any], gen_after: dict[str, Any]
) -> dict[str, Any]:
    changed_files = sorted(name for name in before if before[name] != after[name])
    outside = sorted(set(changed_files) - ALLOWED_PARAMETER_FILES)
    if outside:
        raise AssertionError(f"semantic source changes outside allowlist: {outside}")

    # Prove the structural metadata diff by reversing only the requested edits.
    reconstructed = copy.deepcopy(gen_after)
    reconstructed["osy-casename"] = gen_before["osy-casename"]
    reconstructed["osy-date"] = gen_before["osy-date"]
    reconstructed["osy-desc"] = gen_before["osy-desc"]
    ids = {item["id"] for item in CONSTRAINTS.values()}
    reconstructed["osy-constraints"] = [
        row for row in reconstructed["osy-constraints"] if row["ConId"] not in ids
    ]
    tech = keyed(reconstructed["osy-tech"], "Tech")
    groundwater_id = keyed(reconstructed["osy-comm"], "Comm")[GROUNDWATER]["CommId"]
    tech[GROUNDWATER_IRRIGATION]["IAR"].remove(groundwater_id)
    if reconstructed != gen_before:
        raise AssertionError("genData contains a structural change outside the allowlist")

    return {
        "semantic_parameter_files_changed": changed_files,
        "allowed_parameter_files": sorted(ALLOWED_PARAMETER_FILES),
        "changes_outside_allowlist": [],
    }


def snapshot_payloads(case: Path) -> dict[str, Any]:
    return {path.name: read_json(path) for path in sorted(case.glob("*.json"))}


def decimal_mapping(values: dict[str, Decimal]) -> dict[str, int | float]:
    return {year: clean_number(value) for year, value in values.items()}


def model_fix_text(target_name: str, result: dict[str, Any]) -> str:
    baseline = result["baseline"]
    rebase = result["rebase"]
    pathway = result["pathway"]
    caps = result["caps"]
    return f"""# Philippines v15 national water model fixes

Date: 2026-08-04  
Case: `{target_name}`  
Status: **source generation passed; solver validation not yet run**

## Reason

The country model had precipitation-to-runoff/recharge conversions but no
groundwater input on `DEMAGRGWTPHL`, no climate evolution after 2020, and no
national solver ceiling on gross surface-water or groundwater withdrawal.

## Physical classification and equation mapping

- Initial stock: none. The 20.2 km3/year groundwater value is a renewable-flow
  potential, not an aquifer stock.
- Final demand: unchanged. `PHL_PUB_WAT`, `PHL_PWR_WAT` and crop demands remain
  the inherited final demands.
- Continuing real-world constraints: the ERA5 1991-2020 precipitation normal,
  the SSP2-4.5 ensemble-median relative precipitation signal, and the two
  national potential-flow sensitivities.
- Benchmark only: p10/p90 climate values, current withdrawal estimates, local
  groundwater studies, and regional screening data.

`RYTCM.json` feeds `EBb4_EnergyBalanceEachYear4`; `RYTCn.json` CAM and
`RYCn.json` UCC feed `UDC1_UserDefinedConstraintInequality`. Every withdrawal
member is a single-mode pass-through with raw-water IAR = CAM = 1, so each UDC
is an exact gross-withdrawal ceiling.

## Source changes

- `genData.json`: add raw groundwater to the `DEMAGRGWTPHL` IAR list and add
  Tag-0 constraints `WATER_SUR_AVAIL` and `WATER_GWT_POTENTIAL`.
- `RYTCM.json`: set the new irrigation-groundwater IAR to 1.0 in mode 1; scale
  960 BASE hydrology rows (8 coefficient classes x 30 modes x precipitation,
  runoff, recharge and evapotranspiration) by the ERA5 rebase and the single
  SSP2-4.5 median path. `AGRWATPHL` coefficients are unchanged.
- `RYTCn.json`: CAM = 1.0 for exactly three surface and three groundwater
  withdrawal technologies.
- `RYCn.json`: annual UCC paths for the two national ceilings. Policy-scenario
  rows remain null and inherit BASE.

## Before and after

- Model precipitation depth before: {float(baseline['model_precipitation_depth_mm']):.12g} mm/year.
- ERA5 1991-2020 anchor: {float(result['era5_normal_mm']):.12g} mm/year.
- Full-precision rebase factor: {float(rebase):.15g}.
- SSP2-4.5 median multiplier: 2020 = {float(pathway['2020']):.12g},
  2030 = {float(pathway['2030']):.12g}, 2050 = {float(pathway['2050']):.12g},
  2053 = {float(pathway['2053']):.12g}.
- Surface UCC: 2020 = {float(caps['WATER_SUR_AVAIL']['2020']):.12g},
  2053 = {float(caps['WATER_SUR_AVAIL']['2053']):.12g} km3/year.
- Groundwater UCC: 2020 = {float(caps['WATER_GWT_POTENTIAL']['2020']):.12g},
  2053 = {float(caps['WATER_GWT_POTENTIAL']['2053']):.12g} km3/year.

## Generated artifacts and baseline

The structural source was regenerated through `UpdateCase`. The intended
application chain is `DataFile.generateDatafile` -> `preprocessData` ->
`glpsol --check`/LP export -> bounded CBC -> CSV/view export. The unchanged
control is the validated `Philippines_v14_STOCK_TURNOVER/BASE_V14` result:
optimal objective 369630979.503002, 791041 rows, 884956 columns, 12530519
nonzeros, CBC 133.1208 seconds. The candidate budget is 280 seconds.

## Validation status and limitations

Generation, structural preservation, exact-withdrawal proof, all-year source
values, policy inheritance, and hydrological-ratio preservation: **passed**.
Application generation, preprocessing, matrix validation, CBC optimization,
result export, constraint residuals/duals, and baseline comparison: **not run**.

The ceilings are national potential-flow sensitivities, not dependable yield,
environmental-flow-adjusted availability, or groundwater safe yield. Public
and power groundwater pumping electricity remains uncalibrated; irrigation
and public-water demand are also unchanged. No basin, aquifer or storage state
is implied.
"""


def validated_candidate_gate() -> dict[str, Any]:
    """Require a completed disposable validation before live promotion."""
    candidate = STORAGE / DEFAULT_TARGET
    manifest_path = candidate / "documentation" / MANIFEST
    validation_path = candidate / "documentation" / "national_water_validation.json"
    ledger_path = candidate / "documentation" / "national_water_ledger.json"
    for path in (manifest_path, validation_path, ledger_path):
        if not path.is_file():
            raise FileNotFoundError(
                f"live promotion requires the validated disposable artifact: {path}"
            )
    candidate_manifest = read_json(manifest_path)
    validation = read_json(validation_path)
    required_status = {
        "source_generation": "passed",
        "deterministic_design_checks": "passed",
        "generate_datafile": "passed",
        "preprocess_data": "passed",
        "glpsol_check": "passed",
        "cbc": "passed_optimal",
        "baseline_comparison": "passed",
    }
    actual = candidate_manifest["validation_status"]
    failures = {
        name: {"expected": expected, "actual": actual.get(name)}
        for name, expected in required_status.items()
        if actual.get(name) != expected
    }
    if failures:
        raise AssertionError(
            "disposable validation is incomplete: " + json.dumps(failures, indent=2)
        )
    if validation.get("candidate", {}).get("status") != "optimal":
        raise AssertionError("disposable candidate validation is not optimal")
    if candidate_manifest["source_fingerprints_before"] != fingerprints(SOURCE):
        raise AssertionError("live source changed since disposable generation")
    return {
        "candidate": str(candidate),
        "manifest_sha256": sha256(manifest_path),
        "validation_sha256": sha256(validation_path),
        "ledger_sha256": sha256(ledger_path),
        "objective": validation["candidate"]["objective"],
        "status": "passed_optimal",
    }


def build_candidate(case: Path, target_name: str) -> dict[str, Any]:
    source = read_json(SOURCE_DATA)
    before_payloads = snapshot_payloads(case)
    gen_before = copy.deepcopy(before_payloads["genData.json"])
    gen = add_structure(copy.deepcopy(gen_before), target_name)
    write_json(case / "genData.json", gen)

    Config.DATA_STORAGE = STORAGE
    UpdateCase(case.name, gen).updateCase()
    write_json(case / "genData.json", gen)

    result = apply_values(case, source, gen, before_payloads)
    proof = prove_withdrawal_accounting(case, gen)
    assert_policy_inheritance(case, gen)
    equations = assert_model_equations()
    after_payloads = snapshot_payloads(case)
    diff = assert_allowed_semantic_diff(
        before_payloads, after_payloads, gen_before, gen
    )

    write_json(case / "view" / "resData.json", {"osy-cases": []})
    documentation = case / "documentation"
    documentation.mkdir(exist_ok=True)
    shutil.copy2(SOURCE_DATA, documentation / SOURCE_COPY)
    write_text(documentation / MODEL_FIXES, model_fix_text(target_name, result))

    baseline = result["baseline"]
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_case": SOURCE_NAME,
        "target_case": target_name,
        "region": REGION,
        "years": YEARS_EXPECTED,
        "source_data": {
            "path": str(SOURCE_DATA.relative_to(REPO)),
            "sha256": sha256(SOURCE_DATA),
            "installed_copy": f"documentation/{SOURCE_COPY}",
            "scenario_installed": "SSP2-4.5 ensemble median only",
            "p10_p90_status": "research metadata only; no predefined model scenarios",
        },
        "model_formulation": {
            "path": str(MODEL_FILE.relative_to(REPO)),
            "sha256": sha256(MODEL_FILE),
            "equation_checks": equations,
        },
        "observation_classification": {
            "initial_stock": "None; groundwater stock/depletion is not initialized.",
            "final_demand": "No final demand is changed.",
            "continuing_real_world_constraints": [
                "ERA5 1991-2020 national precipitation normal",
                "SSP2-4.5 ensemble-median relative precipitation signal",
                "national surface-water and groundwater potential-flow sensitivities",
            ],
            "benchmark_only": [
                "SSP2-4.5 p10/p90 metadata",
                "current national withdrawal estimates",
                "regional/local groundwater studies and categorical screening",
            ],
        },
        "technology_classification": {
            MIN_PRECIPITATION: "physical source",
            "LNDAGRPHLC01...LNDAGRPHLC08": "physical land/water conversions",
            "six PHL_DEM/DEMAGR withdrawal technologies": "physical pass-throughs",
            "WATER_SUR_AVAIL and WATER_GWT_POTENTIAL": "annual accounting/physical constraint devices",
            "PHL_PUB_WAT, PHL_PWR_WAT and crop commodities": "unchanged final demands",
        },
        "climate": {
            "era5_1991_2020_normal_mm_per_year": clean_number(result["era5_normal_mm"]),
            "source_model_precipitation_depth_mm_per_year": clean_number(
                baseline["model_precipitation_depth_mm"]
            ),
            "source_model_precipitation_volume_km3_per_year": clean_number(
                baseline["model_precipitation_volume_km3"]
            ),
            "national_land_area_1000km2": clean_number(
                baseline["national_land_area_1000km2"]
            ),
            "era5_rebase_factor": clean_number(result["rebase"]),
            "ssp245_median_multiplier": decimal_mapping(result["pathway"]),
            "combined_hydrology_factor": {
                year: clean_number(result["rebase"] * value)
                for year, value in result["pathway"].items()
            },
            "changed_RYTCM_base_rows": len(result["changed_rows"]),
            "maximum_hydrological_closure_ratio_delta": clean_number(
                result["maximum_hydrological_closure_ratio_delta"]
            ),
            "irrigation_water_coefficients_scaled": False,
        },
        "withdrawal_constraints": {
            name: {
                "ConId": CONSTRAINTS[name]["id"],
                "Tag": 0,
                "raw_commodity": CONSTRAINTS[name]["raw_commodity"],
                "members": list(CONSTRAINTS[name]["members"]),
                "annual_UCC_km3": decimal_mapping(values),
                "exactness_proof": proof[name],
            }
            for name, values in result["caps"].items()
        },
        "source_diff": diff,
        "validation_design": {
            "unchanged_control": (
                "validated read-only Philippines_v14_STOCK_TURNOVER/BASE_V14 "
                "saved result; the changed case itself is disposable"
            ),
            "minimal_candidate": (
                "control plus one missing raw-groundwater IAR, 960 climate-linked "
                "BASE coefficients, and two three-member Tag-0 UDCs"
            ),
            "last_known_good_runtime_seconds": 133.12081658299576,
            "bounded_candidate_budget_seconds": 280,
            "deterministic_checks": [
                "source-file semantic allowlist",
                "all-year climate ratios and UCC values",
                "single-mode 1:1 withdrawal exactness",
                "policy-scenario null inheritance",
                "hydrological split/closure ratio preservation",
                "ordinary raw-water input links for every withdrawal route",
            ],
        },
        "known_limitations": [
            "national potential is not dependable yield or environmental-flow-adjusted availability",
            "20.2 km3/year is groundwater potential flow, not aquifer stock or safe yield",
            "public and power groundwater pumping electricity is not calibrated",
            "irrigation and public-water demand are not recalibrated",
            "the model has no basin, aquifer, transfer, head or groundwater-storage state",
        ],
        "source_fingerprints_before": fingerprints(SOURCE),
        "generated_source_fingerprints": fingerprints(case),
        "validation_status": {
            "source_generation": "passed",
            "deterministic_design_checks": "passed",
            "generate_datafile": "not_run",
            "preprocess_data": "not_run",
            "glpsol_check": "not_run",
            "cbc": "not_run",
            "baseline_comparison": "not_run",
            "live_promotion": "not_run",
        },
    }
    write_json(documentation / MANIFEST, manifest)
    return manifest


def generate(target_name: str, overwrite: bool, promote: bool) -> dict[str, Any]:
    target_name = safe_target_name(target_name)
    target = STORAGE / target_name
    if not SOURCE.is_dir():
        raise FileNotFoundError(SOURCE)
    if not SOURCE_DATA.is_file():
        raise FileNotFoundError(SOURCE_DATA)
    if not MODEL_FILE.is_file():
        raise FileNotFoundError(MODEL_FILE)
    if (SOURCE / "documentation" / MANIFEST).exists():
        raise AssertionError("the live source already contains the national water manifest")
    if target == SOURCE:
        raise ValueError("the Philippines v14 source baseline is immutable")
    if target == STORAGE / LIVE_NAME and not promote:
        raise ValueError("installing the live Philippines v15 case requires --promote")
    if promote and target != STORAGE / LIVE_NAME:
        raise ValueError("--promote is only valid for the Philippines v15 live case")
    if target.exists() and not (overwrite or promote):
        raise FileExistsError(f"target exists; pass --overwrite: {target}")

    promotion_gate = validated_candidate_gate() if promote else None
    source_before = fingerprints(SOURCE)
    stage = Path(tempfile.mkdtemp(prefix=f".{target_name}-water-stage-", dir=STORAGE))
    backup: Path | None = None
    installed = False
    try:
        copy_case_inputs(SOURCE, stage)
        if fingerprints(stage) != source_before:
            raise AssertionError("staged source fingerprints differ from live source")
        manifest = build_candidate(stage, target_name)
        if fingerprints(SOURCE) != source_before:
            raise AssertionError("live source changed during candidate generation")

        if target.exists():
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = target.with_name(f"{target.name}.pre-water-{timestamp}")
            if backup.exists():
                raise FileExistsError(backup)
            target.replace(backup)
        stage.replace(target)
        installed = True
        return {
            "status": "success",
            "source": str(SOURCE),
            "target": str(target),
            "backup": str(backup) if backup else None,
            "promoted": promote,
            "promotion_gate": promotion_gate,
            "manifest": str(target / "documentation" / MANIFEST),
            "model_fixes": str(target / "documentation" / MODEL_FIXES),
            "climate_rows_changed": manifest["climate"]["changed_RYTCM_base_rows"],
            "constraints_added": sorted(CONSTRAINTS),
        }
    except Exception:
        if installed and backup is not None and backup.exists():
            failed = target.with_name(f".{target.name}-failed-water-{os.getpid()}")
            target.replace(failed)
            backup.replace(target)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    print(json.dumps(generate(args.target, args.overwrite, args.promote), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
