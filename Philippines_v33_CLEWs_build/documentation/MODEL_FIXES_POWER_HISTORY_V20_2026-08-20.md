# Philippines v20 minimal endogenous power-history calibration — 2026-08-20

## Outcome

V20 improves the historical electricity allocation without adding technologies,
commodities, regions, constraints, activity targets, generation shares, or
realized investment equalities. The accepted candidate is optimal at
369,737,957.77807945. Its full application chain took 215.83 seconds, including
148.45 seconds in CBC, compared with 471.11 seconds and 351.70 seconds for the
latest verifiable unchanged v19 result.

Against DOE gross generation, technology-level WAPE falls from 49.46% to
13.60% in 2020, 46.71% to 16.59% in 2021, 37.31% to 22.51% in 2022, and
33.55% to 31.36% in 2023. It rises from 37.47% to 39.43% in 2024. The change
is therefore promoted as a bounded improvement, not as a claim that a national
copperplate reproduces every historical year.

## Equation-first classification and design

- DOE 2020 installed capacity is an initial-stock cross-check. The residual
  capacities were already installed in v14 and are unchanged here.
- DOE 2020 dependable capacity is an independent continuing physical
  availability driver. For the closed legacy fleets, `AvailabilityFactor` is
  the dependable/nameplate ratio in every model year.
- The documented 2020–2021 Malampaya gas-sales agreements are historical
  contractual/economic drivers. Their take-or-pay payment is represented as a
  sunk fixed cost on the closed legacy gas-power stock plus an equal
  plant-specific variable contract credit. The domestic extraction price
  remains unchanged for all non-power gas users.
- DOE 2020–2024 generation, capacity, and realized stock changes are historical
  validation benchmarks only. None is entered as a generation target, share,
  `TAL`, `TAU`, or new-capacity equality.

The active formulation maps variable cost through `cost` and `OC1_OperatingCosts`
in `WebAPP/SOLVERs/model.v.5.4.txt`; capacity-timeslice and annual availability
through `CAa4_Constraint_Capacity` and `CAb1_PlannedMaintenance`; and annual
technology activity bounds through `AAC1`/`AAC2`. V20 changes only source
parameters read by those existing equations.

## Historical approaches checked before editing

The retained history was audited before choosing this formulation.

- Historical coal dispatch pins had already been removed. Their earlier removal
  increased endogenous 2020 old-coal activity from 209.45 to 276.22 PJ; they
  were not restored.
- Twenty realized 2021–2025 power-addition equalities had already been removed;
  no post-2020 investment pin was restored.
- Geothermal availability, onshore-wind capacity factor, coal and SMR capital
  costs, hydro lifetime, gas chronology/prices, and fossil border prices had
  already been calibrated. Generic price tuning was not repeated.
- No retained three-grid implementation or discarded three-grid experiment was
  found. Earlier large cross-technology constraint formulations had caused
  material solve-time regressions, so regionalization was not added without a
  complete regional-demand and transmission topology.
- A plant/vintage register had been recommended since v14 but never built. V20
  implements only four defensible DOE plant-class clusters because plant-by-plant
  detail was not necessary for this bounded correction.

## Source changes

Only `genData.json`, `RYT.json`, and `RYTM.json` change.

| Technology | Installed MW | Dependable MW | AF before | AF after |
|---|---:|---:|---:|---:|
| `PHL_POW_CHP_COAL_OLD` | 10,943.9 | 10,245.3 | 1 | 0.9361653523880883 |
| `PHL_POW_CHP_NG_OLD` | 3,452.5 | 3,286.1 | 1 | 0.9518030412744388 |
| `PHL_POW_CHP_OIL_OLD` | 4,236.6 | 3,053.6 | 1 | 0.7207666525043667 |
| `PHL_POW_CHP_BIOM_OLD` | 447.4 | 285.4 | 1 | 0.6379079123826553 |

For 2020 and 2021, the old gas plant's raw-gas requirement is
`1.870042735 × 1.056771911 = 1.9762086347176167 PJ/PJ`. The sourced extraction
prices of 6.662111756970275 and 6.68807478018528 MUSD/PJ are unchanged. The
plant-specific credits are therefore 13.16572277957841 and
13.217031130239278 MUSD/PJ of electricity activity. The corresponding full
domestic-envelope payments are shifted into fixed costs on the already closed
legacy gas capacity. Full-envelope cost is conserved to floating-point
precision in both years.

The use of the full domestic production envelope as the maximum contract-payment
proxy is a disclosed judgment because plant-level GSPA contract quantities were
not recovered. This changes a sunk cost on closed residual stock and therefore
does not force its activity.

## Rejected diagnostic candidate

The first disposable candidate shifted the take-or-pay cost at the upstream
extraction technology. It solved optimally, but the zero marginal extraction
cost applied to every gas user. In 2021, non-power users consumed 29.33 PJ of
the processed gas pool and crowded out the contracted power plants. That run is
rejected and retained only as diagnostic evidence. The accepted source applies
the contract credit at `PHL_POW_CHP_NG_OLD`; all other users retain the sourced
gas price. This failure identified the equation and sector indices that required
correction and justified the second optimizer run. Neither run was a sensitivity.

## Validation

The exact v19 source was used as the unchanged baseline; it was not rerun. The
accepted disposable candidate passed:

- byte-identity for all source JSON files outside the three-file allowlist;
- exact cell-diff, scenario-inheritance, full-envelope cost-identity, and
  no-forcing checks;
- UI-path generation and preprocessing;
- GLPK model generation and LP export: 809,933 rows, 901,586 columns, and
  13,080,959 matrix nonzeros;
- one corrective full CBC solve, optimal at 369,737,957.77807945;
- CSV and viewer export; and
- technology, share, total-generation, capacity, binding-constraint, and dual
  validation against the retained DOE tables.

The accepted result binds domestic-gas extraction in 2020 and 2021 with duals
−3.8673493 and −6.193906. The hydro annual availability equation binds in 2020
at 19.075515 PJ with dual −7.6428744.

## Known limitations and stopping rule

Oil and biomass generation remain zero, and hydro remains at 19.08 PJ. Those
gaps reflect absent off-grid/embedded/cogeneration service structure and an
inherited restrictive hydro energy profile. Gas remains too low after the
2020–2021 contract period, especially in 2024. A defensible remedy would require
regional final-demand balances, interconnection limits, more physical hydro
data, and plant-class fuel/operating obligations—not generation fitting.

The 2020 DOE benchmark includes grid-connected, embedded, off-grid, and
test/commissioning output. DOE's national summary is grid-only from 2021 onward.
That boundary break is retained in every benchmark row.

No sensitivities were run. Further sensitivity analysis is intentionally left
to model users.
