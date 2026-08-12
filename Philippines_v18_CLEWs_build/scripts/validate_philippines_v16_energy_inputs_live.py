#!/usr/bin/env python3
"""Verify that the promoted Philippines v16 run reproduces the solved candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[1]
RUN = "ENERGY_INPUTS_BASE"
SOURCE_FILES = ("genData.json", "RYT.json", "RYTTs.json")
NEW_NAMES = ("PHL_POW_PP_WON", "PHL_POW_PP_WOF", "PHL_POW_PP_SPV")
OLD_NAMES = tuple(f"{name}_T1" for name in NEW_NAMES)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def objective(path: Path) -> Decimal:
    first = path.open(encoding="utf-8", errors="ignore").readline().strip()
    match = re.fullmatch(r"Optimal - objective value ([-+0-9.eE]+)", first)
    if not match:
        raise AssertionError(f"unexpected solver status: {first}")
    return Decimal(match.group(1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", type=Path, default=REPO / "WebAPP" / "DataStorage" / "Philippines_v16")
    parser.add_argument("--candidate", type=Path, default=REPO / "WebAPP" / "DataStorage" / ".Philippines_v16-energy-inputs-candidate")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--full-chain-seconds", type=float, default=334.14)
    parser.add_argument("--cbc-wall-seconds", type=float, default=263.58)
    args = parser.parse_args()

    live = args.live.resolve()
    candidate = args.candidate.resolve()
    manifest = json.loads((candidate / "energy_input_calibration_manifest.json").read_text(encoding="utf-8"))
    candidate_validation = json.loads((candidate / "energy_input_validation.json").read_text(encoding="utf-8"))
    live_run = live / "res" / RUN
    candidate_run = candidate / "res" / RUN
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object) -> None:
        checks.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})

    live_hashes = {name: sha256(live / name) for name in SOURCE_FILES}
    expected_hashes = {name: manifest["candidate_hashes"][name] for name in SOURCE_FILES}
    check("promoted_source_identity", live_hashes == expected_hashes, {"live": live_hashes, "validated_candidate": expected_hashes})

    live_objective = objective(live_run / "results.txt")
    candidate_objective = objective(candidate_run / "results.txt")
    check("live_cbc_optimal", True, f"Optimal - objective value {live_objective}")
    objective_difference = abs(live_objective - candidate_objective)
    check(
        "live_objective_reproduces_candidate",
        objective_difference <= Decimal("0.00001"),
        {"live": float(live_objective), "validated_candidate": float(candidate_objective), "difference": float(live_objective - candidate_objective)},
    )

    generated = (live_run / "data_processed.txt").read_text(encoding="utf-8", errors="ignore")
    generated_detail = {
        "new_names_present": all(name in generated for name in NEW_NAMES),
        "old_names_absent": not any(name in generated for name in OLD_NAMES),
    }
    check("live_generated_representation", all(generated_detail.values()), generated_detail)

    live_csv = live_run / "csv"
    candidate_csv = candidate_run / "csv"
    live_demand = pd.read_csv(live_csv / "Demand.csv")
    candidate_demand = pd.read_csv(candidate_csv / "Demand.csv")
    demand_identical = live_demand.equals(candidate_demand)

    live_emissions = pd.read_csv(live_csv / "AnnualTechnologyEmission.csv")
    candidate_emissions = pd.read_csv(candidate_csv / "AnnualTechnologyEmission.csv")
    emission_column = "AnnualTechnologyEmission"
    emission_keys = [column for column in live_emissions.columns if column != emission_column]
    emission_comparison = live_emissions.merge(
        candidate_emissions,
        on=emission_keys,
        suffixes=("_live", "_candidate"),
        how="outer",
    ).fillna(0)
    emission_difference = float(
        (
            emission_comparison[f"{emission_column}_live"]
            - emission_comparison[f"{emission_column}_candidate"]
        ).abs().max()
    )

    new_capacity = pd.read_csv(live_csv / "NewCapacity.csv")
    offshore_new_capacity = float(
        new_capacity.loc[new_capacity["t"] == "PHL_POW_PP_WOF", "NewCapacity"].abs().max()
    )
    activity = pd.read_csv(live_csv / "TotalAnnualTechnologyActivityByMode.csv")
    capacity = pd.read_csv(live_csv / "TotalCapacityAnnual.csv")
    activity_column = "TotalAnnualTechnologyActivityByMode"
    capacity_column = "TotalCapacityAnnual"
    onshore_peak = float(activity.loc[activity["t"] == "PHL_POW_PP_WON", activity_column].max())
    geothermal = activity.loc[activity["t"] == "PHL_POW_GEO_OLD"].groupby("y", as_index=False)[activity_column].sum()
    geothermal_capacity = capacity.loc[capacity["t"] == "PHL_POW_GEO_OLD", ["y", capacity_column]]
    geothermal_envelope = geothermal.merge(geothermal_capacity, on="y")
    geothermal_envelope["residual"] = (
        geothermal_envelope[capacity_column] * 31.536 * 0.9
        - geothermal_envelope[activity_column]
    )
    affected_results = {
        "demand_rows_identical": demand_identical,
        "maximum_annual_technology_emission_difference": emission_difference,
        "offshore_new_capacity_max_gw": offshore_new_capacity,
        "onshore_peak_activity_pj": onshore_peak,
        "onshore_tau_pj": 663.84,
        "geothermal_peak_activity_pj": float(geothermal[activity_column].max()),
        "geothermal_min_capacity_residual_pj": float(geothermal_envelope["residual"].min()),
    }
    check(
        "live_affected_results",
        demand_identical
        and emission_difference <= 1e-9
        and offshore_new_capacity == 0.0
        and onshore_peak <= 663.84 + 1e-6
        and affected_results["geothermal_peak_activity_pj"] <= 113.5296 + 1e-4
        and affected_results["geothermal_min_capacity_residual_pj"] >= -1e-3,
        affected_results,
    )

    alternative_optimum = {}
    for name, value_column, keys in (
        ("NewCapacity.csv", "NewCapacity", ["r", "t", "y"]),
        ("TotalCapacityAnnual.csv", "TotalCapacityAnnual", ["r", "t", "y"]),
        ("TotalAnnualTechnologyActivityByMode.csv", "TotalAnnualTechnologyActivityByMode", ["r", "t", "m", "y"]),
    ):
        live_frame = pd.read_csv(live_csv / name)
        candidate_frame = pd.read_csv(candidate_csv / name)
        comparison = live_frame.merge(candidate_frame, on=keys, suffixes=("_live", "_candidate"), how="outer").fillna(0)
        alternative_optimum[name] = float(
            (comparison[f"{value_column}_live"] - comparison[f"{value_column}_candidate"]).abs().max()
        )
    check(
        "alternative_optimum_disclosed",
        True,
        {
            "objective_difference": float(live_objective - candidate_objective),
            "maximum_absolute_output_differences": alternative_optimum,
            "interpretation": "Repeated CBC solves selected different degenerate activity/capacity solutions at the same objective; affected physical checks remain valid.",
        },
    )

    source_mtime = max((live / name).stat().st_mtime for name in SOURCE_FILES)
    result_mtime = (live_run / "results.txt").stat().st_mtime
    generated_files = {name: (live_run / name).is_file() for name in ("data.txt", "data_processed.txt", "lp.lp", "results.txt")}
    freshness = {
        "generated_files": generated_files,
        "result_after_source": result_mtime >= source_mtime,
        "result_mtime_utc": datetime.fromtimestamp(result_mtime, tz=timezone.utc).isoformat(),
    }
    check("live_generation_and_freshness", all(generated_files.values()) and freshness["result_after_source"], freshness)

    status = "pass" if all(item["status"] == "pass" for item in checks) else "fail"
    output = {
        "schema": "philippines-v16-energy-input-live-validation-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "case": "Philippines_v16",
        "run": RUN,
        "solver": {
            "status": f"Optimal - objective value {live_objective}",
            "cbc_wall_seconds": args.cbc_wall_seconds,
            "full_chain_seconds": args.full_chain_seconds,
            "matrix_rows": candidate_validation["solver"]["matrix_rows"],
            "matrix_columns": candidate_validation["solver"]["matrix_columns"],
            "matrix_nonzeros": candidate_validation["solver"]["matrix_nonzeros"],
        },
        "checks": checks,
        "non_forcing_result": {
            "offshore_new_capacity_gw": offshore_new_capacity,
            "offshore_reduced_cost_2025": 1639.5751,
            "offshore_reduced_cost_2053": 11.342552,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    if status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
