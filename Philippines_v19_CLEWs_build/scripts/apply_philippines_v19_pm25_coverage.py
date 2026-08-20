#!/usr/bin/env python3
"""Add source-traceable PM2.5 factors to existing Philippines technologies."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import date
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parent
CASE = REPO / "case" / "Philippines_v19"
SOURCE_CASE = REPO / "case" / "Philippines_v18"
PM25 = "EMI_xpvk3"
YEARS = [str(year) for year in range(2020, 2054)]
MODES = range(1, 31)

# EMEP/EEA Guidebook Tier 1 factors. Values are on fuel-input basis.
# 1 g/GJ * 1 PJ = 0.001 kt.
INDUSTRY_EF_G_PER_GJ = {"OIL": 20.0, "NG": 0.78, "COAL": 108.0, "BIOM": 140.0}
SMALL_COMBUSTION_EF_G_PER_GJ = {"OIL": 18.0, "NG": 0.78, "COAL": 108.0, "BIOM": 160.0}
ENERGY_INDUSTRIES_EF_G_PER_GJ = {"NG": 0.14, "COAL": 3.4, "BIOM": 133.0}

# EMEP/EEA 2025 Tier 1 tyre+brake and road-surface wear, g/vehicle-km.
# Because road activity is 10^9 vehicle-km, g/km is numerically kt/10^9 km.
ROAD_NONEXHAUST_KT_PER_BILLION_VKM = {
    "23WHEEL": 0.0034 + 0.0016,
    "CAR": 0.0093 + 0.0041,
    "VAN": 0.0139 + 0.0057,
    "TRUL": 0.0139 + 0.0057,
    "BUS": 0.0316 + 0.0205,
    "TRUH": 0.0316 + 0.0205,
}

ROAD_POWERTRAINS = {
    "23WHEEL": ("ELE", "LIQ", "NG"),
    "CAR": ("ELE", "LIQ", "NG", "H2", "PHEV"),
    "VAN": ("ELE", "LIQ", "NG", "H2", "PHEV"),
    "BUS": ("ELE", "LIQ", "NG", "H2", "PHEV"),
    "TRUL": ("ELE", "LIQ", "NG", "H2", "PHEV"),
    "TRUH": ("ELE", "LIQ", "NG", "H2", "PHEV"),
}

INHERITED_ROAD_EXHAUST = {
    "PHL_TRA_23WHEEL_LIQ": 0.006213,
    "PHL_TRA_CAR_LIQ": 0.006867,
    "PHL_TRA_VAN_LIQ": 0.02725,
    "PHL_TRA_BUS_LIQ": 0.095375,
    "PHL_TRA_TRUL_LIQ": 0.0327,
    "PHL_TRA_TRUH_LIQ": 0.08175,
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    gen_path = CASE / "genData.json"
    rytem_path = CASE / "RYTEM.json"
    rytcm_path = CASE / "RYTCM.json"
    if not all(path.is_file() for path in (gen_path, rytem_path, rytcm_path)):
        raise FileNotFoundError("Philippines_v19 must be copied completely from Philippines_v18 first")

    before_hashes = {path.name: sha256(path) for path in CASE.glob("*.json")}
    source_hashes = {path.name: sha256(path) for path in SOURCE_CASE.glob("*.json")}
    if before_hashes != source_hashes:
        raise AssertionError("Philippines_v19 input must be an exact JSON copy of canonical Philippines_v18")
    gen = read_json(gen_path)
    rytem = read_json(rytem_path)
    rytcm = read_json(rytcm_path)
    tech_by_name = {row["Tech"]: row for row in gen["osy-tech"]}
    name_by_id = {row["TechId"]: row["Tech"] for row in gen["osy-tech"]}

    iar_rows = {
        (row["TechId"], row["CommId"], row["MoId"]): row
        for row in rytcm["IAR"]["SC_0"]
    }
    commodity_by_name = {row["Comm"]: row["CommId"] for row in gen["osy-comm"]}

    existing_ear = {
        (scenario, row["TechId"], row["EmisId"], row["MoId"]): row
        for scenario, rows in rytem["EAR"].items() for row in rows
    }
    existing_eacr = {
        (scenario, row["TechId"], row["EmisId"], row["MoId"]): row
        for scenario, rows in rytem["EACR"].items() for row in rows
    }
    changes: dict[str, dict] = {}

    def link_pm25(tech_name: str) -> str:
        tech = tech_by_name[tech_name]
        if PM25 not in tech["EAR"]:
            tech["EAR"].append(PM25)
        return tech["TechId"]

    def set_factor(tech_name: str, values: dict[str, float], method: str, source: str) -> None:
        tech_id = link_pm25(tech_name)
        old_mode1 = existing_ear.get(("SC_0", tech_id, PM25, 1))
        old_values = {year: float(old_mode1[year]) for year in YEARS} if old_mode1 else {year: 0.0 for year in YEARS}
        for scenario in rytem["EAR"]:
            for mode in MODES:
                ear_key = (scenario, tech_id, PM25, mode)
                eacr_key = (scenario, tech_id, PM25, mode)
                if ear_key not in existing_ear:
                    row = {"TechId": tech_id, "EmisId": PM25, "MoId": mode}
                    row.update({year: None for year in YEARS})
                    rytem["EAR"][scenario].append(row)
                    existing_ear[ear_key] = row
                if eacr_key not in existing_eacr:
                    row = {"TechId": tech_id, "EmisId": PM25, "MoId": mode}
                    row.update({year: None for year in YEARS})
                    rytem["EACR"][scenario].append(row)
                    existing_eacr[eacr_key] = row
                for year in YEARS:
                    if scenario == "SC_0":
                        existing_ear[ear_key][year] = float(values[year]) if mode == 1 else 0.0
                        existing_eacr[eacr_key][year] = 0.0
        changes[tech_name] = {
            "tech_id": tech_id,
            "method": method,
            "source": source,
            "old_2020": old_values["2020"],
            "new_2020": values["2020"],
            "new_2030": values["2030"],
            "new_2053": values["2053"],
        }

    def fuel_based(tech_name: str, commodity: str, ef: float, method: str, source: str) -> None:
        tech_id = tech_by_name[tech_name]["TechId"]
        comm_id = commodity_by_name[commodity]
        iar = iar_rows.get((tech_id, comm_id, 1))
        if iar is None:
            raise KeyError(f"missing mode-1 fuel input for {tech_name}: {commodity}")
        values = {year: ef * float(iar[year]) * 0.001 for year in YEARS}
        set_factor(tech_name, values, method, source)

    # Manufacturing combustion: other-industry process heat only. Aggregator,
    # electric and hydrogen routes are excluded because there is no direct PM factor.
    for temperature in ("LPH", "HPH"):
        for fuel, commodity in (("OIL", "PHL_PRO_OIL"), ("NG", "PHL_PRO_NG"),
                                ("COAL", "PHL_PRO_COAL"), ("BIOM", "PHL_PRO_BIOM")):
            fuel_based(
                f"PHL_INDU_OTH{temperature}_{fuel}", commodity, INDUSTRY_EF_G_PER_GJ[fuel],
                "EEA industry Tier 1 fuel-input factor × endogenous IAR × 0.001",
                "SRC_EEA_2023_INDUSTRY_COMBUSTION",
            )
    for fuel, commodity in (("NG", "PHL_PRO_NG"), ("COAL", "PHL_PRO_COAL"),
                            ("BIOM", "PHL_PRO_BIOM")):
        fuel_based(
            f"PHL_INDU_OTHHPH_{fuel}_CCS", commodity, INDUSTRY_EF_G_PER_GJ[fuel],
            "EEA industry Tier 1 fuel-input factor × endogenous CCS-route IAR × 0.001; no PM capture credit assumed",
            "SRC_EEA_2023_INDUSTRY_COMBUSTION",
        )

    # Commercial/service and agricultural stationary combustion.
    for fuel, commodity in (("OIL", "PHL_PRO_OIL"), ("NG", "PHL_PRO_NG"),
                            ("COAL", "PHL_PRO_COAL"), ("BIOM", "PHL_PRO_BIOM")):
        fuel_based(
            f"PHL_SER_HEAT_{fuel}", commodity, SMALL_COMBUSTION_EF_G_PER_GJ[fuel],
            "EEA small-combustion Tier 1 fuel-input factor × endogenous IAR × 0.001",
            "SRC_EEA_2023_SMALL_COMBUSTION",
        )
    for fuel, commodity in (("COAL", "PHL_PRO_COAL"), ("BIOM", "PHL_PRO_BIOM")):
        fuel_based(
            f"PHL_AGR_HEAT_{fuel}", commodity, SMALL_COMBUSTION_EF_G_PER_GJ[fuel],
            "EEA small-combustion Tier 1 fuel-input factor × endogenous IAR × 0.001",
            "SRC_EEA_2023_SMALL_COMBUSTION",
        )
    fuel_based(
        "PHL_HOU_COOK_NG", "PHL_PRO_NG", 1.2,
        "EEA residential gaseous-fuel Tier 1 factor × endogenous IAR × 0.001",
        "SRC_EEA_2023_SMALL_COMBUSTION",
    )

    # Agricultural motive power is represented by an explicit liquid-fuel input.
    # The retained fisheries evidence provides the consistent 43.1 GJ/t diesel NCV.
    agricultural_diesel_g_per_gj = 1913.0 / 43.1
    fuel_based(
        "PHL_AGR_MOT_LIQ", "PHL_PRO_LIQ", agricultural_diesel_g_per_gj,
        "EEA agriculture NRMM Tier 1 1913 g/t diesel ÷ 43.1 GJ/t × endogenous IAR × 0.001",
        "SRC_EEA_2023_NONROAD_MACHINERY;SRC_PHL_FISHERIES_DIESEL_BASIS",
    )

    # Power CCS routes: no particulate capture credit is inferred. The EEA
    # energy-industry Tier 1 combustion factor is applied to each route's fuel IAR.
    for suffix, commodity in (("NGCC", "PHL_PRO_NG"), ("COAL", "PHL_PRO_COAL"),
                              ("BIOM", "PHL_PRO_BIOM")):
        fuel = "NG" if suffix == "NGCC" else suffix
        fuel_based(
            f"PHL_POW_PP_{suffix}_CCS", commodity, ENERGY_INDUSTRIES_EF_G_PER_GJ[fuel],
            "EEA energy-industries Tier 1 fuel-input factor × endogenous CCS-route IAR × 0.001; no PM capture credit assumed",
            "SRC_EEA_2023_ENERGY_INDUSTRIES",
        )

    # Road non-exhaust PM applies to all powertrains. It is added to the six
    # liquid-route exhaust factors already present in v18 and is the only PM
    # component assigned to alternative-powertrain road technologies.
    for vehicle_class, powertrains in ROAD_POWERTRAINS.items():
        increment = ROAD_NONEXHAUST_KT_PER_BILLION_VKM[vehicle_class]
        for powertrain in powertrains:
            tech_name = f"PHL_TRA_{vehicle_class}_{powertrain}"
            tech_id = tech_by_name[tech_name]["TechId"]
            inherited_exhaust = INHERITED_ROAD_EXHAUST.get(tech_name, 0.0)
            values = {
                year: inherited_exhaust + increment
                for year in YEARS
            }
            set_factor(
                tech_name, values,
                "EEA 2025 Tier 1 tyre+brake plus road-surface wear; added to inherited exhaust where present",
                "SRC_EEA_2025_ROAD_NONEXHAUST",
            )

    # Fugitive coal PM: domestic extraction receives the combined mining and
    # handling factor; imports receive handling only. The activity is PJ coal.
    # With 22.1 GJ/t, kg/t divided by GJ/t is numerically kt/PJ.
    set_factor(
        "PHL_PRO_EXTR_COAL", {year: 0.005 / 22.1 for year in YEARS},
        "EEA Tier 1 mining+handling 0.005 kg/t ÷ retained 22.1 GJ/t",
        "SRC_EEA_2023_COAL_MINING_HANDLING;SRC_PHL_V18_FOSSIL_BORDER_INPUTS",
    )
    set_factor(
        "PHL_PRO_IMP_COAL", {year: 0.0003 / 22.1 for year in YEARS},
        "EEA imported-coal handling 0.3 g/t (=0.0003 kg/t) ÷ retained 22.1 GJ/t",
        "SRC_EEA_2023_COAL_MINING_HANDLING;SRC_PHL_V18_FOSSIL_BORDER_INPUTS",
    )

    # Identity and scope note only; no model structure, CO2e coefficient,
    # emission limit, penalty, cost, demand or capacity parameter is changed.
    gen["osy-casename"] = "Philippines_v19"
    gen["osy-date"] = date.today().isoformat()
    gen["osy-desc"] = (
        "Philippines v19 PM2.5 coverage extension. Adds source-traceable endogenous PM2.5 "
        "activity-emission ratios for existing combustion, road non-exhaust, and coal "
        "mining/handling technologies. CO2e, model structure, constraints, costs, demands, "
        "and capacities are unchanged.\n\n" + gen["osy-desc"]
    )

    write_json(gen_path, gen)
    write_json(rytem_path, rytem)
    after_hashes = {path.name: sha256(path) for path in CASE.glob("*.json")}
    changed_files = sorted(name for name in before_hashes if before_hashes[name] != after_hashes[name])
    if changed_files != ["RYTEM.json", "genData.json"]:
        raise AssertionError(f"unexpected changed source files: {changed_files}")

    snapshot = {
        "schema": "philippines-v19-pm25-coverage-v1",
        "date": date.today().isoformat(),
        "base_case": "case/Philippines_v18",
        "base_release": {
            "git_commit": "2735feb",
            "pull_time_local": "2026-08-19T10:09:18-04:00",
            "archive": "Philippines_v18_v18.0.1_MUIO.zip",
            "archive_sha256": "c3f4ee25d2e8c3315ced1be4bf819673859be45079536abb2cfbc40a65d1dc55",
            "note": "Exact working v18 baseline before the later 2020-2025 deployment-cap experiment.",
        },
        "case": "Philippines_v19",
        "emission": {"id": PM25, "name": "PM2_5", "unit": "kt"},
        "scope": "Additional endogenous PM2.5 factors for existing technologies only",
        "changed_source_files": changed_files,
        "technology_count": len(changes),
        "newly_linked_technology_count": sum(1 for item in changes.values() if item["old_2020"] == 0.0),
        "existing_factor_series_extended_count": sum(1 for item in changes.values() if item["old_2020"] != 0.0),
        "technologies": dict(sorted(changes.items())),
        "explicit_exclusions": {
            "PHL_AGR_HEAT_OIL;PHL_AGR_HEAT_NG": "no input-fuel link exists in RYTCM/genData, so a fuel-input factor cannot be mapped safely",
            "PHL_TRA_AVI_LIQ": "EEA states PM2.5 is aircraft- and payload-dependent; the model has no aircraft/LTO/CCD split",
            "PHL_TRA_RAIL*_ELE;PHL_TRA_RAIL*_H2": "the retained rail guidebook provides exhaust factors for diesel/gas oil, not drivetrain-neutral rail wear",
            "PHL_TRA_*_NG;PHL_TRA_*_PHEV": "road non-exhaust is included, but alternative-powertrain exhaust is not inferred without a fleet/standard split",
            "hydrogen;ammonia;fuel-processing technologies": "no defensible PM2.5 factor matching the aggregate model activity boundary was found",
            "crop-residue/waste burning;cement/process dust;road resuspension": "the model has no corresponding explicit activity technology; no residual inventory is introduced",
        },
        "non_changes": [
            "no CO2e factor changes", "no emission caps or penalties", "no exogenous emissions",
            "no technology or commodity additions", "no cost, demand, capacity, activity-bound, or solver changes",
        ],
        "before_sha256": before_hashes,
        "after_sha256": after_hashes,
    }
    snapshot_path = PACKAGE / "data_sources" / "snapshots" / "pm25_coverage_v19_2026-08-19.json"
    write_json(snapshot_path, snapshot)
    print(json.dumps({
        "status": "applied", "changed_files": changed_files,
        "technology_count": len(changes), "snapshot": str(snapshot_path),
    }, indent=2))


if __name__ == "__main__":
    main()
