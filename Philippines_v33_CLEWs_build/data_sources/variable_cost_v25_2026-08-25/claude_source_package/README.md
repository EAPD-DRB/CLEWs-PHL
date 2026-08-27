# Variable cost proposals for Philippines_v23

Compiled 2026-08-25. Regenerate everything in this folder with:

    python3 scripts/propose_philippines_v23_variable_costs.py

run from the repository root. Nothing here has been written into the case. The
model files are untouched; these are proposals with their evidence.

## What the problem is

`VariableCost` in `Philippines_v23/RYTM.json` is 0.0001 for almost everything.
Collapsing the four active scenario layers the way the solver does (last active
non-null wins, SC_0 then SC_3hgjb then SC_w03qj then SC_huc7i) gives 5,490
technology-mode cells for 2020, of which 5,284 hold that placeholder. 178 of
the 183 technologies are affected. Only 24 technologies carry a real number
anywhere: fuel extraction, import and export, two biomass supply chains, one
legacy gas CHP, household electricity distribution, the two environmental
accounting technologies, and the two irrigated and rainfed rice modes in each
of the eight land clusters.

360 of the 5,284 placeholder cells sit on a mode that actually has an input or
an output activity ratio. The other 4,924 are on modes that can never carry
activity, so their value is irrelevant. `VC_INVENTORY.csv` flags which is which
in the `mode_is_active` column.

## Source priority

Philippine national statistics first, then international agencies, then
scientific literature. Every proposal records which tier it came from in
`VC_PROPOSALS.csv`. In the end:

- 108 proposals rest on Philippine national data (PSA crop statistics, PSA CPI,
  a PIDS bus-operator survey, the JICA/DOTC vehicle operating cost model).
- 19 rest on the US EIA, because no Philippine institution publishes
  technology-level variable O&M for power plants. `GAP_VC_PH_POWER_VOM` records
  exactly where that was looked for.
- No proposal needed tier 3.

## The three blocks that got numbers

**Crops, 80 proposals over the 8 land clusters.** PSA runs a cost-and-returns
survey for palay only, so for every other crop the cost per kilogram is the
2021 farmgate unit value times palay's own cost-to-unit-value ratio, 0.749175
irrigated and 0.836761 rainfed. The unit values come from Table 5.1 cell by
cell; the palay costs of 12.49 and 13.95 PHP/kg come from the 2022 yearbook.
Those two costs and the 49.25 PHP/USD rate are exactly what produced the rice
variable costs already stored in the case, which is checked arithmetically in
`CALC_VC_HOUSE_FORMULA_CHECK`, so the new crop costs are consistent with the
old rice ones by construction. The step from cost per kilogram to
`VariableCost` is the house formula, output activity ratio times cost times
1000 divided by the exchange rate. The substitution assumption is
`ASM_COST_RATIO`, and the alternative that would raise non-rice costs by 6 to 9
percent is written out there.

**Road transport, 28 proposals.** A Metro Manila bus operator spent 1,160 PHP a
day on repair and maintenance while running 184.7 bus-km a day, which is 6.2804
PHP/km in 2015 prices. Escalated by the PSA CPI for maintenance and repair of
personal transport equipment, 96.1656 in 2015 to 103.7583 in 2020, that is
6.7764 PHP/km, or 0.137591 USD/km. Divided by the bus capital cost the case
already holds, 74,524.83 USD, that is 1.8462e-06 of the new-vehicle price per
kilometre. The independent check is the JICA/DOTC vehicle operating cost model,
calibrated on Philippine data, which puts bus maintenance parts at 0.182
percent of the new-bus price per 1,000 km, or 1.82e-06 per km: 1.4 percent
apart. That coefficient is then applied to each vehicle class's own capital
cost. Two- and three-wheelers come out at 0.0016 USD/km, which is low, so they
are marked LOW confidence. The five plug-in hybrids take the mean of the
same-class petrol and battery proposals instead, because their stored capital
cost is about 1000 times too large and a capex-proportional rule would inherit
that error.

