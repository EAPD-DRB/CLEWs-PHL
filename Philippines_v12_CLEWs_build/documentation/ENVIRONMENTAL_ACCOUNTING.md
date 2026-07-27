# Philippines v12 environmental accounting

Philippines v12 uses a **hybrid environmental-accounting architecture**:

- land is represented in-model by the exact eight-mode `ENV_LAND` terminal in
  the derived `Philippines_v12_ENV_LAND` case;
- water remains authoritative reporting-only accounting because an exact
  `ENV_WATER` terminal cannot be expressed by the installed technology-level
  user-defined constraint (UDC);
- a separate diagnostic case retains unforced `ENV_WATER` in the Dynamic Graph
  and publishes the authoritative reporting reference into its linked Results
  Pivot variables after optimization; and
- `CO2e` and `PM2_5` remain in the native emissions mechanism.

The source `WebAPP/DataStorage/Philippines_v12` case is unchanged. The
reproducible derived case is:

```text
WebAPP/DataStorage/Philippines_v12_ENV_LAND
```

It contains 173 technologies, 99 commodities and four UDCs, compared with
172, 92 and three in the source case.

The separate diagnostic case is:

```text
WebAPP/DataStorage/Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC
```

It contains 174 technologies, 99 commodities and the same four UDCs. Its
`ENV_WATER` technology has no forcing UDC. The current Pivot values are
postprocessed reporting results; raw optimizer results remain in the saved
CSVs.

## Current evidence

- Authoritative `ENV_WATER` Pivot publication and solver-view backup:
  `diagnostics/environmental_accounting/2026-07-26_env_water_pivot_published/`
- Raw diagnostic-terminal validation:
  `diagnostics/environmental_accounting/2026-07-26_env_water_diagnostic_validation/`
- Diagnostic-case account ledger and raw terminal reconciliation:
  `diagnostics/environmental_accounting/2026-07-26_env_water_diagnostic_accounts/`
- Land-terminal validation:
  `diagnostics/environmental_accounting/2026-07-25_env_land_final/`
- Derived-case account ledger and native emissions:
  `diagnostics/environmental_accounting/2026-07-25_env_land_accounts/`
- Earlier source-case reporting delivery:
  `diagnostics/environmental_accounting/2026-07-25_final/`

The land validation contains 25 passing checks, the eight-mode account ledger,
fresh-control manifests and full per-variable Base/PEP regression reports.
The diagnostic validation contains 18 passing checks. The Pivot publication
contains raw-result and view manifests, a detailed timeslice reference,
linked-variable validation and a backup of the solver-generated views.

## Rebuild, solve and validate

Audit without writing:

```bash
PYTHONHASHSEED=0 python \
  Philippines_v12_CLEWs_build/scripts/generate_environmental_land_case.py \
  --dry-run
```

Create the derived case when the target does not already exist:

```bash
PYTHONHASHSEED=0 python \
  Philippines_v12_CLEWs_build/scripts/generate_environmental_land_case.py
```

Replacing an existing derived case requires the explicit `--overwrite` flag.
The generator promotes an independently validated staged case and retains the
old target as a timestamped backup.

Generate and solve the two existing case definitions:

```bash
PYTHONHASHSEED=0 python \
  Philippines_v12_CLEWs_build/scripts/solve_muiogo_case.py \
  Philippines_v12_ENV_LAND Base_v12 \
  --case-id CS_PHL_V12_BASE_ENVLAND --reuse-existing

PYTHONHASHSEED=0 python \
  Philippines_v12_CLEWs_build/scripts/solve_muiogo_case.py \
  Philippines_v12_ENV_LAND PEP_v12 \
  --case-id CS_PHL_V12_PEP_ENVLAND --reuse-existing
```

After solving a fresh unchanged control as described below, validate:

```bash
PYTHONHASHSEED=0 python \
  Philippines_v12_CLEWs_build/scripts/validate_environmental_land_case.py \
  --label <unique-label>
```

Create the combined derived-case account report:

```bash
python Philippines_v12_CLEWs_build/scripts/report_environmental_accounting.py \
  --model WebAPP/DataStorage/Philippines_v12_ENV_LAND \
  --label <unique-label>
```

Generate or audit the separate diagnostic case with:

```bash
PYTHONHASHSEED=0 python \
  Philippines_v12_CLEWs_build/scripts/generate_environmental_water_diagnostic_case.py \
  --dry-run
```

After solving its Base and PEP cases, generate the ledger and publish the
authoritative reporting reference into Pivot:

