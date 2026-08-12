# Philippines v17 CLEWs model

Philippines v17 is the current whole-country model. It carries the complete v16
model, provenance ledger, and retained evidence forward, then adds a closed
2020 national land account from the PSA/NAMRIA Land Asset Accounts. Existing
`LNDOTHTOT` mode 2 represents endogenous idle/fallow cropland; no technology,
commodity, user constraint, or global mode was added. Forest `VC=-10` is
unchanged. A Philippine policy-rate forest-expansion envelope capped to the
documented forest-suitable 80 percent of brush, a reconciled true-grassland
reserve, central population-urbanization built-up growth, fixed water/barren/
fishpond classes, a 2020 total-cropland floor, and an operationally zero
unallocated ceiling prevent physically implausible land transitions.

Philippines v15 is the validated whole-country MUIO/MUIOGO case that adds a
national precipitation and renewable-water envelope to the Philippines v14
stock-turnover model. The unchanged v14 case is the formal solve baseline; the
v12 build package remains in this repository as inherited lineage and
reproduction evidence.

## Delivered model

- Portable editable case: `muio/Philippines_v17_v17.0.0_MUIO.zip`
- Archive checksum: `muio/SHA256SUMS`
- Case identity: `Philippines_v17`
- Validated run identity: `LAND_SAFEGUARDS_CENTRAL_COMPLETE`
- Horizon: 2020-2053

Extract the `Philippines_v17` folder into
`MUIOGO/WebAPP/DataStorage/`. Generated solver inputs and the 1.3 GB runtime
result directory are intentionally excluded; regenerate them through the
normal MUIOGO application chain.

The original v15 package remains recoverable from Git tag `v15.0.0`; its
archive is also retained here as predecessor evidence.

## Water formulation

- The inherited national hydrology coefficients are rebased to the World Bank
  CCKP ERA5 1991-2020 precipitation normal.
- A single CMIP6 SSP2-4.5 ensemble-median precipitation pathway is installed.
  Retained p10/p90 values are evidence only, so users choose which additional
  scenarios to construct.
- `DEMAGRGWTPHL` consumes raw groundwater one-for-one in its active mode.
- `WATER_SUR_AVAIL` and `WATER_GWT_POTENTIAL` constrain annual gross
  withdrawals from the three corresponding single-mode pass-throughs.
- The ordinary annual commodity balances independently prevent withdrawal
  above modeled raw-water production.

These are national potential-flow sensitivity ceilings. They are not basin
allocations, dependable yield, environmental-flow-adjusted availability,
aquifer storage, or groundwater safe yield. Neither ceiling binds in
`BASE_V15`.

## Source trace

The six canonical, cumulative CSV ledgers are under `data_sources/`:

- `SOURCES.csv`: 123 source and retained-evidence records;
- `CALCULATIONS.csv`: 110 calculations;
- `ASSUMPTIONS.csv`: 76 explicit modeling assumptions;
- `MODEL_MAP.csv`: 72,013 inherited and version-specific mappings;
- `GAPS.csv`: 39 unresolved evidence needs; and
- `CHANGES.csv`: 19 implementation and documentation records.

`data_sources/PHILIPPINES_V17_CANONICAL_SCHEMA_LEDGER.xlsx` is the current
formatted review copy; the CSV files are authoritative. The package carries the complete
inherited-base ledger, v13 calibration record, all 3,253 v14 cell changes, and
the v15 water addition. No earlier installed case or ledger is required.
The complete water pathway and equation map are in
`data_sources/calculation_notes/national_water_v15.md`.
The irrigated-rice engineering-water correction is in
`data_sources/calculation_notes/irrigation_water_engineering_v16_2026-08-11.md`.
The current achieved-crop-yield pathway and equation map are in
`data_sources/calculation_notes/crop_yields_v16_2026-08-11.md`.
The renewable naming, offshore wind, geothermal and onshore wind pathway is in
`data_sources/calculation_notes/energy_inputs_v16_2026-08-11.md`.
The national land-cover pathway is in
`data_sources/calculation_notes/land_cover_v17_2026-08-12.md`.

## Validation

