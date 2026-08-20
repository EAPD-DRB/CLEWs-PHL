# Philippines v20 CLEWs model

Philippines v20 is the minimal endogenous power-history calibration successor
to the validated v19 model. It preserves the full cumulative v19 model and
provenance, adds no technology, commodity, region, or constraint, and changes
only three source files: `genData.json`, `RYT.json`, and `RYTM.json`.

V20 replaces AF=1 on four closed legacy power fleets with DOE 2020
dependable/nameplate ratios. It also represents the documented 2020–2021
Malampaya power-plant take-or-pay economics as a sunk fixed payment plus a
matching plant-specific contract credit. Domestic extraction prices remain
unchanged for all other gas users. No observed generation, fuel share, or
realized post-2020 capacity addition is imposed.

The accepted disposable candidate solved optimally at objective
369737957.77807945 in 215.83 seconds end-to-end and 148.45 CBC seconds. The
2020 generation-mix WAPE falls from 49.46% to 13.60%; 2021 falls from 46.71%
to 16.59%. Later-year limitations are disclosed rather than fitted.

The six CSVs under `data_sources/` are the authoritative, cumulative schema
ledger. `PHILIPPINES_V20_CANONICAL_SCHEMA_LEDGER.xlsx` is a review copy. All
retained evidence and earlier records are included, so v20 does not refer to
v19 as a substitute for its own provenance.

## Delivered model

- Portable editable case: `muio/Philippines_v20_v20.0.0_MUIO.zip`
- Archive checksum: `muio/SHA256SUMS`
- Case identity: `Philippines_v20`
- Horizon: 2020–2053
- Runtime solver files and results: excluded
- Sensitivity runs: none

See `documentation/MODEL_FIXES_POWER_HISTORY_V20_2026-08-20.md` and
`data_sources/snapshots/power_calibration_v20_validation.json`.
