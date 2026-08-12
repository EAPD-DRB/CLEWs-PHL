#!/usr/bin/env python3
"""Validate Philippines v18 energy inputs and inherited v17 land safeguards."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd


PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parent
DEFAULT_CONTROL = REPO / "case" / "Philippines_v17"
DEFAULT_CANDIDATE = REPO / "case" / "Philippines_v18"
DEFAULT_RUN = "ENERGY_INPUTS_V18_BASE"
INPUTS = PACKAGE / "data_sources" / "snapshots" / "energy_inputs_v18_2026-08-12.json"
BUILD = PACKAGE / "data_sources" / "snapshots" / "energy_inputs_v18_build_manifest.json"
OUTPUT = PACKAGE / "data_sources" / "snapshots" / "energy_inputs_v18_validation.json"
EXPECTED_CHANGED = ["RT.json", "RYT.json", "RYTM.json", "RYTTs.json", "genData.json"]
EXPECTED_LAND_2020 = {1: 72.3194, 2: 77.7456, 3: 2.2879, 4: 1.5950, 5: 10.2649, 6: 6.3198, 7: 125.2805, 8: 0.0}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one(rows: list[dict], **coordinates) -> dict:
    matches = [row for row in rows if all(row.get(key) == value for key, value in coordinates.items())]
    if len(matches) != 1:
        raise AssertionError(f"expected one row for {coordinates}; found {len(matches)}")
    return matches[0]


def annual_cf(case: Path, tech_id: str, year: str) -> float:
    cf = read_json(case / "RYTTs.json")["CF"]["SC_0"]
    ys = read_json(case / "RYTs.json")["YS"]["SC_0"]
    cf_by_ts = {row["TsId"]: Decimal(str(row[year])) for row in cf if row["TechId"] == tech_id}
    ys_by_ts = {row["TsId"]: Decimal(str(row[year])) for row in ys}
    return float(sum(cf_by_ts[ts] * ys_by_ts[ts] for ts in ys_by_ts))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, default=DEFAULT_CONTROL)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--run", default=DEFAULT_RUN)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    control = args.control.resolve()
    candidate = args.candidate.resolve()
    inputs = read_json(INPUTS)
    checks: list[dict] = []

    def check(name: str, condition: bool, detail) -> None:
        checks.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})

    result_path = candidate / "res" / args.run / "results.txt"
    status = result_path.read_text(encoding="utf-8").splitlines()[0]
    check("optimal", status.startswith("Optimal - objective value"), status)

    control_gen = read_json(control / "genData.json")
    candidate_gen = read_json(candidate / "genData.json")
    check("case_identity", candidate_gen["osy-casename"] == "Philippines_v18", candidate_gen["osy-casename"])
    structure = {
        "technology_ids": [x["TechId"] for x in control_gen["osy-tech"]] == [x["TechId"] for x in candidate_gen["osy-tech"]],
        "commodity_ids": [x["CommId"] for x in control_gen["osy-comm"]] == [x["CommId"] for x in candidate_gen["osy-comm"]],
        "constraints": control_gen["osy-constraints"] == candidate_gen["osy-constraints"],
        "global_mode_count": control_gen["osy-mo"] == candidate_gen["osy-mo"] == "30",
    }
    check("no_new_model_objects", all(structure.values()), structure)

    names = sorted(path.name for path in control.glob("*.json"))
    changed = [name for name in names if sha256(control / name) != sha256(candidate / name)]
    check("source_diff_scope", changed == EXPECTED_CHANGED, changed)
    exact_land_files = {
        name: sha256(control / name) == sha256(candidate / name)
        for name in ("RYTCM.json", "RYC.json", "RYCn.json", "RYDtb.json", "RYTs.json")
    }
    control_rytm = read_json(control / "RYTM.json")
    candidate_rytm = read_json(candidate / "RYTM.json")
    exact_land_files["RYTM_TAMLL"] = control_rytm["TAMLL"] == candidate_rytm["TAMLL"]
    exact_land_files["RYTM_TAMUL"] = control_rytm["TAMUL"] == candidate_rytm["TAMUL"]
    check("v17_land_constraints_retained", all(exact_land_files.values()), exact_land_files)

    ryt = read_json(candidate / "RYT.json")
    rt = read_json(candidate / "RT.json")
    geo = one(ryt["AF"]["SC_0"], TechId="TEC_0qr3z")
    coal = one(ryt["CC"]["SC_0"], TechId="TEC_46nha")
    smr = one(ryt["CC"]["SC_0"], TechId="TEC_fa6fe")
    import_cap = one(ryt["TAU"]["SC_0"], TechId="TEC_otz0y")
    domestic_cap = one(ryt["TAU"]["SC_0"], TechId="TEC_6rwx6")
    parameter_detail = {
        "geothermal_af_2020": geo["2020"],
        "onshore_wind_annual_cf_2020": annual_cf(candidate, "TEC_1wdli", "2020"),
        "coal_capital_cost_2020": coal["2020"],
        "smr_capital_cost_2020": smr["2020"],
        "smr_life": rt["OL"]["SC_0"][0]["TEC_fa6fe"],
        "large_hydro_life": rt["OL"]["SC_0"][0]["TEC_p3vu5"],
        "lng_cap_2020": import_cap["2020"],
        "lng_cap_2022": import_cap["2022"],
        "lng_cap_2023": import_cap["2023"],
        "lng_cap_2024": import_cap["2024"],
        "domestic_cap_2020": domestic_cap["2020"],
        "domestic_cap_2024": domestic_cap["2024"],
    }
    expected = {
        "geothermal_af_2020": 0.7,
        "onshore_wind_annual_cf_2020": inputs["onshore_wind"]["annual_capacity_factor_after"],
        "coal_capital_cost_2020": inputs["capital_costs"]["coal_power_musd_per_gw"],
        "smr_capital_cost_2020": inputs["capital_costs"]["nuclear_smr_musd_per_gw"],
        "smr_life": 60,
        "large_hydro_life": 60,
        "lng_cap_2020": 0.0,
        "lng_cap_2022": 0.0,
        "lng_cap_2023": inputs["natural_gas"]["lng_import_limit"]["2023_pj"],
        "lng_cap_2024": inputs["natural_gas"]["lng_import_limit"]["2024_2053_pj_per_year"],
        "domestic_cap_2020": inputs["natural_gas"]["domestic_production_mmscf"]["2020"] * inputs["natural_gas"]["mmscf_to_pj"],
        "domestic_cap_2024": inputs["natural_gas"]["domestic_production_mmscf"]["2024"] * inputs["natural_gas"]["mmscf_to_pj"],
    }
    errors = {key: parameter_detail[key] - expected[key] for key in expected}
    check("energy_parameter_values", max(abs(value) for value in errors.values()) <= 1e-10, {"values": parameter_detail, "errors": errors})

    activity = pd.read_csv(candidate / "res" / args.run / "csv" / "TotalAnnualTechnologyActivityByMode.csv")
    value = "TotalAnnualTechnologyActivityByMode"
    imported = activity[activity.t == "PHL_PRO_IMP_NG"].groupby("y")[value].sum()
    domestic = activity[activity.t == "PHL_PRO_EXTR_NG"].groupby("y")[value].sum()
    import_violations = {str(year): float(imported.get(year, 0) - import_cap[str(year)]) for year in range(2020, 2054)}
    domestic_violations = {str(year): float(domestic.get(year, 0) - domestic_cap[str(year)]) for year in range(2020, 2054)}
    check("lng_chronology_and_limits", max(import_violations.values()) <= 5e-5 and float(imported.loc[2020:2022].abs().max()) <= 5e-5, {
        "2020_2022_max_activity_pj": float(imported.loc[2020:2022].abs().max()),
        "maximum_upper_violation_pj": max(import_violations.values()),
        "selected_activity_pj": {str(year): float(imported.get(year, 0)) for year in (2020, 2022, 2023, 2024, 2053)},
    })
    check("domestic_gas_limits", max(domestic_violations.values()) <= 5e-5, {
        "maximum_upper_violation_pj": max(domestic_violations.values()),
        "selected_activity_pj": {str(year): float(domestic.get(year, 0)) for year in (2020, 2021, 2022, 2023, 2024, 2053)},
    })

    env = activity[activity.t == "ENV_LAND"]
    env_2020 = env[env.y == 2020].set_index("m")[value].to_dict()
    class_errors = {str(mode): float(env_2020.get(mode, 0) - expected_value) for mode, expected_value in EXPECTED_LAND_2020.items()}
    supply = activity[activity.t == "MINLNDTOT"].groupby("y")[value].sum()
    terminal = env.groupby("y")[value].sum()
    check("v17_land_2020_reproduced", max(abs(value) for value in class_errors.values()) <= 5e-5, class_errors)
    check("v17_land_closure_reproduced", float((terminal - supply).abs().max()) <= 5e-4 and float((supply - 295.8131).abs().max()) <= 5e-5, {
        "maximum_closure_residual_1000_km2": float((terminal - supply).abs().max()),
        "minimum_supply_1000_km2": float(supply.min()),
        "maximum_supply_1000_km2": float(supply.max()),
    })

    objective = float(pd.read_csv(candidate / "res" / args.run / "csv" / "ObjectiveValue.csv")["ObjectiveValue"].iloc[0])
    control_objective = 369740345.77061987
    report = {
        "schema": "philippines-v18-energy-input-validation-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if all(item["status"] == "pass" for item in checks) else "fail",
        "control": {"case": str(control), "objective": control_objective},
        "candidate": {"case": str(candidate), "run": args.run, "objective": objective},
        "objective_change": {"absolute": objective - control_objective, "percent": (objective - control_objective) / control_objective * 100},
        "checks": checks,
        "build_manifest": str(BUILD),
        "input_snapshot": str(INPUTS),
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
