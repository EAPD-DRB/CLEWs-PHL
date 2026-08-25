# Philippines v12 data sources

This is the current, consolidated human-readable source register. It covers
all three model lineages and distinguishes external data from modeller
assumptions and calculations. The latter are indexed separately so that a
source publication is never confused with a modelling choice.

## How to use this register

1. Find the model row or configuration item in `MODEL_MAP.csv`.
2. Follow its `evidence_ids` into `SOURCES.csv`, `ASSUMPTIONS.csv` and
   `CALCULATIONS.csv`.
3. Use `GAPS.csv` before making a completeness claim and `CHANGES.csv` to
   identify ledger revisions.
4. Use this file for a narrative overview and `calculation_notes/` for
   transformations that need more explanation.
5. Do not claim a more precise origin than the exact locator actually
   retained in the canonical ledgers.

## Historical energy system

| Source ID | Source | Model use | Status |
|---|---|---|---|
| `DS-V10-ENERGY` | Philippines v10 MUIO model and its retained dated change records | Donor for the v12 energy system | Values and changes preserved; a complete original row-level bibliography was not found |
| `DS-V10-MODEL-FIXES` | `WebAPP/DataStorage/Philippines_v12/documentation/history/v10/MODEL_FIXES_2026-07-17.md` | Explains documented PM2.5, transport and orphan-technology corrections | Exact dated record |

The absence of a complete v10 bibliography is a known documentation gap. The
current model must not be described as fully source-traceable for every
inherited energy parameter until that register is reconstructed.
`GAPS.csv` records the precise missing evidence and a proposed recovery path.

## Land, agriculture and water

| Source ID | Provider and dataset | Model use | Location or entry point |
|---|---|---|---|
| `DS-GADM-4.1` | GADM, version 4.1, Philippines administrative level 0 | National boundary and land-cell clipping | `geospatial/boundary/`; https://gadm.org/download_country.html |
| `DS-GAEZ-V4-YIELD` | FAO Global Agro-Ecological Zones v4 | Irrigated/rain-fed and high/low-input crop yield coefficients | https://gaez.fao.org/ |
| `DS-GAEZ-V4-WATER` | FAO GAEZ v4 | Crop water deficit, evapotranspiration and precipitation coefficients | https://gaez.fao.org/ |
| `DS-GAEZ-V4-LANDCOVER` | FAO GAEZ v4 land-cover raster | Cluster shares for bare, built-up, forest, grassland, other and water-body land | `geospatial/summary_stats/`; https://gaez.fao.org/ |
| `DS-FAOSTAT-2020-CROPS` | FAOSTAT crop harvested-area and production tables bundled by the upstream workflow | Crop selection and 2020 crop-output demand anchors | https://www.fao.org/faostat/ |
| `DS-SSP2-POP` | IIASA-WiC SSP2 population series bundled by OSeMOSYS Global | Population-only growth of crop-output demand through 2053 | Upstream model inputs |
| `DS-PAGASA-SEASONS` | PAGASA climate description for the Philippines | Wet season June–November; dry season December–May | https://www.pagasa.dost.gov.ph/information/climate-philippines |
| `DS-CLEWS-GLOBAL` | Pinned CLEWs Global, CLEWs GAEZ and clewsy workflows | Parameter generation, crop aggregation and model structure | `config/upstream_versions.json`, `patches/`, `overrides/` |

Rice is `RCP`; coconuts `CON`; maize `MZE`; vegetables use the tomato proxy
`TOM`; sugar cane is `SGC`; and `OTH` aggregates the remaining selected crops.
These mappings and the population-only growth rule are modelling assumptions,
not observations.

### Recovered exact source chain

The 5 August 2026 recovery closes the earlier broad GAEZ, FAOSTAT and SSP2
traceability gaps:

- The six exact pinned GAEZ input-selection tables and a 90-row manifest now
  record every crop raster's cache filename, URL, file identifier and physical
  source-table line. The selection consists of 48 high-input and 42 low-input
  rasters. Para rubber has no low-input source-table row.
- The two non-crop cache files, `precipitation prc.tif` and `LCType_ncb.tif`,
  are retained byte-for-byte with pinned repository URLs and SHA-256 values.
- `FAOSTAT_2020.csv` and `FAOSTAT_production_2020.csv` are retained with their
  exact checksums. A derived ten-row table records the selected CPC codes,
  harvested-area and production values, flags, proxies, model groups and
  physical source lines.
- The exact SSP Public Database Version 2.0 workbook is retained. The selected
  population row is `data!A1373:Y1373`: `IIASA-WiC POP`, `SSP2`, `PHL`,
  `Population`, `million`. The exact annual 2020–2053 index is retained too.
