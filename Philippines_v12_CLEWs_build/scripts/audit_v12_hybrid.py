#!/usr/bin/env python3
"""Audit v10 preservation, v12 nexus connections, and non-forcing rules."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from build_v12_hybrid import (
    RAW_TO_V10_COMMODITY,
    RETIRED_COMM_NAMES,
    RETIRED_TECH_NAMES,
    raw_tech_selected,
)


ID_FIELDS = (
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


def load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def dump(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def canonical_hash(data: Any) -> str:
    encoded = json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def row_key(row: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple((field, row[field]) for field in ID_FIELDS if field in row)


def parameter_preservation(
    source: Path,
    destination: Path,
    retired_tech_ids: set[str],
    retired_comm_ids: set[str],
) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    checked_rows = 0
    checked_scalar_values = 0

    for source_path in sorted(source.glob("*.json")):
        if source_path.name == "genData.json":
            continue
        target_path = destination / source_path.name
        if not target_path.exists():
            mismatches.append(
                {"file": source_path.name, "issue": "missing destination file"}
            )
            continue
        source_data = load(source_path)
        target_data = load(target_path)
        for parameter, source_scenarios in source_data.items():
            if parameter not in target_data:
                mismatches.append(
                    {
                        "file": source_path.name,
                        "parameter": parameter,
                        "issue": "missing parameter",
                    }
                )
                continue
            for scenario, source_rows in source_scenarios.items():
                target_rows = target_data[parameter].get(scenario)
                if target_rows is None:
                    mismatches.append(
                        {
                            "file": source_path.name,
                            "parameter": parameter,
                            "scenario": scenario,
                            "issue": "missing scenario",
                        }
                    )
                    continue
                target_by_key = {
                    row_key(row): row
                    for row in target_rows
                    if isinstance(row, dict) and row_key(row)
                }
                for source_row in source_rows:
                    if not isinstance(source_row, dict):
                        continue
                    if source_row.get("TechId") in retired_tech_ids:
                        continue
                    if source_row.get("CommId") in retired_comm_ids:
                        continue
                    key = row_key(source_row)
                    if key:
                        checked_rows += 1
                        target_row = target_by_key.get(key)
                        if target_row != source_row:
                            mismatches.append(
                                {
                                    "file": source_path.name,
                                    "parameter": parameter,
                                    "scenario": scenario,
                                    "key": list(key),
                                    "issue": "record changed or missing",
                                }
                            )
                        continue
                    if len(source_rows) != 1 or len(target_rows) != 1:
                        mismatches.append(
                            {
                                "file": source_path.name,
                                "parameter": parameter,
                                "scenario": scenario,
                                "issue": "unkeyed record shape changed",
                            }
                        )
                        continue
                    target_row = target_rows[0]
                    for field, value in source_row.items():
                        if field in retired_tech_ids:
                            continue
                        checked_scalar_values += 1
                        if target_row.get(field) != value:
                            mismatches.append(
                                {
                                    "file": source_path.name,
                                    "parameter": parameter,
                                    "scenario": scenario,
                                    "field": field,
                                    "issue": "scalar value changed or missing",
                                }
                            )

    return {
        "status": "PASS" if not mismatches else "FAIL",
        "checked_dimensioned_records": checked_rows,
        "checked_scalar_values": checked_scalar_values,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:100],
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def positive_equal_locks(csv_dir: Path, selected_names: set[str]) -> list[dict[str, Any]]:
    pairs = (
        (
            "TotalTechnologyAnnualActivityLowerLimit.csv",
            "TotalTechnologyAnnualActivityUpperLimit.csv",
        ),
        (
            "TechnologyActivityByModeLowerLimit.csv",
            "TechnologyActivityByModeUpperLimit.csv",
        ),
        ("TotalAnnualMinCapacity.csv", "TotalAnnualMaxCapacity.csv"),
        (
            "TotalAnnualMinCapacityInvestment.csv",
            "TotalAnnualMaxCapacityInvestment.csv",
        ),
    )
    locks: list[dict[str, Any]] = []
    for lower_name, upper_name in pairs:
        lower_rows = [
            row
            for row in read_csv(csv_dir / lower_name)
            if row.get("TECHNOLOGY") in selected_names
        ]
        upper_rows = [
            row
            for row in read_csv(csv_dir / upper_name)
            if row.get("TECHNOLOGY") in selected_names
        ]
        if not lower_rows or not upper_rows:
            continue
        dimensions = [
            field for field in lower_rows[0] if field not in {"REGION", "VALUE"}
        ]
        upper = {
            tuple(row[field] for field in dimensions): float(row["VALUE"])
            for row in upper_rows
        }
        for row in lower_rows:
            key = tuple(row[field] for field in dimensions)
            lower_value = float(row["VALUE"])
            upper_value = upper.get(key)
            if (
                lower_value > 0
                and upper_value is not None
                and math.isclose(lower_value, upper_value, abs_tol=1e-12)
            ):
                locks.append(
                    {
                        "lower": lower_name,
                        "upper": upper_name,
                        "index": dict(zip(dimensions, key)),
                        "value": lower_value,
                    }
                )
    return locks


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    build = repo / "Philippines_v12_CLEWs_build"
    source = repo / "WebAPP/DataStorage/Philippines_v10"
    destination = repo / "WebAPP/DataStorage/Philippines_v12"
    csv_dir = build / "model/inputs/clewsy"

    old_gen = load(source / "genData.json")
    new_gen = load(destination / "genData.json")
    raw_gen = load(repo / "WebAPP/DataStorage/Philippines_v12_raw_CLEWs/genData.json")

    old_tech_by_name = {item["Tech"]: item for item in old_gen["osy-tech"]}
    old_comm_by_name = {item["Comm"]: item for item in old_gen["osy-comm"]}
    new_tech_by_name = {item["Tech"]: item for item in new_gen["osy-tech"]}
    new_comm_by_name = {item["Comm"]: item for item in new_gen["osy-comm"]}
    raw_tech_by_name = {item["Tech"]: item for item in raw_gen["osy-tech"]}

    retired_tech_ids = {
        old_tech_by_name[name]["TechId"] for name in RETIRED_TECH_NAMES
    }
    retired_comm_ids = {
        old_comm_by_name[name]["CommId"] for name in RETIRED_COMM_NAMES
    }
    retained_tech_names = sorted(set(old_tech_by_name) - RETIRED_TECH_NAMES)
    retained_comm_names = sorted(set(old_comm_by_name) - RETIRED_COMM_NAMES)

    changed_techs = [
        name
        for name in retained_tech_names
        if new_tech_by_name.get(name) != old_tech_by_name[name]
    ]
    changed_comms = [
        name
        for name in retained_comm_names
        if new_comm_by_name.get(name) != old_comm_by_name[name]
    ]
    fisheries_names = sorted(
        name
        for name in retained_tech_names
        if name.startswith("PHL_FSH_") or name == "PHL_POW_TD_FSH"
    )

    preserved_parameter_records = parameter_preservation(
        source, destination, retired_tech_ids, retired_comm_ids
    )

    selected_names = {
        name for name in raw_tech_by_name if raw_tech_selected(name)
    }
    locks = positive_equal_locks(csv_dir, selected_names)
    tamll_rows = [
        row
        for row in read_csv(csv_dir / "TechnologyActivityByModeLowerLimit.csv")
        if row["TECHNOLOGY"] in selected_names
    ]
    positive_tamll = [row for row in tamll_rows if float(row["VALUE"]) > 0]

    new_tech_ids = {
        new_tech_by_name[name]["TechId"] for name in selected_names
    }
    new_comm_ids = {
        item["CommId"]
        for item in new_gen["osy-comm"]
        if item["Comm"] not in old_comm_by_name
    }
    nonbase_nonnull: list[dict[str, Any]] = []
    for path in destination.glob("*.json"):
        if path.name == "genData.json":
            continue
        data = load(path)
        for parameter, scenario_data in data.items():
            for scenario, rows in scenario_data.items():
                if scenario == "SC_0":
                    continue
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    if (
                        row.get("TechId") not in new_tech_ids
                        and row.get("CommId") not in new_comm_ids
                    ):
                        continue
                    values = [
                        value
                        for field, value in row.items()
                        if field not in ID_FIELDS
                    ]
                    if any(value is not None for value in values):
                        nonbase_nonnull.append(
                            {
                                "file": path.name,
                                "parameter": parameter,
                                "scenario": scenario,
                                "key": list(row_key(row)),
                            }
                        )

    constraints_with_new_tech = [
        {
            "constraint": constraint["Con"],
            "technologies": sorted(set(constraint["CM"]) & new_tech_ids),
        }
        for constraint in new_gen["osy-constraints"]
        if set(constraint["CM"]) & new_tech_ids
    ]

    groundwater = new_tech_by_name["DEMAGRGWTPHL"]
    surface = new_tech_by_name["DEMAGRSURPHL"]
    expected_connections = {
        raw: old_comm_by_name[v10]["CommId"]
        for raw, v10 in RAW_TO_V10_COMMODITY.items()
    }
    connectivity = {
        "mapped_commodity_ids": expected_connections,
        "groundwater_irrigation_uses_agricultural_electricity": (
            old_comm_by_name["PHL_AGR_ELE"]["CommId"] in groundwater["IAR"]
        ),
        "surface_irrigation_uses_inherited_surface_water": (
            old_comm_by_name["PHL_WTR_SUR"]["CommId"] in surface["IAR"]
        ),
        "cluster_outputs_feed_inherited_groundwater": all(
            old_comm_by_name["PHL_WTR_GWT"]["CommId"]
            in new_tech_by_name[f"LNDAGRPHLC{cluster:02d}"]["OAR"]
            for cluster in range(1, 9)
        ),
        "cluster_outputs_feed_inherited_surface_water": all(
            old_comm_by_name["PHL_WTR_SUR"]["CommId"]
            in new_tech_by_name[f"LNDAGRPHLC{cluster:02d}"]["OAR"]
            for cluster in range(1, 9)
        ),
    }

    report = {
        "overall_status": "PASS",
        "preservation": {
            "retained_v10_technology_count": len(retained_tech_names),
            "changed_retained_technology_definitions": changed_techs,
            "retained_v10_commodity_count": len(retained_comm_names),
            "changed_retained_commodity_definitions": changed_comms,
            "all_retained_technology_hash": canonical_hash(
                [old_tech_by_name[name] for name in retained_tech_names]
            ),
            "fisheries_technology_count": len(fisheries_names),
            "fisheries_technology_names": fisheries_names,
            "fisheries_hash": canonical_hash(
                [old_tech_by_name[name] for name in fisheries_names]
            ),
            "parameter_records": preserved_parameter_records,
        },
        "new_nexus_non_forcing": {
            "new_technology_count": len(selected_names),
            "positive_lower_equals_upper_lock_count": len(locks),
            "positive_lower_equals_upper_locks": locks,
            "technology_activity_by_mode_lower_limit_rows": len(tamll_rows),
            "positive_landcover_minimum_rows": len(positive_tamll),
            "note": (
                "Positive mode lower limits are upstream structural minimum "
                "built-up/water land-cover shares; none equals an upper limit."
            ),
            "new_technology_udc_memberships": constraints_with_new_tech,
            "nonbase_override_value_count": len(nonbase_nonnull),
            "nonbase_override_values": nonbase_nonnull[:100],
        },
        "connectivity": connectivity,
    }

    failures = []
    if changed_techs:
        failures.append("retained technology definitions changed")
    if changed_comms:
        failures.append("retained commodity definitions changed")
    if preserved_parameter_records["status"] != "PASS":
        failures.append("retained parameter records changed")
    if locks:
        failures.append("new nexus contains positive equality locks")
    if constraints_with_new_tech:
        failures.append("new nexus was added to inherited UDCs")
    if nonbase_nonnull:
        failures.append("new nexus contains scenario overrides")
    if not all(connectivity[key] for key in connectivity if key != "mapped_commodity_ids"):
        failures.append("a required nexus connection is absent")
    if failures:
        report["overall_status"] = "FAIL"
        report["failures"] = failures

    dump(build / "diagnostics/v12_hybrid_audit.json", report)
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
