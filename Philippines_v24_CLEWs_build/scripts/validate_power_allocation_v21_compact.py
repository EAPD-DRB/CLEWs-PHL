#!/usr/bin/env python3
"""Static validation for the compact Philippines v21 candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from apply_power_allocation_v21 import OFFGRID_SECTOR_SHARE, RESIDUE_PJ_PER_MT, YEARS
from apply_power_allocation_v21_compact import OFFGRID_BUILD_LIMIT_GW


T = {"oil": "TEC_2hnym", "hydro": "TEC_p3vu5", "solar": "TEC_1k064", "wind": "TEC_1wdli",
     "biomass": "TEC_gthhk", "off_oil": "TEC_v21oil", "off_re": "TEC_v21ore", "fit": "TEC_v21bio"}
C = {"off": "COM_v21off", "grid": "COM_o7vja"}
FILES = {"R.json", "RE.json", "RS.json", "RT.json", "RTSM.json", "RYC.json", "RYCTs.json", "RYCn.json",
         "RYDtb.json", "RYE.json", "RYS.json", "RYSeDt.json", "RYT.json", "RYTC.json", "RYTCM.json",
         "RYTCn.json", "RYTEM.json", "RYTM.json", "RYTTs.json", "RYTs.json", "genData.json"}
ALLOWED = {"RT.json", "RYC.json", "RYCTs.json", "RYT.json", "RYTCM.json", "RYTEM.json", "RYTM.json",
           "RYTTs.json", "genData.json"}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row(payload: dict, parameter: str, technology: str | None = None, commodity: str | None = None, **keys) -> dict:
    found = [item for item in payload[parameter]["SC_0"]
             if (technology is None or item.get("TechId") == technology)
             and (commodity is None or item.get("CommId") == commodity)
             and all(item.get(key) == value for key, value in keys.items())]
    assert len(found) == 1, (parameter, technology, commodity, keys, len(found))
    return found[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    b, c = args.baseline.resolve(), args.candidate.resolve()
    changed = {name for name in FILES if sha(b / name) != sha(c / name)}
    assert changed == ALLOWED
    bg, cg = read(b / "genData.json"), read(c / "genData.json")
    assert cg["osy-casename"] == "Philippines_v21"
    assert len(cg["osy-tech"]) == len(bg["osy-tech"]) + 3
    assert len(cg["osy-comm"]) == len(bg["osy-comm"]) + 1
    assert len(cg["osy-constraints"]) == len(bg["osy-constraints"])

    br, cr = read(b / "RYT.json"), read(c / "RYT.json")
    stock_errors = {}
    for family, off in (("oil", "off_oil"), ("biomass", "fit")):
        error = max(abs(row(cr, "RC", T[family])[y] + row(cr, "RC", T[off])[y] - row(br, "RC", T[family])[y])
                    for y in YEARS)
        assert error < 1e-12
        stock_errors[family] = error
    error = max(abs(row(cr, "RC", T["hydro"])[y] + row(cr, "RC", T["solar"])[y]
                    + row(cr, "RC", T["wind"])[y] + row(cr, "RC", T["off_re"])[y]
                    - row(br, "RC", T["hydro"])[y] - row(br, "RC", T["solar"])[y]
                    - row(br, "RC", T["wind"])[y]) for y in YEARS)
    assert error < 1e-12
    stock_errors["offgrid_renewables"] = error
    for technology in (T["off_oil"], T["off_re"], T["fit"]):
        assert all(row(cr, "TAL", technology)[y] == 0 for y in YEARS)
        assert all(row(cr, "TAMinCI", technology)[y] == 0 for y in YEARS)
    assert all(row(cr, "TAMaxCI", T["fit"])[y] == 0 for y in YEARS)
    for parameter in ("TAL", "TAU"):
        for old in br[parameter]["SC_0"]:
            assert row(cr, parameter, old["TechId"]) == old

    bc, cc = read(b / "RYC.json"), read(c / "RYC.json")
    off = row(cc, "SAD", commodity=C["off"])
    demand_error = max(abs(sum(row(bc, "SAD", commodity=comm)[y] - row(cc, "SAD", commodity=comm)[y]
                               for comm in OFFGRID_SECTOR_SHARE) - off[y]) for y in YEARS)
    assert demand_error < 1e-12
    profile = read(c / "RYCTs.json")
    profile_error = max(abs(sum(item[y] for item in profile["SDP"]["SC_0"] if item["CommId"] == C["off"]) - 1)
                        for y in YEARS)
    assert profile_error < 2e-7

    ysplit = {item["TsId"]: item for item in read(c / "RYTs.json")["YS"]["SC_0"]}
    cf = {item["TsId"]: item for item in read(c / "RYTTs.json")["CF"]["SC_0"] if item["TechId"] == T["hydro"]}
    hydro_mean = sum(cf[ts]["2020"] * ysplit[ts]["2020"] for ts in cf)
    assert abs(hydro_mean - 0.26438418) < 1e-7

    # Prove that the optional build envelopes leave enough active capacity to
    # meet the exogenous off-grid service in every year.  This catches the r2
    # contradiction: both routes were closed while residual stocks retired.
    rt = read(c / "RT.json")
    lives = rt["OL"]["SC_0"][0]
    rytcm = read(c / "RYTCM.json")
    annual_service_headroom = {}
    timeslice_service_headroom = {}
    service_failures = []
    demand_profiles = {item["TsId"]: item for item in profile["SDP"]["SC_0"]
                       if item["CommId"] == C["off"]}
    technology_profiles = {
        technology: {item["TsId"]: item for item in read(c / "RYTTs.json")["CF"]["SC_0"]
                     if item["TechId"] == technology}
        for technology in (T["off_oil"], T["off_re"])
    }
    for year in YEARS:
        total = 0.0
        capacities = {}
        for technology in (T["off_oil"], T["off_re"]):
            investment_row = row(cr, "TAMaxCI", technology)
            active_build = sum(investment_row[vintage] for vintage in YEARS
                               if int(vintage) <= int(year) < int(vintage) + lives[technology])
            capacity = row(cr, "RC", technology)[year] + active_build
            capacities[technology] = capacity
            af = row(cr, "AF", technology)[year]
            mean_cf = sum(item[year] * ysplit[item["TsId"]][year]
                          for item in technology_profiles[technology].values())
            oar = row(rytcm, "OAR", technology, C["off"], MoId=1)[year]
            total += capacity * 31.536 * min(af, mean_cf) * oar
        annual_service_headroom[year] = total - off[year]
        if annual_service_headroom[year] <= 0:
            service_failures.append({
                "year": year, "level": "annual",
                "service_headroom_pj": annual_service_headroom[year],
                "reason": "exogenous off-grid demand exceeds the maximum stock-and-vintage service envelope",
            })
        for ts in demand_profiles:
            deliverable = 0.0
            for technology, capacity in capacities.items():
                cf_value = technology_profiles[technology][ts][year]
                oar = row(rytcm, "OAR", technology, C["off"], MoId=1)[year]
                deliverable += capacity * 31.536 * cf_value * ysplit[ts][year] * oar
            headroom = deliverable - off[year] * demand_profiles[ts][year]
            timeslice_service_headroom[f"{year}:{ts}"] = headroom
            if headroom <= 0:
                service_failures.append({
                    "year": year, "timeslice": ts, "level": "timeslice",
                    "service_headroom_pj": headroom,
                    "reason": "off-grid demand profile exceeds the maximum capacity-timeslice envelope",
                })
    if service_failures:
        failed_report = {
            "status": "failed_before_optimization", "candidate": str(c),
            "check": "every-year/every-timeslice off-grid stock-vintage-service envelope",
            "first_failure": service_failures[0], "failure_count": len(service_failures),
            "optimizer_runs_required_to_detect": 0,
        }
        args.output.write_text(json.dumps(failed_report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(failed_report, indent=2))
        raise AssertionError(failed_report)
    for technology, limits in OFFGRID_BUILD_LIMIT_GW.items():
        assert all(row(cr, "TAMaxCI", technology)[y] == limits[y] for y in YEARS)

    crop_demand = read(c / "RYC.json")
    biomass_iar = row(rytcm, "IAR", T["fit"], "COM_0", MoId=1)
    resource_checks = {}
    for year in YEARS:
        residue = sum(row(crop_demand, "AAD", commodity=crop)[year] * factor
                      for crop, factor in RESIDUE_PJ_PER_MT.items())
        activity_cap = row(cr, "TAU", T["fit"])[year]
        assert abs(activity_cap * biomass_iar[year] - residue) < 1e-10
        resource_checks[year] = {"residue_pj": residue, "activity_ceiling_pj": activity_cap}
    capacity_ceiling = row(cr, "RC", T["fit"])["2020"] * 31.536 * row(cr, "AF", T["fit"])["2020"]
    assert resource_checks["2020"]["activity_ceiling_pj"] > capacity_ceiling

    report = {
        "status": "passed", "baseline": str(b), "candidate": str(c),
        "changed_source_files": sorted(changed),
        "structure": {"technologies_added": 3, "commodities_added": 1, "constraints_added": 0},
        "max_stock_identity_error_gw": stock_errors, "max_demand_identity_error_pj": demand_error,
        "max_profile_sum_error": profile_error, "hydro_raw_annual_cf": hydro_mean,
        "minimum_annual_offgrid_service_headroom_pj": min(annual_service_headroom.values()),
        "minimum_timeslice_offgrid_service_headroom_pj": min(timeslice_service_headroom.values()),
        "biomass_2020": {**resource_checks["2020"], "capacity_ceiling_pj": capacity_ceiling},
        "checks": {"no_generation_bounds": "passed", "offgrid_replacement_envelope": "passed",
                   "fit_stock_closed_to_new_build": "passed",
                   "physical_residue_ceiling": "passed", "sensitivity_runs": 0},
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
