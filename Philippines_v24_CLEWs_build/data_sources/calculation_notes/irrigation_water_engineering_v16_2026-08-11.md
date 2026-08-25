# Philippines v16 irrigated-rice water engineering repair

Date: 2026-08-11  
Change: `CHG_PHL_V16_IRRIGATION_ENGINEERING_20260811`

## Finding and equation mapping

The reported defect is correct. The inherited mode-19, cluster-1 coefficient
was `0.096 km3/(1000 km2)`, which converts exactly to `960 m3/ha`. GAEZ defines
this quantity as the crop water deficit (`ETm - ETa`), not the total diversion
needed by flooded paddy. Dividing by the existing 0.38 irrigation efficiency
raised the live value to `0.2526315789`, but still omitted land saturation,
standing water, seepage/percolation, and annual multiple cropping.

In the active model, equations `Acc3_AverageAnnualRateOfActivity` and
`EBb4_EnergyBalanceEachYear4` multiply annual land activity in `1000 km2` by
`InputActivityRatio`. Because `1 m` over `1000 km2` is `1 km3`, the corrected
`AGRWATPHL` IAR is an annual gross diversion depth. Crop-land technologies are
physical conversion technologies; observed irrigation service area is an
initial stock; crop demand is existing exogenous final demand; irrigated crop
activity and cluster choice remain endogenous.

No technology, commodity, mode, equation, demand, activity/share bound, or
user-defined constraint is added or changed.

## Sources and frozen inputs

- FAO GAEZ v4 model documentation (`SRC_GAEZ_V4`) establishes that WDe is the
  agroclimatic water deficit, not total paddy duty.
- FAO paddy scheduling (`SRC_FAO_PADDY_SCHEDULING`) gives 200 mm for land
  saturation, 2 mm/day for heavy well-puddled clay where local percolation data
  are absent, and a 20-100 mm standing water layer.
- FAO scheme-water guidance (`SRC_FAO_SCHEME_WATER_NEED`) uses 200 mm
  saturation, a representative 50 mm water layer, and gross requirement equal
  to net requirement divided by scheme efficiency.
- FAO's rice-water synthesis (`SRC_FAO_RICE_WATER_REQUIREMENT`) gives a 100-day
  reference season and a 900-2250 mm/season field-water range.
- NIA Memorandum Circular 125 s. 2025 (`SRC_NIA_IRRIGATION_DESIGN_DUTY_2025`)
  gives soil-based duties of 1.0-5.0 L/s/ha.
- PhilRice's existing 0.38 national delivery-efficiency observation,
  full-precision PSA OpenSTAT 2020 irrigated palay harvested area of
  3,253,454.36 ha, and PSA's 2,006,000 ha irrigation service area are retained.

The normalized, frozen input register is
`snapshots/irrigation_water_engineering_2026.json`. National withdrawal totals
are benchmark-only and do not scale any coefficient.

## Calculations

Cropping intensity:

`3,253,454.36 harvested ha / 2,006,000 service ha = 1.621861595214357 crops/year`

Conservative paddy addition per crop:

`200 mm saturation + 2 mm/day * 100 days + 50 mm standing water = 450 mm/crop`

For cluster `c` and irrigated-rice mode `m`:

`annual gross IAR[c,m] = (GAEZ WDe[c,m] + 0.450 m/crop) * 1.621861595214357 crops/year / 0.38`

`m3/ha/year = IAR * 10,000`

`100-day seasonal duty = ((GAEZ WDe + 0.450) / 0.38) / 0.864 L/s/ha`

| Cluster | TechId | Mode 17 IAR | Mode 19 IAR | Mode 17 m3/ha/yr | Mode 19 m3/ha/yr |
|---|---|---:|---:|---:|---:|
| C01 | TEC_ibnh8 | 1.9551968336 | 2.3303590289 | 19,552 | 23,304 |
| C02 | TEC_9lvqs | 1.9248936301 | 2.0828117328 | 19,249 | 20,828 |
| C03 | TEC_3mwof | 1.9317225210 | 2.2364617787 | 19,317 | 22,365 |
| C04 | TEC_ckkki | 1.9283080756 | 2.0742756191 | 19,283 | 20,743 |
| C05 | TEC_1ky0a | 2.0315950508 | 2.9022786441 | 20,316 | 29,023 |
| C06 | TEC_oeqz2 | 1.9385514120 | 2.3474312562 | 19,386 | 23,474 |
| C07 | TEC_72dqm | 2.2706062333 | 3.5424871685 | 22,706 | 35,425 |
| C08 | TEC_xaiae | 1.9248936301 | 1.9556236393 | 19,249 | 19,556 |

The corresponding seasonal duties are 1.374-2.528 L/s/ha, within NIA's
1-5 L/s/ha table. This check is independent of national withdrawal totals.

## Disposable validation

The control and candidate were both copied from the wind-complete live source
and then frozen. Their only source difference is `RYTCM.json`: 544 values
(`8 clusters * 2 modes * 34 years`). Generation and preprocessing used
`DataFile(case).generateDatafile(run)` and `preprocessData()`; GLPK generated a
791,109-row, 884,956-column matrix with 12,552,173 nonzeros; both CBC runs were
optimal.

| Measure | Control | Candidate | Difference |
|---|---:|---:|---:|
| Objective | 369,730,088.2957077 | 369,730,088.3625874 | +0.0668797 (+1.81e-8%) |
| 2020 irrigated-rice activity | 2.006 Mha | 2.00599 Mha | CSV rounding only |
| 2020 rice irrigation | 0.4332 km3 | 40.4030 km3 | +39.9698 km3 |
| Total capacity | 1,564,675,272.9294 | 1,564,675,272.9294 | 0 |
| Annual technology emissions sum | 10,983.8036 | 10,983.8036 | 0 |

Demand, all activity/share bounds, user constraints, technology/commodity/mode
sets, capacity, and annual emissions are unchanged. The candidate result is
recorded in `snapshots/irrigation_water_validation.json`.

## Promotion and live reproduction

After the simultaneous wind work completed, all live source JSON hashes were
checked against the frozen control. The 544 rice-water cells were then promoted
without modifying any wind or other model inputs. The promoted live source and
validated candidate have identical source hashes, and their generated
`data.txt` files have the same SHA-256 digest.

The live `IRRIGATION_WATER_BASE` chain solved optimally at
`369730088.3629758`, only `0.0003884` above the validated candidate because of
solver tolerance. The live optimum retains 2.006 Mha irrigated-rice area and
uses 41.6286 km3 in 2020, or 20,752 m3/ha/year. Repeated solutions distribute
the same national rice area differently among degenerate cluster options, so
the exact live water total differs from the candidate's 40.403 km3 while
remaining within the validated 19,249-35,425 m3/ha coefficient envelope.
Capacity, annual emissions, demand, and both user-constraint result families
reproduce exactly. The live record is frozen in
`snapshots/irrigation_water_live_validation.json`.

## Limitations

- The 0.38 efficiency is national rather than scheme- and cluster-specific.
- The 2 mm/day value is a conservative heavy, well-puddled clay case; cluster
  soil and scheme measurements should replace it.
- The 2020 cropping intensity is held constant through 2053.
- Existing model structure does not separately route recoverable paddy seepage,
  drainage, or conveyance returns. This data-only repair corrects gross
  withdrawals without inventing a return-flow split.
