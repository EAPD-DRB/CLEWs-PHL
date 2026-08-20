#!/usr/bin/env python3
"""Apply the minimal non-forcing Philippines v20 power calibration candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path


YEARS = [str(year) for year in range(2020, 2054)]
TECHNOLOGIES = {
    "coal_old": "TEC_pyjfk",
    "gas_old": "TEC_ze7d4",
    "oil_old": "TEC_2hnym",
    "biomass_old": "TEC_gthhk",
    "gas_extraction": "TEC_6rwx6",
}
GAS_POWER_INPUT_PJ_PER_PJ = 1.870042735
GAS_PROCESSING_INPUT_PJ_PER_PJ = 1.056771911
DEPENDABLE_CAPACITY = {
    "coal_old": {"installed_mw": 10943.9, "dependable_mw": 10245.3},
    "gas_old": {"installed_mw": 3452.5, "dependable_mw": 3286.1},
    "oil_old": {"installed_mw": 4236.6, "dependable_mw": 3053.6},
    "biomass_old": {"installed_mw": 447.4, "dependable_mw": 285.4},
}
EXPECTED_BEFORE = {
    "af": {name: 1 for name in DEPENDABLE_CAPACITY},
    "gas_old_fixed_cost": {"2020": 22, "2021": 22},
    "gas_extraction_variable_cost": {
        "2020": 6.662111756970275,
        "2021": 6.68807478018528,
    },
    "gas_old_variable_cost": {"2020": 0.0001, "2021": 0.0001},
    "gas_extraction_t137": {
        "2020": 154.9184424432652,
        "2021": 132.3548618308677,
    },
    "gas_old_capacity": {"2020": 3.4525, "2021": 3.4525},
}
def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")


def row(table: dict, parameter: str, technology: str, *, mode: int | None = None) -> dict:
    matches = [
        item
        for item in table[parameter]["SC_0"]
        if item.get("TechId") == technology and (mode is None or item.get("MoId") == mode)
    ]
    if len(matches) != 1:
        raise AssertionError((parameter, technology, mode, len(matches)))
    return matches[0]


def assert_inheritance(table: dict, parameter: str, technology: str, years: list[str], *, mode: int | None = None) -> None:
    for scenario in ("SC_3hgjb", "SC_w03qj", "SC_huc7i"):
        target = [
            item
            for item in table[parameter][scenario]
            if item.get("TechId") == technology and (mode is None or item.get("MoId") == mode)
        ]
        if len(target) != 1:
            raise AssertionError((parameter, technology, scenario, len(target)))
        for year in years:
            if target[0][year] is not None:
                raise AssertionError((parameter, technology, scenario, year, target[0][year]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    case = args.case.resolve()
    gen_path = case / "genData.json"
    ryt_path = case / "RYT.json"
    rytm_path = case / "RYTM.json"
    before_hashes = {path.name: digest(path) for path in (gen_path, ryt_path, rytm_path)}
    gen_data, ryt, rytm = read(gen_path), read(ryt_path), read(rytm_path)

    if gen_data["osy-casename"] != "Philippines_v19":
        raise AssertionError(gen_data["osy-casename"])
    gen_data["osy-casename"] = "Philippines_v20"
    gen_data["osy-date"] = date.today().isoformat()
    gen_data["osy-desc"] = (
        "Philippines v20 minimal endogenous power-history calibration. Existing coal, gas, oil, "
        "and biomass availability is limited by DOE 2020 dependable capacity. The 2020-2021 "
        "Malampaya take-or-pay payment is represented as a sunk fixed cost on the closed legacy "
        "gas fleet and a matching plant-specific contract credit, while other gas users retain the "
        "sourced fuel price. No generation, fuel-share, or capacity-addition target is imposed.\n\n"
        + gen_data["osy-desc"]
    )

    af_changes = []
    for name, capacities in DEPENDABLE_CAPACITY.items():
        technology = TECHNOLOGIES[name]
        target = row(ryt, "AF", technology)
        assert_inheritance(ryt, "AF", technology, YEARS)
        for year in YEARS:
            if target[year] != EXPECTED_BEFORE["af"][name]:
                raise AssertionError((name, year, target[year]))
        value = capacities["dependable_mw"] / capacities["installed_mw"]
        for year in YEARS:
            target[year] = value
        af_changes.append({"technology": technology, "before": 1, "after": value, **capacities})

    gas_fc = row(ryt, "FC", TECHNOLOGIES["gas_old"])
    gas_rc = row(ryt, "RC", TECHNOLOGIES["gas_old"])
    gas_extraction_vc = row(rytm, "VC", TECHNOLOGIES["gas_extraction"], mode=1)
    gas_power_vc = row(rytm, "VC", TECHNOLOGIES["gas_old"], mode=1)
    gas_tau = row(ryt, "TAU", TECHNOLOGIES["gas_extraction"])
    assert_inheritance(ryt, "FC", TECHNOLOGIES["gas_old"], ["2020", "2021"])
    assert_inheritance(rytm, "VC", TECHNOLOGIES["gas_old"], ["2020", "2021"], mode=1)

    top_changes = []
    for year in ("2020", "2021"):
        assert gas_fc[year] == EXPECTED_BEFORE["gas_old_fixed_cost"][year]
        assert gas_rc[year] == EXPECTED_BEFORE["gas_old_capacity"][year]
        assert gas_extraction_vc[year] == EXPECTED_BEFORE["gas_extraction_variable_cost"][year]
        assert gas_power_vc[year] == EXPECTED_BEFORE["gas_old_variable_cost"][year]
        assert gas_tau[year] == EXPECTED_BEFORE["gas_extraction_t137"][year]
        raw_gas_per_power_activity = GAS_POWER_INPUT_PJ_PER_PJ * GAS_PROCESSING_INPUT_PJ_PER_PJ
        plant_contract_credit = gas_extraction_vc[year] * raw_gas_per_power_activity
        added_fixed_cost = gas_tau[year] * gas_extraction_vc[year] / gas_rc[year]
        after_fixed_cost = gas_fc[year] + added_fixed_cost
        after_power_variable_cost = gas_power_vc[year] - plant_contract_credit
        top_changes.append(
            {
                "year": int(year),
                "gas_envelope_pj": gas_tau[year],
                "gas_extraction_variable_cost_musd_per_pj_unchanged": gas_extraction_vc[year],
                "raw_gas_input_per_pj_power_activity": raw_gas_per_power_activity,
                "before_power_variable_cost_musd_per_pj": gas_power_vc[year],
                "plant_contract_credit_musd_per_pj": plant_contract_credit,
                "after_power_variable_cost_musd_per_pj": after_power_variable_cost,
                "before_fixed_cost_musd_per_gw_year": gas_fc[year],
                "added_sunk_cost_musd_per_gw_year": added_fixed_cost,
                "after_fixed_cost_musd_per_gw_year": after_fixed_cost,
                "legacy_gas_capacity_gw": gas_rc[year],
            }
        )
        gas_fc[year] = after_fixed_cost
        gas_power_vc[year] = after_power_variable_cost

    write(gen_path, gen_data)
    write(ryt_path, ryt)
    write(rytm_path, rytm)
    after_hashes = {path.name: digest(path) for path in (gen_path, ryt_path, rytm_path)}

    manifest = {
        "case": str(case),
        "date": date.today().isoformat(),
        "classification": {
            "doe_2020_installed_capacity": "initial stock cross-check",
            "doe_2020_dependable_capacity": "continuing physical availability driver",
            "malampaya_take_or_pay": "historical contractual/economic driver",
            "doe_2020_2024_gross_generation": "benchmark only",
        },
        "changed_source_files": ["genData.json", "RYT.json", "RYTM.json"],
        "before_sha256": before_hashes,
        "after_sha256": after_hashes,
        "availability_changes": af_changes,
        "take_or_pay_changes": top_changes,
        "prohibited_changes_confirmed_absent": [
            "TotalTechnologyAnnualActivityLowerLimit",
            "TotalTechnologyAnnualActivityUpperLimit",
            "technology generation shares",
            "realized post-2020 capacity additions",
        ],
    }
    manifest_path = args.manifest or case / "documentation" / "power_calibration_v20_build_manifest.json"
    write(manifest_path, manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
