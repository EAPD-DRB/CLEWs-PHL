# Philippines v28 cluster land and biomass repair

Date: 2026-08-26  
Canonical parent: Philippines_v25  
Rejected diagnostic predecessors: Philippines_v26 and Philippines_v27 (not used as parents)

## Land architecture

The `ENV_LAND` terminal, its seven `ENV_LND_*` parallel commodities, and the
global `BAL_ENV_LAND` UDC are removed. No solver code changes are made. The
fixed `MINLNDTOT` endowment of 295.8131 thousand km2 supplies `PHL_LND`. The
eight `LNDAGRPHLC01..08` totals retain equal lower and upper bounds that sum to
295.8131; every cluster mode consumes exactly one national land-class commodity
at 1:1. The cluster layer therefore remains the complete spatial partition.
Land not required by the explicitly bounded or demanded classes is allocated
endogenously through existing mode 29 as `LOTHTOT` (OTHER LAND).

The v17 forest, grass/brush, other/fishpond, barren, water and built-up rules are
transferred to the direct land technologies. Forest retains its 72.3194 floor,
2.5 thousand km2/year cumulative expansion envelope and 118.81476 ceiling. The
forest benefit signal on cluster mode 27 is unchanged.

Utility PV and onshore wind use the existing built-up class. They receive no
land commodity, `ITCR`, technology mode, cost, or constraint. After solving,
their footprint is reported as 0.012 times PV total capacity
plus 0.01 times onshore-wind total capacity, in thousand
km2. The 2020 residual-capacity footprint is 0.01641384 thousand
km2, a subset of the unchanged observed built-up total of 10.2649 thousand km2.

`LNDOTHTOT` mode 2 remains idle/fallow cropland and retains `LOTHTOT` hydrology.
It is fixed at 5.2877 thousand km2 only in 2020. Thereafter one sparse service
commodity enforces idle >= productive/24, which is exactly idle >= 4 percent of
total cropland. No all-year 125.2805 cropland floor and no individual crop-land
history pins are added. In the v25 BASE solution, crop demands and yields
endogenously require 119.9928 productive land in 2020; with idle land this
reproduces the 125.2805 observed total.

## Biomass and deferred scope

The generic-biomass and crop-residue supply technologies receive one annual
BASE `TAU` trajectory calculated offline from retained crop demand/productivity
evidence. `RC` and `TAMaxC` are non-binding delivery envelopes; no biomass UDC
or endogenous crop/forest coupling is introduced. Policy scenarios inherit the
same BASE data. Expanded charcoal and domestic biofuel production remain
explicitly deferred. `GAPS.csv` retains the accurate charcoal production/trade
gap and removes the stale duplicate `Dedicated charcoal chain` entry.

## Validation

Run `scripts/preflight_philippines_v28.py` before any full solve. It checks
references and bounds, the exact cluster closure, all 30 cluster land links,
the 2020 land initialization, fallow-service reachability, biomass
deliverability, generated-data integrity, and the actual GLPK matrix-generation
output. The pre-flight does not invoke CBC. A single full BASE solve and
`scripts/validate_philippines_v28.py` remain the final proof.

Retained input snapshot SHA-256: `0e4060bc3857a80df19bd88e48542404a101be267c7d1b685747d320203b5ae1`.
