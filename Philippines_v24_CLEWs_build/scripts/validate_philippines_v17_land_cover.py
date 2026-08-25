#!/usr/bin/env python3
"""Validate Philippines v17 land accounting and transition safeguards."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PACKAGE = Path(__file__).resolve().parents[1]
DEFAULT_CONTROL = PACKAGE.parents[0] / "case" / "Philippines_v16"
DEFAULT_CANDIDATE = PACKAGE.parents[0] / "case" / "Philippines_v17"
CANDIDATE_RUN = "LAND_SAFEGUARDS_CENTRAL_COMPLETE"
RETAINED_CONTROL = PACKAGE / "data_sources" / "snapshots" / "irrigation_water_live_validation.json"
SAFEGUARDS = PACKAGE / "data_sources" / "snapshots" / "land_transition_safeguards.json"
EXPECTED_CLASSES = {
    1: 72.3194,
    2: 77.7456,
    3: 2.2879,
    4: 1.5950,
    5: 10.2649,
    6: 6.3198,
    7: 125.2805,
    8: 0.0,
}
LAND_TECHS = {"MINLNDTOT", "ENV_LAND", "LNDOTHTOT"}
PUBLIC_WATER = "COM_n1j3l"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv(case: Path, run: str, name: str) -> pd.DataFrame:
    return pd.read_csv(case / "res" / run / "csv" / name)


def compare(base: pd.DataFrame, candidate: pd.DataFrame, value: str) -> dict:
    keys = [column for column in base.columns if column != value]
    merged = base.merge(candidate, on=keys, how="outer", suffixes=("_control", "_candidate")).fillna(0)
    difference = merged[f"{value}_candidate"] - merged[f"{value}_control"]
    return {
        "maximum_absolute_row_difference": float(difference.abs().max()),
        "rows_changed_above_1e-8": int((difference.abs() > 1e-8).sum()),
        "control_sum": float(base[value].sum()),
        "candidate_sum": float(candidate[value].sum()),
    }


def solved(case: Path, run: str) -> str:
    return (case / "res" / run / "results.txt").read_text(encoding="utf-8").splitlines()[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, default=DEFAULT_CONTROL)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--candidate-run", default=CANDIDATE_RUN)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--candidate-wall-seconds", type=float, default=310.55)
    args = parser.parse_args()
    control = args.control.resolve()
    candidate = args.candidate.resolve()
    candidate_run = args.candidate_run
    checks: list[dict] = []

    def check(name: str, condition: bool, detail) -> None:
        checks.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})

    candidate_status = solved(candidate, candidate_run)
    check("candidate_optimal", candidate_status.startswith("Optimal - objective value"), candidate_status)
    retained_control = read_json(RETAINED_CONTROL)
    safeguards = read_json(SAFEGUARDS)
    rate = safeguards["calculations"]["annual_restoration_rate"]["output_1000_km2_per_year"]
    brush_pool = safeguards["calculations"]["mapped_brush_shrub_pool"]["model_output_1000_km2"]
    forest_eligible_pool = safeguards["calculations"]["forest_eligible_brush_shrub_pool"]["output_1000_km2"]
    grass_reserve = safeguards["calculations"]["true_grassland_reserve"]["output_1000_km2"]
    built_path = safeguards["calculations"]["central_built_up_path"]
    urban_2020 = built_path["urban_share_2020"]
    urban_2050 = built_path["urban_share_2050"]
    disabled_upper = safeguards["model_rules"]["disabled_mode_upper_sentinel_1000_km2"]
    idle_fallow_ceiling = safeguards["calculations"]["idle_fallow_ceiling"]["output_1000_km2"]
    candidate_demand = read_json(candidate / "RYC.json")
    public_water = next(
        item for item in candidate_demand["AAD"]["SC_0"] if item.get("CommId") == PUBLIC_WATER
    )
    base_public_water = public_water["2020"]

    def expected_built_up(year: int) -> float:
        urban_share = urban_2020 + (urban_2050 - urban_2020) * min(year - 2020, 30) / 30
        return EXPECTED_CLASSES[5] * (public_water[str(year)] / base_public_water) * (urban_share / urban_2020)
    check("retained_v16_control_valid", retained_control["status"] == "pass", {
        "case": retained_control["case"], "run": retained_control["run"],
        "objective": retained_control["solver"]["objective"]
    })

    base_gen = read_json(control / "genData.json")
    cand_gen = read_json(candidate / "genData.json")
    check("case_identity", cand_gen["osy-casename"] == "Philippines_v17", cand_gen["osy-casename"])
    structure = {
        "technology_ids": [x["TechId"] for x in base_gen["osy-tech"]] == [x["TechId"] for x in cand_gen["osy-tech"]],
        "commodity_ids": [x["CommId"] for x in base_gen["osy-comm"]] == [x["CommId"] for x in cand_gen["osy-comm"]],
        "global_mode_count": base_gen["osy-mo"] == cand_gen["osy-mo"] == "30",
        "constraints": base_gen["osy-constraints"] == cand_gen["osy-constraints"],
    }
    check("no_new_model_objects", all(structure.values()), structure)

    source_names = {path.name for path in control.glob("*.json")}
    source_hashes = {name: sha256(control / name) for name in source_names}
    candidate_hashes = {name: sha256(candidate / name) for name in source_names}
    changed_files = sorted(name for name in source_names if source_hashes[name] != candidate_hashes.get(name))
    check("source_diff_scope", changed_files == ["RYT.json", "RYTCM.json", "RYTM.json", "genData.json"], changed_files)
    control_rytm = read_json(control / "RYTM.json")
    candidate_rytm = read_json(candidate / "RYTM.json")
    check("forest_vc_retained", control_rytm["VC"] == candidate_rytm["VC"], "complete VC parameter identical")

    source_bound_errors = []
    for scenario in candidate_rytm["TAMLL"]:
        lower_rows = {
            item["MoId"]: item for item in candidate_rytm["TAMLL"][scenario]
            if item.get("TechId") == "TEC_envland_v12" and item.get("MoId") in range(1, 9)
        }
        upper_rows = {
            item["MoId"]: item for item in candidate_rytm["TAMUL"][scenario]
            if item.get("TechId") == "TEC_envland_v12" and item.get("MoId") in range(1, 9)
        }
        for year in range(2020, 2054):
            year_text = str(year)
            forest_release = min(rate * (year - 2020), forest_eligible_pool)
            expected = {
                1: (EXPECTED_CLASSES[1], EXPECTED_CLASSES[1] + forest_release),
                2: (EXPECTED_CLASSES[2] if year == 2020 else grass_reserve, EXPECTED_CLASSES[2]),
                3: (EXPECTED_CLASSES[3], EXPECTED_CLASSES[3]),
                4: (EXPECTED_CLASSES[4], EXPECTED_CLASSES[4]),
                5: (expected_built_up(year), expected_built_up(year)),
                6: (EXPECTED_CLASSES[6], EXPECTED_CLASSES[6]),
                7: (EXPECTED_CLASSES[7], EXPECTED_CLASSES[7] if year == 2020 else None),
                8: (0.0, disabled_upper),
            }
            for mode, (lower_expected, upper_expected) in expected.items():
                source_bound_errors.append(abs(lower_rows[mode][year_text] - lower_expected))
                if upper_expected is not None:
                    source_bound_errors.append(abs(upper_rows[mode][year_text] - upper_expected))
    check("transition_safeguard_source_bounds", max(source_bound_errors) <= 1e-9, {
        "maximum_absolute_source_error": max(source_bound_errors),
        "scenarios_checked": len(candidate_rytm["TAMLL"]),
        "years_checked": [2020, 2053],
    })
    idle_source_errors = []
    for scenario in candidate_rytm["TAMUL"]:
        idle_upper = next(
            item for item in candidate_rytm["TAMUL"][scenario]
            if item.get("TechId") == "TEC_zty92" and item.get("MoId") == 2
        )
        idle_source_errors.extend(abs(idle_upper[str(year)] - idle_fallow_ceiling) for year in range(2020, 2054))
    check("idle_fallow_source_ceiling", max(idle_source_errors) <= 1e-9, {
        "maximum_absolute_source_error": max(idle_source_errors),
        "ceiling_1000_km2": idle_fallow_ceiling,
    })

    activity = csv(candidate, candidate_run, "TotalAnnualTechnologyActivityByMode.csv")
    value = "TotalAnnualTechnologyActivityByMode"
    env_2020 = activity[(activity.t == "ENV_LAND") & (activity.y == 2020)].set_index("m")[value].to_dict()
    class_error = {str(mode): float(env_2020.get(mode, 0) - expected) for mode, expected in EXPECTED_CLASSES.items()}
    check("base_year_class_equalities", max(abs(v) for v in class_error.values()) <= 5e-5, class_error)
    check("zero_unallocated_2020", abs(env_2020.get(8, 0)) <= 5e-5, env_2020.get(8, 0))

    annual_env = activity[activity.t == "ENV_LAND"].groupby("y")[value].sum()
    annual_supply = activity[activity.t == "MINLNDTOT"].groupby("y")[value].sum()
    check("annual_national_land_equality", float((annual_supply - 295.8131).abs().max()) <= 5e-5, {
        "minimum": float(annual_supply.min()), "maximum": float(annual_supply.max())
    })
    check("annual_land_account_closure", float((annual_env - annual_supply).abs().max()) <= 5e-4, {
        "maximum_absolute_residual_1000_km2": float((annual_env - annual_supply).abs().max())
    })

    env = activity[activity.t == "ENV_LAND"].pivot_table(index="y", columns="m", values=value, aggfunc="sum", fill_value=0)
    forest_upper = pd.Series(
        {year: EXPECTED_CLASSES[1] + min(rate * (year - 2020), forest_eligible_pool) for year in env.index}
    )
    check("forest_protection_floor", float((EXPECTED_CLASSES[1] - env[1]).max()) <= 5e-5, {
        "minimum_solved_1000_km2": float(env[1].min()), "floor_1000_km2": EXPECTED_CLASSES[1]
    })
    check("forest_policy_rate_envelope", float((env[1] - forest_upper).max()) <= 5e-5, {
        "maximum_upper_violation_1000_km2": float((env[1] - forest_upper).max()),
        "rate_1000_km2_per_year": rate,
        "forest_eligible_pool_1000_km2": forest_eligible_pool,
    })
    check("true_grassland_reserve", float((grass_reserve - env[2]).max()) <= 5e-5, {
        "maximum_lower_violation_1000_km2": float((grass_reserve - env[2]).max()),
        "reserve_1000_km2": grass_reserve,
        "note": "Brush above the reserve remains available to cropland and built-up land without a destination-independent release rate."
    })
    check("grass_brush_does_not_exceed_2020_stock", float((env[2] - EXPECTED_CLASSES[2]).max()) <= 5e-5, {
        "maximum_upper_violation_1000_km2": float((env[2] - EXPECTED_CLASSES[2]).max())
    })
    built_expected = pd.Series({year: expected_built_up(int(year)) for year in env.index})
    check("central_built_up_path", float((env[5] - built_expected).abs().max()) <= 5e-5, {
        "maximum_absolute_error_1000_km2": float((env[5] - built_expected).abs().max()),
        "built_up_2050_1000_km2": float(built_expected.loc[2050]),
        "built_up_2053_1000_km2": float(built_expected.loc[2053]),
    })
    fixed_classes = {3: "other_agricultural", 4: "barren", 6: "water_bodies"}
    fixed_errors = {
        name: float((env[mode] - EXPECTED_CLASSES[mode]).abs().max())
        for mode, name in fixed_classes.items()
    }
    check("nonconvertible_classes_preserved", max(fixed_errors.values()) <= 5e-5, fixed_errors)
    check("cropland_2020_stock_floor", float((EXPECTED_CLASSES[7] - env[7]).max()) <= 5e-5, {
        "minimum_solved_1000_km2": float(env[7].min()), "floor_1000_km2": EXPECTED_CLASSES[7]
    })
    check("zero_unallocated_all_years", float(env[8].abs().max()) <= 5e-5, {
        "maximum_absolute_1000_km2": float(env[8].abs().max())
    })
    annual_forest_increase = env[1].diff().dropna()
    check("solved_annual_forest_increase_within_policy_rate", float(annual_forest_increase.max()) <= rate + 5e-5, {
        "maximum_solved_increase_1000_km2": float(annual_forest_increase.max()),
        "policy_rate_1000_km2_per_year": rate,
        "note": "Solved-path check; the source formulation is a cumulative envelope relative to 2020, not a gross parcel transition equation."
    })

    candidate_prod = csv(candidate, candidate_run, "ProductionByTechnologyByMode.csv")
    prod_value = "ProductionByTechnologyByMode"
    candidate_crop = candidate_prod[(candidate_prod.f == "ENV_LND_CROPLAND") & (candidate_prod.t != "LNDOTHTOT")].groupby("y")[prod_value].sum()
    productive_2020 = float(candidate_crop.loc[2020])
    check("productive_cropland_preserved", abs(productive_2020 - 119.9928) <= 5e-4, {
        "retained_v16_2020_1000_km2": 119.9928, "candidate_2020_1000_km2": productive_2020,
    })
    idle_2020 = float(activity[(activity.t == "LNDOTHTOT") & (activity.m == 2) & (activity.y == 2020)][value].sum())
    expected_idle = EXPECTED_CLASSES[7] - productive_2020
    check("idle_fallow_closes_cropland", abs(idle_2020 - expected_idle) <= 5e-4, {
        "idle_fallow_1000_km2": idle_2020,
        "productive_cropland_1000_km2": productive_2020,
        "total_cropland_1000_km2": idle_2020 + productive_2020,
    })
    annual_idle = activity[(activity.t == "LNDOTHTOT") & (activity.m == 2)].groupby("y")[value].sum()
    check("idle_fallow_never_expands_above_base_stock", float((annual_idle - idle_fallow_ceiling).max()) <= 5e-5, {
        "maximum_solved_1000_km2": float(annual_idle.max()),
        "ceiling_1000_km2": idle_fallow_ceiling,
    })

    cand_use = csv(candidate, candidate_run, "UseByTechnologyByMode.csv")
    rice_water_2020 = float(cand_use[(cand_use.f == "AGRWATPHL") & (cand_use.y == 2020)]["UseByTechnologyByMode"].sum())
    retained_water = next(item for item in retained_control["checks"] if item["name"] == "live_irrigated_rice_physics")["detail"]
    check("irrigation_water_within_validated_engineering_range", 38 <= rice_water_2020 <= 72, {
        "candidate_2020_km3": rice_water_2020,
        "retained_v16_live_2020_km3": retained_water["water_km3"],
        "interpretation": "Cluster allocation is degenerate; national productive area remains fixed and water stays in the retained engineering envelope."
    })

    exact_source_regression = {
        "demand_RYC": read_json(control / "RYC.json") == read_json(candidate / "RYC.json"),
        "emissions_RYE": read_json(control / "RYE.json") == read_json(candidate / "RYE.json"),
        "emission_factors_RYTEM": read_json(control / "RYTEM.json") == read_json(candidate / "RYTEM.json"),
        "capacity_and_cost_RT": read_json(control / "RT.json") == read_json(candidate / "RT.json"),
        "time_sliced_capacity_RYTs": read_json(control / "RYTs.json") == read_json(candidate / "RYTs.json"),
        "time_sliced_activity_RYTTs": read_json(control / "RYTTs.json") == read_json(candidate / "RYTTs.json"),
        "user_constraints_RYTCn": read_json(control / "RYTCn.json") == read_json(candidate / "RYTCn.json"),
    }
    check("energy_demand_emission_and_policy_sources_unchanged", all(exact_source_regression.values()), exact_source_regression)

    base_objective = float(retained_control["solver"]["objective"])
    candidate_objective = float(csv(candidate, candidate_run, "ObjectiveValue.csv")["ObjectiveValue"].iloc[0])
    objective_change = candidate_objective - base_objective
    selected_years = [2020, 2021, 2025, 2030, 2040, 2050, 2053]
    land_trajectory = {
        str(year): {str(mode): float(env.loc[year, mode]) for mode in range(1, 9)}
        for year in selected_years
    }
    productive_trajectory = {str(year): float(candidate_crop.loc[year]) for year in selected_years}
    idle_trajectory = {
        str(year): float(activity[(activity.t == "LNDOTHTOT") & (activity.m == 2) & (activity.y == year)][value].sum())
        for year in selected_years
    }
    report = {
        "schema": "philippines-v17-land-cover-validation-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if all(item["status"] == "pass" for item in checks) else "fail",
        "control": {"case": str(control), "run": retained_control["run"], "objective": base_objective, "validation_record": str(RETAINED_CONTROL)},
        "candidate": {"case": str(candidate), "run": candidate_run, "objective": candidate_objective, "cbc_wall_seconds": args.candidate_wall_seconds},
        "objective_change": {"absolute": objective_change, "percent": objective_change / base_objective * 100},
        "checks": checks,
        "land_2020": {
            "environmental_terminal_by_mode_1000_km2": {str(k): float(v) for k, v in env_2020.items()},
            "productive_cropland_1000_km2": productive_2020,
            "idle_fallow_1000_km2": idle_2020,
            "national_total_1000_km2": float(annual_supply.loc[2020]),
        },
        "land_trajectory_selected_years_1000_km2": land_trajectory,
        "productive_cropland_selected_years_1000_km2": productive_trajectory,
        "idle_fallow_selected_years_1000_km2": idle_trajectory,
        "transition_safeguards": {
            "source": str(SAFEGUARDS),
            "annual_policy_rate_1000_km2": rate,
        "mapped_brush_shrub_pool_1000_km2": brush_pool,
        "forest_eligible_brush_shrub_pool_1000_km2": forest_eligible_pool,
        "forest_suitability_fraction": safeguards["calculations"]["forest_eligible_brush_shrub_pool"]["suitability_fraction"],
        "true_grassland_reserve_1000_km2": grass_reserve,
        "maximum_forest_1000_km2": EXPECTED_CLASSES[1] + forest_eligible_pool,
        },
        "regressions": {"exact_unchanged_source_parameters": exact_source_regression, "candidate_2020_irrigation_water_km3": rice_water_2020},
        "interpretation": {
            "forest_vc": "Retained at -10; a sourced expansion envelope and class safeguards are installed, while restoration costs/lags and benefit sensitivities remain deferred.",
            "idle_fallow": "Endogenous nonnegative mode-2 activity on existing LNDOTHTOT; no new global mode or technology.",
            "hydrology": "Both LNDOTHTOT modes produce LOTHTOT, retaining the inherited cluster-mode-29 hydrology proxy.",
            "base_year_status": "The 2020 class observations are initialization equalities, not an independent calibration test.",
            "control_status": "The retained validated current-v16 live run is used. A redundant fresh control was stopped after exceeding twice its established runtime without returning a result; exact source identity protects unaffected sectors."
        }
    }
    output = args.output or PACKAGE / "data_sources" / "snapshots" / "land_cover_validation.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
