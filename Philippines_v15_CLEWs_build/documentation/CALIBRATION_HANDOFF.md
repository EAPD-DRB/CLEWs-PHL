# Philippines calibration handoff

Philippines v15 is technically validated but not fully calibrated for every
sector. Existing v13/v14 changes and the v15 water formulation are part of the
current model; future calibration must begin from this complete v15 ledger and
append or supersede rows in place.

## Diagnostic gaps

| Sector/metric | Observed source ID | Geography/period/unit | Observed value | Model value | Difference | Suspected cause | Candidate future parameter | Applied in v15 |
|---|---|---|---:|---:|---:|---|---|---|
| Groundwater stock/depletion | See `GAPS.csv` | National/subnational | — | Flow ceiling only | Not comparable | Required hydrogeological observations absent | Aquifer stock/state formulation | No |
| Irrigation/public-water source shares | See `GAPS.csv` | National, historical | — | Endogenous | Not assessed | Demand and pumping calibration incomplete | Demand and pumping parameters | No |

## Data requested from national counterparts

| Dataset | Preferred institution | Definition needed | Model use | Priority |
|---|---|---|---|---|
| Aquifer properties and observed heads | MGB/NWRB | Area, thickness, storage coefficient, admissible drawdown, recharge and discharge | Groundwater stock/depletion model | High |
| Sectoral withdrawals and pumping energy | PSA/NWRB/DOE | Annual volume, source, sector and electricity consumption | Water-demand and pumping calibration | High |
| Missing inherited energy bibliography | Original model maintainers | Exact publication and table/row provenance | Complete inherited-sector trace | High |

## Calibration boundary

Create a new model version from the complete v15 package. Copy all six ledgers
and retained evidence first, carry unchanged rows forward, add new rows, and
supersede changed rows. A new release must never use “see v15 ledger” as a
substitute for carrying this provenance into itself.
