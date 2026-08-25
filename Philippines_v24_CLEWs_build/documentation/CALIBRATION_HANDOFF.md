# Philippines v21 calibration handoff

The compact power-allocation repair is complete. Do not continue tuning generic
fuel prices or restore historical dispatch/build pins. If users need a more
detailed successor, the next honest upgrade is plant- and grid-specific
off-grid supply, hydro inflow/reservoir dynamics, and inter-grid transmission;
generation observations must remain validation benchmarks. No sensitivity work
is part of the maintained calibration task.

Philippines v21 is solved and source-traced. The national 2020 land account is
now closed, but spatial land allocation, land transitions, and several water
outputs remain calibration-sensitive. Continue from the complete v21 ledger and append
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
4. Preserve the national PSA/NAMRIA 2020 equality unless replacing it with a
   demonstrably better land account. Do not impose national totals pro rata on
   the eight crop-yield clusters; use an actual spatial overlay.
5. Keep `LNDOTHTOT` mode 2 as the idle/fallow route unless a sourced land-state
   redesign replaces it. Do not add a 31st global mode for the same function.
6. Forest `VC=-10` is deliberately retained. Preserve the installed national
   policy-rate expansion envelope, true-grassland reserve, fixed-class rules,
   cropland floor and zero-unallocated rule unless better evidence supersedes
   them. Parcel-level transition flows, restoration/conversion costs or lags,
   and `0/-5/-10/higher-benefit` sensitivities remain future work.

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
| NAMRIA 2020 raster overlay with the eight model clusters | NAMRIA / model maintainers | Replace national-only land initialization with spatial evidence |
| Forest transition matrices and restoration costs/lags | DENR/FMB/PSA | Constrain and value future land-use change without removing the benefit signal |

## Version boundary

Any new version must carry all six ledgers and retained evidence forward. It
must not cite an earlier ledger as a substitute for including its provenance.
See `../data_sources/calculation_notes/land_water_boundaries_v16_2026-08-11.md`
for the resolved source definitions and calculations.
