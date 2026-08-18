# Philippines v18 power-investment cleanup

Date: 2026-08-17
Case: `Philippines_v18`
Run: `TOMORROWLAND`

## Outcome

The live source now uses the 2020 fleet as its power-sector initial condition and
leaves later investment endogenous. All 20 observed 2021-2025 investment pins
were removed. The four legacy CHP `_OLD` representations are closed to new
entry for the full horizon, while their residual-capacity paths are unchanged.
New conventional coal capacity is limited to 2 GW/year in 2020-2029, followed
by the already documented 2.5, 3 and 5 GW/year bands. `COAL_PHASEOUT` retains an
exact zero from 2031.

Only `case/Philippines_v18/RYT.json` changed: 20 `TAMinCI.SC_0` cells and 42
`TAMaxCI.SC_0` cells. `RC` and every scenario overlay are byte-unchanged.

## Equation-first classification

| Information | Classification | Treatment |
|---|---|---|
| Grid-connected fleet operating in 2020 | Initial stock | Retained in `RC`; no RC cell changed |
| Observed additions in 2021-2025 | Benchmark only | Removed from `TAMinCI`/matching `TAMaxCI`; retained in the validation record |
| DOE projects classified as committed at 31 December 2020 | Candidate continuing commitment evidence | Screened but not applied as minima because project-level technology, COD, survival and irrevocability were not established |
| Legacy coal, gas, oil and biomass CHP `_OLD` routes | Physical stock representations | `TAMaxCI=0` throughout 2020-2053; surviving RC remains available |
| Coal construction speed | Continuing physical delivery envelope | `TAMaxCI=2` GW/year in 2020-2029; later existing bands retained |
| CoalPhaseOut prohibition | Policy constraint | Exact `TAMaxCI=0` from 2031 retained |

The affected power technologies are conversions. The `_OLD` CHP technologies
are stock-only representations. `PHL_POW_PP_WON`, `PHL_POW_PP_SPV`,
`PHL_POW_PP_NGCC`, `PHL_POW_PP_HY_LA`, `PHL_POW_GEO_OLD` and
`PHL_POW_PP_COAL` are investable conversion options, subject to their physical
entry envelopes. No pass-through, demand, accounting or backstop technology was
reclassified.

## Formulation mapping

`TAMaxCI` enters `NCC1_TotalAnnualMaxNewCapacityConstraint` and limits
`NewCapacity` from above. `TAMinCI` enters
`NCC2_TotalAnnualMinNewCapacityConstraint` and limits it from below. Equal
positive values therefore pin an endogenous investment result.

MUIO uses JSON `null` to inherit a preceding active scenario value. Numeric
zero is an active value. The `COAL_PHASEOUT` row consequently keeps `null`
through 2030 and exact `0` in 2031-2053. A value such as `0.0001` would permit
capacity and was not used.

## Source changes

### Removed minima

The 20 positive `TAMinCI.SC_0` cells were set to zero:

- solar PV: 2021-2025 (5);
- coal: 2021, 2022 and 2024 (3);
- legacy oil CHP: 2021, 2022 and 2024 (3);
- legacy biomass CHP: 2022-2024 (3);
- large hydro: 2022-2024 (3);
- geothermal: 2022 and 2025 (2); and
- NGCC: 2025 (1).

The matching positive upper bounds on investable technologies were opened.
The corresponding legacy CHP upper bounds were instead set to zero because
those technologies represent inherited stock, not new-build options.

### Entry treatment

- Mature investable onshore wind, solar PV, NGCC, large hydro and geothermal
  receive the open `999999` sentinel in 2020. Their later deployment envelopes
  remain as previously documented.
- Legacy coal, gas, oil and biomass CHP receive `TAMaxCI=0` in every year.
- Conventional coal receives `TAMaxCI=2` GW/year in every year from 2020
  through 2029. The 2030-2039 2.5, 2040-2050 3.0, and 2051-2053 5.0 GW/year
  values are unchanged.
- `COAL_PHASEOUT` inherits the base coal limit through 2030 and enforces exact
  zero thereafter.

The exact before/after value for every changed cell is recorded in
`data_sources/CALCULATIONS.csv` and `data_sources/MODEL_MAP.csv`, and in
`data_sources/snapshots/power_investment_cleanup_v18_2026-08-17.json`.

## Committed-project screen

DOE's PEP 2020-2040 reports 53 committed projects totaling 8,977.11 MW as of
31 December 2020: coal 4,241; oil 392.04; natural gas 3,500; geothermal 140;
hydro 144.3; solar 408.57; wind 132; and biomass 19.2 MW. Those aggregate
figures do not establish a lossless mapping to model technologies and
commissioning years, nor whether each project was irreversible and ultimately
survived. No new minimum was therefore added. A future minimum requires
project-level evidence of an irreversible commitment known in 2020.

## Deterministic and generated-model checks

