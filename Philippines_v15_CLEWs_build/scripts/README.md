# Philippines v15 MUIOGO scripts

These are the exact source scripts retained by the schema ledger:

- `create_philippines_v15_national_water.py` builds the water delta through
  the MUIOGO source-parameter and `UpdateCase` workflow.
- `validate_philippines_v15_national_water.py` performs deterministic checks,
  application generation, preprocessing, matrix inspection, CBC validation,
  baseline comparison and water-ledger publication.
- `validate_philippines_v15_schema_ledger.py` validates the canonical ledger
  against the live MUIOGO case.
- `provenance.py` performs the generic six-table schema and provenance-graph
  validation.
- `data/philippines_water_precipitation_ssp245.json` is the normalized,
  hash-pinned research input.

The first three scripts retain their original MUIOGO-relative paths. To rerun
them, place them at the documented locations in an EAPD-DRB/MUIOGO checkout
alongside the required baseline and case directories. They are retained here
for exact source traceability; the validation JSON under `../diagnostics/`
records the completed promoted run.