```bash
python Philippines_v12_CLEWs_build/scripts/report_environmental_accounting.py \
  --model \
  WebAPP/DataStorage/Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC \
  --label <unique-label>

PYTHONHASHSEED=0 python \
  Philippines_v12_CLEWs_build/scripts/publish_environmental_water_pivot.py \
  --label <unique-label>
```

Use `--dry-run` on the publisher to validate without changing view files. Do
not hand-edit generated `data.txt`, solver output, result CSV files or Pivot
files. The publisher is the only documented Pivot transformation; it
preserves the raw CSVs and backs up the original generated views.

## Why land can be in-model but water cannot

The exactness proof is evaluated independently for each environmental domain.

### Land proof

The source land commodity `PHL_LND` has:

- one producer, `MINLNDTOT`, with Output Activity Ratio (OAR) 1 in mode 1;
- 30 consumers—the six land-cover and 24 crop-land technologies—with Input
  Activity Ratio (IAR) 1 in mode 1;
- no annual or accumulated demand;
- no input-to-new-capacity or input-to-total-capacity term; and
- no policy-scenario ratio override.

The derived case adds one parallel area-stock output at OAR 1 to every
represented land technology. These outputs preserve the original crop,
pasture, water and other service links; they do not compete with them.

Across `PHL_LND` and the seven parallel stocks:

- `MINLNDTOT` has net coefficient `+1`;
- every represented land technology has net coefficient `−1 + 1 = 0`; and
- every `ENV_LAND` mode has net coefficient `−1`.

The installed technology-level UDC can therefore represent the exact annual
identity:

```text
TotalTechnologyAnnualActivity(MINLNDTOT)
  - TotalTechnologyAnnualActivity(ENV_LAND)
  = 0
```

Individual commodity-balance inequalities make every category residual
nonnegative. The aggregate equality sets their sum to zero, forcing each
`ENV_LAND` mode to consume its complete mapped land stock or residual.

`ENV_LAND` residual capacity, annual activity and model-period activity bounds
are derived from the finite `MINLNDTOT` bounds (`999999`) and are nonbinding:
the largest solved annual terminal total is 295.8132 `10^3 km2`. New terminal
investment is prohibited.

### Water failure

`LNDAGRPHLC01` through `LNDAGRPHLC08` operate in 30 modes. Their
evapotranspiration, raw-groundwater and raw-surface-water coefficients all
vary by mode. For `LNDAGRPHLC07`, for example:

| Mode | Surface water | Groundwater | Evapotranspiration | Total |
|---:|---:|---:|---:|---:|
| 6 | 1.800 | 0.095 | 0.910 | 2.805 |
| 23 | 1.600 | 0.088 | 0.670 | 2.358 |

The largest within-technology combined spread is 0.447. The installed UDC
multiplier is indexed by technology and year:

```text
alpha[t,y] × TotalTechnologyAnnualActivity[t,y]
```

It cannot reproduce:

```text
sum[m] beta[t,m,y] × TotalAnnualTechnologyActivityByMode[t,m,y]
```

An exact in-model `ENV_WATER` would therefore be plausible-looking but
inexact. Water must remain authoritative reporting-only accounting until MUIO
supports a reviewed technology-mode-year constraint multiplier or equivalent
formulation.

### Diagnostic terminal and Pivot publication

The diagnostic case adds `ENV_WATER` without claiming an exact solver
identity:

- mode 1 consumes `PHL_WTR_EVT` at IAR 1;
- mode 2 consumes `PHL_WTR_GWT` at IAR 1;
- mode 3 consumes `PHL_WTR_SUR` at IAR 1; and
- it has no output, demand, water-balance UDC or cost.

The ordinary commodity-balance inequality permits unused production, so the
raw optimizer terminal is usually zero or partial. The reporter instead
calculates:

```text
authoritative reference
  = production by all technologies
  - use by every technology except ENV_WATER
```

Excluding `ENV_WATER` prevents double subtraction. The Pivot publisher repeats
this calculation by timeslice and updates only the terminal's generated view
rows. It leaves the optimization model and raw result CSVs untouched.

## Account dictionary

All results use region `RE1`.

### Land: in-model `ENV_LAND`

Every mode uses `10^3 km2`.

| Mode | Account | Terminal input | Physical source |
|---:|---|---|---|
| 1 | Forest | `ENV_LND_FOREST` | `LNDFORTOT` parallel stock |
| 2 | Grassland | `ENV_LND_GRASSLAND` | `LNDGRSTOT` parallel stock |
| 3 | Other land | `ENV_LND_OTHER` | `LNDOTHTOT` parallel stock |
| 4 | Barren or savannah | `ENV_LND_BARREN` | `LNDBARTOT` parallel stock |
| 5 | Built-up land | `ENV_LND_BUILT` | `LNDBLTTOT` parallel stock |
| 6 | Inland water bodies | `ENV_LND_WATER` | `LNDWATTOT` parallel stock |
| 7 | Cropland | `ENV_LND_CROPLAND` | Parallel stocks from 24 crop-land options |
| 8 | Unallocated modeled land | `PHL_LND` | Endowment remaining after modeled land use |

