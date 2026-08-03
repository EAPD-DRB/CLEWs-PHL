# Land, agriculture and water calibration findings

`KNOWN_LIMITATIONS.md` states that the land-agriculture-water block has not been
calibrated to observed historical land allocation, yields, irrigation withdrawals
or water balances. This note puts numbers on that gap, from a solved run, and
proposes a route to closing part of it.

Nothing here changes the model. `scripts/calibrate_land_water.py` applies the two
corrections below to a copy of the clewsy inputs so they can be reviewed and
rerun; the packaged cases are untouched.

**What was examined.** The `Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC` case, run
`Base_v12`, solved with CBC to optimality. Every number below comes from that
solve or from the model input file it generated.

**How the corrections were tested.** By patching the MUIO case parameters
directly and re-solving, not by rebuilding through otoole. Both re-solves reached
optimality and reproduced every crop demand, so the corrections are feasible and
their effect is measured. The equivalent change through this repository's own
build path has not been run, which is why the script writes to a separate
directory rather than editing the inputs.

## Summary

| | finding | status |
|---|---|---|
| 1 | Crop yields are agro-climatic potential used as actual, so the right output is grown on the wrong area | correction tested |
| 2 | Irrigation withdrawal is roughly 25 times below the reported national figure | correction tested |
| 3 | Base-year land cover is not imposed, so forest absorbs 55% of the country as a residual | documented, no fix proposed |

Findings 1 and 2 are parameter errors with observed targets. Finding 3 is
structural and needs a decision about the land-cover concordance, so this note
only records it.

## Finding 1 -- potential yields used as actual

The crop demands are well calibrated. Rice comes out at 19.30 Mt against 19.29
observed for 2020, maize 8.12 against 8.1, sugarcane 24.40 against about 24.4,
coconut 14.49 against about 14.5. The problem is the area used to produce them.

Dividing solved output by solved area gives the yield the model is effectively
assuming:

| crop | implied | observed 2020 | |
|---|---:|---:|---|
| rice | 8.40 t/ha | 4.15 | 2.0 times too high |
| maize | 8.30 | 3.10 | 2.7 times too high |
| coconut | 4.67 | 4.00 | 1.2 times too high |
| sugarcane | 11.00 | 58.0 | 5.3 times too low |
| vegetables (tomato proxy) | 4.50 | about 8 | 1.7 times too low |

Rice at 8.4 t/ha is Philippine agro-climatic potential, not what farms achieve;
the national rice yield gap is roughly half. The errors run in both directions
and largely cancel in the total, which is why aggregate cropland looks reasonable
at 11.37 Mha against about 12 observed while every individual crop is wrong. Any
result that depends on a particular crop, or on irrigation, inherits the error.

**Correction and result.** Scaling each crop's `OutputActivityRatio` by
solved area over observed harvested area, then re-solving (optimal, 114 s):

| crop | before | after | PSA 2020 | |
|---|---:|---:|---:|---|
| coconut | 31.01 | 36.19 | 36.0 | 1.01 |
| maize | 9.78 | 26.21 | 25.8 | 1.02 |
| rice | 22.98 | 48.72 | 46.5 | 1.05 |
| sugarcane | 22.18 | 4.20 | 4.2 | 1.00 |
| vegetables | 12.22 | 7.00 | 7.0 | 1.00 |
| other | 15.49 | 15.07 | no target | |
| total | 113.66 | 137.40 | about 134.6 | 1.02 |

Areas in 10^3 km^2. Every crop with an observed target lands within 1 to 5 per
cent of it. The residual is spatial: one national factor is applied across eight
clusters with different yields, so per-cluster factors would close it further.

The correction is contained. The objective moves from 375,930,821 to
375,936,578, a change of 0.0015 per cent, cumulative CO2e does not move at four
decimal places, and land closure stays exact at 295.8131. Energy-side results
already in circulation are unaffected.

## Finding 2 -- irrigation withdrawal is about 25 times too low

Irrigated area is close to observed: 1.94 Mha, 17 per cent of cropland, against
roughly 1.9 Mha and 17 per cent. The extent is right. The water applied to it is
not.

Converting `AGRWATPHL` input ratios to per-hectare terms:

| mode | | model | requirement |
|---|---|---:|---|
| 19 | rice, irrigated, high input | 740 m3/ha/yr | 6,000 to 15,000 m3/ha/season |
| 17 | rice, irrigated, low input | 26 m3/ha/yr | as above |
| 6 | sugarcane, irrigated, high | 810 | thousands |
| 5 | vegetables, irrigated, high | 500 | 3,000 to 5,000 |

Total agricultural withdrawal is 2.71 km3/yr against roughly 69 km3/yr reported
for the Philippines. Agriculture is about 80 per cent of national water use and
is effectively absent from the model.

