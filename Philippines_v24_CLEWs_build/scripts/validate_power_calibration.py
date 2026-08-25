#!/usr/bin/env python3
"""Deterministically validate the Philippines v20 power-calibration candidate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


YEARS = [str(year) for year in range(2020, 2054)]
SOURCE_JSON = {
    "R.json", "RE.json", "RS.json", "RT.json", "RTSM.json", "RYC.json", "RYCTs.json",
    "RYCn.json", "RYDtb.json", "RYE.json", "RYS.json", "RYSeDt.json", "RYT.json",
    "RYTC.json", "RYTCM.json", "RYTCn.json", "RYTEM.json", "RYTM.json", "RYTTs.json",
    "RYTs.json", "genData.json",
}
TECH = {
    "coal": "TEC_pyjfk", "gas": "TEC_ze7d4", "oil": "TEC_2hnym",
    "biomass": "TEC_gthhk", "gas_extraction": "TEC_6rwx6",
}
GAS_POWER_INPUT_PJ_PER_PJ = 1.870042735
GAS_PROCESSING_INPUT_PJ_PER_PJ = 1.056771911
EXPECTED_AF = {
    "coal": 10245.3 / 10943.9,
    "gas": 3286.1 / 3452.5,
    "oil": 3053.6 / 4236.6,
    "biomass": 285.4 / 447.4,
}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row(table: dict, parameter: str, technology: str, *, mode: int | None = None) -> dict:
    matches = [item for item in table[parameter]["SC_0"]
               if item.get("TechId") == technology and (mode is None or item.get("MoId") == mode)]
    assert len(matches) == 1, (parameter, technology, mode, len(matches))
    return matches[0]


def cell_diffs(before: dict, after: dict, parameter: str) -> list[dict]:
    changes = []
    for scenario, before_rows in before[parameter].items():
        after_rows = after[parameter][scenario]
        assert len(before_rows) == len(after_rows)
        for row_index, (old, new) in enumerate(zip(before_rows, after_rows, strict=True)):
            assert old.keys() == new.keys()
            for key in old:
                if old[key] != new[key]:
                    changes.append({"scenario": scenario, "row": row_index, "field": key,
                                    "before": old[key], "after": new[key],
                                    "technology": old.get("TechId"), "mode": old.get("MoId")})
    return changes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline, candidate = args.baseline.resolve(), args.candidate.resolve()

    unchanged_files = []
    for name in sorted(SOURCE_JSON - {"genData.json", "RYT.json", "RYTM.json"}):
        assert sha256(baseline / name) == sha256(candidate / name), name
        unchanged_files.append(name)

    bg, cg = read(baseline / "genData.json"), read(candidate / "genData.json")
    identity_before = {key: bg[key] for key in ("osy-casename", "osy-desc", "osy-date")}
    identity_after = {key: cg[key] for key in ("osy-casename", "osy-desc", "osy-date")}
    bg_compare, cg_compare = dict(bg), dict(cg)
    for key in identity_before:
        bg_compare.pop(key)
        cg_compare.pop(key)
    assert bg_compare == cg_compare
    assert identity_before["osy-casename"] == "Philippines_v19"
    assert identity_after["osy-casename"] == "Philippines_v20"

    br, cr = read(baseline / "RYT.json"), read(candidate / "RYT.json")
    bm, cm = read(baseline / "RYTM.json"), read(candidate / "RYTM.json")
    ryt_changes = []
    for parameter in br:
        diffs = cell_diffs(br, cr, parameter)
        if diffs:
            ryt_changes.extend({"parameter": parameter, **diff} for diff in diffs)
    rytm_changes = []
    for parameter in bm:
        diffs = cell_diffs(bm, cm, parameter)
        if diffs:
            rytm_changes.extend({"parameter": parameter, **diff} for diff in diffs)

    assert len(ryt_changes) == 4 * len(YEARS) + 2, len(ryt_changes)
    assert {item["parameter"] for item in ryt_changes} == {"AF", "FC"}
    assert len(rytm_changes) == 2
    assert {item["parameter"] for item in rytm_changes} == {"VC"}
    assert all(item["scenario"] == "SC_0" for item in ryt_changes + rytm_changes)
    assert not cell_diffs(br, cr, "TAL")
    assert not cell_diffs(br, cr, "TAU")
    assert not cell_diffs(br, cr, "TAMinCI")
    assert not cell_diffs(br, cr, "TAMaxCI")

    for name, expected in EXPECTED_AF.items():
        af = row(cr, "AF", TECH[name])
        assert all(abs(af[year] - expected) < 1e-15 for year in YEARS)

    old_fc, new_fc = row(br, "FC", TECH["gas"]), row(cr, "FC", TECH["gas"])
    old_extraction_vc = row(bm, "VC", TECH["gas_extraction"], mode=1)
    new_extraction_vc = row(cm, "VC", TECH["gas_extraction"], mode=1)
    old_power_vc = row(bm, "VC", TECH["gas"], mode=1)
    new_power_vc = row(cm, "VC", TECH["gas"], mode=1)
    gas_tau = row(cr, "TAU", TECH["gas_extraction"])
    gas_rc = row(cr, "RC", TECH["gas"])
    payment_checks = []
    for year in ("2020", "2021"):
        assert new_extraction_vc[year] == old_extraction_vc[year]
        raw_per_power = GAS_POWER_INPUT_PJ_PER_PJ * GAS_PROCESSING_INPUT_PJ_PER_PJ
        full_envelope_power = gas_tau[year] / raw_per_power
        before = (gas_tau[year] * old_extraction_vc[year]
                  + full_envelope_power * old_power_vc[year]
                  + gas_rc[year] * old_fc[year])
        after = (gas_tau[year] * new_extraction_vc[year]
                 + full_envelope_power * new_power_vc[year]
                 + gas_rc[year] * new_fc[year])
        assert abs(before - after) < 1e-10, (year, before, after)
        payment_checks.append({"year": int(year), "full_envelope_cost_before_musd": before,
                               "full_envelope_cost_after_musd": after, "difference_musd": after - before})

    # The gas-fuel row is the only legacy-gas mode-1 IAR above one; water is separate.
    gas_rows = [item for item in read(candidate / "RYTCM.json")["IAR"]["SC_0"]
                if item.get("TechId") == TECH["gas"] and item.get("MoId") == 1]
    fuel_row = max(gas_rows, key=lambda item: item["2020"])
    assert fuel_row["2020"] == GAS_POWER_INPUT_PJ_PER_PJ
    processing_rows = [item for item in read(candidate / "RYTCM.json")["IAR"]["SC_0"]
                       if item.get("TechId") == "TEC_6m11x" and item.get("MoId") == 1]
    assert len(processing_rows) == 1
    assert processing_rows[0]["2020"] == GAS_PROCESSING_INPUT_PJ_PER_PJ
    gas_envelope_checks = []
    for year in ("2020", "2021"):
        max_from_fuel = gas_tau[year] / (fuel_row[year] * processing_rows[0][year])
        max_from_capacity = gas_rc[year] * 31.536 * row(cr, "AF", TECH["gas"])[year]
        assert max_from_fuel < max_from_capacity
        assert row(cr, "TAL", TECH["gas"])[year] == 0
        gas_envelope_checks.append({"year": int(year), "max_generation_from_gas_envelope_pj": max_from_fuel,
                                    "max_generation_from_dependable_capacity_pj": max_from_capacity,
                                    "generation_minimum_pj": 0})

    with args.benchmark.open(newline="", encoding="utf-8") as stream:
        benchmark = list(csv.DictReader(stream))
    assert len(benchmark) == 45
    for item in benchmark:
        assert abs(float(item["gross_generation_pj"]) - float(item["gross_generation_gwh"]) * 0.0036) < 1e-9
        assert item["model_role"] == "benchmark_only"

    report = {
        "status": "passed",
        "baseline": str(baseline),
        "candidate": str(candidate),
        "unchanged_source_files": unchanged_files,
        "identity_before": identity_before,
        "identity_after": identity_after,
        "source_delta": {"RYT_cells": len(ryt_changes), "RYTM_cells": len(rytm_changes),
                         "RYT_parameters": sorted({item["parameter"] for item in ryt_changes}),
                         "RYTM_parameters": sorted({item["parameter"] for item in rytm_changes})},
        "full_envelope_cost_identity": payment_checks,
        "gas_envelopes_are_upper_bounds_not_targets": gas_envelope_checks,
        "generation_benchmark_rows": len(benchmark),
        "generation_benchmark_boundaries": sorted({item["boundary"] for item in benchmark}),
        "checks": {
            "source_allowlist": "passed",
            "scenario_inheritance": "passed by apply script",
            "no_activity_or_investment_bound_change": "passed",
            "dependable_capacity_ratios": "passed",
            "take_or_pay_cost_reclassification": "passed",
            "generation_observations_benchmark_only": "passed",
        },
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
