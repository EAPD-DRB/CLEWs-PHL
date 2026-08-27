# Philippines v15 national water model fixes

Date: 2026-08-04  
Case: `Philippines_v15`  
Status: **fully validated**

## Version identity

The water-enabled model was renamed from
`Philippines_v14_STOCK_TURNOVER/BASE_V14` to
`Philippines_v15/BASE_V15` on 2026-08-04. The unchanged
pre-water case was restored at `Philippines_v14_STOCK_TURNOVER/BASE_V14` as
the comparison baseline. This was an identity-only rename: no model equation,
parameter value, set member, scenario activation or solver result changed.

## Reason

The country model had precipitation-to-runoff/recharge conversions but no
groundwater input on `DEMAGRGWTPHL`, no climate evolution after 2020, and no
national solver ceiling on gross surface-water or groundwater withdrawal.

## Physical classification and equation mapping

- Initial stock: none. The 20.2 km3/year groundwater value is a renewable-flow
  potential, not an aquifer stock.
- Final demand: unchanged. `PHL_PUB_WAT`, `PHL_PWR_WAT` and crop demands remain
  the inherited final demands.
- Continuing real-world constraints: the ERA5 1991-2020 precipitation normal,
  the SSP2-4.5 ensemble-median relative precipitation signal, and the two
  national potential-flow sensitivities.
- Benchmark only: p10/p90 climate values, current withdrawal estimates, local
  groundwater studies, and regional screening data.

`RYTCM.json` feeds `EBb4_EnergyBalanceEachYear4`; `RYTCn.json` CAM and
`RYCn.json` UCC feed `UDC1_UserDefinedConstraintInequality`. Every withdrawal
member is a single-mode pass-through with raw-water IAR = CAM = 1, so each UDC
is an exact gross-withdrawal ceiling.

## Source changes

- `genData.json`: add raw groundwater to the `DEMAGRGWTPHL` IAR list and add
  Tag-0 constraints `WATER_SUR_AVAIL` and `WATER_GWT_POTENTIAL`.
- `RYTCM.json`: set the new irrigation-groundwater IAR to 1.0 in mode 1; scale
  960 BASE hydrology rows (8 coefficient classes x 30 modes x precipitation,
  runoff, recharge and evapotranspiration) by the ERA5 rebase and the single
  SSP2-4.5 median path. `AGRWATPHL` coefficients are unchanged.
- `RYTCn.json`: CAM = 1.0 for exactly three surface and three groundwater
  withdrawal technologies.
- `RYCn.json`: annual UCC paths for the two national ceilings. Policy-scenario
  rows remain null and inherit BASE.

## Before and after

- Model precipitation depth before: 2450.75475021 mm/year.
- ERA5 1991-2020 anchor: 2658.12 mm/year.
- Full-precision rebase factor: 1.08461281153075.
- SSP2-4.5 median multiplier: 2020 = 1,
  2030 = 1.01012265853, 2050 = 1.04309394941,
  2053 = 1.04803964304.
- Surface UCC: 2020 = 125.79,
  2053 = 131.832906698 km3/year.
- Groundwater UCC: 2020 = 20.2,
  2053 = 21.1704007895 km3/year.

## Generated artifacts and baseline

The structural source was regenerated through `UpdateCase`. The intended
application chain is `DataFile.generateDatafile` -> `preprocessData` ->
`glpsol --check`/LP export -> bounded CBC -> CSV/view export. The unchanged
control is the validated `Philippines_v14_STOCK_TURNOVER/BASE_V14` result:
optimal objective 369630979.503002, 791041 rows, 884956 columns, 12530519
nonzeros, CBC 133.1208 seconds. The candidate budget is 280 seconds.

## Validation status and limitations

Generation, structural preservation, exact-withdrawal proof, all-year source
values, policy inheritance, hydrological-ratio preservation, application
generation, preprocessing, matrix validation, CBC optimization, result export,
constraint residuals/duals, and baseline comparison: **passed**.

The ceilings are national potential-flow sensitivities, not dependable yield,
environmental-flow-adjusted availability, or groundwater safe yield. Public
and power groundwater pumping electricity remains uncalibrated; irrigation
and public-water demand are also unchanged. No basin, aquifer or storage state
is implied.

## Solver validation completed 2026-08-04T21:51:46.259209+00:00

Status: **fully validated**

- Application generation: passed_prior_full_validation_artifact_rechecked.
- Preprocessing: passed_prior_full_validation_artifact_rechecked.
- `glpsol --check` and LP export: passed_original_export_and_independent_lp_recheck.
- Short bounded CBC diagnostic: passed_prior_full_validation.
- CBC optimization within 280 seconds: passed_optimal_prior_full_validation.
- CSV and result-view export: passed.
- Baseline comparison: passed.
- Candidate matrix: 791109 rows, 884956 columns,
  12533783 nonzeros.
- CBC solve time: 219.681299 seconds.
- Objective: 369630979.624642610550; change from the unchanged BASE v14
  control: 0.121640622616
  (3.29086654964e-08 percent).
- Unchanged control: `Philippines_v14_STOCK_TURNOVER/BASE_V14`, objective
  369630979.503001987934.
- Maximum exact UDC activity residual:
  3.90000001005e-06 km3/year.
- Minimum raw-water commodity balance surplus:
  -3.8517124e-13 km3/year.
- Maximum activity of the unforced `ENV_WATER` diagnostic:
  26.283414 km3/year.

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

`docs/philippines_v15/validation/schema_ledger_build.json` passed the generic
provenance validation with zero failures and five warnings for intentionally
blank commit fields in the uncommitted working tree.
`docs/philippines_v15/validation/schema_ledger_live.json` passed 12 semantic
checks with zero failures, including live `Philippines_v15/BASE_V15` identity,
all-year formulas, source fingerprints, median-only installation, unchanged
irrigation coefficients, policy inheritance and exact withdrawal accounting.

The full audit trail is in `national_water_validation.json` and the authoritative annual water
publication is `national_water_ledger.json`. All generated artifacts were created from the case
source through the normal application chain; no generated solver file was
promoted as a source edit.
