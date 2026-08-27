# Philippines v14 stock-and-turnover changes

Date: 2026-07-27

Case: `Philippines_v14_STOCK_TURNOVER`

## Reason

The v13 model used narrow historical TotalAnnualTechnologyActivityLowerLimit
and UpperLimit values to reproduce 2020 activity and, for power, dispatch
through 2024. Once released, those constraints allowed discontinuous fuel
switching. This version represents the initial condition with residual stock,
retirement profiles, final demand and full-horizon technology-adoption
ceilings. It does not force historical activity.

## Source files and parameters changed

- `genData.json`: updated case identity and description; removed the unused
  `PHL_POW_HEAT` (`COM_te2a0`) and `PHL_POW_HEAT1` (`COM_pesfw`)
  commodities and removed only the `PHL_POW_GEO_OLD` heat OAR. The
  geothermal electricity OAR and every technology, emission and
  policy/environmental constraint are preserved.
- `RYC.json`, `RYCTs.json`, and `RYTCM.json`: `UpdateCase` removed the
  parameter rows belonging to those deleted commodities. The generator first
  proves that all heat demand/profile values are zero or inherited nulls and
  that no other structural reference exists.
- `RYT.json`: recalibrated `RC`; removed 66 historical `TAL` cells;
  changed 113 historical `TAU` cells; set explicitly classified
  physical stock technologies' 2020 `TAMaxCI` to zero so 2020 is an
  initial-stock year. Capacity-free sectoral electricity pass-throughs retain
  their inherited investment bound.
- `RT.json`: changed household cooking `OL` from 15 years to 10 years, except
  biomass to 8 years.
- `RYT.json`: set every stock-group member's `TAMaxCI` to its documented
  class adoption series in every year (zero in the 2020 initialization year).

Every cell-level before/after value and its source/calculation/assumption IDs
is in `data_sources/PARAMETER_CHANGE_LOG.csv`. The register, calculation
formulas, assumptions and model-data map are in the other files in that
directory and in `docs/philippines_v14_stock_turnover/`.

## Main stock changes

- Power: official DOE 31 December 2020 capacity by technology totals
  26.25 GW. Each official total scales the
  corresponding v13 residual-capacity path; this corrects the stock total while
  retaining inherited retirement timing pending a plant-vintage register.
- Road: official LTO stocks initialize cars (1,134.136 thousand), buses
  (25.292 thousand), and motorcycles/tricycles (7,328.116 thousand). The v13
  effective light-truck, heavy-truck and van stocks remain because the LTO
  truck/utility-vehicle categories do not map one-to-one to the model classes.
- Cooking: 2020 CPH primary-fuel shares are normalized from 99.6% and mapped
  to the existing technologies. Charcoal is represented by the legacy
  `PHL_HOU_COOK_COAL` technology and remains a known commodity proxy.
- Other end uses: the validated v13 BASE `TotalCapacityAnnual` that served the
  former 2020 observed activity is parsed from the full-precision CBC result
  and transferred once to initialize effective capacity. Positive inherited
  values receive a documented one-part-per-million numerical headroom because
  the four-decimal CSV export was too coarse to preserve exact time-slice
  feasibility. The optimal result identity, timestamp and hashes are checked
  and the activity constraint itself is not retained.

## Turnover and adoption formulation

Residual capacity and operational life represent the inherited stock and its
retirement profile. To prevent one option from replacing that stock
immediately, the formulation uses the native `NCC1` equation:

`NewCapacity[t,y] <= TAMaxCI[t,y]`.

For every stock-class member and every year, `TAMaxCI` equals the documented
class adoption series. For road classes, the post-initialization series is the
2020 official new-registration count scaled by service demand. For other
classes, it is uniform-age replacement plus positive service-demand growth
converted at the lowest class capacity-to-activity factor. The series is
recursive: when a previously allowed new-capacity vintage reaches that
technology's operational life, its original allowance is added back to the
current-year ceiling. This prevents a false capacity shortage later in the
horizon while preserving the same physical replacement logic for endogenous
vintages.

This is deliberately a technology-specific adoption ceiling, not a hard
aggregate class-sales cap. It limits how quickly any one technology can take
over while allowing several options to enter in parallel. It imposes no
`TAL`, `TAU`, fuel share or activity share, and it remains active throughout
the horizon rather than ending after a historical calibration window.

