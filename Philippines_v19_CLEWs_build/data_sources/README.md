# Canonical Philippines v19 ledger

The six CSV files in this directory are authoritative, cumulative, and
self-contained. They carry inherited-base, v13, v14, v15, v16, v17, and v18
provenance into v19 and add the PM2.5 coverage records.

- Start with `DATA_SOURCES.md`.
- Trace parameters through `MODEL_MAP.csv` and its `evidence_ids`.
- Review the v19 factor register under `evidence/pm25_v19/`.
- Read `calculation_notes/pm25_coverage_v19_2026-08-19.md` for equations and
  boundaries.
- Read the two `pm25_coverage_v19` snapshots for the exact change and
  validation records.
- Run `../scripts/validate_provenance.py . --stage build` and
  `../scripts/validate_philippines_v19_delivery.py` for final checks.

`PHILIPPINES_V19_CANONICAL_SCHEMA_LEDGER.xlsx` is a formatted review copy. The
historical water-only ledger remains retained under
`history/water_delta_2026-08-04/` and is not authoritative.
