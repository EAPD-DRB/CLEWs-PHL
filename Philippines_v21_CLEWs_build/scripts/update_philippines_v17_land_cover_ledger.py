#!/usr/bin/env python3
"""Append the v17 land-cover records to the inherited cumulative ledger."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
LEDGER = PACKAGE / "data_sources"
SNAPSHOT = LEDGER / "snapshots" / "land_cover_2020.json"
SAFEGUARDS = LEDGER / "snapshots" / "land_transition_safeguards.json"
BUILD = LEDGER / "snapshots" / "land_cover_build_manifest.json"
VALIDATION = LEDGER / "snapshots" / "land_cover_validation.json"
ARCHIVE = PACKAGE / "muio" / "Philippines_v17_v17.0.0_MUIO.zip"
ARCHIVE_MANIFEST = LEDGER / "V17_MODEL_ARCHIVE_MANIFEST.csv"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append_rows(filename: str, rows: list[dict[str, str]], remove_ids: tuple[str, ...] = ()) -> None:
    path = LEDGER / filename
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        existing = list(reader)
    assert fieldnames is not None
    id_column = fieldnames[0]
    new_ids = {row[id_column] for row in rows}
    if len(new_ids) != len(rows):
        raise AssertionError(f"duplicate new IDs for {filename}")
    retained = [row for row in existing if row[id_column] not in new_ids | set(remove_ids)]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(retained + rows)


def main() -> None:
    for path in (SNAPSHOT, SAFEGUARDS, BUILD, VALIDATION, ARCHIVE, ARCHIVE_MANIFEST):
        if not path.is_file():
            raise FileNotFoundError(path)

    append_rows("SOURCES.csv", [
        {
            "source_id": "SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020",
            "provider": "Philippine Statistics Authority; National Mapping and Resource Information Authority",
            "product": "Land Asset Accounts of the Philippines / NAMRIA Land Cover Map 2020",
            "edition": "Special Release 2024-203; released 2024-12-20",
            "reference_period": "2020 closing stock",
            "geography": "Philippines",
            "variable": "Thirteen-class national land cover and total area",
            "source_unit": "km2",
            "exact_locator": "Statistical Table 1; technical notes; normalized transcription in snapshots/land_cover_2020.json",
            "url": "https://psa.gov.ph/statistics/environmental-accounts/node/1684065498",
            "access_date": "2026-08-12",
            "license": "PSA Open Data / CC BY 4.0 as stated on the release page",
            "sha256": sha256(SNAPSHOT),
            "local_file": "snapshots/land_cover_2020.json",
            "notes": "Exact PDF/XLSX URLs are frozen in the snapshot. Publisher anti-bot responses prevented retaining original bytes; the normalized input, mapping, and arithmetic are complete."
        },
        {
            "source_id": "SRC_FAO_FRA_2025_PHL_FOREST",
            "provider": "Food and Agriculture Organization of the United Nations",
            "product": "Global Forest Resources Assessment 2025 country report: Philippines",
            "edition": "FRA 2025",
            "reference_period": "2020",
            "geography": "Philippines",
            "variable": "Forest area",
            "source_unit": "1000 ha",
            "exact_locator": "Country-report handle A03488EN; forest 7226.39 kha",
            "url": "https://openknowledge.fao.org/handle/20.500.14283/A03488EN",
            "access_date": "2026-08-12",
            "license": "FAO publication terms",
            "sha256": sha256(SNAPSHOT),
            "local_file": "snapshots/land_cover_2020.json",
            "notes": "Corroboration only; not treated as fully independent and not used to replace PSA/NAMRIA inputs."
        },
        {
            "source_id": "SRC_PHL_PR1_LAND_DIAGNOSTIC",
            "provider": "EAPD-DRB contributor",
            "product": "CLEWs-PHL pull request 1 land-water findings and failed calibration passes",
            "edition": "head 721f5470e3ccd9e7237622c3270e68eae60a2faa",
            "reference_period": "diagnostic work through 2026-08-06",
            "geography": "Philippines",
            "variable": "Land-account defects and failed formulation variants",
            "source_unit": "diagnostic record",
            "exact_locator": "PR 1; Philippines_v12_CLEWs_build/documentation/LAND_WATER_CALIBRATION_DECISIONS.md section 12",
            "url": "https://github.com/EAPD-DRB/CLEWs-PHL/pull/1",
            "access_date": "2026-08-12",
            "license": "Repository terms",
            "sha256": sha256(SNAPSHOT),
            "local_file": "snapshots/land_cover_2020.json",
            "notes": "Diagnostic provenance only. The old v12 branch was not merged into v17."
        },
        {
            "source_id": "SRC_PHL_EO26_NGP_2011",
            "provider": "Office of the President of the Philippines",
            "product": "Executive Order No. 26: National Greening Program",
            "edition": "2011-02-24",
            "reference_period": "2011-2016 programme period",
            "geography": "Philippines",
            "variable": "National Greening Program area and implementation period",
            "source_unit": "hectares; years",
            "exact_locator": "Section 2, Coverage; normalized record in snapshots/land_transition_safeguards.json",
            "url": "https://lawphil.net/executive/execord/eo2011/eo_26_2011.html",
            "access_date": "2026-08-12",
            "license": "Philippine government publication",
            "sha256": sha256(SAFEGUARDS),
            "local_file": "snapshots/land_transition_safeguards.json",
            "notes": "Reports about 1.5 million hectares over six years. Used as a planning-rate benchmark, not observed net forest-cover change."
        },
        {
            "source_id": "SRC_PHL_EO193_ENGP_2015",
            "provider": "Office of the President of the Philippines",
            "product": "Executive Order No. 193: Expanded National Greening Program",
            "edition": "2015-11-12",
            "reference_period": "2016-2028 programme period",
            "geography": "Philippines",
            "variable": "Restoration scope and estimated degraded forestlands",
            "source_unit": "hectares; land eligibility language",
            "exact_locator": "Whereas clauses and Section 1; normalized record in snapshots/land_transition_safeguards.json",
            "url": "https://lawphil.net/executive/execord/eo2015/eo_193_2015.html",
            "access_date": "2026-08-12",
            "license": "Philippine government publication",
            "sha256": sha256(SAFEGUARDS),
            "local_file": "snapshots/land_transition_safeguards.json",
            "notes": "Targets unproductive, denuded and degraded forestlands; does not make every non-forest land-cover class available for restoration."
        },
        {
            "source_id": "SRC_FAO_FMB_PHL_PLANTATION_SUITABILITY",
            "provider": "FAO Regional Office for Asia and the Pacific; Philippine Forest Management Bureau",
            "product": "Conservation, utilization and management of forest genetic resources in the Philippines",
            "edition": "FORSPA Publication 31; 2002",
            "reference_period": "DENR/MPFD planning database circa 1990s",
            "geography": "Philippines",
            "variable": "National production-plantation suitability screen for grassland and brushland",
            "source_unit": "percent; hectares; slope class",
            "exact_locator": "Potential plantation areas and Table 3; normalized record in snapshots/land_transition_safeguards.json",
            "url": "https://www.fao.org/4/AC648E/ac648e09.htm",
            "access_date": "2026-08-12",
            "license": "FAO publication terms",
            "sha256": sha256(SAFEGUARDS),
            "local_file": "snapshots/land_transition_safeguards.json",
            "notes": "Reports that the DENR/MPFD screen included 80 percent of grassland and brushland subject to slope below 50 percent and no competing use. v17 applies 80 percent to current brush/shrub only."
        },
        {
            "source_id": "SRC_PSA_URBAN_POPULATION_2020",
            "provider": "Philippine Statistics Authority",
            "product": "Urban Population of the Philippines (2020 Census of Population and Housing)",
            "edition": "Reference No. 2022-271; released 2022-07-05",
            "reference_period": "2020",
            "geography": "Philippines",
            "variable": "Urban population and urban share",
            "source_unit": "persons; percent",
            "exact_locator": "Items 1-2; normalized record in snapshots/land_transition_safeguards.json",
            "url": "https://psa.gov.ph/content/urban-population-philippines-2020-census-population-and-housing",
            "access_date": "2026-08-12",
            "license": "PSA Open Data / CC BY 4.0",
            "sha256": sha256(SAFEGUARDS),
            "local_file": "snapshots/land_transition_safeguards.json",
            "notes": "Reports 58.93 million urban residents and a 54.0 percent urban share in 2020."
        },
        {
            "source_id": "SRC_WB_PHL_URBANIZATION_2050",
            "provider": "World Bank and Government of the Philippines",
            "product": "Philippines Urbanization Review: Fostering Competitive, Sustainable and Inclusive Cities",
            "edition": "2017",
            "reference_period": "2050 projection",
            "geography": "Philippines",
            "variable": "Urban population share outlook",
            "source_unit": "percent",
            "exact_locator": "Memorandum to Policy Makers and City Mayors; normalized record in snapshots/land_transition_safeguards.json",
            "url": "https://documents.worldbank.org/curated/en/963061495807736752/pdf/114088-REVISED-PUBLIC-Philippines-Urbanization-Review-Full-Report.pdf",
            "access_date": "2026-08-12",
            "license": "World Bank publication terms",
            "sha256": sha256(SAFEGUARDS),
            "local_file": "snapshots/land_transition_safeguards.json",
            "notes": "Only the approximately 65 percent urban-share outlook is used. Its absolute population projection is not mixed with the model's PSA Scenario 2 population series."
        },
        {
            "source_id": "SRC_PHL_V17_LAND_TRANSITION_INPUTS",
            "provider": "EAPD-DRB",
            "product": "Philippines v17 normalized land-transition safeguard inputs",
            "edition": "2026-08-12",
            "reference_period": "2020-2053",
            "geography": "Philippines",
            "variable": "Policy-rate proxy, grass reserve, eligible brush/shrub pool, class rules and limitations",
            "source_unit": "record",
            "exact_locator": "snapshots/land_transition_safeguards.json",
            "url": "",
            "access_date": "2026-08-12",
            "license": "Repository terms; underlying sources retain provider terms",
            "sha256": sha256(SAFEGUARDS),
            "local_file": "snapshots/land_transition_safeguards.json",
            "notes": "Freezes all numeric inputs, equations, model rules and interpretation limits used by the safeguard build."
        },
        {
            "source_id": "SRC_PHL_V17_LAND_BUILD",
            "provider": "EAPD-DRB",
            "product": "Philippines v17 land-cover build manifest",
            "edition": "2026-08-12",
            "reference_period": "2020-2053",
            "geography": "Philippines",
            "variable": "Source hashes, exact changed files and structural assertions",
            "source_unit": "record",
            "exact_locator": "snapshots/land_cover_build_manifest.json",
            "url": "",
            "access_date": "2026-08-12",
            "license": "Repository terms",
            "sha256": sha256(BUILD),
            "local_file": "snapshots/land_cover_build_manifest.json",
            "notes": "Generated from the complete current v16 source case."
        },
        {
            "source_id": "SRC_PHL_V17_LAND_VALIDATION",
            "provider": "EAPD-DRB",
            "product": "Philippines v17 land-cover full-chain validation",
            "edition": "2026-08-12",
            "reference_period": "2020-2053",
            "geography": "Philippines",
            "variable": "Land closure, class totals, idle/fallow, control regression and solver status",
            "source_unit": "record",
            "exact_locator": "snapshots/land_cover_validation.json",
            "url": "",
            "access_date": "2026-08-12",
            "license": "Repository terms",
            "sha256": sha256(VALIDATION),
            "local_file": "snapshots/land_cover_validation.json",
            "notes": "Uses the retained validated current-v16 live run and a fresh v17 MUIOGO/CBC solve; exact source identity protects unaffected sectors."
        },
        {
            "source_id": "SRC_PHL_V17_MODEL_ARCHIVE",
            "provider": "EAPD-DRB",
            "product": "Philippines v17 result-free portable MUIO case",
            "edition": "v17.0.0",
            "reference_period": "2020-2053",
            "geography": "Philippines",
            "variable": "Archive hash, size, member count, internal root and result exclusion",
            "source_unit": "record",
            "exact_locator": "V17_MODEL_ARCHIVE_MANIFEST.csv",
            "url": "",
            "access_date": "2026-08-12",
            "license": "Repository terms; third-party data retain provider terms",
            "sha256": sha256(ARCHIVE_MANIFEST),
            "local_file": "V17_MODEL_ARCHIVE_MANIFEST.csv",
            "notes": "Generated solver inputs, LP files and solver results are excluded and regenerated through MUIOGO."
        },
    ])

    append_rows("CALCULATIONS.csv", [
        {
            "calculation_id": "CALC_PHL_V17_LAND_RECONCILIATION",
            "formula": "exclude sea/ocean; aggregate 12 terrestrial PSA/NAMRIA classes to seven model classes; multiply by 295813.1/295566.4; close 0.1 km2 display rounding",
            "source_ids": "SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020",
            "assumption_ids": "ASM_PHL_V17_LAND_BOUNDARY;ASM_PHL_V17_CLASS_MAPPING",
            "input_calculation_ids": "",
            "input_values": "published total=295883.7; sea/ocean=317.3; land after exclusion=295566.4; model control=295813.1; scale=1.0008346686226852",
            "input_units": "km2; dimensionless",
            "output_value": "forest=72319.4; grass/woodland=77745.6; other=2287.9; barren=1595.0; built=10264.9; water=6319.8; cropland=125280.5; total=295813.1",
            "output_unit": "km2",
            "script_path": "scripts/build_philippines_v17_land_cover.py",
            "script_version": "2026-08-12",
            "notes": "Complete precision and class transcription are frozen in snapshots/land_cover_2020.json."
        },
        {
            "calculation_id": "CALC_PHL_V17_IDLE_FALLOW",
            "formula": "idle/fallow cropland = 2020 observed cropland equality - solved productive crop-land production",
            "source_ids": "SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020;SRC_PHL_V17_LAND_VALIDATION",
            "assumption_ids": "ASM_PHL_V17_IDLE_FALLOW_MODE;ASM_PHL_V17_LOTHTOT_HYDROLOGY_PROXY",
            "input_calculation_ids": "CALC_PHL_V17_LAND_RECONCILIATION",
            "input_values": "125.2805 - 119.9928",
            "input_units": "1000 km2",
            "output_value": "5.2877",
            "output_unit": "1000 km2",
            "script_path": "scripts/validate_philippines_v17_land_cover.py",
            "script_version": "2026-08-12",
            "notes": "Endogenous solved residual on existing LNDOTHTOT mode 2; not an independently observed series."
        },
        {
            "calculation_id": "CALC_PHL_V17_RESTORATION_POLICY_RATE",
            "formula": "1.5 million ha / 6 years / 100000 ha per 1000 km2",
            "source_ids": "SRC_PHL_EO26_NGP_2011",
            "assumption_ids": "ASM_PHL_V17_NGP_RATE_PROXY",
            "input_calculation_ids": "",
            "input_values": "1.5; 6; 100000",
            "input_units": "million ha; years; ha per 1000 km2",
            "output_value": "2.5",
            "output_unit": "1000 km2/year",
            "script_path": "scripts/build_philippines_v17_land_cover.py",
            "script_version": "2026-08-12",
            "notes": "A transparent upper-envelope proxy; area targeted or planted is not equivalent to surviving net forest-cover gain."
        },
        {
            "calculation_id": "CALC_PHL_V17_GRASS_BRUSH_ELIGIBILITY",
            "formula": "reserve = 19610.0 * 1.0008346686226852 / 1000; mapped brush = 77.7456 - reserve; forest-eligible brush = mapped brush * 0.80",
            "source_ids": "SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020;SRC_FAO_FMB_PHL_PLANTATION_SUITABILITY",
            "assumption_ids": "ASM_PHL_V17_BRUSH_ELIGIBILITY_PROXY",
            "input_calculation_ids": "CALC_PHL_V17_LAND_RECONCILIATION",
            "input_values": "grassland=19610.0; brush/shrubs=58070.8; scale=1.0008346686226852; aggregate=77.7456",
            "input_units": "km2; dimensionless; 1000 km2",
            "output_value": "true-grass reserve=19.6264; mapped brush/shrub=58.1192; forest-eligible brush/shrub=46.49536; maximum forest=118.81476",
            "output_unit": "1000 km2",
            "script_path": "scripts/build_philippines_v17_land_cover.py",
            "script_version": "2026-08-12",
            "notes": "The 80 percent screen applies only to net forest expansion above 2020. All mapped brush remains available to cropland and built-up land through the national balance."
        },
        {
            "calculation_id": "CALC_PHL_V17_BUILT_UP_PATH",
            "formula": "built[y] = 10.2649 * (PSA Scenario 2 population[y]/population[2020]) * (urban_share[y]/0.54); urban share interpolates linearly from 0.54 in 2020 to 0.65 in 2050 and remains 0.65 thereafter",
            "source_ids": "SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020;SRC_PSA_CBPP_2020_SCENARIO2;SRC_PSA_URBAN_POPULATION_2020;SRC_WB_PHL_URBANIZATION_2050",
            "assumption_ids": "ASM_PHL_V17_BUILT_UP_CENTRAL_PATH",
            "input_calculation_ids": "CALC_PHL_V17_LAND_RECONCILIATION;CALC_PHL_V16_PUBLIC_DEMAND",
            "input_values": "built2020=10.2649; urban2020=0.54; urban2050=0.65; annual PSA Scenario 2 population ratio",
            "input_units": "1000 km2; fraction; dimensionless",
            "output_value": "2020=10.2649;2030=11.9326929331;2050=15.4217285825;2053=15.5828875716",
            "output_unit": "1000 km2",
            "script_path": "scripts/build_philippines_v17_land_cover.py",
            "script_version": "2026-08-12",
            "notes": "Central case only. It assumes constant built-up area per urban resident and is fixed by annual TAMLL=TAMUL."
        },
        {
            "calculation_id": "CALC_PHL_V17_LAND_SAFEGUARD_ENVELOPES",
            "formula": "forest release[y]=min(2.5*(y-2020),46.49536); forest lower=72.3194; forest upper=72.3194+release[y]; grass/brush lower=19.6264 and upper=77.7456; built-up lower=upper=central path; modes 3,4,6 fixed at 2020; cropland lower=125.2805; unallocated upper=0.000001",
            "source_ids": "SRC_PHL_V17_LAND_TRANSITION_INPUTS",
            "assumption_ids": "ASM_PHL_V17_NGP_RATE_PROXY;ASM_PHL_V17_BRUSH_ELIGIBILITY_PROXY;ASM_PHL_V17_NONCONVERTIBLE_CLASS_PRESERVATION;ASM_PHL_V17_CROPLAND_RESERVE",
            "input_calculation_ids": "CALC_PHL_V17_RESTORATION_POLICY_RATE;CALC_PHL_V17_GRASS_BRUSH_ELIGIBILITY;CALC_PHL_V17_BUILT_UP_PATH;CALC_PHL_V17_LAND_RECONCILIATION",
            "input_values": "See snapshots/land_transition_safeguards.json",
            "input_units": "1000 km2; year",
            "output_value": "Annual TAMLL/TAMUL values for ENV_LAND modes 1-8, 2020-2053",
            "output_unit": "1000 km2",
            "script_path": "scripts/build_philippines_v17_land_cover.py",
            "script_version": "2026-08-12",
            "notes": "Only forest receives the 80 percent brush-suitability ceiling. Cropland and built-up land may use all brush above the true-grass reserve. The nonzero unallocated sentinel is required because MUIOGO omits numeric-zero activity bounds."
        },
        {
            "calculation_id": "CALC_PHL_V17_LAND_SOLVER_VALIDATION",
            "formula": "retained validated current-v16 live control + fresh v17 generation/preprocessing/CBC solve + source, closure, class, activity, demand, water and emission checks",
            "source_ids": "SRC_PHL_V17_LAND_BUILD;SRC_PHL_V17_LAND_VALIDATION",
            "assumption_ids": "ASM_PHL_V17_BASE_YEAR_EQUALITY;ASM_PHL_V17_FOREST_VC_DEFERRED;ASM_PHL_V17_NGP_RATE_PROXY;ASM_PHL_V17_BRUSH_ELIGIBILITY_PROXY;ASM_PHL_V17_BUILT_UP_CENTRAL_PATH;ASM_PHL_V17_NONCONVERTIBLE_CLASS_PRESERVATION;ASM_PHL_V17_CROPLAND_RESERVE",
            "input_calculation_ids": "CALC_PHL_V17_LAND_RECONCILIATION;CALC_PHL_V17_IDLE_FALLOW;CALC_PHL_V17_LAND_SAFEGUARD_ENVELOPES",
            "input_values": "See snapshots/land_cover_validation.json",
            "input_units": "model units; seconds",
            "output_value": "optimal; exact 2020 land partition; zero unallocated; annual national closure; all transition and class safeguards satisfied",
            "output_unit": "status",
            "script_path": "scripts/validate_philippines_v17_land_cover.py",
            "script_version": "2026-08-12",
            "notes": "Observed 2020 class equalities are initialization, not independent validation."
        },
    ])

    append_rows("ASSUMPTIONS.csv", [
        {
            "assumption_id": "ASM_PHL_V17_LAND_BOUNDARY",
            "statement": "Exclude PSA/NAMRIA Sea and ocean from the terrestrial model and reconcile the remaining land pro rata to the inherited 295813.1 km2 geographic control.",
            "central_value": "1.0008346686226852",
            "unit": "scale factor",
            "evidence_source_ids": "SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "Preserves the current model geography and closes the land account without adding or dropping modeled territory.",
            "notes": "The pre-reconciliation difference is disclosed in the input snapshot."
        },
        {
            "assumption_id": "ASM_PHL_V17_CLASS_MAPPING",
            "statement": "Map brush/shrubs to grassland/woodland, marsh/swamp to water bodies, and fishpond to other agricultural land.",
            "central_value": "seven-class concordance",
            "unit": "classification rule",
            "evidence_source_ids": "SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020;SRC_FAO_FRA_2025_PHL_FOREST",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "Matches the available model stocks while preserving the official forest boundary and treating fishpond as managed production land.",
            "notes": "Replace if a future model adds wetland or aquaculture-land stocks."
        },
        {
            "assumption_id": "ASM_PHL_V17_BASE_YEAR_EQUALITY",
            "statement": "Initialize all eight national ENV_LAND modes with lower-equals-upper activity bounds in 2020 and keep MINLNDTOT lower-equals-upper at 295.8131 thousand km2 in every model year.",
            "central_value": "2020 class equalities; 2020-2053 national equality",
            "unit": "model formulation",
            "evidence_source_ids": "SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020;SRC_PHL_PR1_LAND_DIAGNOSTIC",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "A forest floor absorbs the rewarded residual and an open national endowment lets area disappear; equality fixes the observed base year and closes every annual national account.",
            "notes": "National totals only; no unsupported per-cluster pro-rata pins."
        },
        {
            "assumption_id": "ASM_PHL_V17_IDLE_FALLOW_MODE",
            "statement": "Reuse existing LNDOTHTOT mode 2 as a nonnegative endogenous idle/fallow cropland route, capped at its observed 2020 balancing stock, rather than adding a new technology or global mode.",
            "central_value": "mode 2",
            "unit": "model formulation",
            "evidence_source_ids": "SRC_PHL_V17_LAND_BUILD;SRC_PHL_V17_LAND_VALIDATION",
            "lower_bound": "0",
            "upper_bound": "5.2877",
            "rationale": "Separates observed cropland cover from productive harvested-area-equivalent activity while preventing an accounting mode from absorbing brush as unsourced new idle cropland.",
            "notes": "2020 solved idle/fallow is 5.2877 thousand km2; productive crop technologies have no added upper bound."
        },
        {
            "assumption_id": "ASM_PHL_V17_LOTHTOT_HYDROLOGY_PROXY",
            "statement": "Both LNDOTHTOT modes produce LOTHTOT, so idle/fallow cropland inherits the existing cluster mode-29 other-land hydrology coefficients.",
            "central_value": "LOTHTOT coefficient 1",
            "unit": "proxy formulation",
            "evidence_source_ids": "SRC_PHL_V17_LAND_BUILD",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "Preserves the existing water links without inventing national-to-cluster land-cover shares.",
            "notes": "Upgrade with measured idle/fallow evapotranspiration/runoff and spatial allocation."
        },
        {
            "assumption_id": "ASM_PHL_V17_FOREST_VC_DEFERRED",
            "statement": "Retain forest mode-27 VC=-10 while adding a national expansion envelope; defer restoration/conversion costs or lags and benefit sensitivities.",
            "central_value": "-10",
            "unit": "model variable-cost unit",
            "evidence_source_ids": "SRC_PHL_V17_LAND_BUILD",
            "lower_bound": "",
            "upper_bound": "",
            "rationale": "Preserves the user's forest-benefit policy signal while separate activity bounds prevent implausible instantaneous expansion.",
            "notes": "Future cases proposed: 0, -5, -10, and a higher-benefit case."
        },
        {
            "assumption_id": "ASM_PHL_V17_NGP_RATE_PROXY",
            "statement": "Use the original National Greening Program target area divided by its six-year period as a conservative national forest-expansion envelope rate.",
            "central_value": "2.5",
            "unit": "1000 km2/year",
            "evidence_source_ids": "SRC_PHL_EO26_NGP_2011;SRC_PHL_V17_LAND_TRANSITION_INPUTS",
            "lower_bound": "0",
            "upper_bound": "2.5",
            "rationale": "Provides a transparent Philippine policy-scale rate and prevents the rewarded forest mode from taking the entire residual in one year.",
            "notes": "Programme target area is not measured net forest-cover change; the model uses it only as an upper-envelope proxy."
        },
        {
            "assumption_id": "ASM_PHL_V17_BRUSH_ELIGIBILITY_PROXY",
            "statement": "Preserve the reconciled true-grassland component and apply the DENR/MPFD 80 percent production-plantation suitability screen only to the mapped brush/shrub component when limiting net forest expansion.",
            "central_value": "reserve=19.6264; mapped brush=58.1192; forest-eligible brush=46.49536",
            "unit": "1000 km2",
            "evidence_source_ids": "SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020;SRC_FAO_FMB_PHL_PLANTATION_SUITABILITY;SRC_PHL_V17_LAND_TRANSITION_INPUTS",
            "lower_bound": "19.6264 true grass retained",
            "upper_bound": "46.49536 net forest expansion from brush",
            "rationale": "The national DENR/MPFD screen supplies a documented central suitability fraction while excluding true grassland from forest conversion.",
            "notes": "The ceiling is forest-only. Cropland and built-up land may use the full mapped brush stock. Upgrade with a current parcel overlay of legal forestland, tenure, slope, soils, biodiversity and restoration suitability."
        },
        {
            "assumption_id": "ASM_PHL_V17_BUILT_UP_CENTRAL_PATH",
            "statement": "Grow built-up land in proportion to the model's PSA Scenario 2 population and a linearly rising urban share from 54 percent in 2020 to 65 percent in 2050, holding the share constant thereafter.",
            "central_value": "2020=10.2649;2050=15.4217285825;2053=15.5828875716",
            "unit": "1000 km2",
            "evidence_source_ids": "SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020;SRC_PSA_CBPP_2020_SCENARIO2;SRC_PSA_URBAN_POPULATION_2020;SRC_WB_PHL_URBANIZATION_2050",
            "lower_bound": "annual central path",
            "upper_bound": "annual central path",
            "rationale": "Population alone misses continuing urbanization; constant built-up area per urban resident is a transparent aggregate central approximation.",
            "notes": "No density sensitivity or spatial allocation is included. Development draws land through the closed national balance."
        },
        {
            "assumption_id": "ASM_PHL_V17_NONCONVERTIBLE_CLASS_PRESERVATION",
            "statement": "Keep other agricultural land (mapped fishpond), barren land and water bodies equal to their reconciled 2020 stocks in every future year.",
            "central_value": "2.2879;1.5950;6.3198",
            "unit": "1000 km2",
            "evidence_source_ids": "SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020;SRC_PHL_V17_LAND_TRANSITION_INPUTS",
            "lower_bound": "2020 stock",
            "upper_bound": "2020 stock",
            "rationale": "The aggregate model lacks sourced fishpond, barren-land and wetland transition trajectories; allowing these stocks to disappear created physically invalid residual adjustments.",
            "notes": "Built-up land is no longer fixed; it follows ASM_PHL_V17_BUILT_UP_CENTRAL_PATH."
        },
        {
            "assumption_id": "ASM_PHL_V17_CROPLAND_RESERVE",
            "statement": "Keep total cropland at least at its reconciled 2020 stock while allowing productive crop area to respond endogenously to crop demand and retaining the balance as idle/fallow mode 2.",
            "central_value": "125.2805",
            "unit": "1000 km2 minimum",
            "evidence_source_ids": "SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020;SRC_PHL_V17_LAND_TRANSITION_INPUTS",
            "lower_bound": "125.2805",
            "upper_bound": "national land balance",
            "rationale": "Prevents the model from treating observed idle/fallow cropland as immediately disposable while preserving endogenous food-production choices.",
            "notes": "This is a land reserve, not a forced production level; modeled crop demands remain unchanged."
        },
    ])

    append_rows("MODEL_MAP.csv", [
        {"map_id":"MAP_PHL_V17_LAND_SUPPLY_EQUALITY","model_file":"case/Philippines_v17/RYT.json","parameter":"TAL;TAU","entity":"MINLNDTOT","mode":"","scenario":"SC_0 and inherited policy scenarios","years":"2020-2053","value_or_expression":"295.8131 lower = upper","model_unit":"1000 km2","evidence_ids":"SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020;CALC_PHL_V17_LAND_RECONCILIATION","superseded_by":"","evidence_type":"derived","notes":"Annual national land cannot disappear from the accounts."},
        {"map_id":"MAP_PHL_V17_BASE_YEAR_CLASSES","model_file":"case/Philippines_v17/RYTM.json","parameter":"TAMLL;TAMUL","entity":"ENV_LAND","mode":"1-8","scenario":"SC_0 and inherited policy scenarios","years":"2020","value_or_expression":"72.3194;77.7456;2.2879;1.5950;10.2649;6.3198;125.2805;0","model_unit":"1000 km2","evidence_ids":"SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020;CALC_PHL_V17_LAND_RECONCILIATION","superseded_by":"","evidence_type":"derived","notes":"National initialization equalities; future years follow the separately mapped safeguards."},
        {"map_id":"MAP_PHL_V17_FOREST_EXPANSION_ENVELOPE","model_file":"case/Philippines_v17/RYTM.json","parameter":"TAMLL;TAMUL","entity":"ENV_LAND","mode":"1","scenario":"SC_0 and inherited policy scenarios","years":"2021-2053","value_or_expression":"lower=72.3194; upper=72.3194+min(2.5*(year-2020),46.49536); absolute maximum=118.81476","model_unit":"1000 km2","evidence_ids":"SRC_PHL_EO26_NGP_2011;SRC_FAO_FMB_PHL_PLANTATION_SUITABILITY;CALC_PHL_V17_RESTORATION_POLICY_RATE;CALC_PHL_V17_GRASS_BRUSH_ELIGIBILITY;CALC_PHL_V17_LAND_SAFEGUARD_ENVELOPES","superseded_by":"","evidence_type":"derived","notes":"Forest-only cumulative net expansion ceiling; cropland and built-up conversion of brush is unrestricted by this bound."},
        {"map_id":"MAP_PHL_V17_GRASS_BRUSH_ENVELOPE","model_file":"case/Philippines_v17/RYTM.json","parameter":"TAMLL;TAMUL","entity":"ENV_LAND","mode":"2","scenario":"SC_0 and inherited policy scenarios","years":"2021-2053","value_or_expression":"lower=19.6264; upper=77.7456","model_unit":"1000 km2","evidence_ids":"SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020;CALC_PHL_V17_GRASS_BRUSH_ELIGIBILITY;CALC_PHL_V17_LAND_SAFEGUARD_ENVELOPES","superseded_by":"","evidence_type":"derived","notes":"Protects true grassland only. Brush may convert immediately to cropland or built-up land through the closed national balance."},
        {"map_id":"MAP_PHL_V17_BUILT_UP_PATH","model_file":"case/Philippines_v17/RYTM.json","parameter":"TAMLL;TAMUL","entity":"ENV_LAND","mode":"5","scenario":"SC_0 and inherited policy scenarios","years":"2021-2053","value_or_expression":"10.2649*(PSA population[y]/population[2020])*(urban_share[y]/0.54); lower=upper","model_unit":"1000 km2","evidence_ids":"SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020;SRC_PSA_CBPP_2020_SCENARIO2;SRC_PSA_URBAN_POPULATION_2020;SRC_WB_PHL_URBANIZATION_2050;CALC_PHL_V17_BUILT_UP_PATH","superseded_by":"","evidence_type":"derived","notes":"Central path only; urban share reaches 0.65 in 2050 and remains constant through 2053."},
        {"map_id":"MAP_PHL_V17_FIXED_LAND_CLASSES","model_file":"case/Philippines_v17/RYTM.json","parameter":"TAMLL;TAMUL","entity":"ENV_LAND","mode":"3,4,6","scenario":"SC_0 and inherited policy scenarios","years":"2021-2053","value_or_expression":"other=2.2879; barren=1.5950; water=6.3198; lower=upper","model_unit":"1000 km2","evidence_ids":"SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020;ASM_PHL_V17_NONCONVERTIBLE_CLASS_PRESERVATION;CALC_PHL_V17_LAND_SAFEGUARD_ENVELOPES","superseded_by":"","evidence_type":"derived","notes":"Conservative preservation pending sourced class-specific transition trajectories."},
        {"map_id":"MAP_PHL_V17_CROPLAND_FLOOR","model_file":"case/Philippines_v17/RYTM.json","parameter":"TAMLL","entity":"ENV_LAND","mode":"7","scenario":"SC_0 and inherited policy scenarios","years":"2021-2053","value_or_expression":"125.2805","model_unit":"1000 km2","evidence_ids":"SRC_PSA_NAMRIA_LAND_ACCOUNTS_2020;ASM_PHL_V17_CROPLAND_RESERVE;CALC_PHL_V17_LAND_SAFEGUARD_ENVELOPES","superseded_by":"","evidence_type":"derived","notes":"Total land-cover floor only; crop production remains demand-driven and idle/fallow is endogenous."},
        {"map_id":"MAP_PHL_V17_ZERO_UNALLOCATED","model_file":"case/Philippines_v17/RYTM.json","parameter":"TAMLL;TAMUL","entity":"ENV_LAND","mode":"8","scenario":"SC_0 and inherited policy scenarios","years":"2021-2053","value_or_expression":"lower=0; upper=0.000001","model_unit":"1000 km2","evidence_ids":"SRC_PHL_PR1_LAND_DIAGNOSTIC;CALC_PHL_V17_LAND_SAFEGUARD_ENVELOPES","superseded_by":"","evidence_type":"derived","notes":"MUIOGO omits numeric-zero activity bounds as sparse defaults. The positive sentinel enforces at most 0.001 km2 (0.1 ha), operationally zero, and prevents an unsourced residual class."},
        {"map_id":"MAP_PHL_V17_IDLE_FALLOW_STRUCTURE","model_file":"case/Philippines_v17/genData.json;RYTCM.json","parameter":"IAR;OAR","entity":"LNDOTHTOT; PHL_LND; LOTHTOT; ENV_LND_CROPLAND","mode":"2","scenario":"SC_0 and inherited policy scenarios","years":"2020-2053","value_or_expression":"PHL_LND 1 -> LOTHTOT 1 + ENV_LND_CROPLAND 1","model_unit":"ratio","evidence_ids":"SRC_PHL_V17_LAND_BUILD;CALC_PHL_V17_IDLE_FALLOW","superseded_by":"","evidence_type":"derived","notes":"Existing mode reused; zero value and no activity floor."},
        {"map_id":"MAP_PHL_V17_IDLE_FALLOW_CEILING","model_file":"case/Philippines_v17/RYTM.json","parameter":"TAMUL","entity":"LNDOTHTOT","mode":"2","scenario":"SC_0 and inherited policy scenarios","years":"2020-2053","value_or_expression":"5.2877","model_unit":"1000 km2","evidence_ids":"CALC_PHL_V17_IDLE_FALLOW;ASM_PHL_V17_IDLE_FALLOW_MODE","superseded_by":"","evidence_type":"derived","notes":"Prevents the bookkeeping route from absorbing brush as new idle cropland; productive crop technologies retain their inherited freedom to expand."},
        {"map_id":"MAP_PHL_V17_FOREST_VC_RETAINED","model_file":"case/Philippines_v17/RYTM.json","parameter":"VC","entity":"LNDAGRPHLC01...LNDAGRPHLC08","mode":"27","scenario":"all","years":"2020-2053","value_or_expression":"-10 unchanged from v16","model_unit":"model variable-cost unit","evidence_ids":"SRC_PHL_V17_LAND_BUILD;ASM_PHL_V17_FOREST_VC_DEFERRED","superseded_by":"","evidence_type":"estimated","notes":"Complete VC parameter is identical to v16."},
        {"map_id":"MAP_PHL_V17_LAND_VALIDATION","model_file":"case/Philippines_v17/res/LAND_SAFEGUARDS_CENTRAL_COMPLETE","parameter":"validation evidence","entity":"Philippines_v17","mode":"all","scenario":"SC_0","years":"2020-2053","value_or_expression":"optimal solve; exact class, closure, source-bound, safeguard and solved annual-increase checks; retained validated v16 control comparison","model_unit":"status","evidence_ids":"SRC_PHL_V17_LAND_VALIDATION;CALC_PHL_V17_LAND_SOLVER_VALIDATION","superseded_by":"","evidence_type":"derived","notes":"Generated solver results are validation outputs and excluded from the portable archive."},
        {"map_id":"MAP_PHL_V17_CANONICAL_PACKAGE","model_file":"muio/Philippines_v17_v17.0.0_MUIO.zip","parameter":"complete editable source package","entity":"Philippines_v17","mode":"all","scenario":"all","years":"2020-2053","value_or_expression":"result-free v17.0.0 archive; SHA-256 in V17_MODEL_ARCHIVE_MANIFEST.csv and muio/SHA256SUMS","model_unit":"archive","evidence_ids":"SRC_PHL_V17_MODEL_ARCHIVE;SRC_PHL_V17_LAND_BUILD;SRC_PHL_V17_LAND_VALIDATION","superseded_by":"","evidence_type":"direct","notes":"The surrounding v17 build package carries the complete cumulative ledger and retained evidence; no earlier package is required."},
    ])

    append_rows("GAPS.csv", [
        {"item":"Official PSA/NAMRIA and FAO publication bytes for v17 land evidence","why_absent":"Publisher anti-bot responses returned HTTP 403 for PSA files and reset the FAO connection during packaging.","upgrade_source":"Download the exact URLs frozen in snapshots/land_cover_2020.json when publisher access permits and add their checksums without changing the normalized inputs.","priority":"medium","notes":"The exact normalized transcription, locators, mapping, arithmetic and source URLs are retained now."},
        {"item":"Spatial allocation of national land-cover classes to the eight yield clusters","why_absent":"The retained PSA/NAMRIA table is national and no defensible overlay with the model cluster geometries was available.","upgrade_source":"Overlay NAMRIA Land Cover Map 2020 with the retained eight-cluster polygons and aggregate each model class by cluster.","priority":"high","notes":"v17 deliberately avoids unsupported pro-rata cluster pins."},
        {"item":"Forest transition dynamics and current parcel suitability","why_absent":"v17 installs a national cumulative expansion envelope and a documented 80 percent historical planning screen but lacks gross inter-year transition flows, a current parcel overlay, survival, costs and lags.","upgrade_source":"Observed land-use transition matrices; legal forestland and tenure overlays; slope, soil, biodiversity and restoration suitability; programme survival, costs and duration; conversion costs.","priority":"high","notes":"The 80 percent screen is forest-only and the 2.5 thousand km2/year policy-rate proxy is not measured net forest-cover change."},
        {"item":"Idle/fallow land hydrology","why_absent":"Mode 2 uses LOTHTOT and therefore inherits the existing other-land hydrology proxy rather than measured idle/fallow coefficients.","upgrade_source":"National or cluster-specific idle/fallow runoff, evapotranspiration and precipitation-partition evidence.","priority":"medium","notes":"The proxy is explicit and does not create a per-cluster area cap."},
    ], remove_ids=("Parcel-level forest transition dynamics, restoration costs and benefit sensitivity",))

    append_rows("CHANGES.csv", [
        {"change_id":"CHG_PHL_V17_LAND_COVER_20260812","date":"2026-08-12","class":"B","description":"Added the reconciled PSA/NAMRIA 2020 land partition, annual national closure, idle/fallow cropland, a 2.5 thousand km2/year forest envelope capped to 80 percent of mapped brush, a true-grass reserve, central population-urbanization built-up growth, preserved other/fishpond barren and water stocks, and a 2020 cropland floor while retaining forest VC=-10.","model_objects":"genData.json; RYT.json; RYTM.json; RYTCM.json; ENV_LAND; MINLNDTOT; LNDOTHTOT mode 2","evidence_path":"calculation_notes/land_cover_v17_2026-08-12.md","map_rows_affected":"MAP_PHL_V17_LAND_SUPPLY_EQUALITY;MAP_PHL_V17_BASE_YEAR_CLASSES;MAP_PHL_V17_FOREST_EXPANSION_ENVELOPE;MAP_PHL_V17_GRASS_BRUSH_ENVELOPE;MAP_PHL_V17_BUILT_UP_PATH;MAP_PHL_V17_FIXED_LAND_CLASSES;MAP_PHL_V17_CROPLAND_FLOOR;MAP_PHL_V17_ZERO_UNALLOCATED;MAP_PHL_V17_IDLE_FALLOW_STRUCTURE;MAP_PHL_V17_IDLE_FALLOW_CEILING;MAP_PHL_V17_FOREST_VC_RETAINED;MAP_PHL_V17_LAND_VALIDATION","resolve_status":"resolved","author":"Codex","commit":"51867d9","notes":"The 80 percent cap is forest-only; crops and built-up may clear any brush above the protected true-grass floor. No technology commodity UDC or global mode added."}
    ])
    print("updated v17 cumulative land-cover ledger")


if __name__ == "__main__":
    main()
