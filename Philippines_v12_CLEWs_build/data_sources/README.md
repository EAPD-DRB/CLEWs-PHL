# Data sources, assumptions and calculations

This folder is the main place to answer “where did this number come from?”
The six canonical, machine-readable ledgers are:

- `SOURCES.csv`: datasets, publications, retained model snapshots and exact
  locators.
- `ASSUMPTIONS.csv`: explicit modelling choices and their evidence.
- `CALCULATIONS.csv`: formulas, input/output units and executable locations.
- `MODEL_MAP.csv`: model files, parameters, exact CSV-line locators, values,
  units and evidence IDs.
- `GAPS.csv`: information that could not be recovered without inventing it,
  plus the evidence needed to close each gap.
- `CHANGES.csv`: provenance-ledger changes and their supporting records.

`DATA_SOURCES.md` is the human-readable guide. `calculation_notes/` contains
longer explanations, and `evidence/` contains retained input tables and
calculation evidence. The superseded three-ledger files are preserved in
`../documentation/history/provenance_legacy_2026-07-30/`.

Validate the ledgers with standard Python:

```bash
python3 scripts/provenance.py data_sources \
  --stage build \
  --model-inputs model/inputs
```

The CSVs, Markdown records and validator do not depend on a Codex-specific
runtime and can be read or checked by Claude.

Environmental-accounting formulas are in
`calculation_notes/ENVIRONMENTAL_ACCOUNTING.md`. They use the source v12 JSON,
the generated `ENV_LAND` JSON and normally generated result CSVs as model
evidence; no external coefficient is introduced.

An empty source field is never meant to imply “common knowledge.” Missing
original evidence is recorded in `GAPS.csv`.