- Material build events, including cache quarantine, forced reruns, the final
  Snakemake command and workflow identifier, are indexed from Codex task
  `019f9991-7a2d-72a0-8fa1-6820178dd177`.

See `calculation_notes/SOURCE_PROVENANCE_RECOVERY_2026-08-05.md` for the full
forensic record. The original bytes and checksums of the 90 temporary crop
rasters remain unavailable; their exact reproducible URLs are now retained.

## Fisheries v2.3

| Source ID | Provider and publication | Model use | Status |
|---|---|---|---|
| `FSH-DOE-2023` | Philippine DOE, *2023 Philippine Energy Situationer and Key Energy Statistics*, p. 14 | 240.0-ktoe Fishery control total | Active input; conflicts with later DOE revision |
| `FSH-DOE-2024` | Philippine DOE, *2024 Philippine Energy Situationer and Key Energy Statistics*, p. 34, 2023 Energy Balance Table | Gasoline, diesel and fuel-oil carrier detail | Active input plus documented inference |
| `FSH-DOE-2024-REVISION` | Same 2024 DOE Situationer, p. 14 | Revised 2023 value of 170.8 ktoe and 2024 value of 193.3 ktoe | Diagnostic only; not substituted |
| `FSH-BFAR-PROFILE-2020` | BFAR, *Philippine Fisheries Profile 2020* | Vessel-count plausibility check and sector context | No count copied as an energy or capacity input |
| `FSH-PSA-2020` | PSA, *Fisheries Situation Report, January–December 2020* | Sector context | No parameter copied directly |
| `FSH-BFAR-FOI-HP` | BFAR/FOI request for fishing-vessel engine horsepower, 1995–2020 | Candidate future replacement for effective stock | Attachment not obtained; no values used |
| `FSH-GLOBAL-COMPARATORS` | CLEWs Global/MUIO comparator model packages | Meaning and presence of model parameters | Structural comparison only |

Full publication locators, transformations, quality notes, review needs and
the forensic reconstruction of legacy source codes are in
`../documentation/history/fisheries/DATA_SOURCE_REGISTER_v2.3_2026-07-25.md`.
The exact current Fisheries values are in `evidence/fisheries/`; their
calculation explanation is in `calculation_notes/fisheries/`.

## Environmental-accounting evidence

The accounting layer introduces no external environmental coefficient. Its
sources are the source model definition, the exact unit parallel-stock
identity and the outputs generated by the source and derived cases.

| Source ID | Source | Model use | Status |
|---|---|---|---|
| `DS-V12-ACTIVE-JSON` | Active `WebAPP/DataStorage/Philippines_v12` parameter JSON and MUIO v5.4 formulation | Commodity graph, units, Input Activity Ratio (IAR), Output Activity Ratio (OAR), scenario inheritance and UDC capability | Active model evidence; source hashes retained |
| `DS-V12-SOLVED-RESULTS` | Normal Base and PEP MUIO result CSVs and explicit solver status | Water production/use residuals, land activity, native emissions and objective | Both saved runs optimal; fresh unchanged controls also optimal |
| `DS-V12-ENV-LAND-JSON` | Generated `WebAPP/DataStorage/Philippines_v12_ENV_LAND` JSON and results | Seven parallel stocks, eight-mode `ENV_LAND`, exact aggregate equality and Pivot output | 25/25 validation checks pass for Base and PEP |
| `DS-ENV-ACCOUNTING-METHOD` | `Model-tools/skills/add-environmental-accounting` | Accounting boundary, two-terminal exactness test, reporting-only fallback and validation rules | Applied without importing Namibia identifiers or coefficients |

The fresh-control `data.txt` hashes match the saved Base and PEP source
inputs. The derived case preserves demand, emissions, cost invariants,
objectives and land states within tolerance. Alternate cost-identical bases
change some route-level and water rows; those differences are quantified in
the environmental-accounting validation rather than hidden.

## Known source gaps

The authoritative machine-readable list is `GAPS.csv`. It distinguishes
recoverable missing records from information that was not retained.

- Original publications behind Fisheries legacy symbols `S4`, `S6`–`S10`,
  `S12`, and `S16`–`S17` were not recoverable. Their meanings are documented,
  but they are not fully traceable citations.
- A complete original bibliography and calculation register for the inherited
  v10 energy system was not found.
- The active Fisheries DOE total and the later DOE revision require an
  authoritative same-vintage reconciliation.
- Groundwater abstraction, wastewater returns, desalination feedwater/brine,
  ecological reserves and energy-infrastructure land occupation lack the
  physical links or coefficients needed for additional accounts.
