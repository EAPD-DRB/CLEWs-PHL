#!/usr/bin/env python3
"""Build and validate the Philippines vIS1.5 water-cost boundary correction."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
import time
import types
from datetime import date
from decimal import Decimal, getcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP" / "DataStorage"
SOURCE = STORAGE / ".Philippines_vIS14-water-infrastructure-candidate-20260831"
TARGET = STORAGE / ".Philippines_vIS15-water-boundary-candidate-20260831"
BASELINE_RUN = SOURCE / "res" / "BASE_VIS14_WATER_INFRASTRUCTURE"
RUN_NAME = "BASE_VIS15_WATER_BOUNDARY"
MODEL = ROOT / "WebAPP" / "SOLVERs" / "model.v.5.4.txt"
YEARS = tuple(str(year) for year in range(2020, 2054))
BASE = "SC_0"

OLD_SUR = "PHL_DEM_PWR_SUR_WAT"
OLD_GWT = "PHL_DEM_PWR_GWT_WAT"
OFF_SUR = "PHL_DEM_PWR_SUR_WAT_OFF"
OFF_GWT = "PHL_DEM_PWR_GWT_WAT_OFF"
OLD_COMM = "PHL_PWR_WAT"
OFF_COMM = "PHL_PWR_WAT_OFF"
PUBLIC_SUR = "PHL_DEM_PUB_SUR_WAT"
PUBLIC_GWT = "PHL_DEM_PUB_GWT_WAT"

getcontext().prec = 30
PHL_CPI_2015 = Decimal("115.429504132997")
PHL_CPI_2020 = Decimal("132.7240608691")
PHP_PER_USD_2020 = Decimal("49.62")
SECONDS_PER_YEAR = Decimal("31536000")
MUNICIPAL_LEVEL_III_FEE = Decimal("16.80")
PUBLIC_VC = float(
    MUNICIPAL_LEVEL_III_FEE
    * PHL_CPI_2020 / PHL_CPI_2015
    / (SECONDS_PER_YEAR / Decimal("1000"))
    / PHP_PER_USD_2020
    * Decimal("1000")
)

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(ROOT / "API"))

from Classes.Base import Config  # noqa: E402
from Classes.Case.DataFileClass import DataFile  # noqa: E402
from Classes.Case.OsemosysClass import Osemosys  # noqa: E402
from Classes.Case.UpdateCaseClass import UpdateCase  # noqa: E402


_spec = importlib.util.spec_from_file_location(
    "philippines_vis14_water_costs", ROOT / "scripts" / "philippines_vis14_water_costs.py"
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load vIS1.4 validation helpers")
_v14 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_v14)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def append_rows(path: Path, rows: list[dict]) -> None:
    with path.open(newline="", encoding="utf-8") as stream:
        header = next(csv.reader(stream))
    for row in rows:
        if set(row) != set(header):
            raise RuntimeError(f"schema mismatch in {path.name}: {set(header) ^ set(row)}")
    with path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=header)
        writer.writerows(rows)


def technology_map(gen: dict) -> dict[str, str]:
    return {row["Tech"]: row["TechId"] for row in gen["osy-tech"]}


def commodity_map(gen: dict) -> dict[str, str]:
    return {row["Comm"]: row["CommId"] for row in gen["osy-comm"]}


def source_document() -> str:
    return f"""# Philippines vIS1.5 water-cost boundary and OFF identity correction

Date: 2026-08-31
Parent: Philippines vIS1.4 BASE-only candidate
Status: candidate; not promoted

## Equation-first classification

The affected technologies remain physical source-intake/pump assets. Capital cost, fixed O&M,
operational life, input-output ratios, capacity limits, resource caps, demands, and model equations
are unchanged. The two public-water `VariableCost` coefficients are economic drivers. No observed
activity, source share, dispatch, capacity, or seasonal pattern is imposed.

The pre-split national cooling-water routes are renamed in place as `{OFF_SUR}` and `{OFF_GWT}`,
and their output commodity as `{OFF_COMM}`. Their stable internal IDs and all parameters are
preserved. This makes their actual sole consumer, `PHL_POW_CHP_OIL_OFFGRID`, explicit without
changing the matrix structure or pretending that OFF belongs to an island.

## Public abstraction cost boundary

vIS1.4 used the midpoint marginal operating cost of pump-fed Philippine water districts. That
source covers utility-wide operating expenditure, including administration, staff, treatment or
distribution effects, and growth in fixed expenditure. It is not an abstraction-only coefficient
and partly overlaps the separate fixed O&M now placed on the physical pump asset.

vIS1.5 instead applies the current NWRB/LLDA municipal Level III annual water charge for permitted
flows above 7,000 L/s: PHP16.80 per L/s-year. The PHP5,000 base charge is excluded because it is not
activity-proportional. Converted with Philippine CPI and the BSP 2020 exchange rate:

`16.80 * CPI_2020/CPI_2015 / 31,536 / 49.62 * 1,000 = {PUBLIC_VC:.15g} MUSD/km3`.

The same raw-water charge is used for public surface and groundwater abstraction. It excludes
asset cost, fixed O&M, treatment, distribution, administration, and pumping electricity; the last
remains an endogenous input on the groundwater route. Thus capital, fixed, variable, and energy
terms have non-overlapping boundaries.

## CapacityFactor and island costs

`CapacityFactor` remains 1.0. NIA evidence confirms that irrigation follows cropping calendars and
system-specific water-delivery schedules, including shutdowns, but no national schedule maps those
operations to the model's two representative seasons and worst-day block. A fabricated profile
would impose false physical availability merely to alter solver numerics. The flat profile and its
timeslice degeneracy are disclosed pending a national or scheme-weighted series.

LUZ, VIS, and MIN asset costs remain equal. These routes produce separate node commodities and do
not directly substitute. No public island-specific abstraction cost series was found, so numerical
differentiation would be invented.

## Changed source objects

- `genData.json`: vIS1.5 identity; two national route labels and one commodity label changed to OFF
  through `UpdateCase`; stable IDs, memberships and mappings retained.
