# Environmental-accounting diagnostics

- `2026-07-25_env_land_final/` is the current in-model `ENV_LAND`
  validation, including fresh-control regression reports.
- `2026-07-25_env_land_accounts/` is the current combined derived-case
  account delivery: in-model land, reporting-only water and native emissions.
- `2026-07-25_final/` is the earlier source-case reporting-only delivery.
- `2026-07-25_initial/` is retained pre-final evidence; it predates inclusion
  of the selected fresh-control SHA-256 manifest.

Reporting directories contain:

- `accounts.csv`: reporting-only `ENV_WATER`, derived liquid-water and land
  rows (in-model `ENV_LAND` for the derived-case delivery);
- `account_dictionary.csv`: stable mode mapping, units and meanings;
- `native_emissions.csv`: native annual `CO2e` and `PM2_5` totals;
- `validation.json`: graph, scenario, solver, closure, freshness,
  non-interference and unchanged-control evidence; and
- `summary.json`: compact machine-readable status.

Create a new derived-case reporting directory with:

```bash
python Philippines_v12_CLEWs_build/scripts/report_environmental_accounting.py \
  --model WebAPP/DataStorage/Philippines_v12_ENV_LAND \
  --label <unique-label>
```

After solving a fresh unchanged control, create land-terminal validation
evidence with:

```bash
PYTHONHASHSEED=0 python \
  Philippines_v12_CLEWs_build/scripts/validate_environmental_land_case.py \
  --label <unique-label>
```

Do not overwrite or hand-edit an earlier evidence directory.
