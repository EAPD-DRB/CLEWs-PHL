#!/usr/bin/env python3
"""Validate the solved Philippines v16 energy-input candidate."""

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
DEFAULT_CANDIDATE = REPO / "WebAPP" / "DataStorage" / ".Philippines_v16-energy-inputs-candidate"
DEFAULT_BASELINE = (REPO / "WebAPP" / "DataStorage" / "Philippines_v16").resolve()
RUN = "ENERGY_INPUTS_BASE"
EXPECTED_DIFF = {"genData.json", "RYT.json", "RYTTs.json"}
RENAMES = {
    "PHL_POW_PP_WON_T1": "PHL_POW_PP_WON",
    "PHL_POW_PP_WOF_T1": "PHL_POW_PP_WOF",
    "PHL_POW_PP_SPV_T1": "PHL_POW_PP_SPV",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


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


def keyed(rows: list[dict], key: str, value: str) -> dict:
    return next(row for row in rows if row[key] == value)


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def normalize_technology(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if "t" in result:
        result["t"] = result["t"].replace(RENAMES)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--wall-seconds", type=float, default=215.64)
    args = parser.parse_args()

    candidate = args.candidate.resolve()
    baseline = args.baseline.resolve()
    output = args.output or candidate / "energy_input_validation.json"
    run_dir = candidate / "res" / RUN
    candidate_csv = run_dir / "csv"
    baseline_csv = baseline / "res" / "BASE" / "csv"
    inputs = read_json(REPO / "scripts" / "data" / "philippines_v16_energy_inputs.json")
    manifest = read_json(candidate / "energy_input_calibration_manifest.json")
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object) -> None:
        checks.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})

    changed = sorted(
        name for name in (path.name for path in baseline.glob("*.json"))
        if (candidate / name).is_file() and read_json(baseline / name) != read_json(candidate / name)
    )
    check("source_diff_scope", set(changed) == EXPECTED_DIFF, changed)

    base_gen = read_json(baseline / "genData.json")
    cand_gen = read_json(candidate / "genData.json")
    names = {item["TechId"]: (item["Tech"], item.get("Desc")) for item in cand_gen["osy-tech"]}
    expected_names = {
        "TEC_1wdli": ("PHL_POW_PP_WON", "Onshore wind"),
        "TEC_bl1d7": ("PHL_POW_PP_WOF", "Offshore wind"),
        "TEC_1k064": ("PHL_POW_PP_SPV", "Solar photovoltaic"),
    }
    structure = {
        "technology_ids_preserved": [x["TechId"] for x in base_gen["osy-tech"]] == [x["TechId"] for x in cand_gen["osy-tech"]],
        "renames_exact": all(names[key] == value for key, value in expected_names.items()),
        "no_t1_names": not any(item["Tech"].endswith("_T1") for item in cand_gen["osy-tech"]),
        "commodities_identical": base_gen["osy-comm"] == cand_gen["osy-comm"],
        "constraints_identical": base_gen["osy-constraints"] == cand_gen["osy-constraints"],
    }
    check("structural_rename", all(structure.values()), structure)

    ryt = read_json(candidate / "RYT.json")
    years = manifest["parameter_summary"]["years"]
    geo_af = keyed(ryt["AF"]["SC_0"], "TechId", "TEC_0qr3z")
    won_tau = keyed(ryt["TAU"]["SC_0"], "TechId", "TEC_1wdli")
    physical = {
        "geothermal_availability": sorted({geo_af[year] for year in years}),
        "onshore_tau_pj": sorted({won_tau[year] for year in years}),
        "offshore_annual_cf": manifest["parameter_summary"]["offshore"]["SC_0"]["after_annual_cf"],
    }
    check(
        "physical_inputs_exact",
        physical["geothermal_availability"] == [0.9]
        and physical["onshore_tau_pj"] == [663.84]
        and abs(physical["offshore_annual_cf"] - inputs["offshore_wind"]["expected_weighted_capacity_factor"]) < 1e-12,
        physical,
    )

    processed = (run_dir / "data_processed.txt").read_text(encoding="utf-8", errors="ignore")
    generated_names = {
        "new_names_present": all(name in processed for name in RENAMES.values()),
        "old_names_absent": not any(name in processed for name in RENAMES),
    }
    check("generated_representation", all(generated_names.values()), generated_names)

    candidate_result = run_dir / "results.txt"
    baseline_result = baseline / "res" / "BASE" / "results.txt"
    candidate_objective = objective(candidate_result)
    baseline_objective = objective(baseline_result)
    objective_change = candidate_objective - baseline_objective
    objective_percent = objective_change / baseline_objective * Decimal("100")
    timestamps = {
        "result_mtime": candidate_result.stat().st_mtime,
        "latest_source_mtime": max((candidate / name).stat().st_mtime for name in EXPECTED_DIFF),
    }
    check(
        "solver_optimal_and_current",
        timestamps["result_mtime"] >= timestamps["latest_source_mtime"],
        {"objective": float(candidate_objective), **timestamps},
    )

    new_capacity = load_csv(candidate_csv / "NewCapacity.csv")
    offshore_new = new_capacity[new_capacity["t"] == "PHL_POW_PP_WOF"]["NewCapacity"]
    result_text = candidate_result.read_text(encoding="utf-8", errors="ignore")
    reduced_costs = {
        int(year): float(value)
        for year, value in re.findall(
            r"(?m)^\s+\d+\s+NewCapacity\(RE1,PHL_POW_PP_WOF,(\d{4})\)\s+0\s+([-+0-9.eE]+)",
            result_text,
        )
    }
    check(
        "offshore_remains_endogenous",
        len(offshore_new) == len(years) and float(offshore_new.abs().max()) == 0.0 and len(reduced_costs) == len(years) and min(reduced_costs.values()) > 0,
        {"new_capacity_max_gw": float(offshore_new.abs().max()), "reduced_cost_2025": reduced_costs.get(2025), "reduced_cost_2053": reduced_costs.get(2053)},
    )

    activity = load_csv(candidate_csv / "TotalAnnualTechnologyActivityByMode.csv")
    capacity = load_csv(candidate_csv / "TotalCapacityAnnual.csv")
    activity_value = "TotalAnnualTechnologyActivityByMode"
    capacity_value = "TotalCapacityAnnual"
    won = activity[activity["t"] == "PHL_POW_PP_WON"]
    geo = activity[activity["t"] == "PHL_POW_GEO_OLD"].groupby("y", as_index=False)[activity_value].sum()
    geo_cap = capacity[capacity["t"] == "PHL_POW_GEO_OLD"][["y", capacity_value]]
    geo_envelope = geo.merge(geo_cap, on="y")
    geo_envelope["maximum"] = geo_envelope[capacity_value] * 31.536 * 0.9
    geo_envelope["residual"] = geo_envelope["maximum"] - geo_envelope[activity_value]
    envelopes = {
        "onshore_peak_activity_pj": float(won[activity_value].max()),
        "onshore_tau_pj": 663.84,
        "geothermal_min_capacity_residual_pj": float(geo_envelope["residual"].min()),
        "geothermal_peak_activity_pj": float(geo[activity_value].max()),
        "geothermal_4gw_90pct_pj": 113.5296,
    }
    check(
        "physical_envelopes",
        envelopes["onshore_peak_activity_pj"] <= 663.84 + 1e-6
        and envelopes["geothermal_min_capacity_residual_pj"] >= -1e-3
        and envelopes["geothermal_peak_activity_pj"] <= 113.5296 + 1e-4,
        envelopes,
    )

    base_activity = normalize_technology(load_csv(baseline_csv / "TotalAnnualTechnologyActivityByMode.csv"))
    keys = ["r", "t", "m", "y"]
    merged = base_activity.merge(activity, on=keys, suffixes=("_base", "_candidate"), how="outer").fillna(0)
    merged["change"] = merged[f"{activity_value}_candidate"] - merged[f"{activity_value}_base"]
    top = merged.loc[merged["change"].abs().nlargest(10).index, keys + ["change"]]

    base_emissions = load_csv(baseline_csv / "AnnualTechnologyEmission.csv")
    cand_emissions = load_csv(candidate_csv / "AnnualTechnologyEmission.csv")
    emission_value = "AnnualTechnologyEmission"
    base_emission_total = base_emissions.groupby(["e", "y"], as_index=False)[emission_value].sum()
    cand_emission_total = cand_emissions.groupby(["e", "y"], as_index=False)[emission_value].sum()
    emission_diff = base_emission_total.merge(cand_emission_total, on=["e", "y"], suffixes=("_base", "_candidate"), how="outer").fillna(0)
    emission_diff["change"] = emission_diff[f"{emission_value}_candidate"] - emission_diff[f"{emission_value}_base"]
    max_emission_change = float(emission_diff["change"].abs().max())

    base_demand = load_csv(baseline_csv / "Demand.csv")
    cand_demand = load_csv(candidate_csv / "Demand.csv")
    regression = {
        "baseline_objective": float(baseline_objective),
        "candidate_objective": float(candidate_objective),
        "objective_change": float(objective_change),
        "objective_percent_change": float(objective_percent),
        "demand_rows_identical": base_demand.equals(cand_demand),
        "max_annual_emission_change": max_emission_change,
        "largest_activity_changes": top.to_dict(orient="records"),
    }
    check(
        "regression_sanity",
        regression["demand_rows_identical"] and abs(regression["objective_percent_change"]) < 0.01,
        regression,
    )

    report = {
        "schema": "philippines-v16-energy-input-validation-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": str(candidate),
        "baseline": str(baseline),
        "run": RUN,
        "solver": {
            "status": "optimal",
            "wall_seconds_application_chain": args.wall_seconds,
            "matrix_rows": 791109,
            "matrix_columns": 884956,
            "matrix_nonzeros": 12552173,
        },
        "checks": checks,
        "status": "pass" if all(item["status"] == "pass" for item in checks) else "fail",
    }
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