**Power, 19 proposals.** EIA AEO2023 Table 1, the variable O&M column, deflated
from 2022 to 2020 US dollars with the World Bank US consumer price index
(118.6905 / 134.2112 = 0.884363) and divided by 3.6 to turn USD/MWh into
USD/GJ, which is what MUSD/PJ means here. Wind, solar and storage get zero
because that is the source convention, not because they are free: their O&M is
in the fixed column. Biomass with capture is the one constructed value, biomass
plus the increment capture adds to coal, and is marked LOW confidence.

## The five classes in VC_PROPOSALS.csv

- `PROPOSE` (123 rows): a sourced number.
- `PROPOSE_ZERO` (5): zero is right because the source puts the cost in
  `FixedCost` instead.
- `KEEP` (58): the placeholder is correct. Land and mineral stock accounting
  technologies, unit adapters, blending nodes, the electricity splitters, and
  the 11 technologies whose real mode is already priced and whose placeholder
  sits only on dead modes.
- `REDIRECT` (41): there is a missing cost, but it is fixed, not variable. Every
  end-use heat, cooking and motive device, the fisheries technologies, and the
  six water technologies. The row names the `FixedCost` that should be fixed
  instead. For the two irrigation technologies the placeholder is close to
  right anyway, because irrigation cost is already inside the crop cost.
- `BLOCKED` (9) and `UNSOURCED` (14): see below.

## What is not proposed, and why

Nine non-road transport technologies are blocked on a unit-basis defect, not on
missing data. Their capital cost is a whole-vehicle price - 89,000 MUSD per
10^3 aircraft is 89 million USD each - but their activity is not
vehicle-kilometres. Shipping burns 0.084 MJ per activity unit, a tonne-km
figure; aviation 12.4 MJ, an order of magnitude below what an aircraft burns
per kilometre; rail 88 MJ, a train-km. `ResidualCapacity` is unusable for the
same reason, 3.94 million ships and 2 trains, and the implied utilisations come
out as round assumed numbers, exactly 100,000 km/yr for a ship, exactly 80,000
for a heavy truck, which shows they were back-derived from demand. Fix the unit
basis, then price them. `GAP_VC_NONROAD_TRANSPORT_UNITS`.

Fourteen technologies have a real variable cost that this pass did not find at
cell level: seven hydrogen, direct air capture, synthetic fuel and ammonia
technologies, four fuel processing technologies, and three industrial capture
technologies. Each has a GAPS row naming where to look next.

## Files

| file | what it holds |
| --- | --- |
| `VC_INVENTORY.csv` | every placeholder cell, 5,284 rows, with its mode's inputs, outputs and whether the mode is live |
| `VC_PROPOSALS.csv` | one row per technology, or per crop and regime for the land clusters: class, value, unit, sources, calculation id, confidence, tier |
| `CALCULATIONS.csv` | 81 rows. Every arithmetic step, with its inputs, units, output and the assumptions it leans on |
| `SOURCES.csv` | 12 rows. Provider, edition, and `exact_locator`, which names the table, row, column and value for each figure used |
| `ASSUMPTIONS.csv` | 10 rows. Each with why it was necessary and what it changes |
| `GAPS.csv` | 12 rows. What was needed, which tier, what happened, the consequence, and how to close it |
| `snapshots/` | the retrieved payloads and PDF text extracts, with `MANIFEST.sha256` |

## Reproducing a single number

Take the `calculation_id` from `VC_PROPOSALS.csv`, find it in
`CALCULATIONS.csv`, and read `formula`, `input_values` and `input_units`. The
`source_ids` on that row point into `SOURCES.csv`, whose `exact_locator` names
the table, row and column, and whose `local_file` points at the snapshot. The
PSA snapshots record the exact POST body, because these tables need a POST and
return nothing useful on a GET.

## Caveats worth carrying forward

The PSA website was behind a Cloudflare challenge on the day this was compiled,
which was not bypassed, so the 2021 palay costs come from the existing ledger
entry rather than a fresh download. They are validated arithmetically against
the case. The model's tomato yield is 8.59 t/ha against PSA's 13.74, so the
tomato proposals are internally consistent but rest on a yield that is 1.6
times too low. `PHL_PRO_PROC_BIOF` has no input commodity at all, so a
placeholder variable cost there means the model makes biofuel out of nothing.
`COTU` is zero for all 37 transport technologies. All of this is in `GAPS.csv`
and `ASSUMPTIONS.csv`.
