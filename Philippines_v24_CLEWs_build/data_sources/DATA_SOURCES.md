# Philippines v17 canonical source ledger

This directory is the authoritative, cumulative provenance package for the
Philippines v17 model. It contains the inherited-base source mappings, the v13
environmental calibration, the v14 stock-and-turnover changes, the v15
national-water addition, and the v16 demand, irrigated-rice,
achieved-crop-yield, and energy-input corrections, plus the v17 national
land-cover accounting repair. It does not require an installed earlier model or an
earlier version's ledger.

## How to trace a model value

1. Find the parameter, entity, year, or archive member in `MODEL_MAP.csv`.
2. Follow `evidence_ids` to `SOURCES.csv`, `CALCULATIONS.csv`, and
   `ASSUMPTIONS.csv`.
3. Open the cited `local_file` under this directory or use the precise external
   publication locator.
4. Consult `CHANGES.csv` for chronology and `GAPS.csv` before making a
   completeness claim.

The six authoritative CSVs contain:

- `SOURCES.csv`: 123 external sources and retained evidence records;
- `CALCULATIONS.csv`: 110 calculation records;
- `ASSUMPTIONS.csv`: 76 explicit modeling assumptions;
- `MODEL_MAP.csv`: 72,013 mappings;
- `GAPS.csv`: 39 known evidence limitations; and
- `CHANGES.csv`: 19 provenance and model-change records.

## What was carried forward

The detailed inherited-base map contributes 68,624 rows. Exact source evidence
retained inside v15 includes the GAEZ selection tables and raster manifest,
FAOSTAT files and selected records, the SSP2 workbook and selected row,
geospatial summaries, build inputs, Fisheries evidence, environmental accounts,
and dated v10 corrections.

Exact byte copies of the retained raw-build configuration and CSV inputs are
also exposed at `../config/config.yaml` and `../model/inputs/`, the standard
locations expected by the current Model-tools package validator. Their existing
68,612 input-map rows and eight configuration-map rows point to those active
copies; the country-specific validator proves that all 70 promoted files match
their retained evidence counterparts byte for byte.

The v13 layer records the coherent PM2.5 unit conversion, 18 installed
technology factors, cooking-oil CO2e correction, and annual blue-hydrogen
capture calculation. The v14 layer retains its source register, 35
calculations, 13 assumptions, 33 summary mappings, and all 3,253 exact
before/after parameter changes. The v15 layer retains the complete water
formulation, annual climate pathway, constraint values, manifests and
validation records. The v16 crop-yield layer replaces absolute GAEZ attainable
potential with unit-matched achieved national yields, resolves fresh-cane and
retained-vegetable-aggregate definitions, and preserves an explicit
non-forcing validation trail. The land/water boundary addendum records the
AQUASTAT 2006 comparable gross/net pair, the differently scoped 2020 variables,
and the whole-coconut-versus-copra distinction without changing model inputs.
The v17 layer retains the exact PSA/NAMRIA transcription and URLs, seven-class
reconciliation, annual land equality, idle/fallow formulation, solver record,
archive manifest, and explicit deferred forest-dynamics gaps.

## Self-contained evidence

`evidence/RETAINED_EVIDENCE_MANIFEST.csv` records every retained evidence
file's path, size, role and SHA-256. The current portable model is
`../muio/Philippines_v17_v17.0.0_MUIO.zip`; its hash, size, member count,
internal root, and result exclusion are in `V17_MODEL_ARCHIVE_MANIFEST.csv`.
The v16 and v15 archives remain retained chronology, not dependencies.

Historical version names remain in identifiers and narrative to preserve
chronology. They are not path dependencies. The former water-only ledger is
preserved unchanged under `history/water_delta_2026-08-04/`.

See `calculation_notes/CANONICAL_LEDGER_RECONSTRUCTION_2026-08-05.md` for the
reconstruction record and `calculation_notes/national_water_v15.md` for the
water equations and annual pathway. See
`calculation_notes/irrigation_water_engineering_v16_2026-08-11.md` for the
irrigated-rice engineering-water coefficients, sources, equations, scope guard,
solve comparison, and limitations. See
`calculation_notes/crop_yields_v16_2026-08-11.md` for the crop equations,
source observations, parameter map, before/after results, and open spatial
crop-water gaps. See
`calculation_notes/land_water_boundaries_v16_2026-08-11.md` for the AQUASTAT
and coconut product-boundary resolution.
See `calculation_notes/energy_inputs_v16_2026-08-11.md` for the renewable
naming correction, offshore and onshore wind calculations, geothermal
availability treatment, equation map and non-forcing validation.
See `calculation_notes/land_cover_v17_2026-08-12.md` for the national class
mapping, exact reconciliation, base-year equality, and idle/fallow calculation.

## Remaining limits

The ledger does not invent missing evidence. The most important remaining gap
is the original bibliography behind part of the inherited energy model. The
original v13 workbook and source-result bytes are also absent, although their
hashes, selected values, formulas, derived stocks and validation records
survive. These and all other limits are stated in `GAPS.csv`.
