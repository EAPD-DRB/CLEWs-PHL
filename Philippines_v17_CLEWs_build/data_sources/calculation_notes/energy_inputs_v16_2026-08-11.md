# Philippines v16 energy-input correction

## Scope and physical classification

This change corrects three input-side energy assumptions and removes a
misleading local naming suffix. It does not prescribe a generation mix.

| Item | Classification | Treatment |
|---|---|---|
| Offshore wind capacity factor | Physical resource/performance input | Replace the inherited annual mean and retain the inherited relative timeslice shape. |
| Geothermal availability | Physical operating input | Restore the inherited CLEWs Global value of 0.9. |
| Onshore wind annual ceiling | Continuing screened technical-resource constraint | Replace 1,594.08 PJ/year with 663.84 PJ/year. |
| DOE geothermal capacity and generation | Benchmark only | Retain for validation; do not fit activity or availability to observed generation. |
| Wind, solar and geothermal construction/activity | Endogenous outcome | No target, lower bound, share or user constraint is added. |

Existing capacity, final demands, costs, lifetimes and technology IDs are
unchanged. The physical inputs are written only to `SC_0`; the three policy
scenario rows remain null and inherit the same physical values.

## Naming correction

OSeMOSYS Global defines suffix `01` as investable capacity and `00` as
non-investable historical capacity. It is not a resource-quality tier. During
the earlier MUIO import, three investable technologies acquired a local `_T1`
suffix and “tier 1” descriptions even though no tiers 2 or 3 existed. The
stable IDs are preserved while names and descriptions are changed:

- `TEC_1wdli`: `PHL_POW_PP_WON_T1` -> `PHL_POW_PP_WON` (Onshore wind)
- `TEC_bl1d7`: `PHL_POW_PP_WOF_T1` -> `PHL_POW_PP_WOF` (Offshore wind)
- `TEC_1k064`: `PHL_POW_PP_SPV_T1` -> `PHL_POW_PP_SPV` (Solar photovoltaic)

No commodity name contains `_T1`, so no commodity rename is required. The
structural edit is made in `genData.json` and propagated through `UpdateCase`;
parameter links continue to use the unchanged technology IDs.

## Offshore wind

NREL report NREL/TP-5R00-92293 gives annual net capacity factors for Philippine
offshore development zones A-G (Figure 10, printed page 10), technical-potential
capacity by zone and foundation type (Table 4, printed page 13), and states
that 15% losses are already included (Table 2, printed page 9).

| Zone | Net CF | Fixed MW | Floating MW | Total MW |
|---|---:|---:|---:|---:|
| A | 35.28% | 383 | 2,764 | 3,147 |
| B | 20.80% | 174 | 1,184 | 1,358 |
| C | 28.67% | 477 | 5,622 | 6,099 |
| D | 28.78% | 414 | 26,806 | 27,220 |
| E | 24.56% | 573 | 0 | 573 |
| F | 27.18% | 228 | 2,006 | 2,234 |
| G | 21.17% | 704 | 1,404 | 2,108 |

The capacity-weighted mean is

`sum(zone capacity x zone CF) / sum(zone capacity)`

`= 12,171.8594 MW-equivalent / 42,739 MW`

`= 0.2847380261587777`.

The inherited 30-timeslice profile has a YearSplit-weighted annual mean of
`0.19427924507532`. Every timeslice value is multiplied by
`0.2847380261587777 / 0.19427924507532 = 1.4656121710190289`. This preserves
the inherited relative seasonal/diurnal shape while installing the sourced
annual mean. `AvailabilityFactor` remains 1 because the NREL capacity factors
already include losses; applying an additional availability derating would
double count them.

The source path is `RYTTs.json / CapacityFactor / TEC_bl1d7`. In the active
formulation, this reaches the timeslice capacity envelope through
`CAa4_Constraint_Capacity`; annual availability is enforced by
`CAb1_PlannedMaintenance`.

## Geothermal

`RYT.json / AvailabilityFactor / TEC_0qr3z` changes from 1.0 to 0.9 for every
model year. This restores the value in the retained inherited CLEWs Global
`AvailabilityFactor.csv` rows for `PWRGEOPHLXX01`.

The unchanged 4 GW annual capacity ceiling and corrected availability imply

