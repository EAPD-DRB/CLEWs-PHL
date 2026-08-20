# PHL_POW_HEAT assessment and implementation

Date: 2026-07-28

Case: `Philippines_v14_STOCK_TURNOVER`

## Decision

Remove `PHL_POW_HEAT` (`COM_te2a0`), `PHL_POW_HEAT1` (`COM_pesfw`) and
only the `PHL_POW_GEO_OLD` → `PHL_POW_HEAT` output link. Retain the
geothermal electricity output and all geothermal capacity, cost, lifetime,
availability and emissions parameters.

## Model evidence

- `PHL_POW_HEAT1` has no producer, consumer, demand or constraint link.
- `PHL_POW_HEAT` has one producer and no sink or demand.
- Its base-scenario geothermal-old OAR is 1 in mode 1 for every model year.
- The local commodity-balance inequality permits the output to be discarded.
- The pre-change v14 BASE result reports 60.8046 PJ in 2020, exactly equal to
  geothermal electricity activity; it is therefore an accounting duplicate,
  not observed useful heat.

## External evidence and boundary

The 2020 World Geothermal Congress Philippines update reports 1.87 MWt and
12.65 TJ/year of direct use in 2019, entirely bathing and swimming. It does
not support a national district-heating chain or a one-for-one power-plant
heat coproduct. DOE energy-balance documentation and IRENA's Southeast Asia
review likewise do not establish such a modeled market. Direct use is kept
outside this model boundary unless a future module provides site-specific
demand, resource temperature, delivery infrastructure, efficiency and cost
data.

## Reproducibility and safety

`remove_unused_heat_commodities` verifies exact IDs and exact structural
references, rejects any nonzero demand/profile value, applies the change to
`genData.json`, and passes it through `UpdateCase`. Structural validation then
requires the two IDs and all associated rows to be absent while every other
source parameter remains semantically unchanged. Solver validation and the
pre-change v14 A/B are recorded in `VALIDATION_V14_2026-07-27.md` and
`validation_results.json`.

## Promoted validation result

The live `BASE_V14` run is optimal with objective
`369630979.503002`. The pre-change control is preserved at
`Philippines_v14_STOCK_TURNOVER.backup-20260728T212440Z/BASE_V14` with
objective `369630979.50300163`. The difference is `3.5763e-07`
(`9.6753e-14%`).

The candidate has zero changed demand, emissions, fixed-cost,
annualized-investment-cost and capital-investment rows at the validation
tolerance. The 1,015 pre-change `PHL_POW_HEAT` production rows, totaling
3,814.257 PJ over the model horizon, are absent. CBC selected a different
cost-identical basis for some late-year dispatch and water routing; the exact
rows are retained in `validation_results.json`.
