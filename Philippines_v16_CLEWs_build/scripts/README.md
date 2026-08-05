# Philippines v16 MUIOGO scripts

The v15 model-construction scripts are retained unchanged as provenance. The
v16-specific canonical validator checks the identity-only successor package.

These are the exact source scripts retained by the schema ledger:

- `create_philippines_v15_national_water.py` builds the water delta through
  the MUIOGO source-parameter and `UpdateCase` workflow.
- `validate_philippines_v15_national_water.py` performs deterministic checks,
  application generation, preprocessing, matrix inspection, CBC validation,
  baseline comparison and water-ledger publication.
- `build_canonical_philippines_v15_ledger.py` reproducibly assembles the
  cumulative six-table ledger from evidence retained inside the v15 package.
- `build_philippines_v15_ledger_workbook.py` regenerates the non-authoritative
  review workbook from those six CSVs.
- `validate_philippines_v15_schema_ledger.py` validates the cumulative ledger,
  retained evidence and current model archive without an earlier live case.
- `validate_philippines_v15_canonical_ledger.py` is the implementation behind
  that compatibility entry point.
- `validate_philippines_v16_canonical_ledger.py` validates the current v16
  standalone ledger and result-free archive.
- `provenance.py` performs the generic six-table schema and provenance-graph
  validation.
- `validate_package.py` and `validate_provenance.py` apply the current generic
  Model-tools package, repository-pin and model-input coverage checks.
- `audit_no_forcing.py`, `estimate_resources.py`, `freeze_raw_baseline.py` and
  `validate_delivery.py` are the reusable Model-tools utilities. A raw-baseline
  freeze is not claimed for this evolved, partly calibrated v15 case.
- `data/philippines_water_precipitation_ssp245.json` is the normalized,
  hash-pinned research input.

The water generator and full before/after model validator retain their original
MUIOGO-relative paths and need the historical baseline to repeat that old A/B
exercise. The canonical ledger build and validation do not: all of their
inputs are inside this v15 package. The completed promoted-run evidence remains
under `../diagnostics/` and `../data_sources/snapshots/`.
