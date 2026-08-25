# Philippines v21 CLEWs model

Philippines v21 is the endogenous power-allocation repair successor to the
validated v20 model. It preserves the full cumulative v20 model and
provenance, remains a single-region whole-country model, and adds three
compact power representations plus one final electricity service commodity:

- off-grid oil generation, with the official 2020 stock and optional replacement;
- aggregate off-grid hydro/solar/wind, with the official 2020 stocks and
  optional replacement;
- the closed 250 MW FIT-eligible biomass tranche; and
- off-grid customer electricity sales, reallocated from existing national
  final demand.

It also restores the retained physical seasonal hydro profile. No observed
technology generation, generation share, activity equality, realized capacity
addition, deviation penalty, or sensitivity case is imposed.

The accepted candidate solved optimally in 155.89 seconds, compared with
148.45 seconds for the source-matched v20 result. Technology WAPE improves in
every benchmark year: 13.60% to 6.48% in 2020, 16.59% to 7.86% in 2021,
22.51% to 14.90% in 2022, 31.36% to 23.96% in 2023, and 39.43% to 33.46% in
2024. Total-generation errors are reported separately and are not what WAPE
measures.

Permanent changes are confined to the source files `genData.json`, `RT.json`,
`RYC.json`, `RYCTs.json`, `RYT.json`, `RYTCM.json`, `RYTEM.json`, `RYTM.json`,
and `RYTTs.json`. Generated `data.txt`, `data_processed.txt`, and `lp.lp` were
never edited.

The six CSVs under `data_sources/` are the authoritative, cumulative schema
ledger. `PHILIPPINES_V21_CANONICAL_SCHEMA_LEDGER.xlsx` is a review copy. All
retained evidence and earlier records are included, so v21 does not refer to
v20 as a substitute for its own provenance.

## Delivered model

- Portable editable case: `muio/Philippines_v21_v21.0.0_MUIO.zip`
- Archive checksum: `muio/SHA256SUMS`
- Case identity: `Philippines_v21`
- Horizon: 2020–2053
- Runtime solver files and results: excluded
- Sensitivity runs: none

See `documentation/MODEL_FIXES_POWER_ALLOCATION_V21_2026-08-20.md` and
`data_sources/snapshots/power_allocation_v21_provenance_validation.json`.
