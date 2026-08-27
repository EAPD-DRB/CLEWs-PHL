# Philippines v16 water-demand calibration — 2026-08-07

## Outcome

Three accounting omissions were corrected without forcing irrigated area or water-source shares.

1. The `AGRWATPHL` input ratios on `LNDAGRPHLC01`-`LNDAGRPHLC08` now represent gross diversion: each inherited base-scenario coefficient is divided by 0.38. This changes water used per unit of endogenous irrigated-land activity, not the selected land area.
2. `PHL_PUB_WAT` accumulated annual demand is PSA Scenario 2 population multiplied by 70 litres/person/day and 365 days. The two existing public-water routes have an output ratio of 0.75, so their production includes 25 percent NRW while final demand remains delivered water.
3. The existing public and power groundwater routes consume 0.70 PJ of their sector electricity commodity per km3 pumped. The coefficient is `round(0.00981 * 50 m / 0.70, 2)`.

No technology, commodity, user-defined constraint, demand for irrigated area, technology activity bound, or prescribed source share was added. Approximately 1.7 Mha is a benchmark only. If endogenous irrigation does not approach it, the next diagnosis belongs in yields, costs, land/productivity coefficients, food balance, or water accounting—not in an imposed area target.

## Classification and equations

- Initial stocks: unchanged.
- Final demand: `PHL_PUB_WAT` only.
- Continuing physical coefficients: irrigation efficiency, NRW, groundwater head, and pump efficiency.
- Benchmark only: approximately 1.7 Mha irrigated area.
- `LNDAGRPHLCxx` technologies: physical land-to-crop conversions.
- Public and power surface/groundwater technologies: pass-throughs.

In the commodity balance, crop-land activity now consumes gross rather than net `AGRWATPHL`. Public-route activity must be `PHL_PUB_WAT demand / 0.75`. Groundwater-route activity also consumes electricity, so choosing groundwater is no longer energetically free.

## Source changes

- `genData.json`: added `PHL_SER_ELE` to the public-groundwater IAR membership and `PHL_POW_ELE` to the power-groundwater IAR membership.
- `RYTCM.json`: transformed 240 base irrigation-water rows (95 have positive values), set both public-water mode-1 OARs to 0.75, and populated the two new mode-1 electricity IARs at 0.70; policy rows inherit from `SC_0`.
- `RYC.json`: replaced the base `PHL_PUB_WAT` demand trajectory. Values are 2.790129496 km3 in 2020, 3.0372253345 in 2030, 3.4824356175 in 2050, and 3.5188275045 in 2053.

The structural edit passed through `UpdateCase`; permanent edits were not made to generated solver files. Promoted SHA-256 values are:

- `genData.json`: `a1f1c683f564605e8285f150ee3c0244cf0a53ca7ef9f62fb6703e9bd1920e2b`
- `RYTCM.json`: `83923df0f47169aa8a0e4044acb6c2bf58732a636211d814df31cbd7ea62b788`
- `RYC.json`: `67fb414c38f349b8f82adaf3df0f6b5366178481bb3801682b3365971f39c0f4`

## Reproducibility check

The exact promoted candidate was generated and preprocessed through `DataFile`, passed GLPK matrix construction, and solved to CBC optimality as `BASE_V15`.

- Candidate objective: 369630979.58388072
- Stored v16 baseline objective: 369630979.6246426
- Difference: -0.04076188, approximately -1.10e-8 percent
- CBC wall-clock solve: 178.28 seconds
- Complete generation/solve/export chain: 226.13 seconds
- Stored baseline complete runtime: approximately 219.68 seconds

No policy or sensitivity runs were performed. Generated `data.txt`, `data_processed.txt`, `lp.lp`, and solver results remained in the disposable case and were not promoted. The only warnings were existing pandas future warnings during result export.

## Schema-ledger trace

The six canonical tables under `Philippines_v16_CLEWs_build/data_sources/` record the two external sources, seven assumptions, four calculations, five source-to-model mappings, four open data gaps, and the model change. The package provenance validator passes with zero failures; its warnings are blank commit identifiers for uncommitted or inherited changes and unused retained v14 sources.
