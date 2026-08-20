# MODEL FIX: irrigated-rice water engineering coefficients

Date: 2026-08-11  
Change ID: `CHG_PHL_V16_IRRIGATION_ENGINEERING_20260811`

## Reason

The inherited GAEZ high-input rice coefficient in cluster 1 was 0.096 km3 per
1000 km2, or 960 m3/ha. It was a crop-water-deficit raster value, not a total
flooded-paddy diversion requirement. The earlier division by 0.38 efficiency
did not add saturation, ponding, percolation, or multiple-cropping water.

## Source parameter change

Only `RYTCM.json`, parameter `IAR`, commodity `COM_sp9qb` (`AGRWATPHL`), base
scenario `SC_0`, modes 17 and 19, technologies `TEC_ibnh8`, `TEC_9lvqs`,
`TEC_3mwof`, `TEC_ckkki`, `TEC_1ky0a`, `TEC_oeqz2`, `TEC_72dqm`, and
`TEC_xaiae`, years 2020-2053 are changed. There are 544 numeric cells.

The annual gross coefficient is:

`(cluster/mode GAEZ WDe + 0.450 m/crop) * (3,253,454.36 / 2,006,000 crops/year) / 0.38`

FAO engineering components are 200 mm saturation, 2 mm/day percolation for a
conservative heavy well-puddled clay case over 100 days, and 50 mm standing
water. Resulting annual coefficients are 1.9249-3.5425 km3 per 1000 km2, or
19,249-35,425 m3/ha/year. Seasonal equivalents are 1.374-2.528 L/s/ha, within
NIA's 1-5 L/s/ha soil design-duty range.

No technology, commodity, mode, final demand, stock, capacity, cost, activity
bound, share, or user constraint is added or changed. Irrigated area and
cluster allocation remain endogenous. The values are not scaled to a national
withdrawal total.

## Evidence and calculations

The authoritative schema-ledger entry and full source locators are in:

- `Philippines_v16_CLEWs_build/data_sources/snapshots/irrigation_water_engineering_2026.json`
- `Philippines_v16_CLEWs_build/data_sources/calculation_notes/irrigation_water_engineering_v16_2026-08-11.md`
- `Philippines_v16_CLEWs_build/data_sources/snapshots/irrigation_water_manifest.json`
- `Philippines_v16_CLEWs_build/data_sources/snapshots/irrigation_water_validation.json`

## Validation

- Deterministic source guard: passed; only `RYTCM.json` differs and exactly 544
  intended cells change.
- Application generation/preprocessing: passed through the normal `DataFile`
  path.
- GLPK matrix check: passed; 791,109 rows, 884,956 columns, 12,552,173
  nonzeros.
- CBC matched control: optimal objective 369,730,088.2957077.
- CBC matched candidate: optimal objective 369,730,088.3625874.
- Objective change: +0.0668797, or +1.81e-8 percent.
- 2020 irrigated-rice activity: unchanged at about 2.006 Mha.
- 2020 rice irrigation: 0.4332 to 40.4030 km3, equivalent to 20,141 m3/ha.
- Total annual capacity, annual technology emissions, demand, and user
  constraint outputs: unchanged.

The initial disposable run was rejected because simultaneous wind work changed
the live source after its snapshot. A new unchanged control and candidate were
therefore rebuilt from the same wind-complete source; only that matched A/B is
accepted above.

Promotion was performed only after the wind work completed and the live source
was proven identical to the frozen control. The promoted source is byte-for-byte
identical to the validated candidate across all source JSON files. The live
`IRRIGATION_WATER_BASE` run solved optimally at 369,730,088.3629758 on the same
791,109 x 884,956 matrix. Its generated `data.txt` hash equals the candidate's;
the objective difference is 0.0003884. Live 2020 irrigated rice is 2.006 Mha
and 41.6286 km3 (20,752 m3/ha/year). Capacity, emissions, demand, and user
constraints reproduce exactly. The alternative 40.403 versus 41.629 km3
candidate/live water totals arise from degenerate endogenous cluster allocation
and are not forced to agree.

## Known limitations

Efficiency, percolation, and cropping intensity require future scheme/cluster
observations. Recoverable irrigation return flows remain implicit because this
task is a data-only correction and no evidence-supported structural split is
available.