`4 GW x 31.536 PJ/GW-year x 0.9 = 113.5296 PJ/year`.

The separate 126 PJ annual activity limit is therefore slack. DOE 2020 values
of 1,928 MW installed capacity, 1,753 MW dependable capacity and 10,756,815
MWh gross generation imply utilization benchmarks of 0.6368577375 and
0.7004594018 respectively. They are not an availability observation: outages,
steam-field performance, curtailment and economic dispatch are not separately
identified, so the model is not fitted to either benchmark.

## Onshore wind

The USAID-NREL report NREL/TP-7A40-71814, Table B-2 (printed page 62), reports
Philippine restricted-screen onshore-wind generation potential of 27.0, 120.9
and 36.5 TWh/year across its three LCOE bands:

`(27.0 + 120.9 + 36.5) TWh/year x 3.6 PJ/TWh = 663.84 PJ/year`.

`RYT.json / TotalTechnologyAnnualActivityUpperLimit / TEC_1wdli` therefore
changes from 1,594.08 to 663.84 PJ/year for 2020-2053. This is a continuing
screened physical-resource ceiling enforced by
`AAC2_TotalAnnualTechnologyActivityUpperLimit`, not an activity target.

## Reproducible implementation

The normalized source register is
`../snapshots/energy_inputs_2026-08-11.json`. Its SHA-256 is
`d16ac808cda4bf15b19c4969e406234cd1cd66a40ba96948b610c23b69cdf744`.
The generator, validator and ledger publisher are retained under `../../scripts/`.
The generator copies the live case to a disposable candidate, applies the
structural renames through `UpdateCase`, overlays only the three calibrated
parameter families and proves that the semantic source diff is limited to
`genData.json`, `RYT.json` and `RYTTs.json`.

The full-precision candidate manifest and validation output are retained in
`../snapshots/energy_input_calibration_manifest.json` and
`../snapshots/energy_input_validation.json`. The six canonical CSV ledgers
record the external sources, assumptions, calculations, exact model mappings,
known gaps and change chronology. The CSVs are authoritative; the workbook is
a generated review copy.

## Validation result

The disposable `ENERGY_INPUTS_BASE` candidate passed source-scope, stable-ID,
commodity-identity, parameter-exactness, generated-representation,
solver-freshness, endogenous-offshore and physical-envelope checks. The full
application chain generated and preprocessed the solver data, passed GLPK
matrix checking and solved optimally with CBC.

- objective: 369,730,088.2957073;
- application-chain wall time: 215.64 seconds;
- matrix: 791,109 rows, 884,956 columns and 12,552,173 nonzeros;
- objective change from the unchanged control: +1,088.09526617
  (+0.000294295353%);
- final-demand rows changed: 0;
- onshore wind peak activity: 2.4657 PJ/year, below 663.84 PJ/year;
- geothermal peak activity: 113.5296 PJ/year, equal to the corrected physical
  envelope within exported-CSV precision; and
- offshore new capacity: 0 GW, with positive reduced costs of 1,639.5751 in
  2025 and 11.342552 in 2053.

The zero offshore build is an endogenous result, not a failed correction. The
capacity-factor defect has been removed; under the remaining costs and system
conditions, offshore wind is still not selected. No build is forced to make
the historical or expected outcome appear.

After promotion, `Philippines_v16/ENERGY_INPUTS_BASE` was regenerated through
the normal application chain. It solved optimally at 369,730,088.29570782;
CBC wall time was 263.58 seconds and total application-chain time was 334.14
seconds. The live source hashes exactly equal the candidate hashes and all
seven live checks pass. Its objective differs from the candidate by
0.00000053. Repeated CBC solves selected different degenerate activity and
capacity solutions at that same objective; the live record discloses the
largest differences. Demand and annual technology emissions reproduce, while
offshore new capacity remains zero, onshore activity remains below its ceiling
and geothermal remains within its corrected capacity/availability envelope.
The authoritative live record is
`../snapshots/energy_input_live_validation.json`.

## Known limits

The exact NREL hourly zone/grid-cell series is not frozen, so this repair keeps
the inherited timeslice shape. The offshore resource ceiling has not yet been
aligned to the same screened geography. Geothermal 0.9 is a restored inherited
engineering assumption rather than a Philippine plant-level outage series.
Both evidence gaps are recorded in `GAPS.csv`.
