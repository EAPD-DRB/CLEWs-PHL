# Philippines v15 schema-ledger routing

The six canonical tables document the implemented national-water delta and its immediate v14 lineage.

- `SOURCES.csv`: authoritative external evidence, immediate case lineage and retained validation evidence.
- `CALCULATIONS.csv`: formulas, full-precision inputs, outputs and script hashes.
- `ASSUMPTIONS.csv`: boundary, scenario and interpretation choices separated from observations.
- `MODEL_MAP.csv`: live JSON file, parameter, entity, mode, scenario, years, units and evidence IDs.
- `GAPS.csv`: missing evidence required for dependable-yield, seasonal or aquifer-stock modeling.
- `CHANGES.csv`: water implementation, identity and documentation history.

The machine-readable CSVs are canonical. `PHILIPPINES_V15_WATER_SCHEMA_LEDGER.xlsx` is a formatted review copy of the same rows. Retained evidence snapshots are under `snapshots/`, and `calculation_notes/national_water_v15.md` prints the complete annual pathway and source-to-equation map.

Scope: this ledger fully traces the v15 water changes. Unchanged non-water parameters inherit their immediate lineage from `SRC_PHL_V14_CASE` and retain the detailed legacy tables in `docs/philippines_v14_stock_turnover/`.
