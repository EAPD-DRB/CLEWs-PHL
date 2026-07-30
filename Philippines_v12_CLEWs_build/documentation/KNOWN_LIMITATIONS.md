# Philippines v12 known limitations

These limitations are part of the model record. They should be checked before
using results in advice or presentations.

## Source traceability

- The inherited v10 energy system does not have a complete surviving
  row-level source register. Its model values and dated change records are
  preserved, but some original publications, calculations and analyst choices
  still need to be reconstructed. The consolidated register labels this gap
  explicitly instead of inventing citations.
- `MODEL_MAP.csv` now locates every populated in-scope raw-input row by file
  and CSV line and carries the best recoverable unit. That immediate lineage
  does not replace missing original publications, raw download manifests or a
  complete technology-specific unit dictionary; those items remain explicit
  in `GAPS.csv`.
- Several Fisheries engineering inputs retain legacy symbols (`S4`, `S6`–
  `S10`, `S12`, `S16`–`S17`) whose intended meaning is known but whose
  original publication identity is not. The v2.3 source register explains
  each one.
- The active Fisheries total uses a 240.0-ktoe DOE control total while a later
  DOE publication reports a revised 170.8-ktoe value for 2023. The later
  value is recorded as a conflict, not silently substituted.

## Representation and calibration

- The land–agriculture–water block has not been calibrated to observed
  historical land allocation, yields, irrigation withdrawals or water
  balances.
- Vegetable production uses the GAEZ tomato proxy. The “other crops” group is
  an aggregation.
- Crop-output demand grows with an SSP2 population series; this is a scenario
  rule, not an official Philippine crop forecast.
- Fisheries long-run demand paths, energy allocation and effective residual
  stock include explicit analyst assumptions documented in the data-source
  files.

## Attribution limits

- Crop technologies have no direct liquid-fuel input, and inherited
  agricultural motive fuel is not allocated by crop.
- Groundwater-pumping electricity cannot be attributed exactly to individual
  crops because all irrigated crops draw from one pooled agricultural-water
  commodity.

## Environmental accounting

- The unchanged source case has reporting-only accounts. The derived
  `Philippines_v12_ENV_LAND` case contains the exact land terminal, while
  water remains authoritative reporting-only accounting.
- An exact in-model water terminal is not possible with the installed
  technology-level user-defined constraint because each spatial cluster has
  mode-dependent water coefficients.
- The separate diagnostic case contains an unforced `ENV_WATER` sink. Its raw
  solver activity is usually zero or partial and is not the water account.
- The current diagnostic-case Pivot deliberately displays authoritative
  postprocessed `ENV_WATER` values instead of the unforced solver variable.
  Raw result CSVs remain unchanged for optimizer provenance.
- Re-solving regenerates the solver views. Run
  `scripts/publish_environmental_water_pivot.py` after every solve before
  interpreting `ENV_WATER` in Pivot.
- Adding the zero-cost land terminal and equality can select a different
  cost-identical solver basis. Fresh-control comparisons preserve the exact
  route-level differences; demand, emissions, costs, objectives and land-state
  accounts agree within their declared tolerances.
- Modeled groundwater and surface-water residuals are not estimates of
  sustainable yield, legal availability, accessibility, quality or ecological
  reserve.
- `DEMAGRGWTPHL` has no raw `PHL_WTR_GWT` input, so groundwater-irrigation
  activity does not reduce the raw-groundwater residual.
- Cost-identical solver bases can change the groundwater/surface-water split.
  In the fresh controls, the split changed by up to 21.1144 `10^9 m3`; the
  PEP liquid-water total changed by up to 0.5807 `10^9 m3`.
- Result CSVs round contributing rows to four decimal places. Terminal/source
  land reconciliation is accepted within 0.005 `10^3 km2`; stock-flow
  aggregation is accepted within 0.05 because it sums many rounded
  technology/mode/timeslice rows.
- Wastewater returns, desalination feedwater/brine, ecological reserves and
  energy-infrastructure land footprints remain data gaps and are not inferred.
