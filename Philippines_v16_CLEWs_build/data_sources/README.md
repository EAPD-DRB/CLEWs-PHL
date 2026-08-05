# Canonical Philippines v15 ledger

The six CSV files in this directory are authoritative. They are cumulative and
self-contained: inherited-base, v13, v14 and v15 provenance is carried in this
package rather than delegated to an earlier version.

- Start with `DATA_SOURCES.md` for the human-readable guide.
- Use `MODEL_MAP.csv` for parameter-to-evidence tracing.
- Use `evidence/RETAINED_EVIDENCE_MANIFEST.csv` to verify retained files.
- Run `../scripts/validate_philippines_v15_schema_ledger.py` to validate the
  schema, evidence hashes, lineage coverage and current model archive without
  an earlier live case.

The historical water-only ledger is preserved under
`history/water_delta_2026-08-04/` and is not authoritative.