“Other land” retains the upstream definition and is not assumed to be
forest-suitable. Grassland is environmentally present but human-influenced.
The terminal reports modeled land state; it does not establish ecological
condition or protection status.

`PHL_POW_PP_SPV_T1` lists `PHL_LND` in metadata but has zero land IARs. No
solar photovoltaic land footprint was invented.

### Water: authoritative reporting account

Every water row uses `10^9 m3`.

| Reporting mode | Account | Calculation |
|---:|---|---|
| 1 | Water vapor returned | Production of `PHL_WTR_EVT` less use |
| 2 | Modeled raw groundwater remaining | Production of `PHL_WTR_GWT` less modeled use |
| 3 | Modeled raw surface water remaining | Production of `PHL_WTR_SUR` less modeled use |
| — | Modeled raw liquid water remaining | Mode 2 plus mode 3 |

In the diagnostic case, these authoritative values appear under the existing
`ENV_WATER` name in Pivot after publication. This is a reporting-layer result,
not the raw solver activity of the unforced terminal.

Mode 1 is evapotranspiration returned to the atmosphere, not useful liquid
water. Modes 2 and 3 are residuals in modeled raw resource pools. They are not
sustainable yield, legal availability, accessible supply, water quality or
ecological reserve.

`DEMAGRGWTPHL` produces the pooled agricultural-water commodity but has no
`PHL_WTR_GWT` input. Its activity therefore does not reduce the raw-groundwater
residual. This remains a model-structure limitation.

### Native emissions

The reporter aggregates existing annual technology emissions for `CO2e` and
`PM2_5`. No new factor, gas disaggregation or land-use-change emission is
introduced. Native unit metadata is `MTon`.

## Viewing the accounts

### MUIO Dynamic Graph

Open `Philippines_v12_ENV_LAND`. Each represented land technology has an
additional parallel output to an `ENV_LND_*` commodity, which connects to the
corresponding `ENV_LAND` mode. Mode 8 consumes residual `PHL_LND`. Original
crop and land-cover service links remain present.

Open `Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC` to see `ENV_WATER`. Its three
water inputs remain visible because the Dynamic Graph reads `genData.json`,
which the publisher does not change.

### MUIO Pivot

Select **Total Annual Technology Activity By Mode**, filter `Tech` to
`ENV_LAND`, and include `Mo Id`. The generated Pivot data are stored under
`TATABM` in `view/RYTM.json`; Base and PEP each expose modes 1–8.

In the diagnostic case, filter `Tech` to `ENV_WATER`:

- **Total Technology Model Period Activity** shows published `TTMPA`;
- **Total Annual Technology Activity By Mode** shows published `TATABM`;
- **Rate Of Activity** shows published `ROA`;
- **Rate Of Use By Technology By Mode** shows published `ROUBT`; and
- **Use By Technology By Mode** shows published `UBT`.

`Production By Technology By Mode` and its rate remain zero because
`ENV_WATER` has no output. The raw solver-selected terminal behavior remains
available in
`2026-07-26_env_water_diagnostic_accounts/water_terminal_reconciliation.csv`
and the solver-view backup.

## Validation results

Both candidate and fresh unchanged-control runs solved optimally:

| Run | Candidate objective | Fresh-control objective | Absolute difference |
|---|---:|---:|---:|
| Base | 375,930,821.34054434 | 375,930,821.3405436 | 0.00000072 |
| PEP | 375,953,763.45952636 | 375,953,763.4595314 | 0.00000507 |

Physical validation:

- terminal modes are exactly 1–8;
- maximum terminal-to-source land difference is 0.0003 `10^3 km2`;
- maximum aggregate land-closure difference is 0.0001 `10^3 km2`;
- the reported `BAL_ENV_LAND` value is exactly zero for every year;
- maximum stock production/use difference is 0.0042 `10^3 km2`, reflecting
  four-decimal CSV aggregation; and
- fresh-control and candidate land-state accounts agree within 0.0003
  `10^3 km2`.

Demand, native emissions, fixed cost, variable cost, investment cost, capital
investment, emissions penalty, salvage value and objective all agree with the
fresh unchanged controls within declared tolerances.

