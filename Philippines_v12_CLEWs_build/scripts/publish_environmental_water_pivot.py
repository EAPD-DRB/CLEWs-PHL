#!/usr/bin/env python3
"""Publish authoritative ENV_WATER reporting values to MUIO Pivot views.

This is a presentation-layer postprocessor for the explicitly diagnostic
Philippines v12 case. It does not change model JSON, solver inputs, solver
outputs, or result CSV files. It replaces only the ENV_WATER rows in the
generated Pivot JSON files, preserving a byte-for-byte backup and manifests of
the solver-generated views.

The authoritative reference is calculated at timeslice resolution:

    water production - use by every technology except ENV_WATER

Small negative timeslice residuals within result-CSV precision are normalized
to zero. The corresponding rounding correction is removed from the largest
positive timeslice for the same commodity and year so the published
timeslices sum exactly to the authoritative annual reference.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable

import report_environmental_accounting as accounting_reporter


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_MODEL_NAME = "Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC"
DEFAULT_MODEL = ROOT / "WebAPP" / "DataStorage" / EXPECTED_MODEL_NAME
DIAGNOSTICS_ROOT = (
    ROOT
    / "Philippines_v12_CLEWs_build"
    / "diagnostics"
    / "environmental_accounting"
)
MARKER_NAME = "environmental_water_pivot_publication.json"
TERMINAL = "ENV_WATER"
BASE_SCENARIO = "SC_0"
VALUE_QUANTUM = Decimal("0.0001")
RESULT_TOLERANCE = Decimal("0.002")
VIEW_TOLERANCE = Decimal("0.00011")
PIVOT_FILES = ("RT.json", "RYTM.json", "RYTMTs.json", "RYTCMTs.json")
WATER_MODES = {
    1: {
        "commodity": "PHL_WTR_EVT",
        "account": "water_vapor_returned",
    },
    2: {
        "commodity": "PHL_WTR_GWT",
        "account": "modeled_raw_groundwater_remaining",
    },
    3: {
        "commodity": "PHL_WTR_SUR",
        "account": "modeled_raw_surface_water_remaining",
    },
}
RAW_RESULT_FILES = (
    "TotalTechnologyModelPeriodActivity.csv",
    "TotalAnnualTechnologyActivityByMode.csv",
    "RateOfActivity.csv",
    "ProductionByTechnologyByMode.csv",
    "UseByTechnologyByMode.csv",
    "RateOfUseByTechnologyByMode.csv",
)


class PublicationError(RuntimeError):
    """Raised when publishing cannot proceed safely."""


def read_json(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationError(f"Cannot read JSON {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise PublicationError(f"Cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def manifest(paths: Iterable[Path], base: Path) -> dict[str, str]:
    return {
        str(path.relative_to(base)): sha256_file(path)
        for path in sorted(paths, key=lambda item: str(item))
    }


def decimal_value(value: Any, context: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PublicationError(f"Invalid numeric value for {context}: {value!r}") from exc
    if not result.is_finite():
        raise PublicationError(f"Non-finite numeric value for {context}: {value!r}")
    return result


def displayed(value: Decimal) -> float:
    rounded = value.quantize(VALUE_QUANTUM, rounding=ROUND_HALF_UP)
    if rounded == 0:
        return 0.0
    return float(rounded)


def csv_rows(path: Path) -> Iterable[dict[str, str]]:
    try:
        handle = path.open(newline="", encoding="utf-8")
    except OSError as exc:
        raise PublicationError(f"Cannot open result CSV {path}: {exc}") from exc
    with handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise PublicationError(f"Result CSV has no header: {path}")
        for row in reader:
            yield row


def parse_optimal(results_path: Path) -> dict[str, Any]:
    try:
        with results_path.open(encoding="utf-8", errors="replace") as handle:
            first_line = handle.readline().strip()
    except OSError as exc:
        raise PublicationError(f"Cannot read solver status {results_path}: {exc}") from exc
    match = re.fullmatch(
        r"Optimal - objective value ([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)",
        first_line,
    )
    if match is None:
        raise PublicationError(
            f"{results_path} does not begin with explicit Optimal status: {first_line!r}"
        )
    return {"status": "Optimal", "objective": float(match.group(1))}


def resolve_model(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_dir():
        raise PublicationError(f"Model directory does not exist: {resolved}")
    if resolved.name != EXPECTED_MODEL_NAME:
        raise PublicationError(
            f"This postprocessor accepts only {EXPECTED_MODEL_NAME}, got {resolved.name}"
        )
    if resolved.is_symlink():
        raise PublicationError("Model directory must not be a symlink")
    return resolved


def validate_terminal_structure(model: Path, gen_data: dict[str, Any]) -> dict[str, Any]:
    technologies = [
        row for row in gen_data.get("osy-tech", []) if row.get("Tech") == TERMINAL
    ]
    if len(technologies) != 1:
        raise PublicationError(f"Expected one {TERMINAL} technology, found {len(technologies)}")
    terminal = technologies[0]
    if "UNFORCED DIAGNOSTIC ONLY" not in str(terminal.get("Desc", "")):
        raise PublicationError(f"{TERMINAL} is not labelled as an unforced diagnostic")
    if any(
        row.get("Con") == "BAL_ENV_WATER"
        for row in gen_data.get("osy-constraints", [])
    ):
        raise PublicationError("Diagnostic model unexpectedly contains BAL_ENV_WATER")

    years = [str(year) for year in gen_data.get("osy-years", [])]
    timeslices = [str(row["Ts"]) for row in gen_data.get("osy-ts", [])]
    if not years or not timeslices:
        raise PublicationError("Model has no years or timeslices")

    commodity_ids = {
        row["Comm"]: row["CommId"] for row in gen_data.get("osy-comm", [])
    }
    expected_commodities = {
        definition["commodity"] for definition in WATER_MODES.values()
    }
    if not expected_commodities.issubset(commodity_ids):
        missing = sorted(expected_commodities - set(commodity_ids))
        raise PublicationError(f"Missing water commodities: {missing}")

    ratios = read_json(model / "RYTCM.json")
    base_iar = [
        row
        for row in ratios.get("IAR", {}).get(BASE_SCENARIO, [])
        if row.get("TechId") == terminal["TechId"]
    ]
    base_oar = [
        row
        for row in ratios.get("OAR", {}).get(BASE_SCENARIO, [])
        if row.get("TechId") == terminal["TechId"]
    ]
    if base_oar:
        raise PublicationError(f"{TERMINAL} unexpectedly has output ratios")

    observed: dict[tuple[int, str], dict[str, Any]] = {}
    commodity_names = {value: key for key, value in commodity_ids.items()}
    for row in base_iar:
        mode = int(row["MoId"])
        commodity = commodity_names.get(row["CommId"])
        if commodity is None:
            raise PublicationError(f"Undefined ENV_WATER commodity ID: {row['CommId']}")
        nonzero = {
            year: decimal_value(row.get(year, 0) or 0, f"IAR {mode}/{commodity}/{year}")
            for year in years
        }
        values = set(nonzero.values())
        if values == {Decimal(0)}:
            continue
        if values != {Decimal(1)}:
            raise PublicationError(
                f"{TERMINAL} mode {mode}/{commodity} is neither inactive nor "
                "IAR 1 in every year"
            )
        observed[(mode, commodity)] = row
    expected = {
        (mode, definition["commodity"])
        for mode, definition in WATER_MODES.items()
    }
    if set(observed) != expected:
        raise PublicationError(
            f"Unexpected {TERMINAL} IAR mapping: {sorted(observed)}, expected {sorted(expected)}"
        )

    graph_hash = sha256_file(model / "genData.json")
    return {
        "technology_id": terminal["TechId"],
        "years": years,
        "timeslices": timeslices,
        "graph_hash": graph_hash,
        "graph_inputs": [
            {
                "mode": mode,
                "commodity": WATER_MODES[mode]["commodity"],
                "iar": 1,
            }
            for mode in sorted(WATER_MODES)
        ],
    }


def load_year_splits(
    model: Path,
    gen_data: dict[str, Any],
    years: list[str],
    timeslices: list[str],
) -> dict[tuple[str, str], Decimal]:
    ts_id_to_number = {
        str(row["TsId"]): str(row["Ts"]) for row in gen_data["osy-ts"]
    }
    base_rows = read_json(model / "RYTs.json").get("YS", {}).get(BASE_SCENARIO, [])
    splits: dict[tuple[str, str], Decimal] = {}
    for row in base_rows:
        ts = ts_id_to_number.get(str(row.get("TsId")))
        if ts is None:
            raise PublicationError(f"Unknown timeslice ID in YearSplit: {row.get('TsId')}")
        for year in years:
            value = decimal_value(row.get(year), f"YearSplit {ts}/{year}")
            if value <= 0:
                raise PublicationError(f"Non-positive YearSplit for {ts}/{year}: {value}")
            splits[(ts, year)] = value
    expected = {(ts, year) for ts in timeslices for year in years}
    if set(splits) != expected:
        missing = sorted(expected - set(splits))
        raise PublicationError(f"Incomplete YearSplit coverage; first missing: {missing[:5]}")
    for year in years:
        total = sum((splits[(ts, year)] for ts in timeslices), Decimal(0))
        if abs(total - 1) > Decimal("0.0001"):
            raise PublicationError(f"YearSplit does not sum to one in {year}: {total}")
    return splits


def authoritative_reporter_values(
    model: Path,
    run: str,
    gen_data: dict[str, Any],
) -> dict[tuple[int, str], Decimal]:
    accounts, _, _, _ = accounting_reporter.build_run_accounts(
        model,
        run,
        gen_data,
        has_env_land=True,
        has_env_water=True,
    )
    result: dict[tuple[int, str], Decimal] = {}
    for row in accounts:
        if row["domain"] == "WATER" and row["reporter"] == "ENV_WATER_REFERENCE":
            result[(int(row["mode"]), str(row["year"]))] = decimal_value(
                row["value"],
                f"authoritative reporter {run}/{row['mode']}/{row['year']}",
            )
    return result


def compute_run_reference(
    model: Path,
    run: str,
    years: list[str],
    timeslices: list[str],
    year_splits: dict[tuple[str, str], Decimal],
    gen_data: dict[str, Any],
) -> dict[str, Any]:
    csv_path = model / "res" / run / "csv"
    production: defaultdict[tuple[str, str, str, str], Decimal] = defaultdict(Decimal)
    ordinary_use: defaultdict[tuple[str, str, str, str], Decimal] = defaultdict(Decimal)
    regions: set[str] = set()
    water_commodities = {
        definition["commodity"] for definition in WATER_MODES.values()
    }

    for row in csv_rows(csv_path / "ProductionByTechnologyByMode.csv"):
        commodity = row.get("f")
        if commodity not in water_commodities:
            continue
        region = str(row.get("r"))
        key = (region, commodity, str(row["l"]), str(row["y"]))
        production[key] += decimal_value(
            row["ProductionByTechnologyByMode"],
            f"{run} production {key}",
        )
        regions.add(region)

    for row in csv_rows(csv_path / "UseByTechnologyByMode.csv"):
        commodity = row.get("f")
        if commodity not in water_commodities or row.get("t") == TERMINAL:
            continue
        region = str(row.get("r"))
        key = (region, commodity, str(row["l"]), str(row["y"]))
        ordinary_use[key] += decimal_value(
            row["UseByTechnologyByMode"],
            f"{run} ordinary use {key}",
        )
        regions.add(region)

    if len(regions) != 1:
        raise PublicationError(
            f"Pivot postprocessor requires one region, found {sorted(regions)} in {run}"
        )
    region = next(iter(regions))
    contribution: dict[tuple[int, str, str], Decimal] = {}
    raw_reference: dict[tuple[int, str, str], Decimal] = {}
    rate: dict[tuple[int, str, str], Decimal] = {}
    annual: dict[tuple[int, str], Decimal] = {}
    maximum_negative = Decimal(0)
    maximum_adjustment = Decimal(0)
    total_rounding_correction = Decimal(0)

    for mode, definition in WATER_MODES.items():
        commodity = definition["commodity"]
        for year in years:
            raw_by_ts: dict[str, Decimal] = {}
            for ts in timeslices:
                key = (region, commodity, ts, year)
                raw = production[key] - ordinary_use[key]
                if raw < -RESULT_TOLERANCE:
                    raise PublicationError(
                        f"Negative water residual exceeds tolerance in "
                        f"{run}/{commodity}/{year}/TS{ts}: {raw}"
                    )
                maximum_negative = min(maximum_negative, raw)
                raw_by_ts[ts] = raw

            annual_target = sum(raw_by_ts.values(), Decimal(0))
            if annual_target < -RESULT_TOLERANCE:
                raise PublicationError(
                    f"Negative annual water residual in {run}/{commodity}/{year}: "
                    f"{annual_target}"
                )
            if annual_target < 0:
                annual_target = Decimal(0)

            normalized = {
                ts: max(raw, Decimal(0)) for ts, raw in raw_by_ts.items()
            }
            correction = sum(normalized.values(), Decimal(0)) - annual_target
            if correction < 0:
                raise PublicationError(
                    f"Internal normalization error in {run}/{commodity}/{year}: "
                    f"{correction}"
                )
            remaining = correction
            for ts in sorted(
                timeslices,
                key=lambda item: normalized[item],
                reverse=True,
            ):
                if remaining <= 0:
                    break
                reduction = min(normalized[ts], remaining)
                normalized[ts] -= reduction
                remaining -= reduction
            if remaining != 0:
                raise PublicationError(
                    f"Cannot normalize timeslice rounding in "
                    f"{run}/{commodity}/{year}: {remaining}"
                )
            total_rounding_correction += correction

            if sum(normalized.values(), Decimal(0)) != annual_target:
                raise PublicationError(
                    f"Normalized timeslices do not sum to annual reference in "
                    f"{run}/{commodity}/{year}"
                )
            annual[(mode, year)] = annual_target
            for ts in timeslices:
                raw = raw_by_ts[ts]
                published = normalized[ts]
                contribution[(mode, ts, year)] = published
                raw_reference[(mode, ts, year)] = raw
                rate[(mode, ts, year)] = published / year_splits[(ts, year)]
                maximum_adjustment = max(
                    maximum_adjustment,
                    abs(published - raw),
                )

    reporter_values = authoritative_reporter_values(model, run, gen_data)
    expected_keys = {
        (mode, year) for mode in WATER_MODES for year in years
    }
    if set(reporter_values) != expected_keys:
        missing = sorted(expected_keys - set(reporter_values))
        raise PublicationError(
            f"Reporter coverage differs from Pivot reference in {run}: {missing[:5]}"
        )
    maximum_reporter_difference = max(
        (
            abs(annual[key] - reporter_values[key])
            for key in expected_keys
        ),
        default=Decimal(0),
    )
    if maximum_reporter_difference > Decimal("0.0000001"):
        raise PublicationError(
            f"Timeslice and authoritative annual reporter differ in {run}: "
            f"{maximum_reporter_difference}"
        )

    return {
        "run": run,
        "region": region,
        "solver": parse_optimal(model / "res" / run / "results.txt"),
        "contribution": contribution,
        "raw_reference": raw_reference,
        "rate": rate,
        "annual": annual,
        "model_period": sum(annual.values(), Decimal(0)),
        "maximum_negative_timeslice_residual": maximum_negative,
        "maximum_timeslice_rounding_adjustment": maximum_adjustment,
        "total_timeslice_rounding_correction": total_rounding_correction,
        "maximum_reporter_difference": maximum_reporter_difference,
    }


def view_terminal_maps(
    views: dict[str, dict[str, Any]],
    run: str,
    years: list[str],
) -> dict[str, Any]:
    annual: dict[tuple[int, str], Decimal] = {}
    for row in views["RYTM.json"]["TATABM"][run]:
        if row.get("Tech") != TERMINAL:
            continue
        mode = int(row["MoId"])
        for year in years:
            annual[(mode, year)] = decimal_value(
                row.get(year, 0),
                f"view TATABM {run}/{mode}/{year}",
            )

    rate_activity: dict[tuple[int, str, str], Decimal] = {}
    for row in views["RYTMTs.json"]["ROA"][run]:
        if row.get("Tech") != TERMINAL:
            continue
        mode = int(row["MoId"])
        ts = str(row["Ts"])
        for year in years:
            if year in row:
                rate_activity[(mode, ts, year)] = decimal_value(
                    row[year],
                    f"view ROA {run}/{mode}/{ts}/{year}",
                )

    variable_maps: dict[str, dict[tuple[int, str, str, str], Decimal]] = {}
    for variable in ("ROUBT", "UBT"):
        values: dict[tuple[int, str, str, str], Decimal] = {}
        for row in views["RYTCMTs.json"][variable][run]:
            if row.get("Tech") != TERMINAL:
                continue
            mode = int(row["MoId"])
            commodity = str(row["Comm"])
            ts = str(row["Ts"])
            for year in years:
                if year in row:
                    values[(mode, commodity, ts, year)] = decimal_value(
                        row[year],
                        f"view {variable} {run}/{mode}/{commodity}/{ts}/{year}",
                    )
        variable_maps[variable] = values

    rt_rows = views["RT.json"]["TTMPA"][run]
    if len(rt_rows) != 1:
        raise PublicationError(f"Unexpected TTMPA view structure for {run}")
    model_period = decimal_value(
        rt_rows[0].get(TERMINAL, 0),
        f"view TTMPA {run}",
    )
    return {
        "TTMPA": model_period,
        "TATABM": annual,
        "ROA": rate_activity,
        "ROUBT": variable_maps["ROUBT"],
        "UBT": variable_maps["UBT"],
    }


def raw_solver_maps(
    model: Path,
    run: str,
) -> dict[str, Any]:
    csv_path = model / "res" / run / "csv"
    annual: dict[tuple[int, str], Decimal] = {}
    for row in csv_rows(csv_path / "TotalAnnualTechnologyActivityByMode.csv"):
        if row.get("t") == TERMINAL:
            annual[(int(row["m"]), str(row["y"]))] = decimal_value(
                row["TotalAnnualTechnologyActivityByMode"],
                f"raw TATABM {run}",
            )

    rate_activity: dict[tuple[int, str, str], Decimal] = {}
    for row in csv_rows(csv_path / "RateOfActivity.csv"):
        if row.get("t") == TERMINAL:
            rate_activity[(int(row["m"]), str(row["l"]), str(row["y"]))] = (
                decimal_value(row["RateOfActivity"], f"raw ROA {run}")
            )

    variable_maps: dict[str, dict[tuple[int, str, str, str], Decimal]] = {}
    for filename, variable in (
        ("RateOfUseByTechnologyByMode.csv", "ROUBT"),
        ("UseByTechnologyByMode.csv", "UBT"),
    ):
        values: dict[tuple[int, str, str, str], Decimal] = {}
        for row in csv_rows(csv_path / filename):
            if row.get("t") == TERMINAL:
                values[
                    (
                        int(row["m"]),
                        str(row["f"]),
                        str(row["l"]),
                        str(row["y"]),
                    )
                ] = decimal_value(row[filename.removesuffix(".csv")], f"raw {variable} {run}")
        variable_maps[variable] = values

    model_period: Decimal | None = None
    for row in csv_rows(csv_path / "TotalTechnologyModelPeriodActivity.csv"):
        if row.get("t") == TERMINAL:
            model_period = decimal_value(
                row["TotalTechnologyModelPeriodActivity"],
                f"raw TTMPA {run}",
            )
    if model_period is None:
        raise PublicationError(f"Raw solver TTMPA has no {TERMINAL} row for {run}")
    return {
        "TTMPA": model_period,
        "TATABM": annual,
        "ROA": rate_activity,
        "ROUBT": variable_maps["ROUBT"],
        "UBT": variable_maps["UBT"],
    }


def compare_maps(
    actual: dict[str, Any],
    expected: dict[str, Any],
    years: list[str],
    timeslices: list[str],
) -> dict[str, Any]:
    mode_commodity = {
        mode: definition["commodity"] for mode, definition in WATER_MODES.items()
    }
    checks: dict[str, Decimal] = {}
    checks["TTMPA"] = abs(actual["TTMPA"] - expected["TTMPA"])

    annual_keys = {(mode, year) for mode in WATER_MODES for year in years}
    checks["TATABM"] = max(
        (
            abs(
                actual["TATABM"].get(key, Decimal(0))
                - expected["TATABM"].get(key, Decimal(0))
            )
            for key in annual_keys
        ),
        default=Decimal(0),
    )

    timeslice_keys = {
        (mode, ts, year)
        for mode in WATER_MODES
        for ts in timeslices
        for year in years
    }
    checks["ROA"] = max(
        (
            abs(
                actual["ROA"].get(key, Decimal(0))
                - expected["ROA"].get(key, Decimal(0))
            )
            for key in timeslice_keys
        ),
        default=Decimal(0),
    )

    for variable in ("ROUBT", "UBT"):
        keys = {
            (mode, mode_commodity[mode], ts, year)
            for mode in WATER_MODES
            for ts in timeslices
            for year in years
        }
        checks[variable] = max(
            (
                abs(
                    actual[variable].get(key, Decimal(0))
                    - expected[variable].get(key, Decimal(0))
                )
                for key in keys
            ),
            default=Decimal(0),
        )
        unexpected = [
            key
            for key, value in actual[variable].items()
            if key not in keys and value != 0
        ]
        if unexpected:
            raise PublicationError(
                f"Unexpected nonzero {variable} ENV_WATER keys: {unexpected[:5]}"
            )

    maximum = max(checks.values(), default=Decimal(0))
    return {
        "maximum_difference": maximum,
        "by_variable": checks,
    }


def expected_published_maps(
    reference: dict[str, Any],
    years: list[str],
    timeslices: list[str],
) -> dict[str, Any]:
    annual = {
        key: Decimal(str(displayed(value)))
        for key, value in reference["annual"].items()
    }
    rate = {
        key: Decimal(str(displayed(value)))
        for key, value in reference["rate"].items()
    }
    contribution = {
        (
            mode,
            WATER_MODES[mode]["commodity"],
            ts,
            year,
        ): Decimal(str(displayed(reference["contribution"][(mode, ts, year)])))
        for mode in WATER_MODES
        for ts in timeslices
        for year in years
    }
    rate_use = {
        (
            mode,
            WATER_MODES[mode]["commodity"],
            ts,
            year,
        ): rate[(mode, ts, year)]
        for mode in WATER_MODES
        for ts in timeslices
        for year in years
    }
    return {
        "TTMPA": Decimal(str(displayed(reference["model_period"]))),
        "TATABM": annual,
        "ROA": rate,
        "ROUBT": rate_use,
        "UBT": contribution,
    }


def validate_existing_view_is_solver_generated(
    model: Path,
    views: dict[str, dict[str, Any]],
    runs: list[str],
    years: list[str],
    timeslices: list[str],
) -> dict[str, Any]:
    details: dict[str, Any] = {}
    for run in runs:
        actual = view_terminal_maps(views, run, years)
        expected = raw_solver_maps(model, run)
        comparison = compare_maps(actual, expected, years, timeslices)
        if comparison["maximum_difference"] > VIEW_TOLERANCE:
            raise PublicationError(
                f"Current Pivot is neither a recorded reporting publication nor "
                f"the raw solver view for {run}; maximum difference "
                f"{comparison['maximum_difference']}"
            )
        details[run] = {
            "maximum_difference": float(comparison["maximum_difference"]),
            "by_variable": {
                key: float(value)
                for key, value in comparison["by_variable"].items()
            },
        }
    return details


def assert_nonterminal_views_unchanged(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    runs: list[str],
) -> None:
    for run in runs:
        before_rt = copy.deepcopy(before["RT.json"]["TTMPA"][run])
        after_rt = copy.deepcopy(after["RT.json"]["TTMPA"][run])
        for rows in (before_rt, after_rt):
            for row in rows:
                row.pop(TERMINAL, None)
        if before_rt != after_rt:
            raise PublicationError(f"Non-ENV_WATER TTMPA rows changed for {run}")

        for filename, variable in (
            ("RYTM.json", "TATABM"),
            ("RYTMTs.json", "ROA"),
        ):
            before_rows = [
                row
                for row in before[filename][variable][run]
                if row.get("Tech") != TERMINAL
            ]
            after_rows = [
                row
                for row in after[filename][variable][run]
                if row.get("Tech") != TERMINAL
            ]
            if before_rows != after_rows:
                raise PublicationError(
                    f"Non-ENV_WATER {variable} rows changed for {run}"
                )

        for variable in before["RYTCMTs.json"]:
            if variable in ("ROUBT", "UBT"):
                before_rows = [
                    row
                    for row in before["RYTCMTs.json"][variable][run]
                    if row.get("Tech") != TERMINAL
                ]
                after_rows = [
                    row
                    for row in after["RYTCMTs.json"][variable][run]
                    if row.get("Tech") != TERMINAL
                ]
            else:
                before_rows = before["RYTCMTs.json"][variable][run]
                after_rows = after["RYTCMTs.json"][variable][run]
            if before_rows != after_rows:
                raise PublicationError(
                    f"Unexpected {variable} Pivot changes for {run}"
                )


def build_published_views(
    views: dict[str, dict[str, Any]],
    references: dict[str, dict[str, Any]],
    runs: list[str],
    years: list[str],
    timeslices: list[str],
) -> dict[str, dict[str, Any]]:
    published = copy.deepcopy(views)
    for run in runs:
        reference = references[run]

        rt_rows = published["RT.json"]["TTMPA"][run]
        if len(rt_rows) != 1:
            raise PublicationError(f"Unexpected TTMPA rows for {run}")
        rt_rows[0][TERMINAL] = displayed(reference["model_period"])

        annual_rows = [
            row
            for row in published["RYTM.json"]["TATABM"][run]
            if row.get("Tech") == TERMINAL
        ]
        if {int(row["MoId"]) for row in annual_rows} != set(WATER_MODES):
            raise PublicationError(f"Unexpected ENV_WATER TATABM modes for {run}")
        for row in annual_rows:
            mode = int(row["MoId"])
            for year in years:
                row[year] = displayed(reference["annual"][(mode, year)])

        activity_rows = [
            row
            for row in published["RYTMTs.json"]["ROA"][run]
            if row.get("Tech") == TERMINAL
        ]
        expected_activity_rows = len(WATER_MODES) * len(timeslices) * len(years)
        if len(activity_rows) != expected_activity_rows:
            raise PublicationError(
                f"ENV_WATER ROA row count for {run} is {len(activity_rows)}, "
                f"expected {expected_activity_rows}"
            )
        observed_activity_keys: set[tuple[int, str, str]] = set()
        for row in activity_rows:
            mode = int(row["MoId"])
            ts = str(row["Ts"])
            row_years = [year for year in years if year in row]
            if len(row_years) != 1:
                raise PublicationError(
                    f"Unexpected ENV_WATER ROA year fields for {run}: {row}"
                )
            year = row_years[0]
            key = (mode, ts, year)
            observed_activity_keys.add(key)
            row[year] = displayed(reference["rate"][key])
        expected_activity_keys = {
            (mode, ts, year)
            for mode in WATER_MODES
            for ts in timeslices
            for year in years
        }
        if observed_activity_keys != expected_activity_keys:
            raise PublicationError(f"Incomplete ENV_WATER ROA keys for {run}")

        for variable, value_key in (
            ("UBT", "contribution"),
            ("ROUBT", "rate"),
        ):
            rows = [
                row
                for row in published["RYTCMTs.json"][variable][run]
                if row.get("Tech") != TERMINAL
            ]
            terminal_rows: list[dict[str, Any]] = []
            for mode, definition in WATER_MODES.items():
                commodity = definition["commodity"]
                for ts in timeslices:
                    row: dict[str, Any] = {
                        "Tech": TERMINAL,
                        "Comm": commodity,
                        "MoId": mode,
                        "Ts": int(ts),
                    }
                    for year in years:
                        value = displayed(reference[value_key][(mode, ts, year)])
                        if value != 0:
                            row[year] = value
                    if len(row) > 4:
                        terminal_rows.append(row)
            published["RYTCMTs.json"][variable][run] = rows + terminal_rows

        for variable in ("PBT", "ROPBT"):
            if any(
                row.get("Tech") == TERMINAL
                for row in published["RYTCMTs.json"].get(variable, {}).get(run, [])
            ):
                raise PublicationError(f"{TERMINAL} unexpectedly has {variable} rows")

    assert_nonterminal_views_unchanged(views, published, runs)
    return published


def validate_published_views(
    views: dict[str, dict[str, Any]],
    references: dict[str, dict[str, Any]],
    runs: list[str],
    years: list[str],
    timeslices: list[str],
    year_splits: dict[tuple[str, str], Decimal],
) -> dict[str, Any]:
    run_details: dict[str, Any] = {}
    for run in runs:
        actual = view_terminal_maps(views, run, years)
        expected = expected_published_maps(references[run], years, timeslices)
        comparison = compare_maps(actual, expected, years, timeslices)
        if comparison["maximum_difference"] > Decimal("0.000001"):
            raise PublicationError(
                f"Published Pivot differs from expected reference in {run}: "
                f"{comparison['maximum_difference']}"
            )

        maximum_annual_use_difference = Decimal(0)
        maximum_rate_activity_difference = Decimal(0)
        for mode, definition in WATER_MODES.items():
            commodity = definition["commodity"]
            for year in years:
                annual_activity = actual["TATABM"][(mode, year)]
                annual_use = sum(
                    (
                        actual["UBT"].get(
                            (mode, commodity, ts, year),
                            Decimal(0),
                        )
                        for ts in timeslices
                    ),
                    Decimal(0),
                )
                maximum_annual_use_difference = max(
                    maximum_annual_use_difference,
                    abs(annual_activity - annual_use),
                )
                annual_from_rate = sum(
                    (
                        actual["ROA"][(mode, ts, year)]
                        * year_splits[(ts, year)]
                        for ts in timeslices
                    ),
                    Decimal(0),
                )
                maximum_rate_activity_difference = max(
                    maximum_rate_activity_difference,
                    abs(annual_activity - annual_from_rate),
                )
                for ts in timeslices:
                    rate_activity = actual["ROA"][(mode, ts, year)]
                    rate_use = actual["ROUBT"].get(
                        (mode, commodity, ts, year),
                        Decimal(0),
                    )
                    maximum_rate_activity_difference = max(
                        maximum_rate_activity_difference,
                        abs(rate_activity - rate_use),
                    )

        if maximum_annual_use_difference > VIEW_TOLERANCE:
            raise PublicationError(
                f"Published annual activity/use mismatch in {run}: "
                f"{maximum_annual_use_difference}"
            )
        if maximum_rate_activity_difference > RESULT_TOLERANCE:
            raise PublicationError(
                f"Published rate/activity mismatch in {run}: "
                f"{maximum_rate_activity_difference}"
            )

        run_details[run] = {
            "solver": references[run]["solver"],
            "region": references[run]["region"],
            "model_period_activity": float(references[run]["model_period"]),
            "maximum_pivot_expected_difference": float(
                comparison["maximum_difference"]
            ),
            "maximum_annual_activity_use_difference": float(
                maximum_annual_use_difference
            ),
            "maximum_rate_activity_difference": float(
                maximum_rate_activity_difference
            ),
            "maximum_negative_timeslice_residual": float(
                references[run]["maximum_negative_timeslice_residual"]
            ),
            "maximum_timeslice_rounding_adjustment": float(
                references[run]["maximum_timeslice_rounding_adjustment"]
            ),
            "total_timeslice_rounding_correction": float(
                references[run]["total_timeslice_rounding_correction"]
            ),
            "maximum_authoritative_reporter_difference": float(
                references[run]["maximum_reporter_difference"]
            ),
        }
    return run_details


def write_json_file(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=4)
        handle.write("\n")


def atomic_write_json(path: Path, value: Any) -> None:
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        write_json_file(temp_path, value)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def write_timeslice_reference(
    path: Path,
    references: dict[str, dict[str, Any]],
    runs: list[str],
    years: list[str],
    timeslices: list[str],
) -> None:
    fields = [
        "run",
        "region",
        "year",
        "timeslice",
        "mode",
        "account",
        "commodity",
        "raw_reference",
        "rounding_adjustment",
        "published_use",
        "published_rate",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for run in runs:
            reference = references[run]
            for year in years:
                for ts in timeslices:
                    for mode, definition in WATER_MODES.items():
                        raw = reference["raw_reference"][(mode, ts, year)]
                        published = reference["contribution"][(mode, ts, year)]
                        writer.writerow(
                            {
                                "run": run,
                                "region": reference["region"],
                                "year": year,
                                "timeslice": ts,
                                "mode": mode,
                                "account": definition["account"],
                                "commodity": definition["commodity"],
                                "raw_reference": str(raw),
                                "rounding_adjustment": str(published - raw),
                                "published_use": str(published),
                                "published_rate": str(
                                    reference["rate"][(mode, ts, year)]
                                ),
                            }
                        )


def stage_view_files(
    model: Path,
    published: dict[str, dict[str, Any]],
) -> dict[str, Path]:
    staged: dict[str, Path] = {}
    try:
        for filename in PIVOT_FILES:
            target = model / "view" / filename
            temp_path = target.with_name(
                f".{target.name}.env-water-{uuid.uuid4().hex}.tmp"
            )
            write_json_file(temp_path, published[filename])
            read_json(temp_path)
            staged[filename] = temp_path
    except Exception:
        for path in staged.values():
            if path.exists():
                path.unlink()
        raise
    return staged


def raw_result_paths(model: Path, runs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for run in runs:
        run_root = model / "res" / run
        paths.append(run_root / "results.txt")
        for filename in RAW_RESULT_FILES:
            path = run_root / "csv" / filename
            if not path.is_file():
                raise PublicationError(f"Missing raw result file: {path}")
            paths.append(path)
    return paths


def load_runs(model: Path) -> list[str]:
    res_data = read_json(model / "view" / "resData.json")
    runs = [str(row["Case"]) for row in res_data.get("osy-cases", [])]
    if runs != ["Base_v12", "PEP_v12"]:
        raise PublicationError(
            f"Expected saved runs Base_v12 and PEP_v12, found {runs}"
        )
    return runs


def current_view_manifest(model: Path) -> dict[str, str]:
    return manifest(
        [model / "view" / filename for filename in PIVOT_FILES],
        model,
    )


def summarize(
    *,
    model: Path,
    runs: list[str],
    references: dict[str, dict[str, Any]],
    state: str,
    dry_run: bool,
    changed: bool,
    evidence: Path | None,
    validation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "PASS",
        "model": model.name,
        "architecture": (
            "solver topology plus authoritative reporting publication in Pivot"
        ),
        "state_before": state,
        "dry_run": dry_run,
        "changed": changed,
        "evidence": str(evidence) if evidence else None,
        "runs": {
            run: {
                "solver": references[run]["solver"],
                "model_period_activity": float(references[run]["model_period"]),
                "maximum_timeslice_rounding_adjustment": float(
                    references[run]["maximum_timeslice_rounding_adjustment"]
                ),
                "pivot_validation": validation[run],
            }
            for run in runs
        },
    }


def publish(model: Path, label: str, dry_run: bool) -> dict[str, Any]:
    model = resolve_model(model)
    gen_data = read_json(model / "genData.json")
    terminal_structure = validate_terminal_structure(model, gen_data)
    years = terminal_structure["years"]
    timeslices = terminal_structure["timeslices"]
    year_splits = load_year_splits(model, gen_data, years, timeslices)
    runs = load_runs(model)
    raw_paths = raw_result_paths(model, runs)
    raw_manifest_before = manifest(raw_paths, model)

    view_paths = [model / "view" / filename for filename in PIVOT_FILES]
    views = {filename: read_json(model / "view" / filename) for filename in PIVOT_FILES}
    view_manifest_before = current_view_manifest(model)
    marker_path = model / "documentation" / MARKER_NAME
    marker = read_json(marker_path) if marker_path.is_file() else None

    references = {
        run: compute_run_reference(
            model,
            run,
            years,
            timeslices,
            year_splits,
            gen_data,
        )
        for run in runs
    }
    published = build_published_views(
        views,
        references,
        runs,
        years,
        timeslices,
    )
    validation = validate_published_views(
        published,
        references,
        runs,
        years,
        timeslices,
        year_splits,
    )

    if (
        marker
        and marker.get("published_view_manifest") == view_manifest_before
        and marker.get("raw_result_manifest") == raw_manifest_before
    ):
        current_validation = validate_published_views(
            views,
            references,
            runs,
            years,
            timeslices,
            year_splits,
        )
        if sha256_file(model / "genData.json") != terminal_structure["graph_hash"]:
            raise PublicationError("Dynamic Graph source changed during validation")
        return summarize(
            model=model,
            runs=runs,
            references=references,
            state="already_published",
            dry_run=dry_run,
            changed=False,
            evidence=Path(marker["evidence"]),
            validation=current_validation,
        )

    raw_view_comparison = validate_existing_view_is_solver_generated(
        model,
        views,
        runs,
        years,
        timeslices,
    )
    if dry_run:
        return summarize(
            model=model,
            runs=runs,
            references=references,
            state="solver_generated",
            dry_run=True,
            changed=False,
            evidence=None,
            validation=validation,
        )

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", label):
        raise PublicationError(
            "Evidence label must contain only letters, digits, period, underscore, "
            "or hyphen"
        )
    evidence = DIAGNOSTICS_ROOT / label
    if evidence.exists():
        raise PublicationError(f"Evidence directory already exists: {evidence}")
    DIAGNOSTICS_ROOT.mkdir(parents=True, exist_ok=True)
    stage_evidence = Path(
        tempfile.mkdtemp(prefix=f".{label}.stage-", dir=DIAGNOSTICS_ROOT)
    )
    backup_dir = stage_evidence / "solver_generated_view_backup"
    backup_dir.mkdir()
    staged_views: dict[str, Path] = {}
    replaced: list[str] = []
    try:
        for path in view_paths:
            shutil.copy2(path, backup_dir / path.name)
        staged_views = stage_view_files(model, published)
        for filename in PIVOT_FILES:
            os.replace(staged_views[filename], model / "view" / filename)
            replaced.append(filename)

        actual_views = {
            filename: read_json(model / "view" / filename)
            for filename in PIVOT_FILES
        }
        actual_validation = validate_published_views(
            actual_views,
            references,
            runs,
            years,
            timeslices,
            year_splits,
        )
        assert_nonterminal_views_unchanged(views, actual_views, runs)
        raw_manifest_after = manifest(raw_paths, model)
        if raw_manifest_after != raw_manifest_before:
            raise PublicationError("Raw solver result files changed during publication")
        if sha256_file(model / "genData.json") != terminal_structure["graph_hash"]:
            raise PublicationError("Dynamic Graph source changed during publication")
        published_manifest = current_view_manifest(model)

        publication = {
            "status": "PASS",
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "model": model.name,
            "terminal": TERMINAL,
            "role": (
                "authoritative reporting publication in Pivot; raw solver terminal "
                "results remain preserved separately"
            ),
            "formula": (
                "production minus use by every technology except ENV_WATER"
            ),
            "variables_published": {
                "RT.json": ["TTMPA"],
                "RYTM.json": ["TATABM"],
                "RYTMTs.json": ["ROA"],
                "RYTCMTs.json": ["ROUBT", "UBT"],
            },
            "variables_intentionally_unchanged": {
                "RYTCMTs.json": ["PBT", "ROPBT"],
                "reason": "ENV_WATER has no output",
            },
            "dynamic_graph": {
                "source": "genData.json",
                "sha256": terminal_structure["graph_hash"],
                "terminal_inputs": terminal_structure["graph_inputs"],
                "unchanged": True,
            },
            "raw_result_manifest": raw_manifest_before,
            "solver_generated_view_manifest": view_manifest_before,
            "published_view_manifest": published_manifest,
            "raw_solver_view_comparison": raw_view_comparison,
            "run_validation": actual_validation,
            "evidence": str(evidence),
            "backup": str(evidence / "solver_generated_view_backup"),
        }
        write_timeslice_reference(
            stage_evidence / "timeslice_reference.csv",
            references,
            runs,
            years,
            timeslices,
        )
        write_json_file(stage_evidence / "publication.json", publication)
        write_json_file(
            stage_evidence / "validation.json",
            {
                "status": "PASS",
                "failed_checks": [],
                "checks": [
                    {
                        "name": "raw_solver_results_preserved",
                        "status": "PASS",
                        "detail": raw_manifest_before,
                    },
                    {
                        "name": "dynamic_graph_topology_preserved",
                        "status": "PASS",
                        "detail": publication["dynamic_graph"],
                    },
                    {
                        "name": "nonterminal_pivot_rows_preserved",
                        "status": "PASS",
                        "detail": (
                            "All non-ENV_WATER Pivot values are structurally equal "
                            "before and after publication."
                        ),
                    },
                    {
                        "name": "authoritative_reporter_parity",
                        "status": "PASS",
                        "detail": {
                            run: actual_validation[run][
                                "maximum_authoritative_reporter_difference"
                            ]
                            for run in runs
                        },
                    },
                    {
                        "name": "linked_pivot_identity",
                        "status": "PASS",
                        "detail": actual_validation,
                    },
                    {
                        "name": "solver_view_backup",
                        "status": "PASS",
                        "detail": str(evidence / "solver_generated_view_backup"),
                    },
                ],
            },
        )
        os.replace(stage_evidence, evidence)
        marker_value = {
            "status": "PUBLISHED",
            "model": model.name,
            "published_at": publication["generated_at"],
            "evidence": str(evidence),
            "raw_result_manifest": raw_manifest_before,
            "published_view_manifest": published_manifest,
            "dynamic_graph_sha256": terminal_structure["graph_hash"],
            "note": (
                "ENV_WATER Pivot values are authoritative postprocessed reporting "
                "values; raw solver CSVs are unchanged."
            ),
        }
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(marker_path, marker_value)
        return summarize(
            model=model,
            runs=runs,
            references=references,
            state="solver_generated",
            dry_run=False,
            changed=True,
            evidence=evidence,
            validation=actual_validation,
        )
    except Exception:
        for filename in replaced:
            backup = backup_dir / filename
            if backup.exists():
                shutil.copy2(backup, model / "view" / filename)
        for path in staged_views.values():
            if path.exists():
                path.unlink()
        if stage_evidence.exists():
            shutil.rmtree(stage_evidence)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL,
        help=f"Diagnostic model directory (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--label",
        default="2026-07-26_env_water_pivot_published",
        help="Unique evidence directory label",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calculate and validate without changing Pivot files",
    )
    args = parser.parse_args()
    try:
        result = publish(args.model, args.label, args.dry_run)
    except PublicationError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
