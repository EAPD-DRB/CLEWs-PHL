# Philippines v14 stock-and-turnover validation

Date: 2026-07-28

Status: **optimal**

## Outcome

The regenerated BASE case is `optimal`. Its objective is
`369630979.503002` versus `369630979.50300163` in the validated
baseline `Philippines_v14_STOCK_TURNOVER.backup-20260728T212440Z/BASE_V14`, a change of `9.675267726022397e-14%`.

The validated chain used the same repository path as the application:
`DataFile.generateDatafile` → `preprocessData` → explicit
`glpsol --check`/LP export → CBC → CSV and pivot generation.

## `PHL_POW_HEAT` structural correction

The regenerated source contains neither `PHL_POW_HEAT`/`COM_te2a0` nor
`PHL_POW_HEAT1`/`COM_pesfw`; the generated raw and preprocessed solver data
also contain no heat token. The `PHL_POW_GEO_OLD` geothermal electricity
output remains present and its stranded heat output is absent. These checks
are recorded as
`removed_heat_commodity_names_present=[]`,
`removed_heat_commodity_ids_present=[]`,
`removed_heat_tokens_in_generated_data=[]`,
and
`geothermal_electricity_output_link_present=True`.

## Root cause established before the solve

OSeMOSYS defines total capacity as residual capacity plus surviving new
capacity (`CAa1`/`CAa2`), limits new capacity with `NCC1`, and limits activity
to available total capacity with `CAa4`/`CAb1`. The earlier prefix rule set
2020 `TAMaxCI=0` for every `PHL_POW_*` technology. That accidentally included
six zero-cost sectoral electricity-distribution pass-throughs with
`ResidualCapacity=0`; their activity capacity was therefore exactly zero.

The source generator now uses an explicit, exhaustive physical-stock versus
capacity-free-pass-through classification. The physical technologies retain
the 2020 investment closure. The pass-throughs retain the inherited dummy
capacity convention. The deterministic equation replay is in
`initial_stock_equation_check.json`.

A second equation replay mapped the remaining presolve infeasibility to the
2020 services-heat time-slice balance. The four-decimal baseline capacity CSV
was short by `3.91053e-06`; the generator now reads full-precision values from
the validated CBC result and applies a documented one-part-per-million
numerical headroom to positive inherited effective stocks.

Finally, both exact aggregate formulations remained feasible but timed out at
280 seconds: first Tag-0 UDCs, then a native `INC1` permit network. A
controlled no-aggregate rollback solved optimally in 125.35 seconds but showed
abrupt annual activity-share changes in five classes. The source formulation
therefore uses full-horizon per-technology `TAMaxCI` adoption ceilings through
native `NCC1`. These do not constrain activity or expire after a calibration
window; they are explicitly not a hard aggregate class-sales cap.

## Checks

| Check | Result |
|---|---|
| Source generation through `UpdateCase` | passed |
| Application data generation | passed |
| Application preprocessing and mode mappings | passed |
| `glpsol --check` and LP export | passed |
| CBC optimization within 280 seconds | passed_optimal |
| CSV extraction and pivot generation | passed |
| Case/run/scenario identity | passed |
| Fresh result timestamps | passed |
| Stock-group TAL/TAU audit | passed |
| Full-horizon technology-adoption bounds | passed |
| Annual within-class activity-share audit | passed (diagnostic) |

The activity-bound audit checked
3128 technology-year cells. It found
0 restrictive stock-group TAL/TAU
cells and 0 positive exact
activity pins.

The adoption audit checked 2278
technology-year rows, found 0 violations and
597 binding ceilings. `NCC1` duals were parsed for
2278 rows. Detailed residuals, duals and informational
class-total build rates are in
`validation_results.json`.