Two exact aggregate implementations were rejected only after controlled
evidence. The corrected Tag-0 UDC version timed out at 280 seconds; disabling
only those rows restored an optimal 125.35-second solve. A source-generated
`INC1`/commodity-balance permit network was feasible but also timed out at 280
seconds. The optimal no-aggregate diagnostic further showed that the proposed
class ceilings bind 257 of 510 class-years across 12 classes (up to 23.30×),
so they were materially reshaping the transition rather than serving as
neutral bookkeeping. The same diagnostic did confirm abrupt activity-share
changes in five classes, including a 64.25-point industrial-heat change in
2021. The full-horizon native `TAMaxCI` formulation targets that takeover
problem without cross-technology coupling.

## Equation-led diagnosis of the initial infeasibility

The local OSeMOSYS formulation and the official model documentation were
reviewed before the corrected case was solved. `CAa1`/`CAa2` define total
capacity as residual capacity plus surviving new capacity, `NCC1` enforces
`NewCapacity <= TAMaxCI`, and `CAa4`/`CAb1` limit activity to available total
capacity.

An earlier prefix-based rule set 2020 `TAMaxCI=0` for every technology whose
name began `PHL_POW_`. That rule incorrectly included the six zero-cost
sectoral electricity-distribution pass-through technologies. They have no
physical residual stock and use the inherited dummy-capacity convention, so
the rule made their available 2020 capacity and activity exactly zero. This
was the structural cause of the infeasibility.

The source generator now requires an explicit, disjoint and exhaustive
classification of physical power stocks and capacity-free pass-throughs. Only
the former receive the 2020 investment closure. The deterministic replay and
equation references are recorded in
`documentation/initial_stock_equation_check.json`.

The subsequent presolve review isolated a second, purely numerical issue in
`EBa11(RE1,3,PHL_SER_HEAT,2020)`: initializing from the rounded
`TotalCapacityAnnual.csv` left maximum service 3.91053e-06 below exact demand.
The generator now parses `TotalCapacityAnnual` from the higher-precision CBC
`results.txt`, retains the CSV as a cross-check, and applies the documented
one-part-per-million headroom only to positive inherited effective stocks.

An all-years capacity-envelope replay then identified a third formulation
issue before promotion: a ceiling based only on retirement of the initial
stock and demand growth did not replace endogenous vintages after their
operational life. Aviation first became short in 2041. The final recursive
ceiling described above restores each allowed vintage at its retirement year;
the deterministic envelope check must report zero class-year service
shortfalls before solver validation.

## Bounds deliberately preserved

Land-use bounds, public groundwater/surface-water supply limits,
`ENV_WATER` diagnostic closure, policy-scenario bounds, and post-2024
renewable resource ceilings remain unchanged. In 2020-2024, renewable
historical dispatch upper bounds are replaced by the inherited technical
resource ceilings rather than removed.

## `PHL_POW_HEAT` structural correction

The inherited heat branch did not represent a Philippine district-heating or
direct-use heat system. `PHL_POW_HEAT1` had no structural link at all.
`PHL_POW_HEAT` had exactly one producer—`PHL_POW_GEO_OLD`—with an output
activity ratio of 1, no consumer and no final demand. Because the local
OSeMOSYS commodity balance is `production >= use + demand`, this output was
discarded without affecting geothermal dispatch. In the validated pre-change
v14 result it therefore reported 60.8046 PJ of heat in 2020, exactly equal to
geothermal electricity activity.

The World Geothermal Congress country update reports Philippine direct
geothermal use of 12.65 TJ/year (0.01265 PJ/year) in 2019, all classified as
bathing and swimming. That is about 4,807 times smaller than the model's
phantom 2020 heat output and is not a coproduct delivered from modeled power
plants. DOE energy-balance definitions and IRENA's Southeast Asia review also
provide no basis for a national district-heat commodity or a one-for-one
geothermal CHP coefficient. The two commodities and sole heat OAR are
therefore deleted rather than calibrated. A future direct-use module requires
site-specific resource, delivered-demand, temperature, network and cost data.

The evidence and calculation rule are registered as
`DS-WGC-DIRECT-USE-2020`, `DS-DOE-EBT-PRIMER-2021`,
`DS-IRENA-SEA-2018`, `AS-HEAT-SYSTEM-BOUNDARY` and
`CAL-HEAT-STRUCTURE`.

## Generation and validation status

The target was generated through `UpdateCase`; copied-input fingerprints,
source-preservation checks and exact parameter changes are recorded in
`stock_turnover_generation.json`.

This document does not claim solver validation. Matrix generation, explicit
`glpsol --check`, CBC optimization, baseline comparison, affected
activity/capacity/emissions, technology-adoption bounds and duals, result
timestamps and case identity must be recorded in
`VALIDATION_V14_2026-07-27.md` and `validation_results.json`.
