# Canonical Philippines v20 ledger

The six CSV files in this directory are authoritative, cumulative, and
self-contained. They carry every inherited record through v19 and append the
v20 power-history sources, calculations, assumptions, exact model maps, gaps,
and change lineage.

- Start with `DATA_SOURCES.md`.
- Trace parameters through `MODEL_MAP.csv` and `evidence_ids`.
- Review the v20 DOE extracts and validation JSON under `snapshots/`.
- Read `../documentation/MODEL_FIXES_POWER_HISTORY_V20_2026-08-20.md` for the
  equation-first design, rejected diagnostic, solve ledger, and limitations.
- Regenerate the review workbook with
  `../scripts/build_philippines_v20_ledger_workbook.py`.

`PHILIPPINES_V20_CANONICAL_SCHEMA_LEDGER.xlsx` is a formatted review copy; the
CSV tables remain authoritative. Earlier workbooks and the dated water ledger
are retained as history and are not dependencies of the current ledger.
