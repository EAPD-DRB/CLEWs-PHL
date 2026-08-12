# Philippines v15 cumulative ledger reconstruction — 5 August 2026

## Purpose

The original Philippines v15 source ledger documented the national-water
addition and treated the earlier stock-turnover case as a blanket inherited
source. That was sufficient for a change review but not for a durable release:
the cited earlier-model folder and separate documentation folder were not part
of the published package.

This documentation-only reconstruction makes the v15 package cumulative and
self-contained. It does not alter the model archive, source JSON, scenarios,
solver inputs, or results.

## Evidence retained inside v15

The package now retains:

- the inherited-base six-table ledger, including its 68,624 row-level model
  mappings;
- the exact GAEZ selection tables and 90-file raster-cache manifest;
- the retained GAEZ base rasters, FAOSTAT input files and selected rows;
- the SSP2 workbook, exact `data!A1373:Y1373` row, and annual population index;
- inherited build configuration, input CSVs, geospatial summaries, patches and
  overrides;
- Fisheries and environmental-accounting evidence and calculation notes;
- the v13 calibration generation, change and validation records;
- the v14 source register, calculations, assumptions, 33-row model map,
  3,253-cell before/after parameter log, generation manifest and validation
  records; and
- the complete v15 water ledger, normalized climate input, manifests,
  validation records, model formulation and portable current-model archive.

`evidence/RETAINED_EVIDENCE_MANIFEST.csv` records the path, size, role and
SHA-256 of every retained evidence file. The current model archive is indexed
separately by `evidence/CURRENT_MODEL_ARCHIVE_MANIFEST.csv`.

## Cumulative mapping rule

The canonical `MODEL_MAP.csv` contains the inherited-base row-level mappings,
explicit v13 environmental-calibration mappings, the v14 summary mappings and
all 3,253 v14 cell changes, and the v15 water mappings. Later rows are the
documented overlays for parameters changed after the inherited build. Values
not covered by a later overlay retain their inherited mapping.

Historical version labels remain in identifiers and narrative because they
describe chronology. They are not path dependencies. All `local_file` evidence
resolves under the v15 `data_sources/` directory. The inherited raw-build maps
point to the identical active copies in `config/` and `model/inputs/`; the
evolved v13-v15 model maps point to the v15 portable archive.

## Limits not concealed

The reconstruction does not invent evidence that was never retained. In
particular, the original bibliography for parts of the inherited energy model,
the original v13 calibration workbook bytes, the original v13 source case and
CBC result bytes, and some downloaded official-publication bytes remain listed
in `GAPS.csv`. Their surviving hashes, exact selected values, formulas,
citations, change records and final model values have been preserved.

The former water-only ledger remains unchanged under
`history/water_delta_2026-08-04/` for audit comparison.
