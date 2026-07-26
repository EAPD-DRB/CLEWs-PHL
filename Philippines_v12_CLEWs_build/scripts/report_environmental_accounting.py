#!/usr/bin/env python3
"""Build validated environmental-account reports for Philippines v12.

The script reads the unchanged Philippines_v12 source case, its exact-land
derived case, or the separate unforced ENV_WATER diagnostic case and their
normally generated MUIO result CSV files. It writes water, land, native-
emissions, and—when applicable—water-terminal reconciliation evidence to a
uniquely labelled diagnostics directory.

Water remains reporting-only because the eight LNDAGRPHLC technologies have
environmental output coefficients that differ by operating mode, while the
installed MUIO user-defined constraint multiplier is technology-level. In the
derived cases, land rows are read from the exact in-model ENV_LAND terminal.
For the diagnostic case, the authoritative water reference explicitly excludes
ENV_WATER consumption and is compared with the terminal's selected activity.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = REPO_ROOT / "WebAPP" / "DataStorage" / "Philippines_v12"
DERIVED_MODEL = (
    REPO_ROOT / "WebAPP" / "DataStorage" / "Philippines_v12_ENV_LAND"
)
DIAGNOSTIC_MODEL = (
    REPO_ROOT
    / "WebAPP"
    / "DataStorage"
    / "Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "Philippines_v12_CLEWs_build"
    / "diagnostics"
    / "environmental_accounting"
)
BASE_SCENARIO = "SC_0"
EXPECTED_CASE_NAME = "Philippines_v12"
DERIVED_CASE_NAME = "Philippines_v12_ENV_LAND"
DIAGNOSTIC_CASE_NAME = "Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC"
ENV_WATER_TECH_NAME = "ENV_WATER"
RESULT_RECONCILIATION_TOLERANCE = 0.002
LAND_CLOSURE_TOLERANCE = 0.005

WATER_ACCOUNTS = (
    {
        "mode": 1,
        "account": "water_vapor_returned",
        "commodity": "PHL_WTR_EVT",
        "interpretation": "Evapotranspiration returned to the atmosphere",
    },
    {
        "mode": 2,
        "account": "modeled_raw_groundwater_remaining",
        "commodity": "PHL_WTR_GWT",
        "interpretation": (
            "Modeled raw groundwater production less modeled raw groundwater use; "
            "not a sustainable-yield estimate"
        ),
    },
    {
        "mode": 3,
        "account": "modeled_raw_surface_water_remaining",
        "commodity": "PHL_WTR_SUR",
        "interpretation": (
            "Modeled raw surface-water production less modeled raw surface-water use; "
            "not an environmental-flow reserve"
        ),
    },
)

LAND_ACCOUNTS = (
    {
        "mode": 1,
        "account": "forest",
        "source": "activity",
        "technologies": ("LNDFORTOT",),
        "interpretation": "Model-defined forest land state",
    },
    {
        "mode": 2,
        "account": "grassland",
        "source": "activity",
        "technologies": ("LNDGRSTOT",),
        "interpretation": "Model-defined grassland state",
    },
    {
        "mode": 3,
        "account": "other_land",
        "source": "activity",
        "technologies": ("LNDOTHTOT",),
        "interpretation": "Model-defined other land; no forest suitability is implied",
    },
    {
        "mode": 4,
        "account": "barren_or_savannah",
        "source": "activity",
        "technologies": ("LNDBARTOT",),
        "interpretation": "Model-defined barren or savannah land state",
    },
    {
        "mode": 5,
        "account": "built_up_land",
        "source": "activity",
        "technologies": ("LNDBLTTOT",),
        "interpretation": "Model-defined built-up land state",
    },
    {
        "mode": 6,
        "account": "inland_water_bodies",
        "source": "activity",
        "technologies": ("LNDWATTOT",),
        "interpretation": "Land-cover area classified as water bodies",
    },
    {
        "mode": 7,
        "account": "cropland",
        "source": "activity",
        "technologies": (
            "LNDRCPHITOT",
            "LNDRCPHRTOT",
            "LNDRCPLITOT",
            "LNDRCPLRTOT",
            "LNDCONHITOT",
            "LNDCONHRTOT",
            "LNDCONLITOT",
            "LNDCONLRTOT",
            "LNDMZEHITOT",
            "LNDMZEHRTOT",
            "LNDMZELITOT",
            "LNDMZELRTOT",
            "LNDTOMHITOT",
            "LNDTOMHRTOT",
            "LNDTOMLITOT",
            "LNDTOMLRTOT",
            "LNDSGCHITOT",
            "LNDSGCHRTOT",
            "LNDSGCLITOT",
            "LNDSGCLRTOT",
            "LNDOTHHITOT",
            "LNDOTHHRTOT",
            "LNDOTHLITOT",
            "LNDOTHLRTOT",
        ),
        "interpretation": "Sum of the 24 modeled crop-land production options",
    },
    {
        "mode": 8,
        "account": "unallocated_modeled_land",
        "source": "commodity_residual",
        "commodity": "PHL_LND",
        "interpretation": (
            "Modeled total-land production less all modeled PHL_LND use; small "
            "positive or negative values inside the declared tolerance are CSV rounding"
        ),
    },
)

EXPECTED_WATER_GRAPH = {
    "PHL_WTR_EVT": {
        "producers": {f"LNDAGRPHLC{index:02d}" for index in range(1, 9)},
        "consumers": set(),
    },
    "PHL_WTR_GWT": {
        "producers": {f"LNDAGRPHLC{index:02d}" for index in range(1, 9)},
        "consumers": {"PHL_DEM_PUB_GWT_WAT", "PHL_DEM_PWR_GWT_WAT"},
    },
    "PHL_WTR_SUR": {
        "producers": {f"LNDAGRPHLC{index:02d}" for index in range(1, 9)},
        "consumers": {
            "DEMAGRSURPHL",
            "PHL_DEM_PUB_SUR_WAT",
            "PHL_DEM_PWR_SUR_WAT",
        },
    },
}

EXPECTED_LAND_GRAPH = {
    "producers": {"MINLNDTOT"},
    "consumers": {
        *(account["technologies"][0] for account in LAND_ACCOUNTS[:6]),
        *LAND_ACCOUNTS[6]["technologies"],
    },
}

WATER_BACKSTOP_PATTERN = re.compile(
    r"(?:^BST|BACKSTOP|DEFICIT|UNMET|DUMMY)", re.IGNORECASE
)


class ValidationError(RuntimeError):
    """Raised when source or result evidence cannot support the accounts."""


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_manifest(model: Path, runs: Iterable[str]) -> dict[str, str]:
    files = sorted(model.glob("*.json"))
    files.extend(
        path
        for name in ("resData.json", "viewDefinitions.json")
        if (path := model / "view" / name).is_file()
    )
    for run in runs:
        run_path = model / "res" / run
        files.extend(
            path
            for path in (
                run_path / "data.txt",
                run_path / "data_processed.txt",
                run_path / "results.txt",
                run_path / "csv" / "TotalAnnualTechnologyActivityByMode.csv",
                run_path / "csv" / "ProductionByTechnologyByMode.csv",
                run_path / "csv" / "UseByTechnologyByMode.csv",
                run_path / "csv" / "AnnualTechnologyEmission.csv",
                run_path / "csv" / "ObjectiveValue.csv",
            )
            if path.is_file()
        )
    return {
        path.relative_to(model).as_posix(): sha256(path)
        for path in sorted(set(files))
    }


def csv_rows(path: Path, value_column: str, key_columns: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValidationError(f"No header in {path}")
        missing = set((*key_columns, value_column)) - set(reader.fieldnames)
        if missing:
            raise ValidationError(f"{path} lacks columns {sorted(missing)}")
        rows = list(reader)
    seen: set[tuple[str, ...]] = set()
    for row in rows:
        key = tuple(row[column] for column in key_columns)
        if key in seen:
            raise ValidationError(f"Duplicate result key in {path}: {key}")
        seen.add(key)
        value = float(row[value_column])
        if not math.isfinite(value):
            raise ValidationError(f"Non-finite value in {path}: {key}")
    return rows


def aggregate(
    rows: Iterable[dict[str, str]],
    value_column: str,
    group_columns: tuple[str, ...],
    predicate: Any | None = None,
) -> dict[tuple[str, ...], float]:
    result: dict[tuple[str, ...], float] = defaultdict(float)
    for row in rows:
        if predicate is not None and not predicate(row):
            continue
        key = tuple(row[column] for column in group_columns)
        result[key] += float(row[value_column])
    return dict(result)


def nonzero_ratio_graph(
    gen_data: dict[str, Any], ratios: dict[str, Any]
) -> dict[str, dict[str, set[str]]]:
    technologies = {row["TechId"]: row["Tech"] for row in gen_data["osy-tech"]}
    commodities = {row["CommId"]: row["Comm"] for row in gen_data["osy-comm"]}
    years = [str(year) for year in gen_data["osy-years"]]
    graph: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"producers": set(), "consumers": set()}
    )
    for parameter, side in (("OAR", "producers"), ("IAR", "consumers")):
        for row in ratios[parameter][BASE_SCENARIO]:
            if any(float(row[year] or 0) != 0 for year in years):
                graph[commodities[row["CommId"]]][side].add(
                    technologies[row["TechId"]]
                )
    return dict(graph)


def assert_expected_graph(
    graph: dict[str, dict[str, set[str]]],
    checks: list[dict[str, Any]],
    has_env_land: bool,
    has_env_water: bool,
) -> None:
    for commodity, expected in EXPECTED_WATER_GRAPH.items():
        actual = graph.get(commodity, {"producers": set(), "consumers": set()})
        for side in ("producers", "consumers"):
            expected_side = set(expected[side])
            if side == "consumers" and has_env_water:
                expected_side.add(ENV_WATER_TECH_NAME)
            if actual[side] != expected_side:
                raise ValidationError(
                    f"{commodity} {side}: expected {sorted(expected_side)}, "
                    f"found {sorted(actual[side])}"
                )
    land = graph.get("PHL_LND", {"producers": set(), "consumers": set()})
    for side in ("producers", "consumers"):
        expected = set(EXPECTED_LAND_GRAPH[side])
        if side == "consumers" and has_env_land:
            expected.add("ENV_LAND")
        if land[side] != expected:
            raise ValidationError(
                f"PHL_LND {side}: expected {sorted(expected)}, "
                f"found {sorted(land[side])}"
            )
    checks.append(
        {
            "name": "environmental_commodity_graph",
            "status": "PASS",
            "detail": "Water and total-land producers and consumers match the declared boundary.",
        }
    )


def assert_no_environmental_scenario_overrides(
    gen_data: dict[str, Any],
    ratios: dict[str, Any],
    commodity_names: set[str],
    checks: list[dict[str, Any]],
) -> None:
    commodity_ids = {
        row["CommId"]
        for row in gen_data["osy-comm"]
        if row["Comm"] in commodity_names
    }
    years = [str(year) for year in gen_data["osy-years"]]
    overrides: list[str] = []
    for parameter in ("IAR", "OAR"):
        for scenario, rows in ratios[parameter].items():
            if scenario == BASE_SCENARIO:
                continue
            for row in rows:
                if row["CommId"] in commodity_ids and any(
                    row[year] is not None for year in years
                ):
                    overrides.append(
                        f"{parameter}/{scenario}/{row['TechId']}/{row['CommId']}/{row['MoId']}"
                    )
    if overrides:
        raise ValidationError(
            "Environmental ratios have non-base overrides: " + ", ".join(overrides[:20])
        )
    checks.append(
        {
            "name": "scenario_inheritance",
            "status": "PASS",
            "detail": "Connected environmental ratios inherit unchanged from SC_0 in policy scenarios.",
        }
    )


def water_terminal_diagnostic(
    gen_data: dict[str, Any], ratios: dict[str, Any]
) -> dict[str, Any]:
    years = [str(year) for year in gen_data["osy-years"]]
    technology_names = {row["TechId"]: row["Tech"] for row in gen_data["osy-tech"]}
    commodity_ids = {
        row["CommId"]
        for row in gen_data["osy-comm"]
        if row["Comm"] in {account["commodity"] for account in WATER_ACCOUNTS}
    }
    coefficients: dict[tuple[str, int, str], float] = defaultdict(float)
    for parameter, sign in (("OAR", 1.0), ("IAR", -1.0)):
        for row in ratios[parameter][BASE_SCENARIO]:
            if row["CommId"] not in commodity_ids:
                continue
            for year in years:
                coefficients[(row["TechId"], int(row["MoId"]), year)] += (
                    sign * float(row[year] or 0)
                )
    failures: list[dict[str, Any]] = []
    for technology_id in sorted({key[0] for key in coefficients}):
        values = [
            value
            for (candidate, _mode, _year), value in coefficients.items()
            if candidate == technology_id and value != 0
        ]
        if not values:
            continue
        spread = max(values) - min(values)
        if spread > 1e-12:
            failures.append(
                {
                    "technology": technology_names[technology_id],
                    "minimum_net_coefficient": min(values),
                    "maximum_net_coefficient": max(values),
                    "spread": spread,
                }
            )
    return {
        "json_multimode_terminal_safe": not failures,
        "installed_udc_granularity": "technology-year",
        "required_granularity": "technology-mode-year",
        "mode_dependent_technologies": failures,
        "maximum_spread": max(
            (item["spread"] for item in failures),
            default=0.0,
        ),
    }


def parse_optimal_status(results_path: Path) -> dict[str, Any]:
    with results_path.open(encoding="utf-8", errors="replace") as handle:
        first_line = handle.readline().strip()
    match = re.fullmatch(
        r"Optimal - objective value ([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)",
        first_line,
    )
    if match is None:
        raise ValidationError(
            f"{results_path} does not begin with an explicit optimal status: {first_line!r}"
        )
    return {"status": "Optimal", "objective": float(match.group(1))}


def reconcile_result_ratios(
    gen_data: dict[str, Any],
    ratios: dict[str, Any],
    activity_rows: list[dict[str, str]],
    production_rows: list[dict[str, str]],
    use_rows: list[dict[str, str]],
) -> float:
    technology_names = {row["TechId"]: row["Tech"] for row in gen_data["osy-tech"]}
    commodity_names = {row["CommId"]: row["Comm"] for row in gen_data["osy-comm"]}
    years = [str(year) for year in gen_data["osy-years"]]
    relevant = {
        *(account["commodity"] for account in WATER_ACCOUNTS),
        "PHL_LND",
    }
    activity = {
        (row["t"], int(row["m"]), row["y"]): float(
            row["TotalAnnualTechnologyActivityByMode"]
        )
        for row in activity_rows
    }
    observed = {
        "OAR": aggregate(
            production_rows,
            "ProductionByTechnologyByMode",
            ("f", "t", "m", "y"),
            lambda row: row["f"] in relevant,
        ),
        "IAR": aggregate(
            use_rows,
            "UseByTechnologyByMode",
            ("f", "t", "m", "y"),
            lambda row: row["f"] in relevant,
        ),
    }
    maximum_error = 0.0
    for parameter in ("OAR", "IAR"):
        for row in ratios[parameter][BASE_SCENARIO]:
            commodity = commodity_names[row["CommId"]]
            if commodity not in relevant:
                continue
            technology = technology_names[row["TechId"]]
            mode = int(row["MoId"])
            for year in years:
                expected = activity.get((technology, mode, year), 0.0) * float(
                    row[year] or 0
                )
                actual = observed[parameter].get(
                    (commodity, technology, str(mode), year), 0.0
                )
                maximum_error = max(maximum_error, abs(expected - actual))
    if maximum_error > RESULT_RECONCILIATION_TOLERANCE:
        raise ValidationError(
            "Saved environmental production/use rows do not reconcile with current "
            f"JSON ratios and activity: max error {maximum_error:.12g} exceeds "
            f"{RESULT_RECONCILIATION_TOLERANCE}"
        )
    return maximum_error


def build_run_accounts(
    model: Path,
    run: str,
    gen_data: dict[str, Any],
    has_env_land: bool,
    has_env_water: bool,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    csv_path = model / "res" / run / "csv"
    activity_rows = csv_rows(
        csv_path / "TotalAnnualTechnologyActivityByMode.csv",
        "TotalAnnualTechnologyActivityByMode",
        ("r", "t", "m", "y"),
    )
    production_rows = csv_rows(
        csv_path / "ProductionByTechnologyByMode.csv",
        "ProductionByTechnologyByMode",
        ("r_x", "f", "t", "y", "m", "r_y", "l", "r"),
    )
    use_rows = csv_rows(
        csv_path / "UseByTechnologyByMode.csv",
        "UseByTechnologyByMode",
        ("r_x", "f", "t", "y", "m", "r_y", "l", "r"),
    )
    emission_rows = csv_rows(
        csv_path / "AnnualTechnologyEmission.csv",
        "AnnualTechnologyEmission",
        ("r", "t", "e", "y"),
    )

    ratios = read_json(model / "RYTCM.json")
    reconciliation_error = reconcile_result_ratios(
        gen_data,
        ratios,
        activity_rows,
        production_rows,
        use_rows,
    )

    activity = aggregate(
        activity_rows,
        "TotalAnnualTechnologyActivityByMode",
        ("r", "t", "y"),
    )
    activity_by_mode = aggregate(
        activity_rows,
        "TotalAnnualTechnologyActivityByMode",
        ("r", "t", "m", "y"),
    )
    production = aggregate(
        production_rows,
        "ProductionByTechnologyByMode",
        ("r", "f", "y"),
    )
    use = aggregate(
        use_rows,
        "UseByTechnologyByMode",
        ("r", "f", "y"),
    )
    ordinary_water_use = aggregate(
        use_rows,
        "UseByTechnologyByMode",
        ("r", "f", "y"),
        lambda row: row["t"] != ENV_WATER_TECH_NAME,
    )
    use_by_technology = aggregate(
        use_rows,
        "UseByTechnologyByMode",
        ("r", "f", "t", "y"),
    )
    native_emissions = aggregate(
        emission_rows,
        "AnnualTechnologyEmission",
        ("r", "e", "y"),
    )

    regions = sorted({row["r"] for row in activity_rows})
    years = [str(year) for year in gen_data["osy-years"]]
    commodity_units = {
        row["Comm"]: row["UnitId"] for row in gen_data["osy-comm"]
    }
    emission_units = {row["Emis"]: row["UnitId"] for row in gen_data["osy-emis"]}
    water_units = {
        commodity_units[account["commodity"]] for account in WATER_ACCOUNTS
    }
    if len(water_units) != 1:
        raise ValidationError(f"Water account units differ: {sorted(water_units)}")
    water_unit = next(iter(water_units))
    land_unit = commodity_units["PHL_LND"]

    accounts: list[dict[str, Any]] = []
    water_reconciliation: list[dict[str, Any]] = []
    closure_errors: list[float] = []
    minimum_water_residual = math.inf
    minimum_land_residual = math.inf
    for region in regions:
        for year in years:
            for definition in WATER_ACCOUNTS:
                commodity = definition["commodity"]
                value = production.get(
                    (region, commodity, year), 0.0
                ) - ordinary_water_use.get(
                    (region, commodity, year), 0.0
                )
                minimum_water_residual = min(minimum_water_residual, value)
                accounts.append(
                    {
                        "run": run,
                        "region": region,
                        "year": year,
                        "domain": "WATER",
                        "reporter": (
                            "ENV_WATER_REFERENCE"
                            if has_env_water
                            else "ENV_WATER"
                        ),
                        "mode": definition["mode"],
                        "account": definition["account"],
                        "unit": water_unit,
                        "value": value,
                        "equation": (
                            f"production({commodity}) - ordinary use({commodity}; "
                            f"excluding {ENV_WATER_TECH_NAME})"
                            if has_env_water
                            else f"production({commodity}) - use({commodity})"
                        ),
                        "interpretation": definition["interpretation"],
                    }
                )
                if has_env_water:
                    terminal_counted = activity_by_mode.get(
                        (
                            region,
                            ENV_WATER_TECH_NAME,
                            str(definition["mode"]),
                            year,
                        ),
                        0.0,
                    )
                    unaccounted_gap = value - terminal_counted
                    if (
                        value < -RESULT_RECONCILIATION_TOLERANCE
                        or terminal_counted < -RESULT_RECONCILIATION_TOLERANCE
                        or terminal_counted
                        > value + RESULT_RECONCILIATION_TOLERANCE
                    ):
                        status = "INVALID"
                    elif abs(unaccounted_gap) <= RESULT_RECONCILIATION_TOLERANCE:
                        status = "FULL"
                    elif (
                        value <= RESULT_RECONCILIATION_TOLERANCE
                        and terminal_counted <= RESULT_RECONCILIATION_TOLERANCE
                    ):
                        status = "EMPTY"
                    elif terminal_counted <= RESULT_RECONCILIATION_TOLERANCE:
                        status = "ZERO"
                    else:
                        status = "PARTIAL"
                    coverage = (
                        100.0 * terminal_counted / value
                        if value > RESULT_RECONCILIATION_TOLERANCE
                        else ""
                    )
                    water_reconciliation.append(
                        {
                            "run": run,
                            "region": region,
                            "year": year,
                            "mode": definition["mode"],
                            "account": definition["account"],
                            "commodity": commodity,
                            "unit": water_unit,
                            "reference_available": value,
                            "terminal_counted": terminal_counted,
                            "unaccounted_gap": unaccounted_gap,
                            "coverage_percent": coverage,
                            "status": status,
                        }
                    )
            liquid_value = sum(
                row["value"]
                for row in accounts[-len(WATER_ACCOUNTS) :]
                if row["mode"] in (2, 3)
            )
            accounts.append(
                {
                    "run": run,
                    "region": region,
                    "year": year,
                    "domain": "WATER_SUMMARY",
                    "reporter": (
                        "ENV_WATER_REFERENCE_DERIVED"
                        if has_env_water
                        else "ENV_WATER_DERIVED"
                    ),
                    "mode": "",
                    "account": "modeled_raw_liquid_water_remaining",
                    "unit": water_unit,
                    "value": liquid_value,
                    "equation": (
                        "ENV_WATER mode 2 modeled raw groundwater remaining + "
                        "mode 3 modeled raw surface water remaining"
                    ),
                    "interpretation": (
                        "Derived liquid-water total; excludes mode 1 water vapor"
                    ),
                }
            )

            land_values: dict[int, float] = {}
            for definition in LAND_ACCOUNTS:
                if has_env_land:
                    value = activity_by_mode.get(
                        (
                            region,
                            "ENV_LAND",
                            str(definition["mode"]),
                            year,
                        ),
                        0.0,
                    )
                    equation = f"activity(ENV_LAND mode {definition['mode']})"
                    if definition["mode"] == 8:
                        minimum_land_residual = min(minimum_land_residual, value)
                elif definition["source"] == "activity":
                    value = sum(
                        activity.get((region, technology, year), 0.0)
                        for technology in definition["technologies"]
                    )
                    equation = " + ".join(
                        f"activity({technology})"
                        for technology in definition["technologies"]
                    )
                elif definition["source"] == "commodity_use":
                    commodity = definition["commodity"]
                    value = sum(
                        use_by_technology.get(
                            (region, commodity, technology, year), 0.0
                        )
                        for technology in definition["technologies"]
                    )
                    equation = " + ".join(
                        f"use({commodity} by {technology})"
                        for technology in definition["technologies"]
                    )
                elif definition["source"] == "commodity_residual":
                    commodity = definition["commodity"]
                    value = production.get(
                        (region, commodity, year), 0.0
                    ) - use.get((region, commodity, year), 0.0)
                    equation = f"production({commodity}) - use({commodity})"
                    minimum_land_residual = min(minimum_land_residual, value)
                else:
                    raise AssertionError(definition["source"])
                land_values[definition["mode"]] = value
                accounts.append(
                    {
                        "run": run,
                        "region": region,
                        "year": year,
                        "domain": "LAND",
                        "reporter": "ENV_LAND",
                        "mode": definition["mode"],
                        "account": definition["account"],
                        "unit": land_unit,
                        "value": value,
                        "equation": equation,
                        "interpretation": definition["interpretation"],
                    }
                )
            total_land = production.get((region, "PHL_LND", year), 0.0)
            closure_errors.append(abs(sum(land_values.values()) - total_land))

    if minimum_water_residual < -RESULT_RECONCILIATION_TOLERANCE:
        raise ValidationError(
            f"Water residual is negative beyond tolerance: {minimum_water_residual}"
        )
    maximum_land_closure_error = max(closure_errors, default=0.0)
    if maximum_land_closure_error > LAND_CLOSURE_TOLERANCE:
        raise ValidationError(
            f"Land accounts do not close: max error {maximum_land_closure_error} "
            f"exceeds {LAND_CLOSURE_TOLERANCE}"
        )
    if minimum_land_residual < -LAND_CLOSURE_TOLERANCE:
        raise ValidationError(
            f"Unallocated modeled land is negative beyond tolerance: {minimum_land_residual}"
        )

    emissions: list[dict[str, Any]] = []
    for (region, emission, year), value in sorted(native_emissions.items()):
        emissions.append(
            {
                "run": run,
                "region": region,
                "year": year,
                "emission": emission,
                "unit": emission_units[emission],
                "value": value,
                "equation": "sum of native AnnualTechnologyEmission over technologies",
                "interpretation": "Native MUIO/OSeMOSYS emissions account; no new factor added",
            }
        )

    reconciliation_status_counts: dict[str, int] = defaultdict(int)
    for row in water_reconciliation:
        reconciliation_status_counts[row["status"]] += 1

    return accounts, emissions, water_reconciliation, {
        "run": run,
        "regions": regions,
        "years": [years[0], years[-1]],
        "solver": parse_optimal_status(model / "res" / run / "results.txt"),
        "maximum_result_ratio_reconciliation_error": reconciliation_error,
        "maximum_land_closure_error": maximum_land_closure_error,
        "minimum_unallocated_land_residual": minimum_land_residual,
        "minimum_water_residual": minimum_water_residual,
        "water_terminal_reconciliation_status_counts": dict(
            sorted(reconciliation_status_counts.items())
        ),
        "water_terminal_minimum_coverage_percent": min(
            (
                float(row["coverage_percent"])
                for row in water_reconciliation
                if row["coverage_percent"] != ""
            ),
            default=None,
        ),
        "water_terminal_maximum_unaccounted_gap": max(
            (
                float(row["unaccounted_gap"])
                for row in water_reconciliation
            ),
            default=None,
        ),
    }


def compare_unchanged_control(
    source_model: Path,
    control_model: Path,
    runs: list[str],
    gen_data: dict[str, Any],
    source_accounts: list[dict[str, Any]],
    source_emissions: list[dict[str, Any]],
) -> dict[str, Any]:
    control_model = control_model.resolve()
    if control_model == source_model:
        raise ValidationError("Unchanged control path must differ from the source model")
    if control_model.is_symlink():
        raise ValidationError("Unchanged control path must not be a symlink")
    control_gen_data = read_json(control_model / "genData.json")
    if control_gen_data != gen_data:
        raise ValidationError("Unchanged control genData.json differs from the source")
    source_top = {
        path.name: sha256(path) for path in sorted(source_model.glob("*.json"))
    }
    control_top = {
        path.name: sha256(path) for path in sorted(control_model.glob("*.json"))
    }
    if source_top != control_top:
        raise ValidationError("Unchanged control top-level JSON hashes differ from source")

    control_accounts: list[dict[str, Any]] = []
    control_emissions: list[dict[str, Any]] = []
    run_status: list[dict[str, Any]] = []
    data_hash_identity: dict[str, bool] = {}
    processed_hash_identity: dict[str, bool] = {}
    has_env_land = any(
        row["Tech"] == "ENV_LAND" for row in gen_data["osy-tech"]
    )
    for run in runs:
        accounts, emissions, validation = build_run_accounts(
            control_model, run, gen_data, has_env_land
        )
        control_accounts.extend(accounts)
        control_emissions.extend(emissions)
        run_status.append(validation)
        source_run = source_model / "res" / run
        control_run = control_model / "res" / run
        data_hash_identity[run] = sha256(source_run / "data.txt") == sha256(
            control_run / "data.txt"
        )
        processed_hash_identity[run] = sha256(
            source_run / "data_processed.txt"
        ) == sha256(control_run / "data_processed.txt")
    if not all(data_hash_identity.values()):
        raise ValidationError(
            "Fresh unchanged-control data.txt differs from the saved source input"
        )

    def account_key(row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            row["run"],
            row["region"],
            row["year"],
            row["domain"],
            row["mode"],
            row["account"],
        )

    source_account_map = {
        account_key(row): float(row["value"]) for row in source_accounts
    }
    control_account_map = {
        account_key(row): float(row["value"]) for row in control_accounts
    }
    if source_account_map.keys() != control_account_map.keys():
        raise ValidationError("Unchanged control account row set differs from source")

    account_differences: dict[str, float] = defaultdict(float)
    for key, source_value in source_account_map.items():
        run, _region, _year, _domain, _mode, account = key
        account_differences[f"{run}/{account}"] = max(
            account_differences[f"{run}/{account}"],
            abs(source_value - control_account_map[key]),
        )

    def emission_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
        return (row["run"], row["region"], row["year"], row["emission"])

    source_emission_map = {
        emission_key(row): float(row["value"]) for row in source_emissions
    }
    control_emission_map = {
        emission_key(row): float(row["value"]) for row in control_emissions
    }
    if source_emission_map.keys() != control_emission_map.keys():
        raise ValidationError("Unchanged control emission row set differs from source")
    maximum_emission_difference = max(
        (
            abs(value - control_emission_map[key])
            for key, value in source_emission_map.items()
        ),
        default=0.0,
    )
    objective_differences = {
        source["run"]: abs(
            source["solver"]["objective"]
            - next(
                control["solver"]["objective"]
                for control in run_status
                if control["run"] == source["run"]
            )
        )
        for source in (
            build_run_accounts(
                source_model, run, gen_data, has_env_land
            )[2]
            for run in runs
        )
    }
    return {
        "status": "PASS",
        "control_model": str(control_model),
        "python_hash_seed": "0",
        "top_level_json_hashes_identical": True,
        "control_selected_sha256": selected_manifest(control_model, runs),
        "data_txt_hashes_identical": data_hash_identity,
        "data_processed_hashes_identical": processed_hash_identity,
        "processed_hash_note": (
            "A false value reflects ordering of generated set members under the "
            "explicit control hash seed; data.txt identity proves the same parameter input."
        ),
        "objective_absolute_differences": objective_differences,
        "maximum_account_absolute_differences": dict(
            sorted(account_differences.items())
        ),
        "maximum_native_emission_absolute_difference": maximum_emission_difference,
        "interpretation": (
            "Separate groundwater and surface-water residuals may exchange under "
            "cost-identical routing. The derived liquid-water sum is more stable "
            "but is also basis-sensitive in PEP. Water vapor, land states, native "
            "emissions, objective values, and every account difference are reported "
            "explicitly rather than assumed invariant."
        ),
        "control_run_validation": run_status,
    }


def atomic_write_json(path: Path, data: Any) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temporary, path)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument(
        "--run",
        action="append",
        dest="runs",
        help="Saved run to account; repeat for multiple runs (default: all saved runs).",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--unchanged-control-model",
        type=Path,
        help=(
            "Freshly solved unchanged copy used to verify saved inputs and quantify "
            "degenerate-basis differences."
        ),
    )
    parser.add_argument(
        "--label",
        default=datetime.now().astimezone().strftime("%Y-%m-%dT%H%M%S%z"),
        help="Unique evidence-directory label.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize without writing diagnostics.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = args.model.resolve()
    output_root = args.output_root.resolve()
    label = args.label
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+-]*", label):
        raise ValidationError(f"Unsafe label: {label!r}")
    allowed_models = {
        DEFAULT_MODEL.resolve(): EXPECTED_CASE_NAME,
        DERIVED_MODEL.resolve(): DERIVED_CASE_NAME,
        DIAGNOSTIC_MODEL.resolve(): DIAGNOSTIC_CASE_NAME,
    }
    if model not in allowed_models:
        raise ValidationError(
            "This model-specific reporter accepts only "
            f"{sorted(str(path) for path in allowed_models)}, not {model}"
        )
    if model.is_symlink() or output_root.is_symlink():
        raise ValidationError("Model and output paths must not be symlinks")
    if not (model / "genData.json").is_file():
        raise FileNotFoundError(model / "genData.json")

    gen_data = read_json(model / "genData.json")
    expected_case_name = allowed_models[model]
    if gen_data.get("osy-casename") != expected_case_name:
        raise ValidationError(
            f"Expected osy-casename {expected_case_name}, found "
            f"{gen_data.get('osy-casename')!r}"
        )
    has_env_land = expected_case_name in {
        DERIVED_CASE_NAME,
        DIAGNOSTIC_CASE_NAME,
    }
    has_env_water = expected_case_name == DIAGNOSTIC_CASE_NAME
    res_data = read_json(model / "view" / "resData.json")
    saved_runs = [row["Case"] for row in res_data.get("osy-cases", [])]
    runs = args.runs or saved_runs
    unknown_runs = sorted(set(runs) - set(saved_runs))
    if unknown_runs:
        raise ValidationError(f"Unknown saved runs: {unknown_runs}")

    before_manifest = selected_manifest(model, runs)
    ratios = read_json(model / "RYTCM.json")
    graph = nonzero_ratio_graph(gen_data, ratios)
    checks: list[dict[str, Any]] = []
    assert_expected_graph(graph, checks, has_env_land, has_env_water)
    assert_no_environmental_scenario_overrides(
        gen_data,
        ratios,
        {
            *(account["commodity"] for account in WATER_ACCOUNTS),
            "PHL_LND",
        },
        checks,
    )
    terminal_diagnostic = water_terminal_diagnostic(gen_data, ratios)
    if terminal_diagnostic["json_multimode_terminal_safe"]:
        raise ValidationError(
            "The expected mode-dependent water limitation was not reproduced; "
            "review whether an in-model terminal has become possible."
        )
    if has_env_water:
        water_technologies = [
            row
            for row in gen_data["osy-tech"]
            if row["Tech"] == ENV_WATER_TECH_NAME
        ]
        if len(water_technologies) != 1:
            raise ValidationError(
                f"Expected one diagnostic ENV_WATER, found {len(water_technologies)}"
            )
        water_technology = water_technologies[0]
        if water_technology.get("OAR"):
            raise ValidationError("Diagnostic ENV_WATER must have no outputs")
        if any(
            row["Con"] == "BAL_ENV_WATER"
            or water_technology["TechId"] in row.get("CM", [])
            for row in gen_data["osy-constraints"]
        ):
            raise ValidationError(
                "Diagnostic ENV_WATER must not have a forcing constraint"
            )
        checks.append(
            {
                "name": "water_diagnostic_architecture",
                "status": "PASS",
                "detail": (
                    "Mode-dependent source coefficients remain; ENV_WATER is "
                    "present only as an explicitly unforced diagnostic terminal."
                ),
            }
        )
    else:
        checks.append(
            {
                "name": "water_reporting_only_architecture",
                "status": "PASS",
                "detail": (
                    "Mode-dependent water coefficients were reproduced; no "
                    "inexact in-model ENV_WATER terminal was added."
                ),
            }
        )

    technology_names = {row["Tech"] for row in gen_data["osy-tech"]}
    backstops = sorted(
        name for name in technology_names if WATER_BACKSTOP_PATTERN.search(name)
    )
    all_accounts: list[dict[str, Any]] = []
    all_emissions: list[dict[str, Any]] = []
    all_water_reconciliation: list[dict[str, Any]] = []
    run_validation: list[dict[str, Any]] = []
    for run in runs:
        accounts, emissions, water_reconciliation, validation = build_run_accounts(
            model, run, gen_data, has_env_land, has_env_water
        )
        all_accounts.extend(accounts)
        all_emissions.extend(emissions)
        all_water_reconciliation.extend(water_reconciliation)
        run_validation.append(validation)
    unchanged_control = None
    if args.unchanged_control_model is not None:
        unchanged_control = compare_unchanged_control(
            model,
            args.unchanged_control_model,
            runs,
            gen_data,
            all_accounts,
            all_emissions,
        )
        checks.append(
            {
                "name": "fresh_unchanged_control",
                "status": "PASS",
                "detail": (
                    "Fresh control data.txt hashes match the saved inputs; "
                    "degenerate-basis differences are quantified."
                ),
            }
        )
    checks.extend(
        [
            {
                "name": "solver_status",
                "status": "PASS",
                "detail": f"All {len(runs)} saved runs begin with explicit Optimal status.",
            },
            {
                "name": "account_closure",
                "status": "PASS",
                "detail": (
                    f"Water residuals are nonnegative within {RESULT_RECONCILIATION_TOLERANCE}; "
                    f"land closes within {LAND_CLOSURE_TOLERANCE} in result-CSV units."
                ),
            },
            {
                "name": "native_emissions",
                "status": "PASS",
                "detail": "Existing CO2e and PM2_5 rows were aggregated without new factors.",
            },
        ]
    )
    if has_env_water:
        status_counts: dict[str, int] = defaultdict(int)
        for row in all_water_reconciliation:
            status_counts[row["status"]] += 1
        checks.append(
            {
                "name": "water_terminal_reconciliation",
                "status": (
                    "FAIL" if status_counts.get("INVALID", 0) else "PASS"
                ),
                "detail": {
                    "row_count": len(all_water_reconciliation),
                    "status_counts": dict(sorted(status_counts.items())),
                    "authoritative_reference": (
                        "production minus use by all technologies except ENV_WATER"
                    ),
                    "terminal_value": (
                        "TotalAnnualTechnologyActivityByMode for ENV_WATER"
                    ),
                },
            }
        )

    after_manifest = selected_manifest(model, runs)
    if after_manifest != before_manifest:
        raise ValidationError("Source model or selected result evidence changed during reporting")
    checks.append(
        {
            "name": "source_non_interference",
            "status": "PASS",
            "detail": f"{len(before_manifest)} selected source/result hashes are unchanged.",
        }
    )

    failed_checks = [
        row["name"] for row in checks if row["status"] != "PASS"
    ]
    validation = {
        "status": "PASS" if not failed_checks else "FAIL",
        "failed_checks": failed_checks,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model": expected_case_name,
        "architecture": (
            "exact in-model ENV_LAND plus unforced diagnostic ENV_WATER and "
            "authoritative reporting reference"
            if has_env_water
            else (
                "in-model ENV_LAND plus reporting-only water"
                if has_env_land
                else "reporting-only"
            )
        ),
        "runs": runs,
        "checks": checks,
        "run_validation": run_validation,
        "water_terminal_diagnostic": terminal_diagnostic,
        "backstop_or_deficit_technology_names": backstops,
        "account_count": len(all_accounts),
        "emission_account_count": len(all_emissions),
        "water_terminal_reconciliation_count": len(all_water_reconciliation),
        "tolerances": {
            "result_ratio_reconciliation": RESULT_RECONCILIATION_TOLERANCE,
            "land_closure": LAND_CLOSURE_TOLERANCE,
            "reason": (
                "MUIO result CSV values are rounded to four decimal places, and "
                "annual accounts aggregate many technology/mode/timeslice rows."
            ),
        },
        "data_gaps_not_filled": [
            "Groundwater irrigation technology DEMAGRGWTPHL has no PHL_WTR_GWT input link.",
            "No wastewater return fractions or destinations are encoded.",
            "No desalination feedwater, recovery, or brine coefficients are encoded.",
            "No ecological reserve, accessibility, quality, or sustainable-yield rule is encoded.",
            "PHL_POW_PP_SPV_T1 lists PHL_LND in metadata but all land-input coefficients are zero, so no solar-PV land occupation is reported.",
            "Inherited energy-source traceability remains incomplete.",
        ],
        "unchanged_control_comparison": unchanged_control,
        "source_manifest_sha256": before_manifest,
    }

    summary = {
        "status": validation["status"],
        "model": expected_case_name,
        "architecture": validation["architecture"],
        "runs": runs,
        "account_rows": len(all_accounts),
        "native_emission_rows": len(all_emissions),
        "water_terminal_reconciliation_rows": len(all_water_reconciliation),
        "water_terminal_reconciliation_status_counts": dict(
            sorted(
                (
                    status,
                    sum(
                        row["status"] == status
                        for row in all_water_reconciliation
                    ),
                )
                for status in {
                    row["status"] for row in all_water_reconciliation
                }
            )
        ),
        "maximum_water_coefficient_spread": terminal_diagnostic["maximum_spread"],
        "source_hashes_unchanged": True,
    }
    if args.dry_run:
        print(json.dumps(summary, indent=2))
        return

    output_root.mkdir(parents=True, exist_ok=True)
    target = output_root / label
    if target.exists():
        raise FileExistsError(
            f"Evidence directory already exists; use a new --label: {target}"
        )
    stage = output_root / f".{label}.tmp-{os.getpid()}"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    try:
        write_csv(
            stage / "accounts.csv",
            all_accounts,
            [
                "run",
                "region",
                "year",
                "domain",
                "reporter",
                "mode",
                "account",
                "unit",
                "value",
                "equation",
                "interpretation",
            ],
        )
        write_csv(
            stage / "native_emissions.csv",
            all_emissions,
            [
                "run",
                "region",
                "year",
                "emission",
                "unit",
                "value",
                "equation",
                "interpretation",
            ],
        )
        if has_env_water:
            write_csv(
                stage / "water_terminal_reconciliation.csv",
                all_water_reconciliation,
                [
                    "run",
                    "region",
                    "year",
                    "mode",
                    "account",
                    "commodity",
                    "unit",
                    "reference_available",
                    "terminal_counted",
                    "unaccounted_gap",
                    "coverage_percent",
                    "status",
                ],
            )
        dictionary_rows = [
            {
                "domain": "WATER",
                "reporter": (
                    "ENV_WATER_REFERENCE"
                    if has_env_water
                    else "ENV_WATER"
                ),
                "mode": row["mode"],
                "account": row["account"],
                "unit": next(
                    item["UnitId"]
                    for item in gen_data["osy-comm"]
                    if item["Comm"] == row["commodity"]
                ),
                "source": row["commodity"],
                "interpretation": row["interpretation"],
            }
            for row in WATER_ACCOUNTS
        ] + [
            {
                "domain": "LAND",
                "reporter": "ENV_LAND",
                "mode": row["mode"],
                "account": row["account"],
                "unit": next(
                    item["UnitId"]
                    for item in gen_data["osy-comm"]
                    if item["Comm"] == "PHL_LND"
                ),
                "source": (
                    row.get("commodity")
                    or " + ".join(row.get("technologies", ()))
                ),
                "interpretation": row["interpretation"],
            }
            for row in LAND_ACCOUNTS
        ] + [
            {
                "domain": "WATER_SUMMARY",
                "reporter": (
                    "ENV_WATER_REFERENCE_DERIVED"
                    if has_env_water
                    else "ENV_WATER_DERIVED"
                ),
                "mode": "",
                "account": "modeled_raw_liquid_water_remaining",
                "unit": next(
                    item["UnitId"]
                    for item in gen_data["osy-comm"]
                    if item["Comm"] == "PHL_WTR_GWT"
                ),
                "source": "ENV_WATER modes 2 + 3",
                "interpretation": (
                    "Derived liquid-water total; excludes mode 1 water vapor"
                ),
            }
        ]
        write_csv(
            stage / "account_dictionary.csv",
            dictionary_rows,
            [
                "domain",
                "reporter",
                "mode",
                "account",
                "unit",
                "source",
                "interpretation",
            ],
        )
        atomic_write_json(stage / "validation.json", validation)
        atomic_write_json(stage / "summary.json", summary)
        os.replace(stage, target)
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage)
        raise
    print(json.dumps({**summary, "output": str(target)}, indent=2))
    if failed_checks:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
