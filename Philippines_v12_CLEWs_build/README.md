# Philippines v12 CLEWs model

Philippines v12 is a hybrid MUIO case that retains the historical Philippines
v10 energy system, imports the current Fisheries **v2.3** sector, and replaces
the old placeholder land block with a country-specific, uncalibrated CLEWs
Global land–agriculture–water system.

## Start here

- Current model description: `documentation/CURRENT_MODEL.md`
- Model structure: `documentation/MODEL_STRUCTURE.md`
- Environmental accounting: `documentation/ENVIRONMENTAL_ACCOUNTING.md`
- Data sources: `data_sources/DATA_SOURCES.md`
- Assumptions: `data_sources/ASSUMPTIONS.csv`
- Calculations used by the model: `data_sources/CALCULATIONS.csv`
- Model-to-source map: `data_sources/MODEL_DATA_MAP.csv`
- Known limitations: `documentation/KNOWN_LIMITATIONS.md`
- Chronological history: `documentation/HISTORY.md`

Current guidance is separated from dated evidence. Historical records are
under `documentation/history/` and remain available without being mistaken
for the current formulation.

## Delivered models

- Portable source MUIO case:
  `muio/Philippines_v12_v12.0.0_MUIO.zip`
- Portable environmental-land MUIO case:
  `muio/Philippines_v12_ENV_LAND_v12.0.0_MUIO.zip`
- Portable diagnostic-case archive:
  `muio/Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC_v12.0.0_MUIO.zip`
- Environmental-land generator:
  `scripts/generate_environmental_land_case.py`
- Environmental-land validator:
  `scripts/validate_environmental_land_case.py`
- Environmental-water diagnostic generator and validator:
  `scripts/generate_environmental_water_diagnostic_case.py` and
  `scripts/validate_environmental_water_diagnostic_case.py`
- Rebuild script: `scripts/build_v12_hybrid.py`
- Full dated build record:
  `documentation/history/v12_build/BUILD_REPORT_2026-07-25.md`
- Fisheries v2.3 import record:
  `documentation/history/v12_build/FISHERIES_V23_IMPORT_PACKAGE_RECORD_2026-07-25.md`
- Fisheries detailed source record:
  `documentation/history/fisheries/DATA_SOURCE_REGISTER_v2.3_2026-07-25.md`
- Fisheries import audit: `diagnostics/fisheries_v23_import_audit.json`
- Validation summary: `diagnostics/validation_summary.json`
- Preservation and non-forcing audit: `diagnostics/v12_hybrid_audit.json`
- Sector summary: `diagnostics/sector_representation.json`
- Current environmental-land validation:
  `diagnostics/environmental_accounting/2026-07-25_env_land_final/`
- Current derived-case water, land and emissions accounts:
  `diagnostics/environmental_accounting/2026-07-25_env_land_accounts/`
- Current diagnostic water accounts and terminal reconciliation:
  `diagnostics/environmental_accounting/2026-07-26_env_water_diagnostic_accounts/`
- Current diagnostic-case validation:
  `diagnostics/environmental_accounting/2026-07-26_env_water_diagnostic_validation/`
- Current authoritative `ENV_WATER` Pivot publication and solver-view backup:
  `diagnostics/environmental_accounting/2026-07-26_env_water_pivot_published/`
- Environmental-accounting reporter:
  `scripts/report_environmental_accounting.py`
- Environmental-water Pivot publisher:
  `scripts/publish_environmental_water_pivot.py`
- Pinned upstream versions: `config/upstream_versions.json`
- Local upstream changes: `patches/`

## Representation

The unchanged source case contains 172 technologies, 92 commodities and three
constraints over 2020–2053 with the inherited v10 30-timeslice structure. The
derived environmental-land case contains 173 technologies, 99 commodities and
four constraints. The separate environmental-water diagnostic case contains
174 technologies, 99 commodities and four constraints.

Environmental accounting is hybrid. The derived case adds an exact eight-mode
`ENV_LAND` terminal, seven parallel land-stock commodities and the
`BAL_ENV_LAND` equality. Water vapor and modeled raw groundwater/surface-water
residuals remain reporting-only because the cluster technologies have
mode-dependent water coefficients that the installed technology-level MUIO
user-defined constraint cannot represent exactly. The separate diagnostic
case retains a three-mode, unforced `ENV_WATER` sink in the Dynamic Graph. A
reversible postprocessor publishes the authoritative
production-minus-ordinary-use reference under that existing name in the
linked Results Pivot variables without changing raw solver CSVs. Native
emissions remain in the existing mechanism.

