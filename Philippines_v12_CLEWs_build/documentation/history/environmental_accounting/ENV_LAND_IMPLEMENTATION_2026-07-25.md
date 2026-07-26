# ENV_LAND implementation record — 25 July 2026

## Decision

The earlier reporting-only implementation treated failure of the water-domain
exactness proof as a reason not to add either environmental terminal. The
method was reassessed by domain. The water proof still fails, but the land
proof passes.

The source `Philippines_v12` case remains unchanged. A reproducible derived
case, `Philippines_v12_ENV_LAND`, now contains exact in-model land accounting.

## Additions

- one `ENVIRONMENT` technology group;
- seven parallel land-stock commodities;
- parallel OAR 1 stock outputs on six land-cover and 24 crop-land
  technologies;
- one `ENV_LAND` terminal with modes 1–8;
- one equality UDC, `BAL_ENV_LAND`;
- complete MUIO parameter rows for all years, timeslices, modes and scenarios;
  and
- regenerated Base and PEP solver, CSV and Pivot results.

The exact aggregate coefficients are `+1` for `MINLNDTOT` and `−1` for
`ENV_LAND`. Every represented land technology has land-domain net coefficient
zero because it consumes one unit of `PHL_LND` and produces one unit of its
parallel stock.

## Validation

Evidence is under
`diagnostics/environmental_accounting/2026-07-25_env_land_final/`.

- 25/25 checks pass.
- Both candidate and fresh-control Base/PEP runs are optimal.
- Maximum terminal/source land difference: 0.0003 `10^3 km2`.
- Maximum aggregate closure difference: 0.0001 `10^3 km2`.
- `BAL_ENV_LAND` result: exactly zero in every year.
- Maximum stock production/use difference: 0.0042 `10^3 km2`.
- Demand, emissions, all cost invariants and objective agree with the fresh
  controls within tolerance.

Eleven route-level result files differ because the added zero-cost accounting
variables select another cost-identical basis. The full row-level reports are
retained and the results are not described as row-for-row unchanged.

## Water

`ENV_WATER` remains absent. All three connected water streams have
mode-dependent coefficients, with a maximum within-technology combined spread
of 0.447. The reporting-only water accounts remain the exact available
implementation under the installed technology-level UDC.

## Skill review

The implementation exposed an ambiguity in the environmental-accounting
skill: the proof was defined for domain `D`, but several later requirements
used all-or-nothing wording for the two terminals. The skill and its MUIO JSON
workflow reference were updated to require independent water/land decisions
and permit a documented mixed architecture when only one domain passes.