**Correction and result.** Scaling all `AGRWATPHL` input ratios so the national
total meets the reported figure, applied on top of finding 1, then re-solving
(optimal, 129 s):

| | original | after finding 1 | after both | observed |
|---|---:|---:|---:|---:|
| agricultural withdrawal, km3 | 2.71 | 6.31 | 69.01 | about 69 |
| surface water withdrawn, km3 | 44.8 | 48.4 | 111.1 | about 85 total |
| surface water generated, km3 | 302.2 | 335.2 | 335.2 | |
| share of surface water used | 14.8% | 14.4% | 33.1% | |
| applied per irrigated hectare | 1,397 | 2,521 | 27,556 m3/ha/yr | NIA duty 31,500 to 47,300 |

The resulting rate sits just below the National Irrigation Administration's
design duty range, so it is a slightly conservative gross diversion figure
including conveyance losses. That is the right concept for a withdrawal.

**What did not change is the more useful result.** Irrigated area stays at 25.04,
rainfed at 112.36, forest at 156.05 -- identical to the decimal place -- and the
objective moves by 0.1 in 376 million. An eleven-fold increase in irrigation
water has no consequence because water carries neither a cost nor a binding
constraint in this model. It is a pure accounting passthrough.

So the correction is worth making, because withdrawal is a reported output and it
becomes defensible. It does not make land and water interact. That would need a
binding water constraint, and there is none: `MINPRCPHL`, the single source of all
water, carries no activity or capacity limit and falls through to the 999999
default, while precipitation enters as a per-hectare coefficient on land rather
than as a national endowment. Even with corrected withdrawals there is 224 km3 of
surface water headroom, so an annual national cap would not bind either.
Philippine water scarcity is seasonal and basin-level; representing it would need
dry-season timeslices with precipitation availability factors, and that is a
change of resolution rather than of calibration.

## Finding 3 -- base-year land cover is not imposed

Forest comes out at 179.78 x10^3 km2 against 72.26 observed (FAO FRA 2025 reports
7,226.39 thousand hectares). Correcting the yields moves it only to 156.05, so
this is a separate matter.

`geospatial/summary_stats/PHL_LandCover_byCluster_summary.csv` is complete: seven
classes summing to exactly 295,813.1 km2. The mapping in
`overrides/workflow/scripts/clewsy.py` then assigns them as follows.

| class | area, 10^3 km2 | lower limit written | solved 2020 |
|---|---:|---|---:|
| Cropland | 43.37 | no | 113.66 |
| Forest land | 85.82 | no | 179.78 |
| Other agricultural land | 164.25 | no | 0.00 |
| Built-up land | 0.77 | yes | 0.77 |
| Water bodies | 1.60 | yes | 1.60 |
| Grassland and woodland | no data | | 0.00 |
| Barren and sparsely vegetated | no data | | 0.00 |

The mode lower-limit loop skips Cropland, Forest land and Other agricultural
land, leaving that margin free for the optimiser. The consequence is that
164,254 km2, 55 per cent of the country, is not carried into the model and forest
absorbs the entire residual. Two of seven classes are pinned; the whole model
contains eight mode lower-limit rows.

Leaving the margin free is a reasonable choice for projecting forward. It is a
different matter in the base year, where the usual practice is to reproduce
observed cover and let the transition optimise.

There is also a data question underneath it. `LCType10`, 55 per cent of the
national territory, maps to a single "Other agricultural land" class, and the
grassland and barren source classes carry no data at all. A land-cover product
whose legend puts half a country in one bucket cannot calibrate a land model, so
closing this finding probably means revisiting the concordance, perhaps against
NAMRIA's national land cover, before any pinning is attempted.

**Order matters.** Finding 1 has to come first. Pinning base-year cover before
correcting the yields would set cropland at the land-cover table's 43.37 x10^3
km2, which cannot produce observed national output at any plausible yield, so the
model would either become infeasible or drive forest down to roughly 15 x10^3
km2.

## Suggested next steps

1. Decide the yield targets. The script uses PSA 2020 harvested area; per-cluster
   factors derived from PSA regional data would be better than the single
   national factor used here.
2. Decide the irrigation target. FAO AQUASTAT's roughly 69 km3/yr is contested and
   lower estimates near 30 km3/yr exist. This is the number most in need of a
   sourcing decision, and the script keeps it in one place for that reason.
3. Run the corrections through this repository's own build path and confirm parity,
   which this note has not done.
4. Treat finding 3 as a separate piece of work, starting with the land-cover
   concordance rather than with the model.

## Files

- `scripts/calibrate_land_water.py` -- applies findings 1 and 2 to a copy of the
  clewsy inputs, prints the factors and the rows changed, and can emit a JSON
  report. Refuses to write over its own inputs.
- This note.
