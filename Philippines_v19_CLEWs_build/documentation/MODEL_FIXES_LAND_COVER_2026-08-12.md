# Philippines v17 national land-cover accounting

## Outcome

Philippines v17 carries the complete v16 model forward and adds a closed,
source-traced national land account. The 2020 model now reports the reconciled
PSA/NAMRIA land-cover partition exactly, productive cropland is unchanged, and
the difference between observed cropland cover and modeled crop activity is an
explicit idle/fallow quantity rather than missing land or a fabricated forest
residual. Future land is now protected by a Philippine policy-rate forest
expansion envelope capped to the documented forest-suitable share of brush, a
retained true-grassland reserve, central built-up growth, fixed water/barren/
fishpond classes, a 2020 cropland floor, and zero unallocated land.

No technology, commodity, user constraint, or global mode was added. Existing
`LNDOTHTOT` mode 2 is reused for idle/fallow cropland. Forest variable cost is
retained at `-10` exactly as requested.

## Evidence and reconciliation

The primary source is the Philippine Statistics Authority's *Land Asset
Accounts of the Philippines*, Special Release 2024-203, released 20 December
2024, with the 2020 closing stock derived from NAMRIA Land Cover Map 2020. The
official release, technical notes, statistical-workbook locators, exact 13-class
transcription, mapping, and reconciliation are frozen in
`../data_sources/snapshots/land_cover_2020.json`.

The published total is 295,883.7 km2 including 317.3 km2 classified as sea and
ocean. Removing that boundary artefact leaves 295,566.4 km2. The remaining land
classes are scaled by 1.0008346686226852 to the inherited model control of
295,813.1 km2. This preserves the current model geography while changing its
area by zero. A final 0.1 km2 rounding closure is assigned between cropland and
water bodies. The seven model classes are:

| Model class | 2020 km2 | `ENV_LAND` mode |
|---|---:|---:|
| Forest | 72,319.4 | 1 |
| Grassland and woodland | 77,745.6 | 2 |
| Other agricultural / fishpond | 2,287.9 | 3 |
| Barren | 1,595.0 | 4 |
| Built-up | 10,264.9 | 5 |
| Water bodies | 6,319.8 | 6 |
| Cropland | 125,280.5 | 7 |
| Unallocated | 0.0 | 8 |
| **Total** | **295,813.1** | |

FAO FRA 2025 reports 7,226.39 kha of Philippine forest and is retained as
corroboration, not as a substitute source. The close agreement is not treated
as fully independent because both official products may share national inputs.

Direct downloads from PSA and FAO were blocked by the publishers' anti-bot or
connection layer during packaging. The package therefore retains exact official
URLs and the normalized, checksummed transcription needed to reproduce every
model input; missing publisher bytes remain disclosed rather than silently
omitted.

The transition safeguard also uses Executive Order 26 (2011), whose National
Greening Program target covered about 1.5 million hectares over six years, and
Executive Order 193 (2015), which targets remaining unproductive, denuded and
degraded forestlands. Exact locators, URLs, numeric inputs and interpretation
limits are frozen in
`../data_sources/snapshots/land_transition_safeguards.json`.

The forest-only lifetime ceiling uses a national DENR/Master Plan for Forestry
Development suitability screen reported by FAO and authored by the Philippine
Forest Management Bureau. It includes 80 percent of grassland and brushland in
potential production-plantation areas, subject to slope below 50 percent and no
competing use. v17 applies that 80 percent only to the current mapped brush/
shrub stock; mapped true grassland is excluded. The source is an older national
planning screen, not a current parcel-level suitability map.

Built-up growth uses the PSA 2020 urban share of 54 percent and the World Bank/
Government of the Philippines Urbanization Review outlook of approximately 65
percent urban in 2050. Population follows the existing PSA Scenario 2 annual
series already used in v16. The World Bank report's absolute population is not
used.

## Formulation

`MINLNDTOT` receives equal lower and upper annual activity limits of 295.8131
thousand km2 for 2020–2053. This prevents terrestrial area from disappearing
from the accounts.

The eight `ENV_LAND` mode lower and upper limits are equal to the table above in
2020. These are national initialization equalities. They are not apportioned
pro rata across the eight crop-yield clusters and are not presented as an
independent model calibration result.

For later years, the original NGP planning rate is converted as:

`1.5 million ha / 6 years = 0.25 million ha/year = 2.5 thousand km2/year`.