The transition audit checked
2211 adjacent-year
technology-share rows. The largest absolute year-to-year activity-share
change is
32.79
percentage points; changes above 25 points remain in
TURN_AGR_HEAT, TURN_RAILF, TURN_RAILP, TURN_SER_HEAT. This is reported as a diagnostic, not converted into an
activity pin. Capacity turnover constrains replacement speed, while dispatch
among already available stocks can still respond to costs and demand. The
largest events and their technologies are in `validation_results.json`.

## Matrix, timing and artifacts

The matrix has 791041 rows,
884956 columns and
12530519 nonzeros. CBC took
133.12081658299576 seconds. Every generated artifact
is recorded with its timestamp, size and SHA-256 hash in
`validation_results.json`.

## Baseline comparison

The baseline is `Philippines_v14_STOCK_TURNOVER.backup-20260728T212440Z/BASE_V14`. The complete activity, capacity,
emissions and production comparisons—including rows present only in the
pre-change model—are in `validation_results.json`. For the heat-removal A/B,
the intended structural difference is limited to the deleted heat branch;
the regression separately records physical invariants and alternate-optimum
basis changes.

The invariant regression passed:

- objective delta:
  `3.5762786865234375e-07` against an absolute
  tolerance of `0.001`;
- changed demand rows: `0`;
- changed emissions rows: `0`;
- changed fixed-cost rows:
  `0`;
- changed annualized-investment-cost rows:
  `0`;
- changed capital-investment rows:
  `0`.

Removing redundant rows changed the cost-identical basis chosen by CBC. The
annual-activity comparison records changes for
PHL_DEM_PWR_GWT_WAT, PHL_DEM_PWR_SUR_WAT, PHL_AGR_HEAT_NG, PHL_AGR_HEAT_OIL, PHL_DEM_PUB_GWT_WAT, PHL_DEM_PUB_SUR_WAT, PHL_POW_PP_HY_LA, PHL_POW_GEO_OLD, PHL_POW_PP_SPV_T1, ENV_WATER, PHL_INDU_OTHHPH_NG, PHL_INDU_OTHLPH_NG, PHL_INDU_OTHLPH_H2, PHL_INDU_OTHHPH_H2, PHL_AGR_HEAT_ELE;
the capacity comparison changes only
no technology.
These are reported rather than hidden. The unchanged objective, demands,
emissions, fixed costs and investment costs distinguish the alternate optimum
from a policy or accounting effect of useful heat.

## Diagnostic history (not validation)

- Equation replay isolated the blanket PHL_POW_* 2020 capacity closure as the structural infeasibility; the source generator now preserves capacity-free pass-through technologies.
- Full-precision result parsing plus one-part-per-million headroom removed a 3.91053e-06 services-heat balance shortfall caused by the rounded baseline CSV.
- The corrected generic-UDC case timed out at 280 seconds; a controlled no-UDC rollback solved optimally in 125.35 seconds. A native permit-network source formulation also timed out at 280 seconds. The no-aggregate result showed >25-point annual share changes in five classes, so the final source uses full-horizon, uncoupled NCC1 technology-adoption bounds.

These failed or interrupted diagnostics were not promoted. This report refers
only to the regenerated source case and the fresh artifacts recorded here.

## Limitations

- Official plant-vintage data are not yet integrated; DOE 2020 technology
  totals scale the inherited v13 retirement paths.
- LTO categories that do not map one-to-one to model technologies retain
  validated v13 effective stocks, with the assumption identified in the source
  register.
- Household charcoal uses the existing coal-cooking technology as a documented
  commodity proxy.
- EDGAR is retained for emissions benchmarking; it is not the source for
  physical stock or turnover inputs.
- The remaining >25-point utilization changes identify the next empirical
  calibration need: technology-specific utilization, sales and vintage data.
  They are not suppressed with temporary activity constraints.
- Small documented geothermal direct use is outside the current model
  boundary. Adding it later requires site-specific useful-heat demand,
  resource temperature, delivery infrastructure, efficiency, utilization and
  cost data; it must not be recreated as a one-for-one power-plant coproduct.
