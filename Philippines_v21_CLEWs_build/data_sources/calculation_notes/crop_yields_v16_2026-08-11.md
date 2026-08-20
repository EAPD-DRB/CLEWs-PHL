# Philippines v16 achieved-crop-yield repair

Date: 2026-08-11
Change: `CHG_PHL_V16_CROP_YIELDS_20260811`

## Finding and physical interpretation

The crop-land technologies are conversion technologies whose activity is in
`1000 km2`. In the active OSeMOSYS commodity balance,
`OutputActivityRatio` multiplies that land activity to produce a crop
commodity in Mt. The inherited absolute coefficients were GAEZ
agro-climatically attainable potential yields, not observations of achieved
production per unit of farmed land. Using them as achieved yields preserved
national crop output because crop demand was unchanged, but assigned the
output to the wrong crop area.

Sugarcane and vegetables demonstrated a second defect rather than the same
potential-versus-achieved bias. The inherited GAEZ sugarcane layer is in kg
sugar/ha while `CRPSGC` demand is fresh cane. The inherited tomato layer is in
kg dry matter/ha while `CRPTOM` is the retained `Other vegetables, fresh
n.e.c.` aggregate. Both are repaired with definition-matched production and
area observations, not fitted scale factors.

`CRPTOM` and `CRPOTH` remain existing aggregate commodities. No technology,
commodity, mode, final demand, activity/share bound, or user-defined
constraint was added or changed.

## Observation classification

| Observation | Classification | Use |
|---|---|---|
| Crop production | Existing exogenous final-demand basis | Numerator of achieved yield; demand itself unchanged |
| Irrigated service area | Initial physical stock | Rice irrigated yield denominator and existing residual capacity |
| Rainfed/crop harvested or planted area | Benchmark-only physical-area proxy | Yield denominator; never an activity target |
| GAEZ attainable potential | Benchmark/ceiling evidence | Not used as absolute achieved OAR |
| Existing land and water limits | Continuing physical constraints | Unchanged |

## Frozen sources

- PSA OpenSTAT API snapshot: `snapshots/psa_openstat_agriculture_2020.json`
  (`SRC_PSA_OPENSTAT_AGRICULTURE_2020`). It retains table metadata, query
  results, retrieval timestamps, full-precision 2020 annual national values,
  and the four exact PXWeb endpoints.
- PSA *Selected Statistics on Agriculture and Fisheries 2022*:
  `SRC_PSA_SSAF_2022`, used for 2.006 Mha 2020 national irrigation service
  area and the already sourced rice production costs.
- Retained exact FAOSTAT selection: `SRC_FAOSTAT_PHL_SELECTION`, including
  source flags and the exact components of the existing aggregates.
- GAEZ raster manifest: `SRC_GAEZ_PHL_RASTER_MANIFEST`, which records the
  inherited attainable-potential layers and their sugar/tomato units.
- Curated unit-and-definition register: `snapshots/crop_yields_2020.json`
  (`SRC_PHL_V16_CROP_YIELD_INPUTS`).

## Calculations

One model activity unit is 1000 km2 = 100,000 ha and one crop-output unit is
Mt. Therefore:

`achieved yield [t/ha] = production [t] / area [ha]`

`OAR [Mt/(1000 km2)] = achieved yield [t/ha] / 10`

| Crop/regime | Production (t) | Area basis (ha) | OAR (Mt/1000 km2) | Ledger calculation |
|---|---:|---:|---:|---|
| Irrigated palay | 14,571,765.18 | 2,006,000 service area | 0.7264090319042872 | `CALC_PHL_V16_OAR_RICE_IRRIGATED` |
| Rainfed palay | 4,723,090.34 | 1,465,441.73 harvested-area proxy | 0.32229806503462954 | `CALC_PHL_V16_OAR_RICE_RAINFED` |
| Corn | 8,118,545.90 | 2,553,780.55 harvested area | 0.3179030359519341 | `CALC_PHL_V16_OAR_CORN` |
| Coconut with husk | 14,490,922.69 | 3,651,288.76 planted/harvested area | 0.3968714512187746 | `CALC_PHL_V16_OAR_COCONUT` |
| Fresh sugar cane | 24,398,941.25 | 399,086.05 planted/harvested area | 6.113704362755851 | `CALC_PHL_V16_OAR_SUGARCANE` |
| Other vegetables, fresh n.e.c. | 5,498,265.59 | 639,800 harvested area | 0.8593725523601126 | `CALC_PHL_V16_OAR_VEGETABLES` |
| Existing five-component other-crop aggregate | 10,099,485.12 | 1,283,887 summed component area | 0.7866334903305353 | `CALC_PHL_V16_OAR_OTHER_CROPS` |

