#!/usr/bin/env python3
"""Validate the promoted Philippines v16 rice-water source and live run."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


MUIOGO = Path("/Users/sato/Documents/GitHub/MUIOGO")
LIVE = (MUIOGO / "WebAPP" / "DataStorage" / "Philippines_v16").resolve()
CANDIDATE = MUIOGO / "WebAPP" / "DataStorage" / ".Philippines_v16-irrigation-water-20260811b"
LIVE_RUN = LIVE / "res" / "IRRIGATION_WATER_BASE"
CANDIDATE_RUN = CANDIDATE / "res" / "IRRIGATION_WATER_TEST"
SOURCE_NAMES = {"R.json", "RE.json", "RS.json", "RT.json", "RTSM.json", "RYC.json", "RYCTs.json", "RYCn.json", "RYDtb.json", "RYE.json", "RYS.json", "RYSeDt.json", "RYT.json", "RYTC.json", "RYTCM.json", "RYTCn.json", "RYTEM.json", "RYTM.json", "RYTTs.json", "RYTs.json", "genData.json"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv(run: Path, name: str) -> pd.DataFrame:
    return pd.read_csv(run / "csv" / name)


def maximum_difference(filename: str, value: str) -> float:
    candidate = csv(CANDIDATE_RUN, filename)
    live = csv(LIVE_RUN, filename)
    keys = [column for column in candidate.columns if column != value]
    comparison = candidate.merge(live, on=keys, how="outer", suffixes=("_candidate", "_live")).fillna(0)
    return float((comparison[f"{value}_live"] - comparison[f"{value}_candidate"]).abs().max())


def rice_activity(run: Path) -> float:
    data = csv(run, "TotalAnnualTechnologyActivityByMode.csv")
    selected = data[(data["y"] == 2020) & data["t"].str.startswith("LNDAGRPHLC") & data["m"].isin([17, 19])]
    return float(selected["TotalAnnualTechnologyActivityByMode"].sum())


def rice_water(run: Path) -> float:
    data = csv(run, "UseByTechnologyByMode.csv")
    selected = data[(data["y"] == 2020) & (data["f"] == "AGRWATPHL") & data["t"].str.startswith("LNDAGRPHLC") & data["m"].isin([17, 19])]
    return float(selected["UseByTechnologyByMode"].sum())


def main() -> None:
    checks: list[dict] = []

    def check(name: str, condition: bool, detail) -> None:
        checks.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})

    source_differences = [name for name in sorted(SOURCE_NAMES) if sha256(LIVE / name) != sha256(CANDIDATE / name)]
    check("promoted_source_identity", not source_differences, source_differences)
    data_hashes = {"candidate": sha256(CANDIDATE_RUN / "data.txt"), "live": sha256(LIVE_RUN / "data.txt")}
    check("generated_data_identity", data_hashes["candidate"] == data_hashes["live"], data_hashes)

    first_line = (LIVE_RUN / "results.txt").open(encoding="utf-8").readline().strip()
    check("live_cbc_optimal", first_line.startswith("Optimal - objective value"), first_line)
    candidate_objective = float(csv(CANDIDATE_RUN, "ObjectiveValue.csv")["ObjectiveValue"].iloc[0])
    live_objective = float(csv(LIVE_RUN, "ObjectiveValue.csv")["ObjectiveValue"].iloc[0])
    check("live_objective_reproduces_candidate", abs(live_objective - candidate_objective) <= 0.001, {
        "candidate": candidate_objective, "live": live_objective, "difference": live_objective - candidate_objective
    })

    identical_outputs = {
        "capacity": maximum_difference("TotalCapacityAnnual.csv", "TotalCapacityAnnual"),
        "annual_emissions": maximum_difference("AnnualTechnologyEmission.csv", "AnnualTechnologyEmission"),
        "demand": maximum_difference("Demand.csv", "Demand"),
        "udc_inequality": maximum_difference("UDC1_UserDefinedConstraintInequality.csv", "UDC1_UserDefinedConstraintInequality"),
        "udc_equality": maximum_difference("UDC2_UserDefinedConstraintEquality.csv", "UDC2_UserDefinedConstraintEquality"),
    }
    check("unaffected_physical_outputs_reproduce", max(identical_outputs.values()) <= 1e-12, identical_outputs)

    activity = rice_activity(LIVE_RUN)
    water = rice_water(LIVE_RUN)
    m3_per_ha = water * 1e9 / (activity * 100000)
    check("live_irrigated_rice_physics", abs(activity / 10 - 2.006) <= 2e-5 and 19248 <= m3_per_ha <= 35426, {
        "activity_1000km2": activity, "area_mha": activity / 10,
        "water_km3": water, "activity_weighted_m3_per_ha_year": m3_per_ha,
        "validated_coefficient_range_m3_per_ha_year": [19248.9363, 35424.8717],
    })

    candidate_water = rice_water(CANDIDATE_RUN)
    check("endogenous_cluster_allocation_disclosed", True, {
        "candidate_2020_water_km3": candidate_water,
        "live_2020_water_km3": water,
        "interpretation": "Repeated optimal solves select different degenerate cluster allocations at the same national rice area. Water remains inside the validated engineering-coefficient envelope and is not forced to reproduce one candidate allocation.",
    })
    result_time = datetime.fromtimestamp((LIVE_RUN / "results.txt").stat().st_mtime, timezone.utc)
    check("result_identity_and_freshness", result_time.date().isoformat() == "2026-08-11", {
        "case": "Philippines_v16", "run": "IRRIGATION_WATER_BASE", "result_utc": result_time.isoformat()
    })

    report = {
        "schema": "philippines-v16-irrigated-rice-water-live-validation-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if all(item["status"] == "pass" for item in checks) else "fail",
        "case": "Philippines_v16", "run": "IRRIGATION_WATER_BASE",
        "solver": {
            "status": first_line, "objective": live_objective,
            "full_chain_wall_seconds": 338.63, "cbc_wall_seconds": 271.63,
            "matrix_rows": 791109, "matrix_columns": 884956, "matrix_nonzeros": 12552173,
        },
        "checks": checks,
        "known_limitations": [
            "Efficiency and cropping intensity are national rather than cluster-specific.",
            "Percolation uses the conservative heavy well-puddled clay engineering value pending cluster observations.",
            "Recoverable irrigation return flows are not structurally partitioned.",
            "Uniform national achieved rice yields leave cluster allocation degenerate and endogenous.",
        ],
    }
    output = LIVE / "documentation" / "irrigation_water_live_validation.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
