# Philippines v33 gas dispatch and delivery-cost correction

## Outcome

Philippines v32 retained the three reported gas-dispatch defects: the legacy gas fleet had an inherited variable-cost plug, processed gas reached every consumer at the production node, and 2024 gross electricity generation remained materially below DOE. This v33 package corrects the first two economic defects with 15 `VariableCost` rows and leaves electricity demand for a separate evidence-led reconstruction.

The final BASE result is optimal. Gas power generation changes from `48.7106 / 21.4414 / 0.0022 / 0.5738 PJ` in v32 to `62.8636 / 55.4642 / 38.3862 / 1.6374 PJ` in 2021-2024. DOE's benchmark is `68.6160 / 64.3824 / 60.0048 / 64.9692 PJ`. Gas imports fall from `23.2937 PJ` in 2023 and `76.6500 PJ` in 2024 to zero. Non-power processed-gas use falls by 82.1% in 2023 and 79.6% in 2024 without being bounded.

The 2024 gas result remains outside what this annual least-cost formulation can calibrate reliably. Candidate gross generation is `395.7969 PJ`, still `61.1911 PJ` or 13.39% below DOE's `456.988 PJ`. DOE generation is validation-only; no demand coefficient was reverse-fitted to it.

## Equation-first classification

- DOE gas generation and gross generation: benchmark-only observations.
- Existing electricity-sector demands: inherited exogenous final demands, unchanged here.
- `PHL_POW_CHP_NG_OLD`: physical gas-to-electricity stock.
- `PHL_POW_PP_NGCC` and `PHL_POW_PP_NGCC_CCS`: physical gas-to-electricity conversions, unchanged.
- The other 14 `PHL_PRO_NG` consumers: physical conversions or pass-throughs whose mapped output is not electricity.
- The 2020-2021 take-or-pay term: inherited economic contract representation, retained as requested.

`RYTM.json / VC / SC_0` exports to `VariableCost`, which enters `OC1_OperatingCostsVariable` and total discounted cost in `SOLVERs/model.v.5.4.txt`. It changes order of merit only. No activity equation, capacity envelope, service demand, efficiency, lifetime, stock, fuel share, `TAL`, or `TAU` changed.

The deterministic gate verifies the complete processed-gas partition from exact IAR/OAR mappings: 17 consumers exist, the 3 electricity-producing routes remain outside the delivery proxy, and all 14 non-electricity routes receive it. Classification does not rely on technology-name prefixes.

## Source changes

### Legacy gas VOM

`PHL_POW_CHP_NG_OLD`, mode 1, all 34 years:

- 2020-2021: retained the exact inherited take-or-pay credit and replaced only the `0.0001 MUSD/PJ` epsilon VOM with `0.7050283513976835 MUSD/PJ`.
- 2022-2053: replaced `0.0001` with `0.7050283513976835 MUSD/PJ`.

The replacement is the exact full-precision VOM already mapped to `PHL_POW_PP_NGCC` from EIA AEO 2023 Table 1 and the World Bank US CPI deflator (`SRC_VC_EIA_AEO2023_T1`; `SRC_VC_WB_CPI_USA`). Fixed cost and every physical coefficient remain unchanged.

### Non-power delivery proxy

For every year and each of the 14 non-electricity processed-gas routes:

`VC_after[y] = VC_v32[y] + gas_IAR_v32[y] * 8.2 MUSD/PJ_gas_input`

The routes are agriculture heat; three industrial heat routes; two gas-to-hydrogen routes; service heat; household cooking; and all six road-CNG routes. The year-specific v32 IAR is used at full source precision; no efficiency change is embedded.

The `8.2 MUSD/PJ_input` central value is the midpoint of the retained `6.17-10.29` source-derived range from Elizabethtown Gas. It is explicitly a conservative proxy, not a Philippine route-specific tariff. The Philippine DOE's 2024 Energy Investment Kit reports the calibration-period natural-gas market as power-only; the official URL was recorded, but no longer returned the PDF for local archiving on 2026-08-27.

Total source edit: 15 rows × 34 years = 510 `RYTM.json` cells. `genData.json` changes only case identity metadata. All other `RY*.json` files are byte-identical to sealed v32.