The 42 new nexus technologies comprise:

- 24 crop-land options: six crop groups × high/low inputs ×
  irrigated/rain-fed;
- eight spatial cluster allocation technologies;
- six land-cover accounting technologies;
- surface-water and groundwater irrigation technologies;
- national land and precipitation endowments.

Crop outputs are rice, coconuts, maize, vegetables (GAEZ tomato proxy), sugar
cane, and an aggregated other-crops group. The eight clusters cover 295,813.1
km² of land cells.

The new nexus is connected to v10 through:

- `PHL_AGR_ELE` for groundwater pumping;
- `PHL_WTR_SUR` and `PHL_WTR_GWT` for inherited and new water uses;
- `PHL_WTR_PRC` and `PHL_WTR_EVT` for precipitation and
  evapotranspiration;
- `PHL_LND` for the total national land commodity.

## Verification

- Authoritative upstream raw CLEWs solve: **Optimal**, objective
  197,214.48967963.
- Integrated MUIO Base v12: **Optimal**, objective 375,930,821.3405416.
- Integrated MUIO PEP v12: **Optimal**, objective 375,953,763.4595271.
- Preservation audit: 130 retained v10 technology definitions, 55 retained
  commodity definitions, 36,780 dimensioned records, and 2,612 scalar values
  checked with zero mismatches.
- Fisheries: all seven technologies and 2,115 v10-keyed definitions/parameter
  records plus 140 scalar values match Fisheries v2.3 with zero mismatches;
  the sector import changed no non-Fisheries record.
- Crop balances: pass in Base and PEP; the largest reported relative
  difference is 0.0243%, caused by MUIO result CSV rounding.
- Validation suite: 10/10 checks pass.
- Environmental-accounting validation: **Pass**, including optimal saved and
  fresh-control Base and PEP runs, exact regenerated `data.txt` hashes,
  account closure, source non-interference, and documented solver-basis
  sensitivity.
- Derived `ENV_LAND` case: **Pass, 25/25 checks**. Base and PEP solve
  optimally; maximum terminal/source land difference is 0.0003 and maximum
  aggregate closure difference is 0.0001 `10^3 km2`; the land UDC reports
  exactly zero in every year.
- Diagnostic `ENV_WATER` case: **Pass, 18/18 checks**. Base and PEP solve
  optimally. Of 204 raw solver mode-year comparisons, the unforced terminal
  is zero in 194, partial in seven and complete within result precision in
  three.
- Authoritative `ENV_WATER` Pivot publication: **Pass**. Annual Pivot values
  agree with the reporter within 0.0000000000011; annual activity equals
  published water use exactly, timeslice activity equals timeslice water-use
  rate exactly, and model-period totals reconcile exactly. All
  non-`ENV_WATER` Pivot values and the Dynamic Graph source are unchanged.
  The Base-plus-PEP publication took 13.5 seconds.

## Interpretation

The energy setup and current Fisheries v2.3 sector are inherited from v10.
The new nexus is a technically valid raw country build: it uses country
boundary, land cover, agro-climatic potential, water, crop-production, and
population data, but it has not been calibrated to reproduce historical land
allocation, crop yields, irrigation withdrawals, or water balances. It is
suitable for structural exploration and as the starting point for a separate
calibration exercise.

The v10 policy scenarios do not override the new nexus. Changes in energy
results relative to v10 may still occur endogenously because irrigation
electricity and water flows are now connected to the inherited system.

The environmental water residuals describe the saved solver solution, not
unique sustainable water availability. Alternate cost-identical controls can
change the groundwater/surface-water split and, in PEP, the combined liquid
residual. See `documentation/ENVIRONMENTAL_ACCOUNTING.md` before interpreting
these accounts. The in-model land modes reproduce the source land states but
do not imply ecological condition, protection status or forest suitability.
In the diagnostic case, current Pivot values for `ENV_WATER` are authoritative
postprocessed reporting results. The original unforced optimizer values remain
in the raw result CSVs and the preserved solver-view backup.
