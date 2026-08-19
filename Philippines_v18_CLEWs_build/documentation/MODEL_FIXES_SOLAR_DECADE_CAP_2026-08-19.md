# Philippines v18.0.1 solar construction ceiling, 2026-08-19

## Change

`TAMaxCI.SC_0` for `TEC_1k064 / PHL_POW_PP_SPV` is set to 4 GW/year in 2020-2025. The existing 4 GW/year values in 2026-2029 are unchanged, producing one consistent ceiling across 2020-2029.

| Years | Before | After |
|---|---:|---:|
| 2020-2025 | 999999 GW/year | 4 GW/year |
| 2026-2029 | 4 GW/year | 4 GW/year (unchanged) |

This extends the already documented 2026-2029 construction, financing, permitting, and grid-connection envelope across the full decade. It is a judgmental physical upper bound, not an observed-capacity target or a requirement to build solar. The model remains free to invest below it.

No solar minimum-investment value, residual capacity, total-capacity ceiling, scenario overlay, later-year band, or other technology was changed.

## Validation status

Only static JSON and schema-ledger validation was performed. At the user's request, application generation, preprocessing, LP generation, and optimization were not run. The change therefore remains `resolve_required` until the user regenerates and solves the case.

The existing portable MUIO archive was not repackaged.
