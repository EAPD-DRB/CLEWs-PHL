#!/usr/bin/env python3
"""Deterministic design-gate checks for the Philippines v21 power candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


YEARS = [str(year) for year in range(2020, 2054)]
TECH = {
    "oil_grid": "TEC_2hnym", "oil_off": "TEC_v21oil",
    "hydro_grid": "TEC_p3vu5", "hydro_off": "TEC_v21hyd",
    "solar_grid": "TEC_1k064", "solar_off": "TEC_v21sol",
    "wind_grid": "TEC_1wdli", "wind_off": "TEC_v21wnd",
    "biomass_nonfit": "TEC_gthhk", "biomass_fit": "TEC_v21bio",
}
COMM = {"offgrid": "COM_v21off", "residue": "COM_v21res",
        "housing": "COM_9ncwn", "services": "COM_dyc97", "industry": "COM_8qscb"}
SOURCE_FILES = {
    "R.json", "RE.json", "RS.json", "RT.json", "RTSM.json", "RYC.json", "RYCTs.json",
    "RYCn.json", "RYDtb.json", "RYE.json", "RYS.json", "RYSeDt.json", "RYT.json",
    "RYTC.json", "RYTCM.json", "RYTCn.json", "RYTEM.json", "RYTM.json", "RYTTs.json",
    "RYTs.json", "genData.json",
}
ALLOWED = {"RT.json", "RYC.json", "RYCTs.json", "RYT.json", "RYTCM.json", "RYTEM.json",
           "RYTM.json", "RYTTs.json", "genData.json"}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row(payload: dict, parameter: str, technology: str | None = None, commodity: str | None = None,
        *, scenario: str = "SC_0", **keys) -> dict:
    matches = [item for item in payload[parameter][scenario]
               if (technology is None or item.get("TechId") == technology)
               and (commodity is None or item.get("CommId") == commodity)
               and all(item.get(key) == value for key, value in keys.items())]
    assert len(matches) == 1, (parameter, technology, commodity, scenario, keys, len(matches))
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline, candidate = args.baseline.resolve(), args.candidate.resolve()

    changed = {name for name in SOURCE_FILES if sha(baseline / name) != sha(candidate / name)}
    assert changed == ALLOWED, (changed, ALLOWED)
    bg, cg = read(baseline / "genData.json"), read(candidate / "genData.json")
    assert bg["osy-casename"] == "Philippines_v20"
    assert cg["osy-casename"] == "Philippines_v21"
    assert len(cg["osy-tech"]) == len(bg["osy-tech"]) + 5
    assert len(cg["osy-comm"]) == len(bg["osy-comm"]) + 2
    assert len(cg["osy-constraints"]) == len(bg["osy-constraints"])
    assert {item["TechId"] for item in cg["osy-tech"]} - {item["TechId"] for item in bg["osy-tech"]} == {
        TECH["oil_off"], TECH["hydro_off"], TECH["solar_off"], TECH["wind_off"], TECH["biomass_fit"]}

    br, cr = read(baseline / "RYT.json"), read(candidate / "RYT.json")
    split_pairs = [
        (TECH["oil_grid"], TECH["oil_off"]), (TECH["hydro_grid"], TECH["hydro_off"]),
        (TECH["solar_grid"], TECH["solar_off"]), (TECH["wind_grid"], TECH["wind_off"]),
        (TECH["biomass_nonfit"], TECH["biomass_fit"]),
    ]
    stock_checks = []
    for retained, separated in split_pairs:
        before = row(br, "RC", retained)
        after_a, after_b = row(cr, "RC", retained), row(cr, "RC", separated)
        max_error = max(abs(after_a[year] + after_b[year] - before[year]) for year in YEARS)
        assert max_error < 1e-12, (retained, separated, max_error)
        stock_checks.append({"retained": retained, "separated": separated,
                             "2020_before_gw": before["2020"], "2020_after_sum_gw": after_a["2020"] + after_b["2020"],
                             "max_annual_identity_error_gw": max_error})

    for technology in (TECH["oil_off"], TECH["hydro_off"], TECH["solar_off"],
                       TECH["wind_off"], TECH["biomass_fit"]):
        assert all(row(cr, "TAMaxCI", technology)[year] == 0 for year in YEARS)
        assert all(row(cr, "TAMinCI", technology)[year] == 0 for year in YEARS)
        assert all(row(cr, "TAL", technology)[year] == 0 for year in YEARS)
    # Existing generation/activity bounds are byte-for-byte unchanged.
    for parameter in ("TAL", "TAU"):
        for old in br[parameter]["SC_0"]:
            assert row(cr, parameter, old["TechId"]) == old

    bc, cc = read(baseline / "RYC.json"), read(candidate / "RYC.json")
    offgrid = row(cc, "SAD", commodity=COMM["offgrid"])
    demand_checks = []
    for year in YEARS:
        reductions = sum(row(bc, "SAD", commodity=comm)[year] - row(cc, "SAD", commodity=comm)[year]
                         for comm in (COMM["housing"], COMM["services"], COMM["industry"]))
        assert abs(reductions - offgrid[year]) < 1e-12, (year, reductions, offgrid[year])
        demand_checks.append({"year": int(year), "offgrid_final_demand_pj": offgrid[year],
                              "reduction_from_existing_sector_demands_pj": reductions})

    rycts = read(candidate / "RYCTs.json")
    profile_sums = {}
    for year in YEARS:
        value = sum(item[year] for item in rycts["SDP"]["SC_0"] if item["CommId"] == COMM["offgrid"])
        assert abs(value - 1) < 2e-7, (year, value)
        profile_sums[year] = value

    rytts = read(candidate / "RYTTs.json")
    ysplit = read(candidate / "RYTs.json")
    ts = [item["TsId"] for item in cg["osy-ts"]]
    ys = {item["TsId"]: item for item in ysplit["YS"]["SC_0"]}
    hydro_means = {}
    target_mean = 0.3834 * (2 * 0.2507) + 0.1447 * (2 * 0.2493)
    for technology in (TECH["hydro_grid"], TECH["hydro_off"]):
        cfs = {item["TsId"]: item for item in rytts["CF"]["SC_0"] if item["TechId"] == technology}
        for year in YEARS:
            mean = sum(cfs[item][year] * ys[item][year] for item in ts)
            assert abs(mean - target_mean) < 1e-7, (technology, year, mean, target_mean)
        hydro_means[technology] = mean

    rytcm = read(candidate / "RYTCM.json")
    residue_factors = {"COM_zrfky": 3.0071250000000003, "COM_ec7z7": 2.929464, "COM_vwhhn": 6.275775}
    crop_techs = [item for item in cg["osy-tech"] if set(residue_factors).intersection(item.get("OAR", []))]
    assert len(crop_techs) == 8
    for technology in crop_techs:
        for mode in range(1, 31):
            residue = row(rytcm, "OAR", technology["TechId"], COMM["residue"], MoId=mode)
            for year in YEARS:
                expected = sum(row(rytcm, "OAR", technology["TechId"], crop, MoId=mode)[year] * factor
                               for crop, factor in residue_factors.items())
                assert abs(residue[year] - expected) < 1e-12

    # The exogenous crop-product demands alone make the FIT stock's full-load
    # fuel need feasible; no crop output or biomass generation minimum is used.
    crop_demands = read(candidate / "RYC.json")
    residue_floor_2020 = sum(row(crop_demands, "AAD", commodity=crop)["2020"] * factor
                             for crop, factor in residue_factors.items())
    biomass_af = row(cr, "AF", TECH["biomass_fit"])["2020"]
    biomass_rc = row(cr, "RC", TECH["biomass_fit"])["2020"]
    biomass_activity_max = biomass_rc * 31.536 * biomass_af
    biomass_fuel_ratio = row(rytcm, "IAR", TECH["biomass_fit"], COMM["residue"], MoId=1)["2020"]
    biomass_fuel_need = biomass_activity_max * biomass_fuel_ratio
    assert residue_floor_2020 > biomass_fuel_need

    offgrid_oil_af = row(cr, "AF", TECH["oil_off"])["2020"]
    offgrid_oil_rc = row(cr, "RC", TECH["oil_off"])["2020"]
    offgrid_oil_max = offgrid_oil_rc * 31.536 * offgrid_oil_af
    offgrid_sales_2020 = offgrid["2020"]
    oil_output_ratio = row(rytcm, "OAR", TECH["oil_off"], COMM["offgrid"], MoId=1)["2020"]
    assert offgrid_oil_max * oil_output_ratio > offgrid_sales_2020

    report = {
        "status": "passed", "baseline": str(baseline), "candidate": str(candidate),
        "changed_source_files": sorted(changed),
        "structure": {"technologies_added": 5, "commodities_added": 2, "constraints_added": 0},
        "stock_split_checks": stock_checks,
        "offgrid_demand_2020_2024": demand_checks[:5],
        "offgrid_profile_sum_range": [min(profile_sums.values()), max(profile_sums.values())],
        "hydro_annual_raw_cf": hydro_means,
        "biomass_2020": {"minimum_residue_from_crop_demands_pj": residue_floor_2020,
                         "full_load_residue_need_pj": biomass_fuel_need,
                         "full_load_generation_pj": biomass_activity_max},
        "offgrid_oil_2020": {"gross_activity_ceiling_pj": offgrid_oil_max,
                             "delivered_sales_ceiling_pj": offgrid_oil_max * oil_output_ratio,
                             "final_sales_demand_pj": offgrid_sales_2020},
        "checks": {
            "source_allowlist": "passed", "stock_conservation_every_year": "passed",
            "demand_reallocation_every_year": "passed", "no_generation_bounds": "passed",
            "closed_new_stock_classes": "passed", "hydro_profile_mean": "passed",
            "crop_residue_coefficients": "passed", "offgrid_capacity_adequacy": "passed",
            "sensitivity_runs": 0,
        },
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
