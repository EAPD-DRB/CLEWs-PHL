# Philippines v20 canonical source ledger

This directory is the authoritative cumulative provenance package for
Philippines v20. It carries forward the complete inherited-base through v19
sources, assumptions, calculations, mappings, gaps, changes, and retained
evidence, then adds the v20 power-history records. No earlier package or installed case
is required to interpret the ledger.

## How to trace a value

1. Find the parameter, technology, year, or archive in `MODEL_MAP.csv`.
2. Follow `evidence_ids` to `SOURCES.csv`, `CALCULATIONS.csv`, and
   `ASSUMPTIONS.csv`.
3. Open the cited `local_file` or use the recorded external publication
   locator.
4. Read `CHANGES.csv` for chronology and `GAPS.csv` before making a coverage
   or calibration claim.

The six CSVs are authoritative. The `.xlsx` file is a generated review copy.
`evidence/RETAINED_EVIDENCE_MANIFEST.csv` records inherited retained files;
the PM2.5 source PDFs have their own byte-level
`evidence/pm25_v19/SOURCE_MANIFEST.csv` and are also registered in
`SOURCES.csv`.

## V20 evidence chain

- `snapshots/doe_power_validation_2020_2024.csv` and
  `doe_power_capacity_2020_2024.csv` retain the official benchmark mappings and
  boundary notes.
- `snapshots/power_plant_clusters_2020.csv` retains the four DOE
  installed/dependable plant-class clusters used as physical drivers.
- `snapshots/power_calibration_v20_build_manifest.json` and
  `power_calibration_v20_static_validation.json` retain exact source hashes,
  changed cells, inheritance, no-forcing checks, and cost identity.
- `snapshots/power_calibration_v20_validation.json` retains all historical
  errors, bindings, duals, run lineage, and limitations.
- `snapshots/power_calibration_v20_promotion_identity.json` proves live source
  and generated solver-input identity without a second live solve.
- `V20_MODEL_ARCHIVE_MANIFEST.csv` and `muio/SHA256SUMS` identify the result-free
  v20 delivery.

## V19 evidence chain

V19 starts from the exact result-free v18.0.1 archive at Git commit `2735feb`
(SHA-256 `c3f4ee25d2e8c3315ced1be4bf819673859be45079536abb2cfbc40a65d1dc55`).
The later 2020-2025 deployment-cap experiment is excluded.

- `evidence/pm25_v19/FACTOR_SELECTION.csv` records all selected factors,
  source table/page locators, units, uncertainty bounds, applications, and
  boundaries.
- `calculation_notes/pm25_coverage_v19_2026-08-19.md` records equations, unit
  conversions, model boundaries, exclusions, and solve interpretation.
- `snapshots/pm25_coverage_v19_2026-08-19.json` records all 52 affected
  technologies and complete source-file hashes before and after the patch.
- `snapshots/pm25_coverage_v19_validation.json` records scope, evidence,
  generation, matrix, bounded solve, CO2e identity, and PM2.5 result checks.
- `V19_MODEL_ARCHIVE_MANIFEST.csv` and `muio/SHA256SUMS` identify the exact
  result-free delivery archive.

## Remaining limits

The added factors are EMEP/EEA Tier 1 fallbacks, not Philippine
technology-specific calibration. Alternative-powertrain exhaust, aviation,
rail, agriculture oil/gas heat without an input link, and PM sources without a
matching model activity remain explicitly unresolved in `GAPS.csv`. No
exogenous residual inventory is implied and absent factors are not evidence of
zero emissions.
