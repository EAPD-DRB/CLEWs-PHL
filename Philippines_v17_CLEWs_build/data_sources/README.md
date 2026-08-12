# Canonical Philippines v17 ledger

The six CSV files in this directory are authoritative. They are cumulative and
self-contained: inherited-base, v13, v14, v15, v16, and v17 provenance is carried in this
package rather than delegated to an earlier version.

- Start with `DATA_SOURCES.md` for the human-readable guide.
- Use `MODEL_MAP.csv` for parameter-to-evidence tracing.
- Use `evidence/RETAINED_EVIDENCE_MANIFEST.csv` to verify retained files.
- Use `calculation_notes/crop_yields_v16_2026-08-11.md` for the current crop
  OAR definitions, exact calculations, solve comparison, and limitations.
- Use `calculation_notes/irrigation_water_engineering_v16_2026-08-11.md` for
  the irrigated-rice engineering-water calculation, source map, validation,
  and limitations.
- Use `calculation_notes/energy_inputs_v16_2026-08-11.md` for the renewable
  naming correction, offshore and onshore wind calculations, geothermal
  availability, equation map, candidate solve and promoted live validation.
- Use `calculation_notes/land_cover_v17_2026-08-12.md` for the national
  PSA/NAMRIA class mapping, reconciliation, land equality, and idle/fallow
  calculation.
- Run `../scripts/provenance.py` and
  `../scripts/validate_philippines_v17_delivery.py` to validate the schema,
  evidence hashes, input coverage, archive, and current source identity.

The historical water-only ledger is preserved under
`history/water_delta_2026-08-04/` and is not authoritative.

The formatted current review copy is
`PHILIPPINES_V17_CANONICAL_SCHEMA_LEDGER.xlsx`; the six CSV files remain the
source of truth.
