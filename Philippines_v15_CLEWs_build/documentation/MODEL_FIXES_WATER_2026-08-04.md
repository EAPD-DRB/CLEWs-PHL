# Philippines v15 national water model fix

Date: 2026-08-04  
Live case: `WebAPP/DataStorage/Philippines_v15`  
Run: `BASE_V15`  
Status: **fully validated and promoted**

## Version identity

The implemented water model is version 15:
`Philippines_v15/BASE_V15`. The unchanged pre-water model is
retained as `Philippines_v14_STOCK_TURNOVER/BASE_V14` and remains the formal
baseline. Renaming the implemented case changed only case/run identity; it did
not change an equation, source parameter, set member, active scenario or
solver value.

## Reason and physical classification

The inherited country model converted precipitation into surface water,
groundwater recharge and evapotranspiration, but `DEMAGRGWTPHL` did not consume
raw groundwater. Precipitation was stationary after 2020 and the optimizer had
no national ceiling on gross surface-water or groundwater withdrawal.

- Initial stock: none. The 20.2 km3/year groundwater value is potential
  renewable flow, not aquifer storage or safe yield.
- Final demand: unchanged. Public water, cooling water and crop demands retain
  their inherited paths.
- Continuing constraints: the ERA5 1991-2020 national precipitation normal,
  one SSP2-4.5 ensemble-median relative precipitation path, and national
  potential-flow sensitivity ceilings.
- Benchmark only: p10/p90 projections, current-withdrawal estimates and local or
  regional groundwater studies. They are not installed as model scenarios.

`MINPRCPHL` is a physical source; `LNDAGRPHLC01...C08` are physical
land/hydrology conversions; the six water-demand technologies are physical
pass-throughs; the two new UDCs are annual physical/accounting constraints.

## Source changes

The reproducible generator is
`scripts/create_philippines_v15_national_water.py`; research inputs are in
`scripts/data/philippines_water_precipitation_ssp245.json`.

- `genData.json`: raw `PHL_WTR_GWT` was added to the `DEMAGRGWTPHL` IAR list.
  Tag-0 UDCs `WATER_SUR_AVAIL` and `WATER_GWT_POTENTIAL` were added, each with
  exactly three withdrawal technologies.
- `RYTCM.json`: the new irrigation-groundwater IAR is 1.0 in mode 1. Exactly 960
  BASE rows (8 coefficient classes x 30 modes x precipitation, surface runoff,
  groundwater recharge and evapotranspiration) use the ERA5 rebase and the
  SSP2-4.5 median path. `AGRWATPHL` irrigation-requirement coefficients are
  unchanged.
- `RYTCn.json`: CAM = 1.0 on the three surface and three groundwater withdrawal
  technologies; all other new CAM/CNCM/CCM values retain their defaults.
- `RYCn.json`: UCC contains the two annual ceilings. Policy-scenario rows are
  null and inherit BASE.

No other source parameter JSON changed semantically. Structural regeneration
used `UpdateCase`; no generated solver file was edited or promoted.

## Before and after

- Model precipitation before: 724.96536 km3/year over 295.8131 thousand km2,
  or 2450.754750212 mm/year.
- ERA5 1991-2020 anchor: 2658.12 mm/year.
- Full-precision rebase: 1.0846128115307467.
- SSP2-4.5 median multiplier: 1.0 (2020), 1.010122658529793 (2030),
  1.043093949410924 (2050), 1.048039643043094 (2053).
- Surface UCC: 125.79 km3/year in 2020 and 131.832906698391 in 2053.
- Groundwater UCC: 20.2 km3/year in 2020 and 21.170400789471 in 2053.

The exactness proof passes because every UDC member has only active mode 1,
raw-water IAR = 1.0 and CAM = 1.0. Therefore its annual UDC activity sum is
exactly gross withdrawal. The ordinary `EBb4_EnergyBalanceEachYear4` rows also
enforce withdrawal no greater than modeled raw-water production.

## Validation