Eleven route-level result files differ because the added zero-cost accounting
variables and equality select another cost-identical basis. These include
activity, production/use, capacity and the commodity-balance diagnostic. Full
changed keys and magnitudes are retained in `regression_Base_v12.json` and
`regression_PEP_v12.json`. They are not described as row-for-row unchanged.

The candidate matrix is larger because MUIO creates annual, timeslice and
capacity equations for the new technology and seven commodities:

| Run | Rows: control | Rows: candidate | Columns: control | Columns: candidate |
|---|---:|---:|---:|---:|
| Base | 769,139 | 794,437 | 860,236 | 884,377 |
| PEP | 769,154 | 794,452 | 860,236 | 884,377 |

Single-run wall times were about 263/449 seconds for the controls and 354/536
seconds for the candidates. These are retained as observations, not a formal
performance benchmark.

### ENV_WATER diagnostic and published Pivot

Both diagnostic runs solved optimally. The raw unforced terminal was zero in
194 of 204 mode-year comparisons, partial in seven and complete within result
precision in three. This raw behavior remains preserved rather than being
described as exact accounting.

The authoritative Pivot publication passed:

- maximum annual Pivot-to-reporter difference:
  `0.00000000000104`;
- annual activity-to-published-use difference: exactly `0`;
- timeslice activity-rate to water-use-rate difference: exactly `0`;
- model-period reconciliation difference: exactly `0`;
- maximum annual difference reconstructed from rounded rates:
  `0.00001935234`;
- all non-`ENV_WATER` Pivot values unchanged; and
- Dynamic Graph source and terminal connections unchanged.

Example published 2020 values in `10^9 m3`:

| Run | Vapor | Groundwater | Surface water |
|---|---:|---:|---:|
| Base | 404.9373 | 20.2706 | 257.4726 |
| PEP | 404.9371 | 20.2706 | 257.4725 |

The model-period totals are 22,439.5632 for Base and 21,168.5896 for PEP. The
publication took 13.5 seconds for both runs and required no additional solve.

## Reproducing the fresh unchanged control

The validation used
`WebAPP/DataStorage/Philippines_v12_ENV_LAND_Control_20260725`:

```bash
mkdir -p WebAPP/DataStorage/Philippines_v12_ENV_LAND_Control_20260725
rsync -a --exclude res \
  WebAPP/DataStorage/Philippines_v12/ \
  WebAPP/DataStorage/Philippines_v12_ENV_LAND_Control_20260725/
mkdir -p \
  WebAPP/DataStorage/Philippines_v12_ENV_LAND_Control_20260725/res/Base_v12/csv \
  WebAPP/DataStorage/Philippines_v12_ENV_LAND_Control_20260725/res/PEP_v12/csv

PYTHONHASHSEED=0 python \
  Philippines_v12_CLEWs_build/scripts/solve_muiogo_case.py \
  Philippines_v12_ENV_LAND_Control_20260725 Base_v12 \
  --case-id CS_PHL_V12_ENVLAND_CONTROL_BASE --reuse-existing

PYTHONHASHSEED=0 python \
  Philippines_v12_CLEWs_build/scripts/solve_muiogo_case.py \
  Philippines_v12_ENV_LAND_Control_20260725 PEP_v12 \
  --case-id CS_PHL_V12_ENVLAND_CONTROL_PEP --reuse-existing
```

The control's selected source manifest matches the source exactly. Its Base
and PEP `data.txt` hashes also match the saved source inputs.

## Example land accounts

| Run | Year | Forest | Built-up | Water bodies | Cropland | Unallocated |
|---|---:|---:|---:|---:|---:|---:|
| Base | 2020 | 179.7818 | 0.7698 | 1.5984 | 113.6631 | 0.0000 |
| Base | 2053 | 136.5595 | 1.0458 | 1.5984 | 156.6094 | 0.0000 |
| PEP | 2020 | 179.7818 | 0.7698 | 1.5984 | 113.6631 | 0.0000 |
| PEP | 2053 | 136.5595 | 1.0458 | 1.5984 | 156.6094 | 0.0000 |

Grassland, other land and barren/savannah are zero in these displayed rows
but remain explicit modes.

## Data gaps not filled

- Groundwater irrigation lacks a raw-groundwater input link.
- Wastewater return fractions and destinations are unavailable.
- Desalination feedwater, recovery and brine coefficients are unavailable.
- Ecological reserves, sustainable yield, accessibility and water quality are
  not modeled.
- Energy-infrastructure land-footprint coefficients are unavailable.
- The inherited v10 energy system still has incomplete row-level source
  traceability.

No coefficient or constraint was invented to fill these gaps.
