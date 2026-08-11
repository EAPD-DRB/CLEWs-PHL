# Philippines v16 calibration handoff

Philippines v16 is solved and source-traced, but several land and water outputs
remain calibration-sensitive. Continue from the complete v16 ledger and append
or supersede records in place.

## Land and water gate

Before promoting further land/water calibration:

1. Use the retained PSA OpenSTAT 2020 snapshot for the selected national crop
   production and area definitions. Treat observed areas as stocks or
   benchmark-only values according to their physical meaning; do not pin crop
   activity or shares.
2. Keep `CRPCON` as whole coconut with husk. It is not copra. Add a separate
   sourced processing conversion only if a future study needs copra.
3. Use AQUASTAT only as a boundary benchmark. The comparable 2006 pair is
   65.590 km3/year withdrawal and 33.280 km3/year net requirement (50.74%,
   published as 51%). The current 2020 pair is 67.85109005 and 33.280
   (49.05%), but variable 4250 covers broader agricultural withdrawal. Neither
   pair is installed as efficiency or replaces another model assumption in
   this provenance-only change.

The reviewed 67.965 km3/year figure is not recorded as a 2020 FAO observation:
it was not reproduced as a single current AQUASTAT Philippines value and does
not yield FAO's 51% ratio with 33.280. The reviewed official material also did
not substantiate a Philippines-specific FAO reliability warning; retain the
general boundary and country-data caution instead.

## Highest-priority evidence gaps

| Dataset | Preferred institution | Model use |
|---|---|---|
| Crop- and scheme-specific gross diversions and net requirements | NIA/PSA | Replace or spatially refine the national irrigation-efficiency assumption |
| Subnational crop production and exactly matched area definitions | PSA/NIA | Validate achieved yields and spatial crop allocation |
| Aquifer properties, observed heads, withdrawals, and pumping energy | MGB/NWRB/DOE | Groundwater stocks, depletion, and pumping calibration |
| Missing inherited energy bibliography | Original model maintainers | Complete inherited-sector trace |

## Version boundary

Any new version must carry all six ledgers and retained evidence forward. It
must not cite an earlier ledger as a substitute for including its provenance.
See `../data_sources/calculation_notes/land_water_boundaries_v16_2026-08-11.md`
for the resolved source definitions and calculations.