The values are installed uniformly in all eight existing clusters and all
existing crop modes for 2020-2053. This is the smallest defensible repair
because the prior coefficients were also time-invariant and no compatible
subnational achieved-yield series has been frozen.

Rainfed and irrigated rice residual capacities are 14.6544173 and 20.06
`1000 km2`. Rice variable cost is expressed per unit of land activity, so the
source-backed PHP/kg values are preserved after the OAR change:

`VC = OAR * PHP/kg * 1000 kg/t / 49.25 PHP/USD`

This gives 91.29051791336207 for rainfed modes and 184.22028037532075 million
USD per `1000 km2` for irrigated modes.

## Source-file changes

- `genData.json`: description metadata only, clarifying fresh cane, coconut
  with husk, the retained vegetables aggregate, and the retained other-crop
  aggregate.
- `RYT.json`: full-precision rainfed rice residual capacity; irrigated rice
  remains 20.06.
- `RYTCM.json`: 192 existing OAR rows / 6,528 annual cells.
- `RYTM.json`: 1,088 existing rice variable-cost cells to preserve PHP/kg.

The source manifest is `snapshots/crop_yield_calibration_manifest.json`.

## Validation

The repair was first applied to the disposable case
`.Philippines_v16-crop-yields` and generated through
`DataFile.generateDatafile()` and `.preprocessData()`.

- YAML environment preflight: passed (`PyYAML 6.0.3`).
- Deterministic source diff and non-forcing guards: passed.
- GLPK model/matrix check: passed; 791,109 rows, 884,956 columns,
  12,552,173 matrix nonzeros, and 422,220 objective-row nonzeros.
- Initial 60-second bounded CBC diagnostic: timed out before a feasible
  solution, consistent with the established multi-minute runtime; no result
  from that diagnostic was used.
- Full CBC: optimal; 245.45 wall seconds; no primal infeasibility.
- MUIO CSV and Results Viewer export: passed.
- Eleven deterministic and result checks: passed in
  `snapshots/crop_yield_validation.json`.
- Promoted live BASE regeneration: passed; CBC wall 227.30 seconds and full
  application chain 286.42 seconds.
- Six live-only source, solver, objective, area, emissions, and freshness
  checks: passed in `snapshots/crop_yield_live_validation.json`.

| Crop/regime | Previous 2020 area (Mha) | Repaired 2020 area (Mha) | Observed basis (Mha) |
|---|---:|---:|---:|
| Irrigated rice | 2.00600 | 2.00600 | 2.00600 |
| Rainfed rice | 0.87965 | 1.46545 | 1.46544173 |
| Corn | 0.97814 | 2.55378 | 2.55378055 |
| Coconut | 3.12499 | 3.65128 | 3.65128876 |
| Sugarcane | 2.21809 | 0.39908 | 0.39908605 |
| Other vegetables | 1.22184 | 0.63981 | 0.63980 |
| Other crops | 1.54928 | 1.28390 | 1.283887 |

The objective changed from 369,729,128.8422815 to 369,729,000.2004411
(-0.0000347935%). Annual technology emissions were unchanged row for row.
Crop output remained at the existing demand basis; displayed differences are
only the four-decimal CSV exporter rounding.

## Disclosed limitations

The correction makes national crop output per unit of area definitionally
and numerically coherent. It does not calibrate spatial crop allocation.
Uniform national yields leave cluster selection endogenous against
heterogeneous water and land coefficients. In the disposable result,
irrigated-rice `AGRWATPHL` use changed from 13.1820 to 0.4332 model water
units even though irrigated area stayed 2.006 Mha. This is recorded as a
high-priority spatial crop-water gap; imposing a cluster or water share would
hide the missing driver and is not an acceptable remedy.

Harvested area may count multiple annual crops on one physical hectare, and
the retained `CRPTOM`/`CRPOTH` aggregates do not resolve component-mix change.
These limitations are recorded in `GAPS.csv`.
