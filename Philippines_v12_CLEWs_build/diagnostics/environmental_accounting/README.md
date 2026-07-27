# Environmental-accounting diagnostics

- `2026-07-26_env_water_pivot_published/` is the current authoritative
  `ENV_WATER` Results Pivot publication. It contains publication/validation
  manifests, the timeslice reference and a backup of the four original
  solver-generated Pivot files. The GitHub delivery stores that backup as
  `solver_generated_view_backup.zip` because one uncompressed view exceeds
  GitHub's individual-file limit; local publisher runs retain the directory.
- `2026-07-26_env_water_diagnostic_validation/` validates the separate
  unforced `ENV_WATER` experiment against the exact-land baseline.
- `2026-07-26_env_water_diagnostic_accounts/` contains the authoritative
  diagnostic-case ledger and raw terminal reconciliation.
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

The Pivot-publication directory additionally contains:

- `publication.json`: source, backup and published SHA-256 manifests;
- `timeslice_reference.csv`: the detailed production-minus-ordinary-use
  calculation; and
- `solver_generated_view_backup/` or its distribution ZIP: the original
  `RT.json`, `RYTM.json`, `RYTMTs.json` and `RYTCMTs.json`.

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

After every diagnostic-case solve, publish the authoritative reference into
the linked `ENV_WATER` Results Pivot variables with:

```bash
PYTHONHASHSEED=0 python \
  Philippines_v12_CLEWs_build/scripts/publish_environmental_water_pivot.py \
  --label <unique-label>
```

Use `--dry-run` to calculate and validate without changing view files. The
publisher leaves raw solver CSVs and model JSON unchanged.

Do not overwrite or hand-edit an earlier evidence directory.
