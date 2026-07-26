#!/usr/bin/env python3
"""Generate an unforced ENV_WATER diagnostic on top of Philippines v12 ENV_LAND.

The generated case is deliberately diagnostic rather than an exact in-model
water account.  Its three ENV_WATER modes may consume the modeled residuals,
but no user-defined constraint forces them to do so.  The authoritative water
values remain the separately generated production-minus-ordinary-use report.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import tempfile
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import generate_environmental_land_case as land


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = (
    REPO_ROOT / "WebAPP" / "DataStorage" / "Philippines_v12_ENV_LAND"
)
DEFAULT_TARGET = (
    REPO_ROOT
    / "WebAPP"
    / "DataStorage"
    / "Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC"
)
EXPECTED_SOURCE_CASE = "Philippines_v12_ENV_LAND"
TARGET_CASE_NAME = "Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC"
BASE_SCENARIO = "SC_0"
ENV_WATER_TECH_ID = "TEC_envwater_diag_v12"
ENV_WATER_TECH_NAME = "ENV_WATER"
ENVIRONMENT_GROUP_NAME = "ENVIRONMENT"
WATER_UNIT = "10<sup>9</sup>m<sup>3</sup>"
SELECTED_VIEW_FILES = ("resData.json", "viewDefinitions.json")

WATER_CATEGORIES = (
    {
        "mode": 1,
        "account": "water_vapor_returned",
        "commodity": "PHL_WTR_EVT",
    },
    {
        "mode": 2,
        "account": "modeled_raw_groundwater_remaining",
        "commodity": "PHL_WTR_GWT",
    },
    {
        "mode": 3,
        "account": "modeled_raw_surface_water_remaining",
        "commodity": "PHL_WTR_SUR",
    },
)

RT_VALUES = {
    "TMPAL": 0,
    "OL": 1,
    "CAU": 1,
    "DRI": 0.05,
}
RYT_FIXED_VALUES = {
    "COTU": 0,
    "TAL": 0,
    "TAMinCI": 0,
    "TAMinC": 0,
    "TAMaxCI": 0,
    "FC": 0,
    "CC": 0,
    "AF": 1,
}
RYTM_FIXED_VALUES = {
    "TAIML": 0,
    "TADML": 0,
    "TAMLL": 0,
    "VC": 0,
}

DERIVED_README = """# Philippines v12 ENV_WATER diagnostic case

This case is generated from `Philippines_v12_ENV_LAND`. It retains the exact
eight-mode `ENV_LAND` account and adds an **unforced diagnostic**
three-mode `ENV_WATER` technology:

1. water vapor returned;
2. modeled raw groundwater remaining; and
3. modeled raw surface water remaining.

`ENV_WATER` has no balance constraint and is not an authoritative account.
Its activity may be zero, partial, or complete because the standard commodity
balances permit unused production. Compare its activity with the authoritative
production-minus-ordinary-use ledger in:

`../../../Philippines_v12_CLEWs_build/diagnostics/environmental_accounting/`

- Generator:
  `../../../Philippines_v12_CLEWs_build/scripts/generate_environmental_water_diagnostic_case.py`
- Reporter:
  `../../../Philippines_v12_CLEWs_build/scripts/report_environmental_accounting.py`
- Validator:
  `../../../Philippines_v12_CLEWs_build/scripts/validate_environmental_water_diagnostic_case.py`
- Local documentation index: `documentation/README.md`

Do not use `ENV_WATER` activity without its reconciliation report. Do not edit
generated solver inputs, outputs, CSV files, or Pivot files by hand.
"""

DERIVED_DOCUMENTATION_README = """# ENV_WATER diagnostic case documentation

The canonical documentation is kept in the v12 build package:

- `../../../../Philippines_v12_CLEWs_build/documentation/ENVIRONMENTAL_ACCOUNTING.md`
- `../../../../Philippines_v12_CLEWs_build/documentation/CURRENT_MODEL.md`
- `../../../../Philippines_v12_CLEWs_build/data_sources/`

This case contains:

- exact in-model `ENV_LAND` modes 1-8;
- unforced diagnostic `ENV_WATER` modes 1-3; and
- no `BAL_ENV_WATER` constraint.