## Diagnostic sequence and solve economy

Two independent diagnostic directories are excluded from the candidate and seal:

1. Five active road-CNG rows plus cooking left `PHL_TRA_23WHEEL_NG` as a bypass. One optimal diagnostic run identified `29.5878 PJ` of three-wheel gas use in 2023 and 2024.
2. Closing all six road-CNG rows plus cooking shifted gas to industrial heat, service heat, and gas-to-hydrogen. One optimal diagnostic run established that the defect was commodity-wide.

Each failed scope was preserved as a separate top-level diagnostic and was not patched or re-solved. The final candidate was rebuilt cleanly from sealed v32 after the exact omitted consumer partition was identified. Its inventory contains only the four canonical required runs.

## Validation

Canonical baseline: sealed `Philippines_v32`, with source and generated identities verified before editing. BASE objective `838560.95562083`; runtime `66.157660291 s`; matrix `467075 × 517844`, `8194641` nonzeros.

The source gate passed before model generation:

- exactly 510 permitted VC cells changed;
- all 476 delivery cells follow the exact IAR formula;
- the legacy VOM and retained take-or-pay arithmetic are exact;
- the processed-gas consumer partition is complete;
- all policy VC overrides remain null;
- all other parameter JSON files are byte-identical;
- no activity/share bound changed;
- provenance rows and archived Elizabethtown hash are present exactly once.

All four cases were generated with `DataFile.generateDatafile()`, preprocessed with `.preprocessData()`, checked by `glpsol --check`, and solved by CBC. Policy optimizations ran concurrently in isolated run directories; reported runtime ratios therefore include shared CPU/memory contention.

| Scenario | Status | Objective | Change vs v32 | Runtime | Ratio | Matrix delta |
|---|---|---:|---:|---:|---:|---:|
| BASE | Optimal | 852438.33485986 | +1.6549% | 78.1788 s | 1.1817× | 0 |
| COAL_PHASEOUT | Optimal | 873334.54788478 | +2.2080% | 124.4918 s | 0.9546× | 0 |
| RE | Optimal | 862660.13060768 | +1.7483% | 132.5055 s | 0.9436× | 0 |
| EV | Optimal | 828191.95783998 | +1.5516% | 148.5331 s | 1.0577× | 0 |

Run-specific hashes, timestamps, objectives, gas balances, extraction-cap residuals and duals, top adjacent activity changes, and exact baseline comparisons are in `gas_delivery_four_scenario_validation_v33.json`. Candidate qualification is in `gas_delivery_candidate_status_v33.json`.

## Known limitations and deferred work

- The delivery adder is a transparent proxy. It does not distinguish CNG stations, household distribution, industrial delivery, or gas-to-hydrogen siting.
- Embedding the proxy in conversion VC cannot represent endogenous investment in a future gas distribution network. A future gas-in-transport or industrial-gas scenario needs explicit infrastructure and route-specific evidence.
- Non-power gas remains endogenous and is reduced, not prohibited; 2024 use is `29.3682 PJ`.
- Demand and station service are unchanged. Electricity demand should be rebuilt from independent sector electricity sales and physical service/output evidence; DOE gross generation must remain validation-only.
- The 2024 gas/coal split remains unresolved in an annual least-cost model and must not be closed with a gas dispatch target or bound.
- The irrigated-rice correction remains separate and is unaffected.

## Files

- Source: `RYTM.json`, `genData.json` identity metadata.
- Provenance: `data_sources/SOURCES.csv`, `ASSUMPTIONS.csv`, `CALCULATIONS.csv`, `MODEL_MAP.csv`, `GAPS.csv`, and `CHANGES.csv`.
- Evidence and gates: `documentation/gas_delivery_source_change_v33.json`, `preflight_gas_delivery_v33.json`, `gas_delivery_four_scenario_validation_v33.json`, and `gas_delivery_candidate_status_v33.json`.
- Generated run artifacts: `res/BASE_V33_GAS_DELIVERY`, `COAL_PHASEOUT_V33_GAS_DELIVERY`, `RE_V33_GAS_DELIVERY`, and `EV_V33_GAS_DELIVERY`.
