# Philippines v15 CLEWs model

Philippines v15 is the validated whole-country MUIO/MUIOGO case that adds a
national precipitation and renewable-water envelope to the Philippines v14
stock-turnover model. The unchanged v14 case is the formal solve baseline; the
v12 build package remains in this repository as inherited lineage and
reproduction evidence.

## Delivered model

- Portable editable case: `muio/Philippines_v15_v15.0.0_MUIO.zip`
- Archive checksum: `muio/SHA256SUMS`
- Case identity: `Philippines_v15`
- Validated run identity: `BASE_V15`
- Horizon: 2020-2053

Extract the `Philippines_v15` folder into
`MUIOGO/WebAPP/DataStorage/`. Generated solver inputs and the 1.3 GB runtime
result directory are intentionally excluded; regenerate them through the
normal MUIOGO application chain.

## Water formulation

- The inherited national hydrology coefficients are rebased to the World Bank
  CCKP ERA5 1991-2020 precipitation normal.
- A single CMIP6 SSP2-4.5 ensemble-median precipitation pathway is installed.
  Retained p10/p90 values are evidence only, so users choose which additional
  scenarios to construct.
- `DEMAGRGWTPHL` consumes raw groundwater one-for-one in its active mode.
- `WATER_SUR_AVAIL` and `WATER_GWT_POTENTIAL` constrain annual gross
  withdrawals from the three corresponding single-mode pass-throughs.
- The ordinary annual commodity balances independently prevent withdrawal
  above modeled raw-water production.

These are national potential-flow sensitivity ceilings. They are not basin
allocations, dependable yield, environmental-flow-adjusted availability,
aquifer storage, or groundwater safe yield. Neither ceiling binds in
`BASE_V15`.

## Source trace

The six canonical CSV ledgers are under `data_sources/`:

- `SOURCES.csv`: 21 source and retained-evidence records;
- `CALCULATIONS.csv`: 13 full-precision calculations;
- `ASSUMPTIONS.csv`: 12 explicit modeling assumptions;
- `MODEL_MAP.csv`: 14 mappings to live source files and parameters;
- `GAPS.csv`: 9 unresolved evidence needs; and
- `CHANGES.csv`: 5 implementation and documentation records.

`data_sources/PHILIPPINES_V15_WATER_SCHEMA_LEDGER.xlsx` is a formatted review
copy; the CSV files are authoritative. The complete annual pathway and
equation map are in
`data_sources/calculation_notes/national_water_v15.md`.

## Validation

The promoted case completed application generation, preprocessing,
`glpsol --check`, LP inspection, a bounded CBC diagnostic, full CBC
optimization, result export, and comparison with the unchanged v14 baseline.

- status: optimal;
- objective: 369630979.62464261;
- CBC solve time: 219.681299 seconds;
- matrix: 791109 rows, 884956 columns, 12533783 nonzeros;
- maximum exact UDC residual: 0.00000390000001 km3/year;
- final-demand changed rows: 0; and
- emission changed rows: 0.

The generic provenance validation passed with zero failures and six retained
digests verified. The live semantic ledger validation passed all 12 checks.
See `diagnostics/` and `documentation/MODEL_FIXES_WATER_2026-08-04.md`.

## Reproduction scripts

The exact MUIOGO generator and validator used for v15 are retained under
`scripts/`, with the normalized research input under `scripts/data/`. See
`scripts/README.md` for their expected location in an MUIOGO checkout.
