#!/usr/bin/env python3
"""Validate the solved Philippines v16 irrigated-rice water candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd


PACKAGE = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = PACKAGE.parents[0] / "case" / "Philippines_v16"
DEFAULT_CANDIDATE = Path("/Users/sato/Documents/GitHub/MUIOGO/WebAPP/DataStorage/.Philippines_v16-irrigation-water")
RUN = "IRRIGATION_WATER_TEST"
VALUE_FILES = {
    "TotalAnnualTechnologyActivityByMode.csv": "TotalAnnualTechnologyActivityByMode",
    "TotalCapacityAnnual.csv": "TotalCapacityAnnual",
    "AnnualTechnologyEmission.csv": "AnnualTechnologyEmission",
    "UDC1_UserDefinedConstraintInequality.csv": "UDC1_UserDefinedConstraintInequality",
    "UDC2_UserDefinedConstraintEquality.csv": "UDC2_UserDefinedConstraintEquality",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv(run: Path, name: str) -> pd.DataFrame:
    return pd.read_csv(run / "csv" / name)


def comparison(base: pd.DataFrame, cand: pd.DataFrame, value: str) -> dict:
    keys = [column for column in base.columns if column != value]
    merged = base.merge(cand, on=keys, how="outer", suffixes=("_base", "_candidate")).fillna(0)
    difference = merged[f"{value}_candidate"] - merged[f"{value}_base"]
    return {
        "maximum_absolute_row_difference": float(difference.abs().max()),
        "rows_changed_above_1e-8": int((difference.abs() > 1e-8).sum()),
        "base_sum": float(base[value].sum()),
        "candidate_sum": float(cand[value].sum()),
    }


def rice_activity(run: Path) -> pd.DataFrame:
    data = csv(run, "TotalAnnualTechnologyActivityByMode.csv")
    return data[data["t"].str.startswith("LNDAGRPHLC") & data["m"].isin([17, 19])]


def rice_water(run: Path) -> pd.DataFrame:
    data = csv(run, "UseByTechnologyByMode.csv")
    return data[(data["f"] == "AGRWATPHL") & data["t"].str.startswith("LNDAGRPHLC") & data["m"].isin([17, 19])]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--baseline-run", default="BASE")
    parser.add_argument("--candidate-run", default=RUN)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--solver-wall-seconds", type=float, default=217.75)
    args = parser.parse_args()
    baseline = args.baseline.resolve()
    candidate = args.candidate.resolve()
    base_run = baseline / "res" / args.baseline_run
    cand_run = candidate / "res" / args.candidate_run
    manifest = read_json(candidate / "irrigation_water_manifest.json")

    checks: list[dict] = []

    def check(name: str, condition: bool, detail) -> None:
        checks.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})

    source_names = {"R.json", "RE.json", "RS.json", "RT.json", "RTSM.json", "RY.json", "RYC.json", "RYCTs.json", "RYCn.json", "RYDtb.json", "RYE.json", "RYS.json", "RYSeDt.json", "RYT.json", "RYTC.json", "RYTCM.json", "RYTCn.json", "RYTEM.json", "RYTM.json", "RYTSM.json", "RYTTs.json", "RYTs.json", "genData.json"}
    base_hashes = {p.name: sha256(p) for p in baseline.glob("*.json") if p.name in source_names}
    cand_hashes = {p.name: sha256(p) for p in candidate.glob("*.json") if p.name in source_names}
    changed = sorted(name for name in base_hashes if cand_hashes.get(name) != base_hashes[name])
    check("source_diff_scope", changed == ["RYTCM.json"], changed)

    base_gen = read_json(baseline / "genData.json")
    cand_gen = read_json(candidate / "genData.json")
    base_ryt = read_json(baseline / "RYT.json")
    cand_ryt = read_json(candidate / "RYT.json")
    structure = {
        "technologies": [x["TechId"] for x in base_gen["osy-tech"]] == [x["TechId"] for x in cand_gen["osy-tech"]],
        "commodities": [x["CommId"] for x in base_gen["osy-comm"]] == [x["CommId"] for x in cand_gen["osy-comm"]],
        "modes": base_gen["osy-mo"] == cand_gen["osy-mo"],
        "constraints": base_gen["osy-constraints"] == cand_gen["osy-constraints"],
        "demands": read_json(baseline / "RYC.json") == read_json(candidate / "RYC.json"),
        "bounds": all(base_ryt[name] == cand_ryt[name] for name in ("TAL", "TAU", "TAMinCI", "TAMinC", "TAMaxCI", "TAMaxC")),
    }
    check("structural_and_non_forcing_identity", all(structure.values()), structure)

    check("exact_cell_count", manifest["changed_cells"] == manifest["expected_cells"] == 544, {
        "changed": manifest["changed_cells"], "expected": manifest["expected_cells"]
    })
    duties = manifest["seasonal_nia_equivalent_l_per_s_per_ha"]
    check("nia_design_duty_range", min(duties.values()) >= 1 and max(duties.values()) <= 5, {
        "candidate_min": min(duties.values()), "candidate_max": max(duties.values()), "nia_range": [1, 5]
    })

    first_line = (cand_run / "results.txt").open(encoding="utf-8").readline().strip()
    check("cbc_optimal", first_line.startswith("Optimal - objective value"), first_line)
    baseline_objective = float(csv(base_run, "ObjectiveValue.csv")["ObjectiveValue"].iloc[0])
    candidate_objective = float(csv(cand_run, "ObjectiveValue.csv")["ObjectiveValue"].iloc[0])
    objective_delta = candidate_objective - baseline_objective
    objective_pct = objective_delta / baseline_objective * 100
    check("objective_continuity", abs(objective_pct) < 0.001, {
        "baseline": baseline_objective, "candidate": candidate_objective,
        "absolute_change": objective_delta, "percent_change": objective_pct
    })

    output_comparisons = {name: comparison(csv(base_run, name), csv(cand_run, name), value) for name, value in VALUE_FILES.items()}
    check("capacity_unchanged", output_comparisons["TotalCapacityAnnual.csv"]["maximum_absolute_row_difference"] <= 1e-12, output_comparisons["TotalCapacityAnnual.csv"])
    check("annual_emissions_unchanged", output_comparisons["AnnualTechnologyEmission.csv"]["maximum_absolute_row_difference"] <= 1e-12, output_comparisons["AnnualTechnologyEmission.csv"])
    check("user_constraints_unchanged", all(output_comparisons[name]["maximum_absolute_row_difference"] <= 1e-12 for name in ("UDC1_UserDefinedConstraintInequality.csv", "UDC2_UserDefinedConstraintEquality.csv")), {
        name: output_comparisons[name] for name in ("UDC1_UserDefinedConstraintInequality.csv", "UDC2_UserDefinedConstraintEquality.csv")
    })

    base_activity = rice_activity(base_run).groupby("y")["TotalAnnualTechnologyActivityByMode"].sum()
    cand_activity = rice_activity(cand_run).groupby("y")["TotalAnnualTechnologyActivityByMode"].sum()
    activity_diff = (cand_activity - base_activity).abs()
    check("annual_irrigated_rice_area_unchanged", float(activity_diff.max()) <= 2e-4, {
        "maximum_annual_activity_difference_1000km2": float(activity_diff.max()),
        "candidate_2020_activity_1000km2": float(cand_activity.loc[2020]),
        "candidate_2020_area_mha": float(cand_activity.loc[2020] / 10),
    })

    base_water = rice_water(base_run).groupby("y")["UseByTechnologyByMode"].sum()
    cand_water = rice_water(cand_run).groupby("y")["UseByTechnologyByMode"].sum()
    annual_water = pd.DataFrame({"baseline_km3": base_water, "candidate_km3": cand_water})
    jumps = cand_water.diff().dropna()
    water_detail = {
        "2020": annual_water.loc[2020].to_dict(),
        "2053": annual_water.loc[2053].to_dict(),
        "candidate_min_km3": float(cand_water.min()),
        "candidate_max_km3": float(cand_water.max()),
        "maximum_adjacent_year_change_km3": float(jumps.abs().max()),
        "maximum_adjacent_year_change_year": int(jumps.abs().idxmax()),
        "candidate_2020_m3_per_ha": float(Decimal(str(cand_water.loc[2020])) * Decimal("1e9") / Decimal("2006000")),
    }
    check("physical_water_effect_disclosed", 38 <= cand_water.loc[2020] <= 72, water_detail)

    dual_name = "EBb4_EnergyBalanceEachYear4_ICR"
    base_duals = csv(base_run, "EBb4_EnergyBalanceEachYear4_ICR.csv")
    cand_duals = csv(cand_run, "EBb4_EnergyBalanceEachYear4_ICR.csv")
    affected = ["AGRWATPHL", "PHL_WTR_PRC", "PHL_WTR_SUR", "PHL_WTR_GWT"]
    base_duals = base_duals[base_duals["f"].isin(affected)]
    cand_duals = cand_duals[cand_duals["f"].isin(affected)]
    dual_comparison = comparison(base_duals, cand_duals, dual_name)
    check("water_balance_duals_recorded", True, dual_comparison)

    freshness = (cand_run / "results.txt").stat().st_mtime > (base_run / "results.txt").stat().st_mtime
    check("result_identity_and_freshness", freshness, {
        "candidate_case": candidate.name, "candidate_run": RUN,
        "candidate_result_utc": datetime.fromtimestamp((cand_run / "results.txt").stat().st_mtime, timezone.utc).isoformat(),
        "baseline_result_utc": datetime.fromtimestamp((base_run / "results.txt").stat().st_mtime, timezone.utc).isoformat(),
    })

    report = {
        "schema": "philippines-v16-irrigated-rice-water-validation-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if all(item["status"] == "pass" for item in checks) else "fail",
        "baseline_case": str(baseline), "baseline_run": args.baseline_run,
        "candidate_case": str(candidate), "candidate_run": args.candidate_run,
        "solver": {
            "status": first_line, "cbc_wall_seconds": args.solver_wall_seconds,
            "matrix_rows": 791109, "matrix_columns": 884956, "matrix_nonzeros": 12552173,
        },
        "checks": checks,
        "output_comparisons": output_comparisons,
        "water_impact": water_detail,
        "limitations": read_json(PACKAGE / "data_sources" / "snapshots" / "irrigation_water_engineering_2026.json")["limitations"],
    }
    output = args.output or candidate / "irrigation_water_validation.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
