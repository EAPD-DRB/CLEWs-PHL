# ENV_WATER diagnostic experiment — 26 July 2026

The separate
`WebAPP/DataStorage/Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC` case retains
the exact `ENV_LAND` account and adds one unforced, three-mode `ENV_WATER`
technology:

| Mode | Input at IAR 1 | Meaning |
|---:|---|---|
| 1 | `PHL_WTR_EVT` | Water vapor returned |
| 2 | `PHL_WTR_GWT` | Modeled raw groundwater remaining |
| 3 | `PHL_WTR_SUR` | Modeled raw surface water remaining |

The terminal has no output, demand or `BAL_ENV_WATER` constraint. Its raw
solver activity is compared with:

```text
production by all technologies
  - use by every technology except ENV_WATER
```

Excluding `ENV_WATER` prevents its diagnostic consumption from being
subtracted twice.

Both Base and PEP solved optimally. Across 204 raw solver mode-year
comparisons, 194 are zero, seven partial and three complete within result
precision. This confirms that the unforced terminal is not an exact water
account.

Evidence:

- `diagnostics/environmental_accounting/2026-07-26_env_water_diagnostic_accounts/`
- `diagnostics/environmental_accounting/2026-07-26_env_water_diagnostic_validation/`