The reconciled 19,610.0 km2 published true-grassland component is 19.6264
thousand km2. The remaining mapped brush/shrub component is 58.1192 thousand
km2. Applying the documented 80 percent screen makes 46.49536 thousand km2 the
maximum net forest expansion above 2020 and gives an absolute forest ceiling of
118.81476 thousand km2. For year `y`, `released[y] = min(2.5 * (y - 2020),
46.49536)`. Forest is bounded between 72.3194 and `72.3194 + released[y]`.
Grass/brush is bounded between the true-grass reserve of 19.6264 and its 2020
stock of 77.7456. There is no destination-independent brush release rate:
cropland and built-up land may use all brush above the grass reserve. The
forest envelope constrains net forest stock rather than tracking gross parcels.

Built-up land is fixed annually to
`10.2649 * population[y]/population[2020] * urban_share[y]/0.54`, with urban
share interpolated linearly to 0.65 in 2050 and held there through 2053. This
gives 11.93269 thousand km2 in 2030, 15.42173 in 2050 and 15.58289 in 2053.
Other agricultural/fishpond, barren and water stocks remain equal to their 2020
values because no defensible transition paths are available.
Cropland remains at least 125.2805 thousand km2, leaving productive area
demand-driven and putting any balance in idle/fallow mode 2. Unallocated land
has `TAMLL=0` and `TAMUL=0.000001` thousand km2. MUIOGO treats a numeric-zero
activity bound as a sparse default and omits it from solver data, so the small
positive upper sentinel is required to enforce the disabled mode. It permits
at most 0.001 km2 (0.1 ha), which is operationally zero at this model scale.

`LNDOTHTOT` retains its original mode 1:

`PHL_LND -> LOTHTOT + ENV_LND_OTHER`

Existing mode 2 is activated as:

`PHL_LND -> LOTHTOT + ENV_LND_CROPLAND`

Mode-2 activity is nonnegative and endogenous. In 2020, productive crop
technologies use 119.9928 thousand km2 and mode 2 supplies the remaining 5.2877
thousand km2, closing observed cropland to 125.2805 thousand km2. Its all-year
upper bound is 5.2877 so this bookkeeping route cannot clear brush merely to
create new idle cropland; productive crop technologies remain free to expand
as food demand requires. Both modes
still produce `LOTHTOT`; the existing cluster mode-29 treatment of that
commodity remains the hydrology proxy. This is an explicit assumption, not
spatial evidence.

## Deliberately deferred

The forest `VC=-10` benefit signal is unchanged. The national cumulative
expansion and land-class safeguards are now installed. Parcel-level legal and
ecological eligibility, gross inter-year transition flows, restoration survival,
restoration/conversion costs or lags, and the proposed `0`, `-5`, `-10`, and
higher-benefit sensitivity cases remain future policy-design tasks.

## Validation

The generator changes only `genData.json`, `RYT.json`, `RYTM.json`, and
`RYTCM.json`; it verifies complete `VC` identity with v16 and rejects any new
technology, commodity, or global mode. The full v17 MUIOGO/CBC run
`LAND_SAFEGUARDS_CENTRAL_COMPLETE` solved optimally at objective
369,740,345.77061987. Forest is 74.8194 thousand km2 in 2021, peaks at 105.2568
in 2034, remains below 118.81476 and above its protected 72.3194 floor; the
largest solved annual increase is 2.5. Built-up reaches 15.4217 thousand km2 in
2050. Other/fishpond, barren and water remain at their 2020 values, cropland
never falls below 125.2805, true grassland never falls below 19.6264, idle/
fallow never exceeds 5.2877, and unallocated land is zero in every year. The
retained validated current-v16 live control, exact unaffected-source identity,
annual closure, class values, productive cropland, idle/fallow, water, demand,
and emissions checks are retained in
`../data_sources/snapshots/land_cover_validation.json`.

Against the immediately preceding `LAND_SAFEGUARDS_BASE` solve, the final
objective is 1,032.0577 lower (-0.000279%). Final demand, annual technology
emissions, total capacity and new capacity are unchanged. Aggregate non-land
variable cost changes by only 0.0489 model cost units over the full horizon
(0.0000136%). Row-level activity and production shifts remain in degenerate
precipitation, water-source, fuel-supply and industrial routes, but do not
change those structural cross-sector outputs.
