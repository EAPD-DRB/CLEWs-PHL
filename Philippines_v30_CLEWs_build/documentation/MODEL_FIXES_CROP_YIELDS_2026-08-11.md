# Philippines v16 crop-yield parameter repair

Date: 2026-08-11  
Change ID: `CHG_PHL_V16_CROP_YIELDS_20260811`

## Repair

The crop-land `OutputActivityRatio` values were dimensionally valid model
coefficients but represented GAEZ agro-climatically attainable potential, not
achieved national output per unit of farmed area. They have been replaced by
unit-matched 2020 achieved yields from frozen PSA OpenSTAT and retained
FAOSTAT observations.

Sugarcane now uses fresh-cane tonnes per harvested hectare rather than GAEZ
sugar-equivalent output. `CRPTOM` remains the existing `Other vegetables,
fresh n.e.c.` aggregate and uses an aggregate-matched FAOSTAT coefficient
rather than tomato dry matter. `CRPOTH` remains the existing five-component
aggregate. No new model object was required.

## Changed source parameters

| Source file | Change |
|---|---|
| `genData.json` | Commodity/technology descriptions only |
| `RYT.json` | Full-precision rainfed rice residual capacity |
| `RYTCM.json` | Existing crop OAR cells for all eight clusters, existing modes, and 2020-2053 |
| `RYTM.json` | Rice land-activity VC recalculated to preserve sourced PHP/kg cost |

Final crop demands, all input ratios, land/water limits, activity bounds,
shares, user-defined constraints, technologies, commodities, and modes are
unchanged. Observed crop area is a validation benchmark or initial stock, not
an imposed activity target.

## Validation record

The disposable candidate passed application generation, preprocessing,
GLPK matrix validation, a full CBC solve, MUIO result export, source-diff
guards, structural checks, production/area reconciliation, objective
comparison, emissions comparison, and timestamp/case identity checks.

- CBC status: optimal
- Disposable CBC wall time: 245.45 seconds
- Regenerated live BASE CBC wall time: 227.30 seconds; full chain 286.42 seconds
- Objective: 369,729,000.2004411 versus 369,729,128.8422815 BASE
- Objective change: -0.0000347935%
- Matrix: 791,109 rows; 884,956 columns; 12,552,173 nonzeros
- Annual technology emissions: unchanged row for row
- 2020 repaired crop areas: irrigated rice 2.00600 Mha; rainfed rice
  1.46545; corn 2.55378; coconut 3.65128; sugarcane 0.39908; other
  vegetables 0.63981; other crops 1.28390

The first 60-second diagnostic CBC run ended before feasibility and was not
used. The full solve completed normally within the established runtime
envelope.

The promoted live run reproduced the disposable candidate objective exactly,
matched all four promoted source hashes, retained zero annual-emission row
difference, and passed all six live-only checks in
`crop_yield_live_validation.json`.

## Provenance and limitations

The authoritative source rows, exact locators, hashes, definitions, formulas,
input values, mappings, assumptions, gaps, and change history are in:

- `Philippines_v16_CLEWs_build/data_sources/SOURCES.csv`
- `Philippines_v16_CLEWs_build/data_sources/CALCULATIONS.csv`
- `Philippines_v16_CLEWs_build/data_sources/ASSUMPTIONS.csv`
- `Philippines_v16_CLEWs_build/data_sources/MODEL_MAP.csv`
- `Philippines_v16_CLEWs_build/data_sources/GAPS.csv`
- `Philippines_v16_CLEWs_build/data_sources/CHANGES.csv`
- `Philippines_v16_CLEWs_build/data_sources/calculation_notes/crop_yields_v16_2026-08-11.md`

National yields are uniform across clusters because no compatible subnational
achieved-yield source is frozen. Spatial crop-water allocation is therefore
not calibrated. Irrigated-rice modeled water use changes materially through
endogenous cluster selection despite unchanged national irrigated area. This
is disclosed as a high-priority gap and is not forced with a spatial share.
