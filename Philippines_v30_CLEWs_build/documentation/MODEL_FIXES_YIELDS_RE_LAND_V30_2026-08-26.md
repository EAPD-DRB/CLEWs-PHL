# Philippines v30 crop-yield and renewable-land implementation

Date: 2026-08-26  
Parent: `Philippines_v29`  
Status: complete and validated; four scenarios solved optimally under the 300-second deadline

## Crop systems and yields

V29's physical cropland and shared irrigation structure is retained. V30 operates one full-cost management system for each crop and water regime: modes `1,3,4,5,6,8,10,11,16,19,22,24`. The twelve inherited low-input modes are operationally disabled with a `0.000001` thousand km2 upper bound. This is not a crop-share calibration: the optimizer remains free to choose crop, rainfed versus irrigated production, cluster, area and output. It removes only a high/low comparison that lacked paired Philippine yield-and-cost observations.

Only the active 2020 output ratios remain exactly the v24/v29 coefficients: the official Philippine production/area initialization normalized over the inherited GAEZ spatial pattern. From 2021 to 2050, each crop/water system follows the FAO *Future of Food and Agriculture 2050* Philippines Business As Usual yield index, rebased to its model 2020 value and linearly interpolated between FAO milestones. For 2051-2053 the published 2040-2050 annual slope continues. Thus observed 2021-2024 outcomes are not installed in the model; they remain out-of-sample checks. Restricted PSA palay and tomato microdata catalogs were inspected but not downloaded or redistributed; they are documented as future upgrade routes, not silently treated as evidence.

## Dynamic built-up land

No new land technology is created. The existing chain remains:

`PHL_LND -> LNDBLTTOT -> LBLTTOT -> LNDAGRPHLC01-08 mode 26 -> PHL_BUILT_SITE`.

Population, solar PV and onshore wind all consume `PHL_BUILT_SITE`. The exact annual equation, solved inside every scenario, is:

`BuiltActivity[y] = PopulationBuilt[y] + 0.012 * PVTotalCapacity[y] + 0.010 * WindTotalCapacity[y]`.

The factors are thousand km2/GW (1.2 ha/MW for PV and 1.0 ha/MW direct disturbance for wind). The population component follows the inherited v17 population-built path after removing the estimated 2020 renewable footprint. Its 2020 value is 10.24848616 thousand km2. Adding 2020 PV (1.01207 GW) and wind (0.4269 GW) reconstructs the observed 10.2649 thousand km2 exactly.

Because the equation uses total installed capacity, RE requires land during optimization and automatically differs by scenario. Built expansion consumes the national `PHL_LND` endowment and therefore competes with cropland and other convertible classes. A same-year equality UDC prevents unused surplus built-site production.

V30 also clears an obsolete policy-scenario override inherited from v28 that capped idle cropland at 5.2877 thousand km2. BASE already left this choice open. All scenarios now inherit the same open BASE bound, so policy cases are not forced to cultivate surplus land.

## Provenance and run boundary

All six authoritative v29 CSV ledgers and every retained evidence file were copied before adding v30 records. The audit found that v29's CSV ledger was complete, but its README still described v18 and no v29-formatted workbook had been produced. V30 replaces the README, corrects the inherited v29 completion status, and generates `PHILIPPINES_V30_CANONICAL_SCHEMA_LEDGER.xlsx` as a formatted view of the complete standalone CSV ledger.

The v30 pre-flight checks identifier integrity, scenario inheritance, exact land equations, 2020 reconstruction, crop-mode activation, unchanged observed yield anchors, removal of future yield growth, analytical land headroom, complete provenance and generated matrices. CBC has a hard 300-second limit per scenario and is never called by the builder or pre-flight.