The v17 `LAND_SAFEGUARDS_CENTRAL_COMPLETE` run solved optimally at objective
369740345.77061987; CBC wall time was 304.58 seconds. The 2020 account closes to
295.8131 thousand km2 with zero unallocated land. Productive cropland remains
119.9928 thousand km2 and existing `LNDOTHTOT` mode 2 supplies 5.2877 thousand
km2 of idle/fallow land and that bookkeeping route never exceeds its base stock.
Forest rises by no more than 2.5 thousand km2 in any solved year, peaks at
105.2568 thousand km2 in 2034, remains below the 118.81476 forest-only ceiling,
and remains above its 2020 floor. Built-up follows the central path to 15.4217
thousand km2 in 2050. Fixed water/barren/fishpond classes, the true-grassland
reserve, cropland floor and all-year zero-unallocated rule all pass. Exact source regressions confirm unchanged demand,
emissions, energy capacity/cost inputs, time-sliced energy parameters, user
constraints, and the complete `VC` parameter. See
`data_sources/snapshots/land_cover_validation.json` and
`documentation/MODEL_FIXES_LAND_COVER_2026-08-12.md`.

Against the immediately preceding safeguarded v17 solve, final demand,
annual technology emissions, total capacity and new capacity are unchanged.
The objective is 1,032.0577 lower (-0.000279%). Aggregate non-land variable
cost changes by 0.0489 model cost units over the full horizon (0.0000136%);
larger row-level activity differences are alternative allocations among
degenerate precipitation, water-source, fuel-supply and industrial routes,
not new capacity, demand or emissions outcomes.

The transition inputs, calculations, exact source locators and limitations are
frozen in `data_sources/snapshots/land_transition_safeguards.json`.

The promoted case completed application generation, preprocessing,
`glpsol --check`, LP inspection, a bounded CBC diagnostic, full CBC
optimization, result export, and comparison with the unchanged v14 baseline.

- status: optimal;
- objective: 369630979.62464261;
- CBC solve time: 219.681299 seconds;
- matrix: 791109 rows, 884956 columns, 12533783 nonzeros;
- maximum exact UDC residual: 0.00000390000001 km3/year;
- final-demand changed rows: 0; and
- emission changed rows: 0.

The v16 canonical validator checks the generic schema, every retained-evidence
manifest entry, the current model archive, cumulative lineage coverage and the
absence of external installed-case dependencies. See `diagnostics/` and
`documentation/MODEL_FIXES_WATER_2026-08-04.md`.

The 2026-08-11 crop-yield candidate separately passed source-diff and
non-forcing guards, application generation, preprocessing, GLPK matrix check,
full CBC optimization, result export, and BASE comparison. It solved optimally
in 245.45 seconds at objective 369729000.2004411. The matrix has 791109 rows,
884956 columns, and 12552173 nonzeros; annual technology emissions were
unchanged. See `data_sources/snapshots/crop_yield_validation.json`.

The 2026-08-11 energy-input candidate also passed source-scope and non-forcing
guards, application generation, preprocessing, GLPK matrix checking, full CBC
optimization and BASE comparison. It solved optimally in 215.64 seconds at
objective 369730088.2957073. Offshore wind remained endogenous and was not
built; positive reduced costs show that the remaining no-build result is not
caused by the corrected capacity factor. See
`data_sources/snapshots/energy_input_validation.json`.
The promoted source was then regenerated independently as
`Philippines_v16/ENERGY_INPUTS_BASE`; it solved optimally at
369730088.29570782 in 334.14 seconds and reproduced the candidate objective
within 0.00000053. See
`data_sources/snapshots/energy_input_live_validation.json`.

The 2026-08-11 irrigated-rice engineering-water correction changed only 544
`IAR` cells in `RYTCM.json`; no object, demand, activity bound, share, or user
constraint was added. The matched candidate and promoted live runs both solved
optimally on the unchanged 791109 by 884956 matrix. Live 2020 rice irrigation
is 41.6286 km3, or 20752 m3/ha/year. See
`data_sources/snapshots/irrigation_water_live_validation.json` and
`documentation/MODEL_FIXES_IRRIGATION_WATER_2026-08-11.md`.

## Reproduction scripts

The exact MUIOGO generator and validator used for v15 are retained under
`scripts/`, along with the v16 packaging validator. The normalized research
input remains under `scripts/data/`. See `scripts/README.md`.