The reporting ledger excludes `ENV_WATER` consumption when calculating the
reference residual, then compares that reference with terminal activity.
"""


class GenerationError(RuntimeError):
    """Raised when the diagnostic case cannot be generated safely."""


def resolve_paths(source: Path, target: Path) -> tuple[Path, Path]:
    source = source.resolve()
    target = target.resolve(strict=False)
    if not source.is_dir():
        raise GenerationError(f"Source case does not exist: {source}")
    if source.is_symlink() or (target.exists() and target.is_symlink()):
        raise GenerationError("Source and target case paths must not be symlinks")
    if source == target:
        raise GenerationError("Source and target case paths must differ")
    if source in target.parents or target in source.parents:
        raise GenerationError("Source and target must not be ancestor/descendant paths")
    if target.parent != source.parent:
        raise GenerationError(
            "The diagnostic case must be a sibling of the exact-land source case"
        )
    return source, target


def inherited_values_are_null(
    scenarios: dict[str, list[dict[str, Any]]],
    selector: dict[str, Any],
    years: list[str],
) -> bool:
    for scenario, rows in scenarios.items():
        if scenario == BASE_SCENARIO:
            continue
        matches = [
            row
            for row in rows
            if all(row.get(key) == value for key, value in selector.items())
        ]
        if len(matches) != 1:
            return False
        if any(matches[0][year] is not None for year in years):
            return False
    return True


def audit_source(source: Path) -> dict[str, Any]:
    gen_data = land.read_json(source / "genData.json")
    if gen_data.get("osy-casename") != EXPECTED_SOURCE_CASE:
        raise GenerationError(
            f"Expected source case {EXPECTED_SOURCE_CASE}, found "
            f"{gen_data.get('osy-casename')!r}"
        )
    if sum(row["Tech"] == land.ENV_TECH_NAME for row in gen_data["osy-tech"]) != 1:
        raise GenerationError("Source must contain exactly one exact ENV_LAND")
    if any(row["Tech"] == ENV_WATER_TECH_NAME for row in gen_data["osy-tech"]):
        raise GenerationError("Source already contains ENV_WATER")

    groups = [
        row
        for row in gen_data["osy-techGroups"]
        if row["TechGroup"] == ENVIRONMENT_GROUP_NAME
    ]
    if len(groups) != 1:
        raise GenerationError("Source must contain exactly one ENVIRONMENT group")
    environment_group_id = groups[0]["TechGroupId"]

    existing_names = {
        *(row["Tech"] for row in gen_data["osy-tech"]),
        *(row["Comm"] for row in gen_data["osy-comm"]),
        *(row["Con"] for row in gen_data["osy-constraints"]),
    }
    if ENV_WATER_TECH_NAME in existing_names:
        raise GenerationError(f"Accounting-name collision: {ENV_WATER_TECH_NAME}")
    existing_ids = {
        *(row["TechId"] for row in gen_data["osy-tech"]),
        *(row["CommId"] for row in gen_data["osy-comm"]),
        *(row["ConId"] for row in gen_data["osy-constraints"]),
    }
    if ENV_WATER_TECH_ID in existing_ids:
        raise GenerationError(f"Accounting-ID collision: {ENV_WATER_TECH_ID}")

    years = [str(year) for year in gen_data["osy-years"]]
    scenarios = [row["ScenarioId"] for row in gen_data["osy-scenarios"]]
    mode_count = int(gen_data["osy-mo"])
    modes = list(range(1, mode_count + 1))
    timeslice_ids = [row["TsId"] for row in gen_data["osy-ts"]]
    technology_names = {row["TechId"]: row["Tech"] for row in gen_data["osy-tech"]}
    commodity_by_name = {row["Comm"]: row for row in gen_data["osy-comm"]}
    missing = sorted(
        category["commodity"]
        for category in WATER_CATEGORIES
        if category["commodity"] not in commodity_by_name
    )
    if missing:
        raise GenerationError(f"Missing water commodities: {missing}")
    water_commodities = [commodity_by_name[row["commodity"]] for row in WATER_CATEGORIES]
    units = {row["UnitId"] for row in water_commodities}
    if units != {WATER_UNIT}:
        raise GenerationError(f"Unexpected or inconsistent water units: {sorted(units)}")
    water_ids = {row["CommId"] for row in water_commodities}

    ratios = land.read_json(source / "RYTCM.json")
    coefficients: dict[tuple[str, int, str], float] = {}
    producers: set[str] = set()
    for row in ratios["OAR"][BASE_SCENARIO]:
        if row["CommId"] not in water_ids:
            continue
        technology_id = row["TechId"]
        mode = int(row["MoId"])
        for year in years:
            value = float(row[year] or 0)
            coefficients[(technology_id, mode, year)] = (
                coefficients.get((technology_id, mode, year), 0.0) + value
            )
            if value > 0:
                producers.add(technology_id)
        if not inherited_values_are_null(
            ratios["OAR"],
            {
                "TechId": technology_id,
                "CommId": row["CommId"],
                "MoId": row["MoId"],
            },
            years,
        ):
            raise GenerationError(
                "Water OAR scenario inheritance differs from the base case for "
                f"{technology_names[technology_id]}/{row['CommId']}/{mode}"
            )
    for row in ratios["IAR"][BASE_SCENARIO]:
        if row["CommId"] not in water_ids:
            continue
        if not inherited_values_are_null(
            ratios["IAR"],
            {
                "TechId": row["TechId"],
                "CommId": row["CommId"],
                "MoId": row["MoId"],
            },
            years,
        ):
            raise GenerationError(
                "Water IAR scenario inheritance differs from the base case for "
                f"{technology_names[row['TechId']]}/{row['CommId']}/{row['MoId']}"
            )
    if not producers:
        raise GenerationError("No modeled water producers were found")

    ryc = land.read_json(source / "RYC.json")
    for parameter in ("SAD", "AAD"):
        for commodity in water_commodities:
            rows = [
                row
                for row in ryc[parameter][BASE_SCENARIO]
                if row["CommId"] == commodity["CommId"]
            ]
            if len(rows) != 1 or any(float(rows[0][year] or 0) != 0 for year in years):
                raise GenerationError(
                    f"{parameter}/{commodity['Comm']} must be present and zero"
                )
            if not inherited_values_are_null(
                ryc[parameter], {"CommId": commodity["CommId"]}, years
            ):
                raise GenerationError(
                    f"{parameter}/{commodity['Comm']} does not use scenario inheritance"
                )

    for technology in gen_data["osy-tech"]:
        connected_capacity_inputs = water_ids & set(
            (*technology.get("INCR", []), *technology.get("ITCR", []))
        )
        if connected_capacity_inputs:
            raise GenerationError(
                "Water account commodity has a capacity-input term on "
                f"{technology['Tech']}: {sorted(connected_capacity_inputs)}"
            )
    ryt = land.read_json(source / "RYT.json")
    tau_rows = {
        row["TechId"]: row
        for row in ryt["TAU"][BASE_SCENARIO]
        if row["TechId"] in producers
    }
    if set(tau_rows) != producers:
        missing_bounds = sorted(technology_names[item] for item in producers - set(tau_rows))
        raise GenerationError(
            f"Water producers lack annual activity bounds: {missing_bounds}"
        )

    annual_envelopes: dict[str, float] = {}
    for year in years:
        total = 0.0
        for technology_id in producers:
            activity_upper = float(tau_rows[technology_id][year] or 0)
            if not math.isfinite(activity_upper) or activity_upper <= 0:
                raise GenerationError(
                    "Water producer lacks a finite positive annual activity bound: "
                    f"{technology_names[technology_id]}/{year}/{activity_upper}"
                )
            maximum_combined_oar = max(
                coefficients.get((technology_id, mode, year), 0.0)
                for mode in modes
            )
            if maximum_combined_oar <= 0:
                raise GenerationError(
                    f"Water producer has no positive combined OAR in {year}: "
                    f"{technology_names[technology_id]}"
                )
            total += activity_upper * maximum_combined_oar
        annual_envelopes[year] = total
    annual_upper = max(annual_envelopes.values())
    model_period_upper = sum(annual_envelopes.values())

    return {
        "gen_data": gen_data,
        "years": years,
        "scenarios": scenarios,
        "modes": modes,
        "timeslice_ids": timeslice_ids,
        "environment_group_id": environment_group_id,
        "water_commodities": water_commodities,
        "water_ids": water_ids,
        "producer_names": sorted(technology_names[item] for item in producers),
        "annual_envelopes": annual_envelopes,
        "annual_upper": annual_upper,
        "model_period_upper": model_period_upper,
    }


def append_terminal_parameters(
    data: dict[str, Any],
    audit: dict[str, Any],
) -> None:
    years = audit["years"]
    scenarios = audit["scenarios"]
    modes = audit["modes"]
    annual_upper = audit["annual_upper"]
    model_period_upper = audit["model_period_upper"]

    rt_values = {**RT_VALUES, "TMPAU": model_period_upper}
    for parameter, value in rt_values.items():
        for scenario in scenarios:
            data["RT.json"][parameter][scenario][0][ENV_WATER_TECH_ID] = (
                value if scenario == BASE_SCENARIO else None
            )

    ryt_values = {
        **RYT_FIXED_VALUES,
        "TAU": annual_upper,
        "TAMaxC": annual_upper,
        "RC": annual_upper,
    }
    for parameter, value in ryt_values.items():
        for scenario in scenarios:
            data["RYT.json"][parameter][scenario].append(
                land.year_row(
                    years,
                    value,
                    scenario,
                    TechId=ENV_WATER_TECH_ID,
                )
            )

    rytm_values = {**RYTM_FIXED_VALUES, "TAMUL": annual_upper}
    for parameter, value in rytm_values.items():
        for scenario in scenarios:
            for mode in modes:
                data["RYTM.json"][parameter][scenario].append(
                    land.year_row(
                        years,
                        value,
                        scenario,
                        TechId=ENV_WATER_TECH_ID,
                        MoId=mode,
                    )
                )

    for scenario in scenarios:
        for timeslice_id in audit["timeslice_ids"]:
            data["RYTTs.json"]["CF"][scenario].append(
                land.year_row(
                    years,
                    1,
                    scenario,
                    TechId=ENV_WATER_TECH_ID,
                    TsId=timeslice_id,
                )
            )

    for category, commodity in zip(WATER_CATEGORIES, audit["water_commodities"]):
        for scenario in scenarios:
            for mode in modes:
                data["RYTCM.json"]["IAR"][scenario].append(
                    land.year_row(
                        years,
                        1 if mode == category["mode"] else 0,
                        scenario,
                        TechId=ENV_WATER_TECH_ID,
                        CommId=commodity["CommId"],
                        MoId=mode,
                    )
                )


def build_generated_data(
    source: Path,
    audit: dict[str, Any],
) -> dict[str, Any]:
    data = {
        path.name: deepcopy(land.read_json(path))
        for path in sorted(source.glob("*.json"))
    }
    gen_data = data["genData.json"]
    gen_data["osy-casename"] = TARGET_CASE_NAME
    gen_data["osy-desc"] = (
        f"{gen_data.get('osy-desc', '').rstrip()} "
        "Diagnostic extension with an unforced ENV_WATER sink; its activity "
        "must be reconciled against the reporting-only reference."
    ).strip()
    gen_data["osy-date"] = date.today().isoformat()
    mode_dictionary = "; ".join(
        f"{row['mode']}={row['account']}" for row in WATER_CATEGORIES
    )
    gen_data["osy-tech"].append(
        {
            "TechId": ENV_WATER_TECH_ID,
            "Tech": ENV_WATER_TECH_NAME,
            "Desc": (
                "UNFORCED DIAGNOSTIC ONLY; not an authoritative water account. "
                f"Mode dictionary: {mode_dictionary}. Each mode consumes one "
                "water commodity at IAR 1, but no BAL_ENV_WATER constraint forces "
                "complete residual consumption."
            ),
            "CapUnitId": WATER_UNIT,
            "ActUnitId": WATER_UNIT,
            "TG": [audit["environment_group_id"]],
            "IAR": [row["CommId"] for row in audit["water_commodities"]],
            "OAR": [],
            "INCR": [],
            "ITCR": [],
            "EAR": [],
        }
    )
    append_terminal_parameters(data, audit)
    return data


def validate_generated_data(
    source: Path,
    generated: dict[str, Any],
    audit: dict[str, Any],
) -> dict[str, Any]:
    source_gen = land.read_json(source / "genData.json")
    gen_data = generated["genData.json"]
    expected_counts = {
        "technologies": len(source_gen["osy-tech"]) + 1,
        "commodities": len(source_gen["osy-comm"]),
        "constraints": len(source_gen["osy-constraints"]),
        "technology_groups": len(source_gen["osy-techGroups"]),
    }
    actual_counts = {
        "technologies": len(gen_data["osy-tech"]),
        "commodities": len(gen_data["osy-comm"]),
        "constraints": len(gen_data["osy-constraints"]),
        "technology_groups": len(gen_data["osy-techGroups"]),
    }
    if actual_counts != expected_counts:
        raise GenerationError(
            f"Generated counts differ: expected={expected_counts}, actual={actual_counts}"
        )
    if sum(row["Tech"] == ENV_WATER_TECH_NAME for row in gen_data["osy-tech"]) != 1:
        raise GenerationError("Expected exactly one ENV_WATER technology")
    if any(row["Con"] == "BAL_ENV_WATER" for row in gen_data["osy-constraints"]):
        raise GenerationError("The diagnostic case must not contain BAL_ENV_WATER")

    unchanged_files = {
        path.name for path in source.glob("*.json")
    } - {
        "genData.json",
        "RT.json",
        "RYT.json",
        "RYTM.json",
        "RYTTs.json",
        "RYTCM.json",
    }
    for filename in unchanged_files:
        if generated[filename] != land.read_json(source / filename):
            raise GenerationError(f"Unexpected change in {filename}")

    for filename in ("RYT.json", "RYTM.json", "RYTTs.json", "RYTCM.json"):
        source_data = land.read_json(source / filename)
        candidate_data = generated[filename]
        for parameter, scenarios in source_data.items():
            for scenario, rows in scenarios.items():
                if candidate_data[parameter][scenario][: len(rows)] != rows:
                    raise GenerationError(
                        f"Original rows changed in {filename}/{parameter}/{scenario}"
                    )

    source_rt = land.read_json(source / "RT.json")
    for parameter, scenarios in source_rt.items():
        for scenario, rows in scenarios.items():
            candidate = dict(generated["RT.json"][parameter][scenario][0])
            candidate.pop(ENV_WATER_TECH_ID, None)
            if candidate != rows[0]:
                raise GenerationError(
                    f"Original RT values changed in {parameter}/{scenario}"
                )

    source_tech_by_id = {row["TechId"]: row for row in source_gen["osy-tech"]}
    generated_tech_by_id = {row["TechId"]: row for row in gen_data["osy-tech"]}
    for technology_id, source_technology in source_tech_by_id.items():
        if generated_tech_by_id[technology_id] != source_technology:
            raise GenerationError(
                f"Unexpected metadata change on {source_technology['Tech']}"
            )

    years = audit["years"]
    modes = audit["modes"]
    scenarios = audit["scenarios"]
    water_by_mode = {
        category["mode"]: commodity["CommId"]
        for category, commodity in zip(
            WATER_CATEGORIES, audit["water_commodities"]
        )
    }
    for scenario in scenarios:
        rows = [
            row
            for row in generated["RYTCM.json"]["IAR"][scenario]
            if row["TechId"] == ENV_WATER_TECH_ID
        ]
        if len(rows) != len(WATER_CATEGORIES) * len(modes):
            raise GenerationError(
                f"Unexpected ENV_WATER IAR row count in {scenario}: {len(rows)}"
            )
        for row in rows:
            mode = int(row["MoId"])
            expected = 1 if water_by_mode.get(mode) == row["CommId"] else 0
            values = [row[year] for year in years]
            if scenario == BASE_SCENARIO:
                if values != [expected] * len(years):
                    raise GenerationError(
                        f"Incorrect ENV_WATER IAR in {scenario}: {row}"
                    )
            elif values != [None] * len(years):
                raise GenerationError(
                    f"ENV_WATER IAR does not inherit in {scenario}: {row}"
                )
        output_rows = [
            row
            for row in generated["RYTCM.json"]["OAR"][scenario]
            if row["TechId"] == ENV_WATER_TECH_ID
        ]
        if output_rows:
            raise GenerationError(f"ENV_WATER unexpectedly has output rows: {scenario}")

    active_modes = land.effective_nonzero_modes(
        generated["RYTCM.json"], ENV_WATER_TECH_ID, years
    )
    if active_modes != {1, 2, 3}:
        raise GenerationError(
            f"ENV_WATER active modes are {sorted(active_modes)}, expected 1-3"
        )
    for parameter in ("CAM", "CNCM", "CCM"):
        if any(
            row["TechId"] == ENV_WATER_TECH_ID
            for scenario in scenarios
            for row in generated["RYTCn.json"][parameter][scenario]
        ):
            raise GenerationError(f"ENV_WATER unexpectedly appears in {parameter}")

    return {
        "status": "PASS",
        "counts": actual_counts,
        "terminal": ENV_WATER_TECH_NAME,
        "terminal_role": "unforced diagnostic; not authoritative",
        "terminal_modes": sorted(active_modes),
        "balance_constraint": None,
        "water_commodities": [
            {
                "mode": category["mode"],
                "account": category["account"],
                "commodity": category["commodity"],
                "unit": WATER_UNIT,
            }
            for category in WATER_CATEGORIES
        ],
        "water_producers": audit["producer_names"],
        "annual_production_envelope_by_year": audit["annual_envelopes"],
        "annual_terminal_activity_upper_bound": audit["annual_upper"],
        "model_period_terminal_activity_upper_bound": audit[
            "model_period_upper"
        ],
        "authoritative_reference": (
            "production minus use by every technology except ENV_WATER"
        ),
    }


def update_res_data(res_data: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(res_data)
    for run in result.get("osy-cases", []):
        run["CaseId"] = f"{run['CaseId']}_ENVWATERDIAG"
        run["Desc"] = (
            f"{run.get('Desc', '').rstrip()} "
            "Unforced ENV_WATER diagnostic; reconcile against the external ledger."
        ).strip()
        run["Runtime"] = date.today().isoformat()
    return result


def materialize_stage(
    source: Path,
    target: Path,
    generated: dict[str, Any],
    generation_record: dict[str, Any],
) -> Path:
    stage = Path(
        tempfile.mkdtemp(prefix=f".{target.name}.stage.", dir=target.parent)
    )
    try:
        for filename, data in generated.items():
            land.write_json(stage / filename, data)
        (stage / "view").mkdir()
        for filename in SELECTED_VIEW_FILES:
            source_file = source / "view" / filename
            if filename == "resData.json":
                land.write_json(
                    stage / "view" / filename,
                    update_res_data(land.read_json(source_file)),
                )
            else:
                shutil.copy2(source_file, stage / "view" / filename)
        (stage / "documentation").mkdir()
        (stage / "README.md").write_text(DERIVED_README, encoding="utf-8")
        (stage / "documentation" / "README.md").write_text(
            DERIVED_DOCUMENTATION_README,
            encoding="utf-8",
        )
        land.write_json(stage / "documentation" / "generation.json", generation_record)
        for run in land.read_json(stage / "view" / "resData.json").get(
            "osy-cases", []
        ):
            (stage / "res" / run["Case"] / "csv").mkdir(parents=True)
        return stage
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    source, target = resolve_paths(args.source, args.target)
    source_before = land.manifest(source)
    audit = audit_source(source)
    generated = build_generated_data(source, audit)
    validation = validate_generated_data(source, generated, audit)
    source_after = land.manifest(source)
    if source_before != source_after:
        raise GenerationError("Source case changed during generation")

    result = {
        "status": "PASS",
        "dry_run": args.dry_run,
        "source": str(source),
        "target": str(target),
        "source_file_count": len(source_before),
        "source_manifest_digest": land.manifest_digest(source_before),
        "source_manifest": source_before,
        "validation": validation,
    }
    if args.dry_run:
        print(json.dumps(result, indent=2))
        return

    stage = materialize_stage(source, target, generated, result)
    try:
        backup = land.promote(stage, target, args.overwrite)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        raise
    result["backup"] = str(backup) if backup is not None else None
    result["target_file_count"] = len(land.manifest(target))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