- `RYTM.json / VC / SC_0`: `{PUBLIC_SUR}` and `{PUBLIC_GWT}`, mode 1, 2020-2053 set to
  `{PUBLIC_VC:.15g}` MUSD/km3. Policy overlays remain null and inherit BASE.
- Canonical schema-ledger rows document the source, calculation, maps, change, and unresolved
  timeslice/island data gaps.

## Validation contract

The source pre-flight must prove the diff is limited to the three OFF labels, identity metadata,
and two public VC rows; preserve every physical coefficient and cap membership; and demonstrate
feasibility from the retained vIS1.4 solution because only positive objective coefficients fall.
Generation, preprocessing, and `glpsol --check` must pass before one CBC BASE run with a 300-second
limit. No policy scenario, seal, promotion, or second optimizer run is authorized.
"""


def write_ledger() -> dict[str, int]:
    ledger = TARGET / "data_sources"
    append_rows(ledger / "SOURCES.csv", [{
        "source_id": "SRC_PHL_VIS15_NWRB_MUNICIPAL_CHARGE",
        "provider": "Laguna Lake Development Authority / National Water Resources Board",
        "product": "2024-2025 Citizen's Charter: annual water charges",
        "edition": "current schedule published 2024-2025",
        "reference_period": "fee schedule adopted 2015 and retained in current charter",
        "geography": "Philippines",
        "variable": "Municipal Level III permitted-withdrawal charge above 7000 L/s",
        "source_unit": "PHP per L/s-year",
        "exact_locator": "Annual Water Charges table: Municipal Level III, >7000 L/s = PHP16.80; base cost PHP5000",
        "url": "https://llda.gov.ph/wp-content/uploads/dox/citizens_charter/2024-2025%20Citizen%27s%20Charter.pdf",
        "access_date": "2026-08-31",
        "license": "",
        "sha256": "",
        "local_file": "water_boundary_vIS15_2026-08-31/SOURCES.csv",
        "notes": "Only the flow-proportional charge is used; the fixed base charge is excluded.",
    }, {
        "source_id": "SRC_PHL_VIS15_NIA_SEASONAL_SCHEDULE_GAP",
        "provider": "Philippines National Irrigation Administration",
        "product": "National and regional irrigation operations and water-delivery schedules",
        "edition": "2019 year-end report and 2026 regional schedule examples",
        "reference_period": "dry, wet and third-crop seasons",
        "geography": "Philippines; system-specific regional examples",
        "variable": "Evidence that irrigation delivery is seasonal and system-specific",
        "source_unit": "cropping season and irrigated hectares",
        "exact_locator": "NIA 2019 year-end report p.13; regional SMC schedules disclose locally varying delivery and shutdown dates",
        "url": "https://nia.gov.ph/sites/default/files/pdf_reader/CY%202019_year-end-report.pdf",
        "access_date": "2026-08-31",
        "license": "",
        "sha256": "",
        "local_file": "water_boundary_vIS15_2026-08-31/SOURCES.csv",
        "notes": "Used to reject an invented national CapacityFactor shape, not to set a coefficient.",
    }])
    append_rows(ledger / "ASSUMPTIONS.csv", [{
        "assumption_id": "ASM_PHL_VIS15_PUBLIC_RAW_WATER_BOUNDARY",
        "statement": "Use only the flow-proportional NWRB municipal Level III resource charge on public abstraction assets.",
        "central_value": "16.80",
        "unit": "PHP2015 per L/s-year",
        "evidence_source_ids": "SRC_PHL_VIS15_NWRB_MUNICIPAL_CHARGE",
        "lower_bound": "",
        "upper_bound": "",
        "rationale": "Matches the physical raw-water abstraction boundary and excludes utility-wide O&M and asset costs.",
        "notes": "Applied equally to surface and groundwater; groundwater electricity remains endogenous.",
    }, {
        "assumption_id": "ASM_PHL_VIS15_KEEP_FLAT_CF",
        "statement": "Retain CapacityFactor=1 until a national or scheme-weighted pumping schedule can be mapped to model timeslices.",
        "central_value": "1",
        "unit": "fraction",
        "evidence_source_ids": "SRC_PHL_VIS15_NIA_SEASONAL_SCHEDULE_GAP",
        "lower_bound": "",
        "upper_bound": "",
        "rationale": "Published delivery schedules vary by system and cropping season; a single national shape would be fabricated.",
        "notes": "The known 18-timeslice degeneracy is disclosed rather than hidden with an epsilon profile.",
    }])
    append_rows(ledger / "CALCULATIONS.csv", [{
        "calculation_id": "CALC_PHL_VIS15_PUBLIC_WITHDRAWAL_VC",
        "formula": "16.80*PHL_CPI2020/PHL_CPI2015/31536/49.62*1000",
        "source_ids": "SRC_PHL_VIS15_NWRB_MUNICIPAL_CHARGE;SRC_VIS14_WB_CPI;SRC_VIS14_BSP_FX_2020",
        "assumption_ids": "ASM_PHL_VIS15_PUBLIC_RAW_WATER_BOUNDARY;ASM_PHL_VIS14_CONSTANT_2020_USD",
        "input_calculation_ids": "",
        "input_values": "16.80;132.7240608691;115.429504132997;31536;49.62;1000",
        "input_units": "PHP2015/(L/s-year);CPI;CPI;m3/(L/s-year);PHP/USD;MUSD/km3 per USD/m3",
        "output_value": f"{PUBLIC_VC:.15g}",
        "output_unit": "MUSD/km3",
        "script_path": "scripts/philippines_vis15_water_boundary.py",
        "script_version": "vIS1.5",
        "notes": "Same coefficient for public surface and groundwater; fixed permit, assets, fixed O&M and electricity excluded.",
    }])
    maps = []
    for tech in (PUBLIC_SUR, PUBLIC_GWT):
        maps.append({
            "map_id": f"MAP_PHL_VIS15_{tech}_VC",
            "model_file": "RYTM.json", "parameter": "VC", "entity": tech, "mode": "1",
            "scenario": BASE, "years": "2020-2053", "value_or_expression": f"{PUBLIC_VC:.15g}",
            "model_unit": "MUSD/km3", "evidence_ids": "CALC_PHL_VIS15_PUBLIC_WITHDRAWAL_VC",
            "superseded_by": "", "evidence_type": "calculation",
            "notes": "Replaces utility-wide marginal operating-cost proxy with raw-water resource charge.",
        })
    for old, new, kind in ((OLD_SUR, OFF_SUR, "technology"), (OLD_GWT, OFF_GWT, "technology"), (OLD_COMM, OFF_COMM, "commodity")):
        maps.append({
            "map_id": f"MAP_PHL_VIS15_{new}_IDENTITY", "model_file": "genData.json",
            "parameter": f"{kind} label", "entity": new, "mode": "", "scenario": "all",
            "years": "2020-2053", "value_or_expression": f"rename {old} to {new}; stable internal ID",
            "model_unit": "identity", "evidence_ids": "",
            "superseded_by": "", "evidence_type": "model-structure audit",
            "notes": "Makes the sole OFF-grid consumer explicit; no parameter or matrix-structure change.",
        })
    append_rows(ledger / "MODEL_MAP.csv", maps)
    append_rows(ledger / "CHANGES.csv", [{
        "change_id": "CHG_PHL_VIS15_WATER_BOUNDARY_OFF",
        "date": "2026-08-31", "class": "cost-boundary and structural identity",
        "description": "Replace public utility-wide operating-cost proxy with the NWRB municipal raw-water charge and rename residual national cooling-water routes as OFF.",
        "model_objects": f"RYTM:VC:{PUBLIC_SUR},{PUBLIC_GWT}; genData:{OLD_SUR},{OLD_GWT},{OLD_COMM}",
        "evidence_path": "data_sources/water_boundary_vIS15_2026-08-31;documentation/MODEL_FIXES_WATER_BOUNDARY_VIS15_2026-08-31.md",
        "map_rows_affected": ";".join(row["map_id"] for row in maps),
        "resolve_status": "candidate", "author": "Codex", "commit": "",
        "notes": "No demand, activity target, source share, CapacityFactor, island cost, cap value or equation changed.",
    }])
    append_rows(ledger / "GAPS.csv", [{
        "item": "National timeslice profile for public, irrigation and cooling-water abstraction",
        "why_absent": "NIA schedules are system- and season-specific and no national pump-operation series maps to the model's representative seasons and worst day.",
        "upgrade_source": "Scheme-weighted NIA and utility hourly/monthly abstraction and pump-availability records, reconciled to model timeslices.",
        "priority": "high", "notes": "CapacityFactor remains 1.0; known exact timeslice ties remain disclosed.",
    }, {
        "item": "Island-specific abstraction asset and O&M costs",
        "why_absent": "No comparable public series allocates source-intake and pumping costs across Luzon, Visayas and Mindanao.",
        "upgrade_source": "NWRB permit-linked utility and plant project accounts with lift, source, capacity, island and price-year fields.",
        "priority": "medium", "notes": "Equal source-class costs are retained; node routes do not directly substitute.",
    }])
    return {"SOURCES.csv": 2, "ASSUMPTIONS.csv": 2, "CALCULATIONS.csv": 1,
            "MODEL_MAP.csv": len(maps), "CHANGES.csv": 1, "GAPS.csv": 2}


def build() -> None:
    if TARGET.exists():
        raise FileExistsError(f"refusing to replace candidate: {TARGET}")
    shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("res", ".DS_Store"))
    gen = read_json(TARGET / "genData.json")
    old_tech_ids = technology_map(gen)
    old_comm_ids = commodity_map(gen)
    gen["osy-casename"] = "Philippines_vIS1.5"
    gen["osy-date"] = "2026-08-31"
    gen["osy-desc"] = (
        "Philippines vIS1.5: vIS1.4 plus public raw-water cost-boundary correction "
        "and explicit OFF cooling-water route identity."
    )
    for row in gen["osy-tech"]:
        if row["Tech"] == OLD_SUR:
            row["Tech"] = OFF_SUR
            row["Desc"] = "OFF-grid power cooling water from surface sources"
        elif row["Tech"] == OLD_GWT:
            row["Tech"] = OFF_GWT
            row["Desc"] = "OFF-grid power cooling water from groundwater sources"
    for row in gen["osy-comm"]:
        if row["Comm"] == OLD_COMM:
            row["Comm"] = OFF_COMM
            row["Desc"] = "Water for cooling in aggregated OFF-grid thermal power plants"

    Config.DATA_STORAGE = STORAGE
    UpdateCase(TARGET.name, gen).updateCase()
    write_json(TARGET / "genData.json", gen)

    ids = technology_map(gen)
    if ids[OFF_SUR] != old_tech_ids[OLD_SUR] or ids[OFF_GWT] != old_tech_ids[OLD_GWT]:
        raise RuntimeError("OFF rename changed stable technology IDs")
    if commodity_map(gen)[OFF_COMM] != old_comm_ids[OLD_COMM]:
        raise RuntimeError("OFF rename changed stable commodity ID")

    rytm = read_json(TARGET / "RYTM.json")
    for tech in (PUBLIC_SUR, PUBLIC_GWT):
        rows = [row for row in rytm["VC"][BASE] if row["TechId"] == ids[tech] and row["MoId"] == 1]
        if len(rows) != 1:
            raise RuntimeError(f"expected one BASE VC row for {tech}")
        for year in YEARS:
            rows[0][year] = PUBLIC_VC
    write_json(TARGET / "RYTM.json", rytm)

    package = TARGET / "data_sources" / "water_boundary_vIS15_2026-08-31"
    package.mkdir(parents=True, exist_ok=True)
    (package / "README.md").write_text(source_document(), encoding="utf-8")
    with (package / "SOURCES.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["source_id", "provider", "title", "use", "url"])
        writer.writerow(["SRC_PHL_VIS15_NWRB_MUNICIPAL_CHARGE", "LLDA / NWRB",
                         "2024-2025 Citizen's Charter", "Municipal Level III flow charge",
                         "https://llda.gov.ph/wp-content/uploads/dox/citizens_charter/2024-2025%20Citizen%27s%20Charter.pdf"])
        writer.writerow(["SRC_PHL_VIS15_NIA_SEASONAL_SCHEDULE_GAP", "NIA",
                         "National and regional irrigation operations", "CapacityFactor evidence gap",
                         "https://nia.gov.ph/sites/default/files/pdf_reader/CY%202019_year-end-report.pdf"])
    with (package / "CALCULATIONS.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["parameter", "technology", "formula", "value", "unit"])
        for tech in (PUBLIC_SUR, PUBLIC_GWT):
            writer.writerow(["VC", tech, "16.80*CPI2020/CPI2015/31536/49.62*1000", f"{PUBLIC_VC:.15g}", "MUSD/km3"])
    ledger_counts = write_ledger()
    docs = TARGET / "documentation"
    (docs / "MODEL_FIXES_WATER_BOUNDARY_VIS15_2026-08-31.md").write_text(source_document(), encoding="utf-8")
    write_json(docs / "vis15_water_boundary_build_manifest.json", {
        "schema": "philippines-vis15-water-boundary-build-v1",
        "source_case": str(SOURCE), "candidate_case": str(TARGET), "optimizer_runs": 0,
        "changed_source_files": ["genData.json", "RYTM.json", "data_sources schema ledger"],
        "public_vc_before": {PUBLIC_SUR: 200.85667253164814, PUBLIC_GWT: 168.9978790344024},
        "public_vc_after": {PUBLIC_SUR: PUBLIC_VC, PUBLIC_GWT: PUBLIC_VC},
        "off_renames": {OLD_SUR: OFF_SUR, OLD_GWT: OFF_GWT, OLD_COMM: OFF_COMM},
        "capacity_factor_change": False, "island_cost_change": False,
        "canonical_schema_ledger_additions": ledger_counts,
    })
    print(json.dumps({"candidate": str(TARGET), "public_vc": PUBLIC_VC,
                      "off_renames": {OLD_SUR: OFF_SUR, OLD_GWT: OFF_GWT, OLD_COMM: OFF_COMM},
                      "ledger_additions": ledger_counts}, indent=2))


def preflight() -> None:
    failures: list[str] = []
    checks: list[dict] = []

    def check(condition: bool, name: str, detail=None):
        checks.append({"check": name, "passed": bool(condition), "detail": detail})
        if not condition:
            failures.append(name)

    src_gen = read_json(SOURCE / "genData.json")
    gen = read_json(TARGET / "genData.json")
    src_ids = technology_map(src_gen)
    ids = technology_map(gen)
    check(gen["osy-casename"] == "Philippines_vIS1.5", "case identity")
    check(OLD_SUR not in ids and OLD_GWT not in ids and OFF_SUR in ids and OFF_GWT in ids,
          "national route labels retired and OFF labels present")
    check(ids[OFF_SUR] == src_ids[OLD_SUR] and ids[OFF_GWT] == src_ids[OLD_GWT],
          "OFF technology IDs stable")
    src_comms = commodity_map(src_gen)
    comms = commodity_map(gen)
    check(OLD_COMM not in comms and OFF_COMM in comms and comms[OFF_COMM] == src_comms[OLD_COMM],
          "OFF commodity ID stable")

    expected_gen = json.loads(json.dumps(src_gen))
    expected_gen["osy-casename"] = gen["osy-casename"]
    expected_gen["osy-date"] = gen["osy-date"]
    expected_gen["osy-desc"] = gen["osy-desc"]
    for row in expected_gen["osy-tech"]:
        if row["Tech"] == OLD_SUR:
            row["Tech"], row["Desc"] = OFF_SUR, "OFF-grid power cooling water from surface sources"
        elif row["Tech"] == OLD_GWT:
            row["Tech"], row["Desc"] = OFF_GWT, "OFF-grid power cooling water from groundwater sources"
    for row in expected_gen["osy-comm"]:
        if row["Comm"] == OLD_COMM:
            row["Comm"], row["Desc"] = OFF_COMM, "Water for cooling in aggregated OFF-grid thermal power plants"
    check(expected_gen == gen, "genData diff limited to identity and OFF labels")

    for path in sorted(SOURCE.glob("*.json")):
        if path.name in {"genData.json", "RYTM.json"}:
            continue
        check(read_json(path) == read_json(TARGET / path.name), f"unchanged source parameter {path.name}")

    src_rytm = read_json(SOURCE / "RYTM.json")
    rytm = read_json(TARGET / "RYTM.json")
    expected_rytm = json.loads(json.dumps(src_rytm))
    for tech in (PUBLIC_SUR, PUBLIC_GWT):
        rows = [row for row in expected_rytm["VC"][BASE] if row["TechId"] == ids[tech] and row["MoId"] == 1]
        for year in YEARS:
            rows[0][year] = PUBLIC_VC
    check(expected_rytm == rytm, "RYTM diff limited to two public BASE VC rows")
    for tech in (PUBLIC_SUR, PUBLIC_GWT):
        row = next(row for row in rytm["VC"][BASE] if row["TechId"] == ids[tech] and row["MoId"] == 1)
        check(all(math.isclose(float(row[y]), PUBLIC_VC, rel_tol=0, abs_tol=1e-13) for y in YEARS),
              f"full-horizon public VC: {tech}", PUBLIC_VC)
        for scenario, rows in rytm["VC"].items():
            if scenario == BASE:
                continue
            overlay = [row for row in rows if row["TechId"] == ids[tech] and row["MoId"] == 1]
            check(len(overlay) == 1 and all(overlay[0][y] is None for y in YEARS),
                  f"policy VC inheritance remains null: {scenario}/{tech}")

    # Exact physical mappings and constraints remain on stable IDs after the label change.
    for key in ("RYTCM.json", "RYTCn.json", "RYT.json", "RT.json", "RYTTs.json"):
        check(read_json(SOURCE / key) == read_json(TARGET / key), f"physical mapping unchanged: {key}")

    baseline = read_json(BASELINE_RUN / "optimization_record.json")
    check(str(baseline.get("status", "")).startswith("Optimal"), "retained vIS1.4 BASE is optimal feasible witness")
    check((BASELINE_RUN / "results.txt").is_file(), "retained vIS1.4 results exist")
    check(0 < PUBLIC_VC < min(200.85667253164814, 168.9978790344024),
          "public coefficients remain positive and only decrease", PUBLIC_VC)
    report = {
        "schema": "philippines-vis15-water-boundary-preflight-v1",
        "status": "passed" if not failures else "failed", "optimizer_runs": 0, "generation_runs": 0,
        "physical_intent": "retain physical pump assets; correct public direct-cost boundary; relabel residual cooling water as OFF",
        "observation_classification": "NWRB fee is an economic driver; NIA schedules are benchmark/gap evidence only",
        "equation_map": {
            "source": "RYTM.json VC / SC_0 / two public technologies; genData labels through UpdateCase",
            "generated": "VariableCost and stable technology/commodity sets",
            "equation": "OC1/OC2 discounted activity cost; no constraint equation changes",
            "expected_effect": "lower public abstraction cost; identical feasible region; OFF labels only",
        },
        "feasibility_proof": (
            "The retained optimal vIS1.4 solution remains feasible because technology and commodity IDs, mappings, "
            "constraints, capacities, lives, efficiencies, demand and all activity coefficients are unchanged; only two "
            "positive objective coefficients decrease and three display labels change."
        ),
        "capacity_factor_decision": "unchanged at 1.0; authoritative evidence is system-specific and cannot support a national timeslice shape",
        "island_cost_decision": "unchanged; routes produce separate node commodities and no sourced island coefficients exist",
        "checks": checks, "failures": failures,
    }
    write_json(TARGET / "documentation" / "vis15_water_boundary_preflight.json", report)
    print(json.dumps({"status": report["status"], "optimizer_runs": 0,
                      "checks": len(checks), "failures": failures}, indent=2))
    if failures:
        raise RuntimeError(f"preflight failed: {failures}")


def datafile() -> DataFile:
    Config.DATA_STORAGE = STORAGE
    return DataFile(TARGET.name)


def generated_vc(path: Path, tech: str) -> list[float]:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"\[RE1,{re.escape(tech)},\*,\*\]:\s*\n[^\n]+:=\s*\n1\s+([^\n]+)", text)
    return [float(value) for value in match.group(1).split()] if match else []


def exact_token_present(text: str, name: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", text) is not None


def generate_check() -> None:
    pre = read_json(TARGET / "documentation" / "vis15_water_boundary_preflight.json")
    if pre.get("status") != "passed" or pre.get("optimizer_runs") != 0:
        raise RuntimeError("blocking source preflight has not passed")
    run = TARGET / "res" / RUN_NAME
    if run.exists():
        raise FileExistsError(f"refusing to replace run: {run}")
    df = datafile()
    scenarios = [{"ScenarioId": item["ScenarioId"], "Scenario": item["Scenario"],
                  "Desc": item.get("Desc", ""), "Active": item["Scenario"] == "BASE"}
                 for item in df.genData["osy-scenarios"]]
    created = df.createCaseRun(RUN_NAME, {
        "Case": RUN_NAME, "CaseId": "CS_PHL_VIS15_WATER_BOUNDARY_BASE",
        "Desc": "Philippines vIS1.5 water-cost boundary BASE", "Runtime": str(date.today()),
        "Scenarios": scenarios,
    })
    if created.get("status_code") != "success":
        raise RuntimeError(json.dumps(created, indent=2))
    timings = {}
    started = time.monotonic(); df.generateDatafile(RUN_NAME); timings["generate"] = time.monotonic() - started
    started = time.monotonic(); df.preprocessData(run / "data.txt", run / "data_processed.txt"); timings["preprocess"] = time.monotonic() - started
    text = (run / "data_processed.txt").read_text(encoding="utf-8")
    vcs = {tech: generated_vc(run / "data_processed.txt", tech) for tech in (PUBLIC_SUR, PUBLIC_GWT)}
    vc_ok = all(len(values) == len(YEARS) and all(math.isclose(v, PUBLIC_VC, rel_tol=0, abs_tol=1e-10) for v in values)
                for values in vcs.values())
    names_ok = all(exact_token_present(text, name) for name in (OFF_SUR, OFF_GWT, OFF_COMM)) and not any(
        exact_token_present(text, name) for name in (OLD_SUR, OLD_GWT, OLD_COMM)
    )
    glpsol = Osemosys._find_solver_binary(df.glpkFolder.resolve(), "glpsol", recursive=False)
    if glpsol is None:
        raise RuntimeError("GLPK unavailable")
    started = time.monotonic()
    checked = subprocess.run([str(glpsol), "--check", "-m", str(MODEL), "-d", str(run / "data_processed.txt"), "--wlp", str(run / "lp.lp")],
                             cwd=df.glpkFolder.resolve() if df.glpsol_is_bundled else None,
                             capture_output=True, text=True, timeout=300)
    timings["glpsol_check_and_lp"] = time.monotonic() - started
    log = checked.stdout + "\n" + checked.stderr
    (run / "glpsol_check.log").write_text(log, encoding="utf-8")
    matrix = _v14.matrix_metrics(log)
    matrix_ok = checked.returncode == 0 and "Model has been successfully generated" in log
    baseline_matrix = read_json(BASELINE_RUN / "generation_matrix_report.json").get("matrix_dimensions", {})
    report = {
        "schema": "philippines-vis15-water-boundary-generation-gate-v1",
        "status": "passed" if vc_ok and names_ok and matrix_ok and matrix == baseline_matrix else "failed",
        "optimizer_runs": 0, "active_scenarios": ["BASE"], "timings_seconds": timings,
        "public_vc_landed": vc_ok, "off_names_landed_and_legacy_names_absent": names_ok,
        "glpsol_returncode": checked.returncode, "matrix_dimensions": matrix,
        "matrix_identical_to_vIS14": matrix == baseline_matrix, "baseline_matrix_dimensions": baseline_matrix,
    }
    write_json(run / "generation_matrix_report.json", report)
    print(json.dumps(report, indent=2))
    if report["status"] != "passed":
        raise RuntimeError("generated-data/matrix gate failed")


def recheck_generated() -> None:
    """Finish the matrix gate when generation completed before the caller yielded."""
    run = TARGET / "res" / RUN_NAME
    if not (run / "data_processed.txt").is_file():
        raise FileNotFoundError("generated data is absent")
    df = datafile()
    text = (run / "data_processed.txt").read_text(encoding="utf-8")
    vcs = {tech: generated_vc(run / "data_processed.txt", tech) for tech in (PUBLIC_SUR, PUBLIC_GWT)}
    vc_ok = all(len(values) == len(YEARS) and all(math.isclose(v, PUBLIC_VC, rel_tol=0, abs_tol=1e-10) for v in values)
                for values in vcs.values())
    names_ok = all(exact_token_present(text, name) for name in (OFF_SUR, OFF_GWT, OFF_COMM)) and not any(
        exact_token_present(text, name) for name in (OLD_SUR, OLD_GWT, OLD_COMM)
    )
    glpsol = Osemosys._find_solver_binary(df.glpkFolder.resolve(), "glpsol", recursive=False)
    if glpsol is None:
        raise RuntimeError("GLPK unavailable")
    existing_log = run / "glpsol_check.log"
    if existing_log.is_file() and (run / "lp.lp").is_file() and "Model has been successfully generated" in existing_log.read_text(encoding="utf-8"):
        log = existing_log.read_text(encoding="utf-8")
        returncode = 0
        elapsed = 0.0
        glpsol_reused = True
    else:
        started = time.monotonic()
        checked = subprocess.run([str(glpsol), "--check", "-m", str(MODEL), "-d", str(run / "data_processed.txt"), "--wlp", str(run / "lp.lp")],
                                 cwd=df.glpkFolder.resolve() if df.glpsol_is_bundled else None,
                                 capture_output=True, text=True, timeout=300)
        elapsed = time.monotonic() - started
        log = checked.stdout + "\n" + checked.stderr
        existing_log.write_text(log, encoding="utf-8")
        returncode = checked.returncode
        glpsol_reused = False
    matrix = _v14.matrix_metrics(log)
    baseline_matrix = read_json(BASELINE_RUN / "generation_matrix_report.json").get("matrix_dimensions", {})
    matrix_ok = returncode == 0 and "Model has been successfully generated" in log
    report = {
        "schema": "philippines-vis15-water-boundary-generation-gate-v1",
        "status": "passed" if vc_ok and names_ok and matrix_ok and matrix == baseline_matrix else "failed",
        "optimizer_runs": 0, "active_scenarios": ["BASE"],
        "timings_seconds": {"generate_and_preprocess_completed_before_caller_yield": True,
                            "glpsol_check_and_lp": elapsed, "completed_glpsol_result_reused": glpsol_reused},
        "public_vc_landed": vc_ok, "off_names_landed_and_legacy_names_absent": names_ok,
        "glpsol_returncode": returncode, "matrix_dimensions": matrix,
        "matrix_identical_to_vIS14": matrix == baseline_matrix, "baseline_matrix_dimensions": baseline_matrix,
    }
    write_json(run / "generation_matrix_report.json", report)
    print(json.dumps(report, indent=2))
    if report["status"] != "passed":
        raise RuntimeError("generated-data/matrix gate failed")


def cap_summary(activity: dict[tuple[str, str], float]) -> dict:
    gen = read_json(TARGET / "genData.json")
    ids = technology_map(gen)
    constraints = {row["Con"]: row for row in gen["osy-constraints"]}
    cap_values = {row["ConId"]: row for row in read_json(TARGET / "RYCn.json")["UCC"][BASE]}
    groups = {
        "WATER_SUR_AVAIL": (PUBLIC_SUR, OFF_SUR, "DEMAGRSURPHL", "PHL_DEM_PWR_SUR_WAT_LUZ", "PHL_DEM_PWR_SUR_WAT_VIS", "PHL_DEM_PWR_SUR_WAT_MIN"),
        "WATER_GWT_POTENTIAL": (PUBLIC_GWT, OFF_GWT, "DEMAGRGWTPHL", "PHL_DEM_PWR_GWT_WAT_LUZ", "PHL_DEM_PWR_GWT_WAT_VIS", "PHL_DEM_PWR_GWT_WAT_MIN"),
    }
    result = {}
    for con, techs in groups.items():
        cap = cap_values[constraints[con]["ConId"]]
        rows = []
        for year in YEARS:
            withdrawal = sum(activity.get((tech, year), 0.0) for tech in techs)
            rows.append((year, withdrawal, float(cap[year]) - withdrawal))
        binding = min(rows, key=lambda row: row[2])
        result[con] = {"minimum_headroom": binding[2], "binding_year": binding[0],
                       "2020_withdrawal": rows[0][1], "2020_cap": float(cap["2020"])}
    return result


def solve(timeout: int) -> None:
    run = TARGET / "res" / RUN_NAME
    gate = read_json(run / "generation_matrix_report.json")
    if gate.get("status") != "passed" or gate.get("optimizer_runs") != 0:
        raise RuntimeError("generation gate is not a clean zero-optimizer pass")
    df = datafile()
    cbc = Osemosys._find_solver_binary(df.cbcFolder.resolve(), "cbc", recursive=False)
    if cbc is None:
        raise RuntimeError("CBC unavailable")
    command = [str(cbc), str(run / "lp.lp"), "solve", "-printing", "all", "-solu", str(run / "results.txt")]
    started = time.monotonic()
    try:
        completed = subprocess.run(command, cwd=df.cbcFolder.resolve() if df.cbc_is_bundled else None,
                                   capture_output=True, text=True, timeout=timeout)
        elapsed = time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - started
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        (run / "cbc.log").write_text(stdout + "\n" + stderr, encoding="utf-8")
        report = {"schema": "philippines-vis15-water-boundary-base-validation-v1", "status": "timed_out",
                  "optimizer_runs": 1, "timeout_seconds": timeout, "solve_seconds": elapsed,
                  "promotion_attempted": False, "stop_point": "BASE timed out; stopped"}
        write_json(run / "optimization_record.json", report)
        write_json(TARGET / "documentation" / "vis15_base_validation.json", report)
        print(json.dumps(report, indent=2)); return
    log = completed.stdout + "\n" + completed.stderr
    (run / "cbc.log").write_text(log, encoding="utf-8")
    if completed.returncode != 0 or not (run / "results.txt").is_file():
        raise RuntimeError(log[-12000:])
    status = (run / "results.txt").read_text(encoding="utf-8").splitlines()[0]
    match = re.search(r"objective value\s+([-+0-9.eE]+)", status)
    objective = float(match.group(1)) if match else None
    baseline = read_json(BASELINE_RUN / "optimization_record.json")
    export_started = time.monotonic(); df.generateCSVfromCBC(run / "data.txt", run / "results.txt", run); export_seconds = time.monotonic() - export_started
    activity = _v14.read_activity(run / "csv" / "TotalAnnualTechnologyActivityByMode.csv")
    baseline_activity = _v14.read_activity(BASELINE_RUN / "csv" / "TotalAnnualTechnologyActivityByMode.csv")
    new_capacity = _v14.read_technology_year_metric(run / "csv" / "NewCapacity.csv", "NewCapacity")
    total_capacity = _v14.read_technology_year_metric(run / "csv" / "TotalCapacityAnnual.csv", "TotalCapacityAnnual")
    tracked = (PUBLIC_SUR, PUBLIC_GWT, OFF_SUR, OFF_GWT, "DEMAGRSURPHL", "DEMAGRGWTPHL",
               "PHL_DEM_PWR_SUR_WAT_LUZ", "PHL_DEM_PWR_SUR_WAT_VIS", "PHL_DEM_PWR_SUR_WAT_MIN",
               "PHL_DEM_PWR_GWT_WAT_LUZ", "PHL_DEM_PWR_GWT_WAT_VIS", "PHL_DEM_PWR_GWT_WAT_MIN")
    baseline_alias = {OFF_SUR: OLD_SUR, OFF_GWT: OLD_GWT}
    technologies = {}
    for tech in tracked:
        old = baseline_alias.get(tech, tech)
        annual = {year: activity.get((tech, year), 0.0) for year in YEARS}
        old_annual = {year: baseline_activity.get((old, year), 0.0) for year in YEARS}
        technologies[tech] = {
            "2020_activity": annual["2020"], "2020_baseline_activity": old_annual["2020"],
            "horizon_activity": sum(annual.values()), "horizon_baseline_activity": sum(old_annual.values()),
            "maximum_new_capacity": max(new_capacity.get((tech, year), 0.0) for year in YEARS),
            "maximum_total_capacity": max(total_capacity.get((tech, year), 0.0) for year in YEARS),
            "inactive_giant_capacity": max(total_capacity.get((tech, year), 0.0) for year in YEARS) > 10000 and sum(annual.values()) < 1e-8,
        }
    comparison = _v14.compare_results(BASELINE_RUN / "csv", run / "csv")
    write_json(run / "result_comparison_vs_vis14.json", comparison)
    baseline_objective = float(baseline["objective"])
    report = {
        "schema": "philippines-vis15-water-boundary-base-validation-v1", "status": status,
        "optimizer_runs": 1, "timeout_seconds": timeout, "solve_seconds": elapsed,
        "baseline_solve_seconds": baseline.get("solve_seconds"), "solve_time_ratio": elapsed / float(baseline["solve_seconds"]),
        "csv_export_seconds": export_seconds, "objective": objective, "baseline_objective": baseline_objective,
        "objective_change": objective - baseline_objective,
        "objective_change_percent": 100 * (objective / baseline_objective - 1),
        "public_vc_musd_per_km3": PUBLIC_VC, "water_caps": cap_summary(activity),
        "water_technology_results": technologies,
        "inactive_giant_capacity_count": sum(row["inactive_giant_capacity"] for row in technologies.values()),
        "result_comparison": {"table_count": comparison["table_count"],
                              "changed_table_count": comparison["changed_table_count"],
                              "unchanged_table_count": comparison["unchanged_table_count"],
                              "changed_tables": [name for name, row in comparison["tables"].items() if row.get("status") == "changed"]},
        "promotion_attempted": False,
        "stop_point": "BASE finished; no policy scenario, seal, promotion, or second optimization was run",
        "cbc_tail": log[-5000:],
    }
    write_json(run / "optimization_record.json", report)
    write_json(TARGET / "documentation" / "vis15_base_validation.json", report)
    with (TARGET / "documentation" / "MODEL_FIXES_WATER_BOUNDARY_VIS15_2026-08-31.md").open("a", encoding="utf-8") as stream:
        stream.write("\n## BASE validation\n\n" +
                     f"CBC status: `{status}`. Runtime: {elapsed:.3f} seconds under a {timeout}-second limit. " +
                     f"Objective: {objective:.8f} MUSD, {objective - baseline_objective:.8f} MUSD " +
                     f"({100 * (objective / baseline_objective - 1):.6f}%) versus vIS1.4. " +
                     f"{comparison['changed_table_count']} of {comparison['table_count']} result tables changed. " +
                     "No policy scenario, seal, promotion, or second optimization was run.\n")
    print(json.dumps({k: report[k] for k in ("status", "optimizer_runs", "timeout_seconds", "solve_seconds",
                                             "baseline_solve_seconds", "solve_time_ratio", "objective",
                                             "objective_change", "objective_change_percent", "water_caps",
                                             "inactive_giant_capacity_count", "result_comparison", "stop_point")}, indent=2))


def postprocess() -> None:
    """Correct rename-aware reporting and add read-only result assessment."""
    run = TARGET / "res" / RUN_NAME
    report_path = TARGET / "documentation" / "vis15_base_validation.json"
    report = read_json(report_path)

    def metric(path: Path, column: str) -> dict[tuple[str, str], float]:
        values = {}
        with path.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                values[(row["t"], row["y"])] = float(row[column])
        return values

    new_capacity = metric(run / "csv" / "NewCapacity.csv", "NewCapacity")
    total_capacity = metric(run / "csv" / "TotalCapacityAnnual.csv", "TotalCapacityAnnual")
    for tech, row in report["water_technology_results"].items():
        row["maximum_new_capacity"] = max(new_capacity.get((tech, year), 0.0) for year in YEARS)
        row["maximum_total_capacity"] = max(total_capacity.get((tech, year), 0.0) for year in YEARS)
        row["inactive_giant_capacity"] = row["maximum_total_capacity"] > 10000 and row["horizon_activity"] < 1e-8
    report["inactive_giant_capacity_count"] = sum(
        row["inactive_giant_capacity"] for row in report["water_technology_results"].values()
    )

    log = (run / "cbc.log").read_text(encoding="utf-8")
    presolve = re.search(r"Presolve (\d+) \([^)]*\) rows, (\d+) \([^)]*\) columns and (\d+)", log)
    iterations = re.search(r"Optimal objective [^\n]+ - (\d+) iterations", log)
    report["solver_diagnostics"] = {
        "presolved_rows": int(presolve.group(1)) if presolve else None,
        "presolved_columns": int(presolve.group(2)) if presolve else None,
        "presolved_elements": int(presolve.group(3)) if presolve else None,
        "iterations": int(iterations.group(1)) if iterations else None,
        "values_passes": len(re.findall(r"End of values pass", log)),
        "vIS14_iterations": 183327,
        "vIS14_values_passes": 14,
        "interpretation": "The public cost correction does not resolve the inherited timeslice/other-model degeneracy.",
    }

    clusters = {f"LNDAGRPHLC{i:02d}" for i in range(1, 9)}
    rice_obs = {"rainfed_area": 14.6544173, "irrigated_area": 20.06,
                "rainfed_production": 4.72309035, "irrigated_production": 14.57176519}
    activity = {}
    with (run / "csv" / "TotalAnnualTechnologyActivityByMode.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            activity[(row["t"], int(row["m"]), row["y"])] = float(row["TotalAnnualTechnologyActivityByMode"])
    rice = {key: 0.0 for key in rice_obs}
    for (tech, mode, year), value in activity.items():
        if tech not in clusters or year != "2020":
            continue
        if mode in {11, 14}: rice["rainfed_area"] += value
        if mode in {17, 19}: rice["irrigated_area"] += value
    with (run / "csv" / "ProductionByTechnologyByMode.csv").open(newline="", encoding="utf-8") as stream:
        production_rows = list(csv.DictReader(stream))
    for row in production_rows:
        if row["t"] in clusters and row["y"] == "2020" and row["f"] == "CRPRCP":
            if int(row["m"]) in {11, 14}: rice["rainfed_production"] += float(row["ProductionByTechnologyByMode"])
            if int(row["m"]) in {17, 19}: rice["irrigated_production"] += float(row["ProductionByTechnologyByMode"])
    power_obs = {"2020": 366.3216, "2021": 382.014, "2022": 401.4576, "2023": 424.8144, "2024": 456.9876}
    power = {year: 0.0 for year in power_obs}
    for row in production_rows:
        if row["y"] in power and row["f"] in {"PHL_POW_ELE_LUZ", "PHL_POW_ELE_VIS", "PHL_POW_ELE_MIN"}:
            power[row["y"]] += float(row["ProductionByTechnologyByMode"])
    report["historical_fit"] = {
        "rice_2020": {"modeled": rice, "error_percent": {key: 100 * (rice[key] / rice_obs[key] - 1) for key in rice_obs},
                      "assessment_vs_vIS14": "unchanged"},
        "gross_grid_generation_2020_2024": {"modeled_pj": power,
            "wape_percent": 100 * sum(abs(power[y] - power_obs[y]) for y in power) / sum(power_obs.values()),
            "vIS14_wape_percent": 4.81687493650311, "assessment_vs_vIS14": "unchanged to reported precision"},
    }
    report["result_interpretation"] = {
        "substantive_water_result": "Public, irrigation and OFF activity are unchanged; island power-water horizon changes are below 0.2 km3.",
        "large_row_level_differences": "Mostly alternative degenerate allocations across land modes, precipitation timeslices, transport balance slack and investment vintages; they do not improve historical fit.",
        "promotion_recommendation": "Do not promote yet if solve speed is a release criterion; cost boundary is corrected, but runtime remains about 59% above vIS1.3.",
    }
    write_json(report_path, report)
    write_json(run / "result_assessment.json", {
        "schema": "philippines-vis15-result-assessment-v1",
        "solver_diagnostics": report["solver_diagnostics"],
        "historical_fit": report["historical_fit"],
        "result_interpretation": report["result_interpretation"],
        "corrected_off_capacity_reporting": {
            OFF_SUR: report["water_technology_results"][OFF_SUR],
            OFF_GWT: report["water_technology_results"][OFF_GWT],
        },
    })
    print(json.dumps({"status": report["status"], "solver_diagnostics": report["solver_diagnostics"],
                      "historical_fit": report["historical_fit"],
                      "off_surface_max_capacity": report["water_technology_results"][OFF_SUR]["maximum_total_capacity"],
                      "recommendation": report["result_interpretation"]["promotion_recommendation"]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("build", "preflight", "generate-check", "recheck-generated", "solve", "postprocess"))
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    if args.phase == "build": build()
    elif args.phase == "preflight": preflight()
    elif args.phase == "generate-check": generate_check()
    elif args.phase == "recheck-generated": recheck_generated()
    elif args.phase == "solve": solve(args.timeout)
    else: postprocess()


if __name__ == "__main__":
    main()