Validator: `scripts/validate_philippines_v15_national_water.py`.

The disposable candidate and the regenerated live case both passed the normal
application chain:

1. deterministic all-year source and balance checks;
2. `DataFile.generateDatafile` and `preprocessData`;
3. `glpsol --check` with LP export;
4. a 30-second bounded CBC no-infeasibility diagnostic;
5. CBC optimization inside the declared 280-second budget;
6. CSV and result-view generation;
7. baseline, residual, dual, timestamp and source-identity comparisons.

The live result is optimal:

- objective: 369630979.62464261;
- unchanged pre-water objective: 369630979.50300199;
- delta: 0.121640622616 (3.29087e-8 percent);
- analytically expected precipitation-source cost delta: 0.121640839152;
- unexplained objective residual: -2.17e-7;
- CBC: 219.681299 seconds;
- matrix: 791109 rows, 884956 columns, 12533783 nonzeros;
- matrix change: +68 rows, 0 columns and +3264 nonzeros;
- maximum exact UDC activity residual: 3.90e-6 km3/year;
- minimum raw-water balance surplus: -3.85e-13 km3/year (numerical zero);
- final-demand changed rows: 0;
- emission changed rows: 0.

The full pre-water case and result are retained at
`WebAPP/DataStorage/Philippines_v14_STOCK_TURNOVER`.
The live audit and authoritative post-solve water publication are:

- `WebAPP/DataStorage/Philippines_v15/documentation/national_water_manifest.json`;
- `WebAPP/DataStorage/Philippines_v15/documentation/national_water_validation.json`;
- `WebAPP/DataStorage/Philippines_v15/documentation/national_water_ledger.json`.

Neither UDC binds in BASE; all UDC duals are zero. Adding the two rows changes
the cost-identical LP basis: the live run uses some groundwater for public or
power water in selected years and changes other zero-cost activity/capacity
rows, while demand, emissions and the economic objective remain invariant apart
from precipitation-source cost. These changes are disclosed in the validation
JSON rather than treated as calibrated source shares.

The inherited unforced `ENV_WATER` diagnostic also takes arbitrary zero-cost
activity (maximum 26.283414 km3/year in the live basis). The authoritative
ledger reconstructs production with its mode-specific values, but does not use
`ENV_WATER` as an account terminal or a constraint.

## Known limitations

- The ceilings are national potential-flow sensitivities, not dependable
  yield, environmental-flow-adjusted availability or groundwater safe yield.
- There is no aquifer stock, head, drawdown, salinity, basin, transfer or
  groundwater-storage state.
- Public and power groundwater pumping electricity remains uncalibrated.
- Irrigation diversions and public-water demand remain uncalibrated, so BASE
  source/sector shares must not be presented as observed Philippine shares.
- The SSP2-4.5 precipitation-to-runoff/recharge response is proportional and
  uses the ensemble median only. p10/p90 remain research metadata for user-made
  scenarios if desired.

## Schema-ledger source trace

Added 2026-08-04 as a documentation-only change. No case source parameter,
generated solver artifact or result file was changed.

The canonical package under `docs/philippines_v15/data_sources/` contains 21
source records, 13 calculations, 12 assumptions, 14 live model mappings, 9
evidence gaps and 5 change records. It traces the v14 source-case lineage;
World Bank CCKP ERA5 and SSP2-4.5 evidence; IPCC scenario framing; Philippine
national surface-water and groundwater benchmarks; groundwater screening and
study leads; the local MUIO equations; full-precision generation evidence; and
the authoritative post-solve water publication. Six retained artifacts are
SHA-256 pinned.

`schema_ledger_build.json` passed the generic provenance validation with zero
failures and five warnings for intentionally blank commit fields in the
uncommitted working tree. `schema_ledger_live.json` passed 12 semantic checks
with zero failures, including live `Philippines_v15/BASE_V15` identity,
all-year formulas, source fingerprints, median-only installation, unchanged
irrigation coefficients, policy inheritance and exact withdrawal accounting.
