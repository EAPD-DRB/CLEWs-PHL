#!/usr/bin/env python3
"""Add the PHL v18 power-investment cleanup to the canonical schema ledger."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
LEDGER = PACKAGE / "data_sources"
SNAPSHOTS = LEDGER / "snapshots"
MANIFEST = SNAPSHOTS / "power_investment_cleanup_v18_2026-08-17.json"
VALIDATION = SNAPSHOTS / "power_investment_cleanup_validation_2026-08-17.json"
SOLVE = SNAPSHOTS / "power_investment_cleanup_solve_2026-08-17.json"
PROMOTION = SNAPSHOTS / "power_investment_cleanup_promotion_identity_2026-08-17.json"
CASE = PACKAGE.parent / "case" / "Philippines_v18"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(name: str) -> tuple[list[str], list[dict[str, str]]]:
    with (LEDGER / name).open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def write_csv(name: str, fields: list[str], rows: list[dict[str, str]]) -> None:
    with (LEDGER / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def append_unique(rows: list[dict[str, str]], key: str, new_rows: list[dict[str, str]]) -> None:
    positions = {row[key]: index for index, row in enumerate(rows)}
    for row in new_rows:
        if row[key] in positions:
            rows[positions[row[key]]] = row
        else:
            positions[row[key]] = len(rows)
            rows.append(row)


def tech_slug(name: str) -> str:
    return name.removeprefix("PHL_POW_")


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
    promotion = json.loads(PROMOTION.read_text(encoding="utf-8"))
    if len(manifest["changes"]) != 62 or validation["status"] != "pass" or promotion["status"] != "pass":
        raise AssertionError("retained implementation evidence is incomplete")

    gen = json.loads((CASE / "genData.json").read_text(encoding="utf-8"))
    tech_ids = {row["Tech"]: row["TechId"] for row in gen["osy-tech"]}

    source_fields, sources = read_csv("SOURCES.csv")
    source_rows = [
        {
            "source_id": "SRC_PHL_DOE_POWER_PLANTS_DEC2020",
            "provider": "Philippines Department of Energy",
            "product": "List of Existing Power Plants (Grid-Connected)",
            "edition": "December 2020",
            "reference_period": "2020",
            "geography": "Philippines; Luzon; Visayas; Mindanao",
            "variable": "Installed and dependable grid-connected capacity by fuel type",
            "source_unit": "MW",
            "exact_locator": "Philippines capacity-mix table: coal 10,944 MW; oil 3,667 MW; natural gas 3,453 MW; geothermal 1,928 MW; hydro 3,749 MW",
            "url": "https://legacy.doe.gov.ph/sites/default/files/pdf/electric_power/electric_power_plants_lvm_summary_grid_december_2020.pdf",
            "access_date": "2026-08-17",
            "license": "Philippine government publication; provider terms",
            "sha256": "",
            "local_file": "",
            "notes": "Supports the 2020 initial-stock information boundary; it does not prescribe post-2020 additions or dispatch.",
        },
        {
            "source_id": "SRC_PHL_PEP_2020_2040_COMMITTED",
            "provider": "Philippines Department of Energy",
            "product": "Philippine Energy Plan 2020-2040",
            "edition": "final e-copy as of 15 June 2023",
            "reference_period": "committed-project register as of 31 December 2020",
            "geography": "Philippines; Luzon; Visayas; Mindanao",
            "variable": "Summary of committed power projects by plant type",
            "source_unit": "project count and MW",
            "exact_locator": "Table 40, page 85: 53 projects and 8,977.11 MW total; coal 4,241; oil 392.04; gas 3,500; geothermal 140; hydro 144.3; solar 408.57; wind 132; biomass 19.2 MW",
            "url": "https://legacy.doe.gov.ph/sites/default/files/pdf/pep/PEP-2020-2040-Final%20eCopy-as-of-15-June-2023.pdf",
            "access_date": "2026-08-17",
            "license": "Philippine government publication; provider terms",
            "sha256": "",
            "local_file": "",
            "notes": "Screened for irreversible 2020 commitments. Aggregate technology totals cannot be losslessly assigned to model technologies and commissioning years, so no new minimum is applied.",
        },
        {
            "source_id": "SRC_PHL_PEP_2023_2050_VOL2_COAL_TRADE",
            "provider": "Philippines Department of Energy",
            "product": "Philippine Energy Plan 2023-2050 Volume II",
            "edition": "PEP 2023-2050",
            "reference_period": "2022",
            "geography": "Philippines",
            "variable": "Coal production, consumption, importation and exportation",
            "source_unit": "million metric tonnes",
            "exact_locator": "Conventional Energy chapter: production 16.06; consumption 36.14; imports 32.7; exports 7.1 million metric tonnes in 2022",
            "url": "https://doe.gov.ph/sites/default/files/pdf/pep/PEP%202023-2050%20%28Volume%20II%29.pdf",
            "access_date": "2026-08-17",
            "license": "Philippine government publication; provider terms",
            "sha256": "",
            "local_file": "",
            "notes": "Benchmark-only evidence for the disclosed full-extraction export pathology; it is not converted to an export activity pin.",
        },
    ]
    for source_id, title, path, note in (
        ("SRC_PHL_V18_PWR_INV_MANIFEST", "Philippines v18 power-investment cleanup manifest", MANIFEST, "Exact 62-cell source delta and pre/post hashes."),
        ("SRC_PHL_V18_PWR_INV_VALIDATION", "Philippines v18 power-investment cleanup validation", VALIDATION, "Static, generated-data, solve, benchmark, fossil-flow and qualified baseline checks."),
        ("SRC_PHL_V18_PWR_INV_SOLVE", "Philippines v18 power-investment cleanup solve record", SOLVE, "Single budgeted CBC optimization record."),
        ("SRC_PHL_V18_PWR_INV_PROMOTION", "Philippines v18 power-investment cleanup promotion identity", PROMOTION, "Live source and data.txt byte identity plus live GLPK matrix check."),
    ):
        source_rows.append(
            {
                "source_id": source_id,
                "provider": "MUIOGO Philippines v18 workflow",
                "product": title,
                "edition": "2026-08-17",
                "reference_period": "2020-2053",
                "geography": "Philippines",
                "variable": "source, generated-model and validation audit record",
                "source_unit": "record",
                "exact_locator": f"data_sources/snapshots/{path.name}",
                "url": "",
                "access_date": "2026-08-17",
                "license": "Repository license",
                "sha256": sha256(path),
                "local_file": f"snapshots/{path.name}",
                "notes": note,
            }
        )
    append_unique(sources, "source_id", source_rows)
    write_csv("SOURCES.csv", source_fields, sources)

    assumption_fields, assumptions = read_csv("ASSUMPTIONS.csv")
    for row in assumptions:
        if row["assumption_id"] == "ASM_PHL_V18_DEPLOY_OLD_STOCK_ONLY":
            row.update(
                statement="The inherited coal, gas, oil and biomass CHP _OLD technologies receive zero new-capacity entry throughout 2020-2053; their unchanged 2020 residual-capacity stocks remain available until retirement.",
                evidence_source_ids="SRC_PHL_DOE_POWER_PLANTS_DEC2020;SRC_MUIO_FORMULATION",
                rationale="These are inherited-stock representations, not investable technology options; geothermal remains the documented exception because the model has no separate geothermal new-build or repowering technology.",
                notes="classification=technology-role rule; no residual-capacity value changes",
            )
            break
    else:
        raise AssertionError("missing inherited old-stock assumption")
    assumption_rows = [
        {
            "assumption_id": "ASM_PHL_V18_PWR_2020_INFORMATION_CUTOFF",
            "statement": "Power-sector initialization uses only the fleet operating in 2020; observed 2021-2025 additions are validation benchmarks, not initial stock or forced investment.",
            "central_value": "2020",
            "unit": "information cutoff year",
            "evidence_source_ids": "SRC_PHL_DOE_POWER_PLANTS_DEC2020;SRC_PHL_DOE_POWER_STATISTICS_2024",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "All sectors should remain endogenous after the common 2020 start year; reproducing later additions with equal lower and upper bounds violates the non-forcing rule.",
            "notes": "RC remains unchanged; later observations are retained in the validation artifact.",
        },
        {
            "assumption_id": "ASM_PHL_V18_PWR_NO_COMMITTED_MINIMA",
            "statement": "The aggregate DOE register of projects classified as committed at end-2020 is not translated into technology-year minimum investment because a lossless project-to-model mapping and irreversible construction screen were not established.",
            "central_value": "0",
            "unit": "new minimum-capacity constraints added",
            "evidence_source_ids": "SRC_PHL_PEP_2020_2040_COMMITTED",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "Aggregate MW by plant type does not prove model technology, commercial-operation year, surviving status or irrevocability for each project.",
            "notes": "A future project-level register may support minimums only for demonstrably irreversible commitments known in 2020.",
        },
        {
            "assumption_id": "ASM_PHL_V18_PWR_MATURE_ENTRY_2020",
            "statement": "Mature investable power technologies are allowed to enter endogenously from 2020 unless a continuing physical deployment envelope applies.",
            "central_value": "999999",
            "unit": "GW/year MUIO open-bound sentinel",
            "evidence_source_ids": "SRC_PHL_DOE_POWER_PLANTS_DEC2020;SRC_MUIO_FORMULATION",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "The first model year is not a historical activity-reproduction window; capacity choice remains endogenous after the 2020 stock is initialized through RC.",
            "notes": "Applies to onshore wind, solar PV, NGCC, large hydro and geothermal in 2020; existing 2026+ envelopes remain.",
        },
        {
            "assumption_id": "ASM_PHL_V18_DEPLOY_PP_COAL_2020_2029",
            "statement": "PHL_POW_PP_COAL may commission at most 2.0 GW/year during 2020-2029; later 2.5, 3.0 and 5.0 GW/year bands are retained unchanged.",
            "central_value": "2.0",
            "unit": "GW/year",
            "evidence_source_ids": "SRC_PHL_DOE_POWER_PLANTS_DEC2020;SRC_PHL_DOE_POWER_STATISTICS_2024;SRC_HEGGARTY_MAX_INVESTMENT_RATE_2024",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "A deliberately generous continuing construction, finance, permitting and grid-integration envelope; it limits speed but does not require coal investment or dispatch.",
            "notes": "Judgmental physical envelope extended to the full first decade; CoalPhaseOut retains exact zero from 2031.",
        },
        {
            "assumption_id": "ASM_PHL_V18_PWR_ZERO_OVERRIDE_SEMANTICS",
            "statement": "In MUIO scenario inheritance, JSON null means inherit while numeric zero is an active exact bound; CoalPhaseOut therefore uses 0, not 0.0001, from 2031.",
            "central_value": "0",
            "unit": "GW/year",
            "evidence_source_ids": "SRC_MUIO_FORMULATION;SRC_PHL_V18_PWR_INV_VALIDATION",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "The generator tests for null/None before applying active scenarios, so replacing zero with a small positive value would incorrectly permit capacity.",
            "notes": "The scenario overlay itself is unchanged; generated TOMORROWLAND values verify the exact zero.",
        },
    ]
    append_unique(assumptions, "assumption_id", assumption_rows)
    write_csv("ASSUMPTIONS.csv", assumption_fields, assumptions)

    calc_fields, calculations = read_csv("CALCULATIONS.csv")
    calculation_rows = [
        {
            "calculation_id": "CALC_PHL_V18_PWR_COMMITTED_SCREEN",
            "formula": "screened DOE end-2020 aggregate committed register -> no applied minimum without project-level technology, COD and irrevocability proof",
            "source_ids": "SRC_PHL_PEP_2020_2040_COMMITTED",
            "assumption_ids": "ASM_PHL_V18_PWR_NO_COMMITTED_MINIMA;ASM_PHL_V18_PWR_2020_INFORMATION_CUTOFF",
            "input_calculation_ids": "",
            "input_values": "53 projects;8977.11",
            "input_units": "count;MW",
            "output_value": "0",
            "output_unit": "new minimum constraints",
            "script_path": "scripts/document_philippines_v18_power_investment_cleanup.py",
            "script_version": "2026-08-17",
            "notes": "Evidence screening, not an optimization calibration.",
        },
        {
            "calculation_id": "CALC_PHL_V18_PWR_RC_UNCHANGED",
            "formula": "candidate RYT.RC == control RYT.RC",
            "source_ids": "SRC_PHL_V18_PWR_INV_MANIFEST;SRC_PHL_V18_PWR_INV_VALIDATION",
            "assumption_ids": "ASM_PHL_V18_PWR_2020_INFORMATION_CUTOFF",
            "input_calculation_ids": "",
            "input_values": "true",
            "input_units": "boolean",
            "output_value": "unchanged",
            "output_unit": "status",
            "script_path": "scripts/validate_philippines_v18_power_investment_cleanup.py",
            "script_version": "2026-08-17",
            "notes": "Only the inherited 2020 fleet and its survival path remain as power initialization.",
        },
    ]
    map_fields, mappings = read_csv("MODEL_MAP.csv")
    mapping_rows: list[dict[str, str]] = [
        {
            "map_id": "MAP_PHL_V18_PWR_RC_UNCHANGED",
            "model_file": "case/Philippines_v18/RYT.json",
            "parameter": "ResidualCapacity",
            "entity": "2020 power fleet technologies",
            "mode": "",
            "scenario": "SC_0 and inherited scenarios",
            "years": "2020-2053",
            "value_or_expression": "unchanged by this cleanup",
            "model_unit": "GW",
            "evidence_ids": "CALC_PHL_V18_PWR_RC_UNCHANGED;ASM_PHL_V18_PWR_2020_INFORMATION_CUTOFF;SRC_PHL_DOE_POWER_PLANTS_DEC2020",
            "superseded_by": "",
            "evidence_type": "derived",
            "notes": "The 2020 stock is inherited; no 2021-2025 observed addition is moved into RC.",
        },
        {
            "map_id": "MAP_PHL_V18_PWR_COMMITTED_SCREEN",
            "model_file": "case/Philippines_v18/RYT.json",
            "parameter": "TotalAnnualMinCapacityInvestment screening",
            "entity": "end-2020 DOE committed-project aggregate",
            "mode": "",
            "scenario": "SC_0",
            "years": "2021 onward",
            "value_or_expression": "no new minimum applied",
            "model_unit": "GW/year",
            "evidence_ids": "CALC_PHL_V18_PWR_COMMITTED_SCREEN;ASM_PHL_V18_PWR_NO_COMMITTED_MINIMA;SRC_PHL_PEP_2020_2040_COMMITTED",
            "superseded_by": "",
            "evidence_type": "derived",
            "notes": "The aggregate register is evidence, not a forced build schedule.",
        },
        {
            "map_id": "MAP_PHL_V18_PWR_COAL_PHASEOUT_ZERO",
            "model_file": "case/Philippines_v18/RYT.json",
            "parameter": "TotalAnnualMaxCapacityInvestment",
            "entity": f"{tech_ids['PHL_POW_PP_COAL']} / PHL_POW_PP_COAL",
            "mode": "",
            "scenario": "SC_3hgjb / COAL_PHASEOUT",
            "years": "2031-2053",
            "value_or_expression": "0",
            "model_unit": "GW/year",
            "evidence_ids": "ASM_PHL_V18_PWR_ZERO_OVERRIDE_SEMANTICS;SRC_MUIO_FORMULATION;SRC_PHL_V18_PWR_INV_VALIDATION",
            "superseded_by": "",
            "evidence_type": "derived",
            "notes": "Unchanged scenario overlay; numeric zero is enforced while null denotes inheritance.",
        },
        {
            "map_id": "MAP_PHL_V18_PWR_VALIDATED_SOLUTION",
            "model_file": "case/Philippines_v18/RYT.json",
            "parameter": "validated source-result identity",
            "entity": "TOMORROWLAND power investment cleanup",
            "mode": "",
            "scenario": "SC_0 + COAL_PHASEOUT + RE + EV",
            "years": "2020-2053",
            "value_or_expression": "optimal objective 369758319.27495068; live source and data.txt byte-identical to candidate",
            "model_unit": "status and objective",
            "evidence_ids": "SRC_PHL_V18_PWR_INV_SOLVE;SRC_PHL_V18_PWR_INV_VALIDATION;SRC_PHL_V18_PWR_INV_PROMOTION",
            "superseded_by": "",
            "evidence_type": "derived",
            "notes": "One candidate optimization; no live re-solve after identity and GLPK checks passed.",
        },
        {
            "map_id": "MAP_PHL_V18_PWR_FOSSIL_TRADE_DIAGNOSTIC",
            "model_file": "case/Philippines_v18/RYTM.json",
            "parameter": "VariableCost diagnostic",
            "entity": "PHL_PRO_EXTR_COAL; PHL_PRO_IMP_COAL; PHL_PRO_EXP_COAL",
            "mode": "1",
            "scenario": "TOMORROWLAND",
            "years": "2022",
            "value_or_expression": "model exports 353.6 PJ domestic coal and imports 1198.1289 PJ; DOE benchmark production 16.06 Mt, exports 7.1 Mt, imports 32.7 Mt",
            "model_unit": "PJ and million metric tonnes",
            "evidence_ids": "SRC_PHL_PEP_2023_2050_VOL2_COAL_TRADE;SRC_PHL_V18_PWR_INV_VALIDATION",
            "superseded_by": "",
            "evidence_type": "direct",
            "notes": "Diagnostic only; no export activity pin or cap is introduced.",
        },
    ]

    for change in manifest["changes"]:
        parameter = change["parameter"]
        technology = change["technology"]
        year = int(change["year"])
        before = change["before"]
        after = change["after"]
        suffix = f"{parameter.upper()}_{tech_slug(technology)}_{year}"
        calc_id = f"CALC_PHL_V18_PWR_INV_{suffix}"
        map_id = f"MAP_PHL_V18_PWR_INV_{suffix}"
        if parameter == "TAMinCI":
            assumption_ids = "ASM_PHL_V18_PWR_2020_INFORMATION_CUTOFF;ASM_PHL_V18_PWR_NO_COMMITTED_MINIMA"
            source_ids = "SRC_PHL_DOE_POWER_STATISTICS_2024;SRC_PHL_V18_PWR_INV_MANIFEST"
            note = "Removed an observed-addition equality pin; the observed value remains a benchmark in the validation snapshot."
            full_parameter = "TotalAnnualMinCapacityInvestment"
        elif technology == "PHL_POW_PP_COAL":
            assumption_ids = "ASM_PHL_V18_DEPLOY_PP_COAL_2020_2029"
            source_ids = "SRC_PHL_DOE_POWER_PLANTS_DEC2020;SRC_PHL_V18_PWR_INV_MANIFEST"
            note = "Continuing construction-speed envelope; no investment or dispatch is required."
            full_parameter = "TotalAnnualMaxCapacityInvestment"
        elif technology in {"PHL_POW_CHP_COAL_OLD", "PHL_POW_CHP_NG_OLD", "PHL_POW_CHP_OIL_OLD", "PHL_POW_CHP_BIOM_OLD"}:
            assumption_ids = "ASM_PHL_V18_DEPLOY_OLD_STOCK_ONLY"
            source_ids = "SRC_PHL_DOE_POWER_PLANTS_DEC2020;SRC_PHL_V18_PWR_INV_MANIFEST"
            note = "Closes new entry for a legacy stock-only representation; RC is unchanged."
            full_parameter = "TotalAnnualMaxCapacityInvestment"
        else:
            assumption_ids = "ASM_PHL_V18_PWR_MATURE_ENTRY_2020;ASM_PHL_V18_PWR_2020_INFORMATION_CUTOFF"
            source_ids = "SRC_PHL_DOE_POWER_PLANTS_DEC2020;SRC_PHL_V18_PWR_INV_MANIFEST"
            note = "Clears a historical or first-year upper pin so investment is endogenous; later physical envelopes remain."
            full_parameter = "TotalAnnualMaxCapacityInvestment"
        calculation_rows.append(
            {
                "calculation_id": calc_id,
                "formula": f"{parameter}.SC_0[{technology},{year}] = {after} (replacing {before})",
                "source_ids": source_ids,
                "assumption_ids": assumption_ids,
                "input_calculation_ids": "",
                "input_values": f"{before};{after}",
                "input_units": "GW/year;GW/year",
                "output_value": str(after),
                "output_unit": "GW/year",
                "script_path": "scripts/apply_philippines_v18_power_investment_cleanup.py",
                "script_version": "2026-08-17",
                "notes": note,
            }
        )
        mapping_rows.append(
            {
                "map_id": map_id,
                "model_file": "case/Philippines_v18/RYT.json",
                "parameter": full_parameter,
                "entity": f"{tech_ids[technology]} / {technology}",
                "mode": "",
                "scenario": "SC_0; policy scenarios inherit unless an existing override is more restrictive",
                "years": str(year),
                "value_or_expression": str(after),
                "model_unit": "GW/year",
                "evidence_ids": f"{calc_id};{assumption_ids};{source_ids};SRC_MUIO_FORMULATION",
                "superseded_by": "",
                "evidence_type": "derived",
                "notes": note,
            }
        )

    append_unique(calculations, "calculation_id", calculation_rows)
    write_csv("CALCULATIONS.csv", calc_fields, calculations)
    append_unique(mappings, "map_id", mapping_rows)
    write_csv("MODEL_MAP.csv", map_fields, mappings)

    gap_fields, gaps = read_csv("GAPS.csv")
    gap_rows = [
        {
            "item": "Project-level mapping of end-2020 committed power capacity",
            "why_absent": "DOE Table 40 is aggregate by plant type and does not establish each project's model technology, surviving status, commercial-operation year or irreversible construction commitment.",
            "upgrade_source": "Freeze the 31 December 2020 project registers and project-level financial-close, construction-progress, cancellation and commissioning records; map each qualifying project to one model technology and vintage.",
            "priority": "medium",
            "notes": "Do not introduce technology-year minima from aggregate totals; new minima require project-level proof of an irreversible commitment known in 2020.",
        },
        {
            "item": "Coal export-import grade, location and price-parity representation",
            "why_absent": "The current single-energy-unit trade formulation makes 2022 export revenue (negative VC 4.266/PJ) exceed import cost (3.057/PJ), so the optimum exports the full 353.6 PJ domestic envelope and backfills with imports; DOE observed 7.1 Mt exports from 16.06 Mt production.",
            "upgrade_source": "Sourced mine-specific coal calorific value and quality, plant fuel specifications, domestic logistics, export terminal capacity and costs, and energy-normalized FOB/CIF price series by grade and location.",
            "priority": "high",
            "notes": "Do not force the observed export volume. Repair commodity differentiation or delivered economics, or apply only a sourced continuing physical terminal constraint.",
        },
        {
            "item": "Source-matched pre-change TOMORROWLAND result after fossil-supply restructuring",
            "why_absent": "The nearest retained optimal TOMORROWLAND result predates the already-present domestic/export fossil technology structure and therefore is not source-identical to the pre-cleanup live case.",
            "upgrade_source": "Retain a source manifest with every canonical solve whenever structural or parameter changes are promoted.",
            "priority": "medium",
            "notes": "The reported -0.002329 percent objective difference is contextual only; it cannot be attributed solely to the 62-cell power cleanup.",
        },
    ]
    append_unique(gaps, "item", gap_rows)
    write_csv("GAPS.csv", gap_fields, gaps)

    change_fields, changes = read_csv("CHANGES.csv")
    change_row = {
        "change_id": "CHG_PHL_V18_POWER_INVESTMENT_CLEANUP_20260817",
        "date": "2026-08-17",
        "class": "B",
        "description": "Removed all 20 post-2020 observed power-investment pins, closed legacy _OLD CHP representations to new entry for the full horizon, opened mature investable technologies in 2020, and extended the 2 GW/year coal construction envelope through 2020-2029 while preserving later bands and CoalPhaseOut's exact zero from 2031.",
        "model_objects": "case/Philippines_v18/RYT.json TAMinCI.SC_0 and TAMaxCI.SC_0 only; RC and scenario overlays unchanged",
        "evidence_path": "documentation/MODEL_FIXES_POWER_INVESTMENT_CLEANUP_2026-08-17.md;data_sources/snapshots/power_investment_cleanup_validation_2026-08-17.json;data_sources/snapshots/power_investment_cleanup_promotion_identity_2026-08-17.json",
        "map_rows_affected": ";".join(row["map_id"] for row in mapping_rows),
        "resolve_status": "resolved",
        "author": "Codex",
        "commit": "",
        "notes": "One disposable CBC run solved optimally at 369758319.27495068 in 371.19 wallclock seconds. Live RYT.json and data.txt are byte-identical to the solved candidate; live GLPK dimensions match; no live CBC rerun. The unrelated coal trade-price pathology is retained as a high-priority gap, not hidden with an activity constraint.",
    }
    append_unique(changes, "change_id", [change_row])
    write_csv("CHANGES.csv", change_fields, changes)

    print(json.dumps({
        "status": "pass",
        "sources_added": len(source_rows),
        "assumptions_added": len(assumption_rows),
        "calculations_added": len(calculation_rows),
        "model_map_rows_added": len(mapping_rows),
        "gaps_added": len(gap_rows),
        "changes_added": 1,
    }, indent=2))


if __name__ == "__main__":
    main()