- Source allowlist: passed; only `RYT.json` changed.
- Exact source delta: passed; 62 cells equal the retained manifest.
- `RC`: byte-unchanged.
- Scenario overlays: byte-unchanged.
- Remaining positive observed-addition pins: zero.
- Legacy stock-only entry: zero in every year.
- Base coal construction bands: passed.
- CoalPhaseOut exact zero from 2031: passed.
- Application generation and preprocessing: passed.
- Effective TOMORROWLAND coal row: 2 GW/year in 2020-2029, 2.5 GW in 2030,
  and zero in 2031-2053.
- GLPK model generation: passed; 808,384 rows, 900,022 columns, 12,892,647
  matrix nonzeros and 427,456 objective-row nonzeros.

## Optimization and result effects

One candidate CBC optimization was run. It was optimal at
`369758319.27495068`; CBC reported 366.20 CPU seconds and 371.19 wallclock
seconds. No control or post-promotion optimization was run.

The formerly pinned additions are now endogenous. Selected outcomes are:

| Technology/year | Observed benchmark (GW) | Model (GW) |
|---|---:|---:|
| Solar PV 2021-2024 | 0.3024; 0.3049; 0.1568; 1.0012 | 0; 0; 0; 0 |
| Solar PV 2025 | 0.2749 | 6.7976528 |
| Coal 2021-2022 | 0.725; 0.7694 | 0; 0 |
| Coal 2023 | 0 | 0.76923797 |
| Coal 2024-2025 | 0.6; no pin | 2; 2 |
| NGCC 2025 | 0.88 | 0 |
| Large hydro 2022-2024 | 0.0159; 0.0468; 0.0352 | 0; 0; 0 |
| Geothermal 2022 / 2025 | 0.0037; 0.0357 | 0; 0.084734196 |
| Legacy oil and biomass CHP pinned years | observed additions | 0 in every case |

All stock-only new-capacity variables are zero, and every conventional-coal
addition respects its effective scenario cap.

The nearest retained TOMORROWLAND result has objective
`369766929.90727115`, a contextual difference of `-8610.6323` or
`-0.0023287%`. It is not a source-matched control because it predates the
already-present fossil-supply restructuring. This difference must not be
attributed solely to the power cleanup.

## Fossil-trade finding

The candidate confirms a separate fossil calibration problem. In 2022 it
extracts and exports the full 353.6 PJ domestic-coal envelope while importing
1,198.1289 PJ. DOE reports 16.06 Mt production, 7.1 Mt exports and 32.7 Mt
imports in 2022, so simultaneous import and export are real but exporting all
domestic production is not.

The cause is economic: domestic extraction costs 1.1149 per PJ, the export
route has variable cost `-4.2659` per PJ (revenue), and imports cost 3.0572 per
PJ. The model can improve its objective by selling domestic coal and replacing
it with cheaper imported coal. This likely reflects missing grade, calorific
value, plant compatibility, location, freight and terminal detail. The result
is disclosed in `GAPS.csv`; it was not hidden with a historical export pin or
cap. A defensible repair should differentiate delivered coal services/economics
or introduce only a sourced continuing physical export constraint.

## Promotion identity

The promoted live `RYT.json` hash and regenerated `data.txt` hash are exactly
the same as the solved candidate:

- `RYT.json`: `333f37a5ac526530af7ea797b119ac7c09ba69be99accd5318b829f68b188792`;
- `data.txt`: `3b5f6e9069b438e1eba1e456627a92df0dbc116b513589a5efea81fe5f78caf8`.

The preprocessor emitted unordered derived-set members in a different textual
order, so `data_processed.txt` and the LP are not byte-identical. The live GLPK
check nevertheless reproduced all matrix dimensions exactly. Under the
solve-economy rule, the solved disposable candidate is the validated result and
no second CBC run was needed. Existing live `results.txt` must not be treated as
a result of the newly regenerated live input.

## Audit artifacts

- `data_sources/snapshots/power_investment_cleanup_v18_2026-08-17.json`
- `data_sources/snapshots/power_investment_cleanup_validation_2026-08-17.json`
- `data_sources/snapshots/power_investment_cleanup_solve_2026-08-17.json`
- `data_sources/snapshots/power_investment_cleanup_promotion_identity_2026-08-17.json`
- `scripts/apply_philippines_v18_power_investment_cleanup.py`
- `scripts/validate_philippines_v18_power_investment_cleanup.py`
- `scripts/run_philippines_v18_power_investment_cleanup.py`
- `scripts/document_philippines_v18_power_investment_cleanup.py`

## Known limitations

- No project-level end-2020 committed-capacity mapping was established; no
  minimum has been manufactured from the aggregate register.
- The nearest retained comparison solve is not source-identical.
- The fossil export/import price-grade problem remains unresolved.
- The later deployment bands remain judgmental physical envelopes and require
  sensitivity analysis where binding.
