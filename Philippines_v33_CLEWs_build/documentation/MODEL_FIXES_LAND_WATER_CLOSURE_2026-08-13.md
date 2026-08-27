# Philippines v18 land-water closure repair — 2026-08-13

## Outcome and physical classification

All fixed national land is required to pass through the eight existing
hydrological clusters. The cluster totals are geography: their existing TAUs
sum exactly to the fixed 295.8131 thousand km2 national land account. Matching
TALs now require those source-derived areas to participate in hydrology.

The optimizer still chooses among all 30 crop and land-cover modes inside each
cluster. No crop output, land-cover mix, irrigated area, water-source share,
withdrawal total, generation or dispatch result is fixed.

- Initial stocks: unchanged.
- Final demands: unchanged.
- Continuing physical constraints: eight geographic cluster areas and
  conservation of water within every cluster-mode.
- Benchmark-only observations: rainfall volume, withdrawal and crop outcomes.

## Equation and parameter mapping

`RYT.json` receives `TAL = existing TAU` for `LNDAGRPHLC01` through `C08`,
2020-2053. This uses the existing annual activity-bound equations. The eight
areas sum to 295.8131 thousand km2, equal to fixed `MINLNDTOT`.

`RYTCM.json` places the existing 0.38 irrigation efficiency at the correct
boundary. `DEMAGRSURPHL` and `DEMAGRGWTPHL` retain raw-water IAR=1 and pumping
electricity, but produce 0.38 units of delivered `AGRWATPHL` per gross unit
withdrawn. Positive cluster irrigation IARs are multiplied by 0.38. For each
cluster, mode and year, precipitation and evapotranspiration remain unchanged;
groundwater and surface outputs are recalculated so
`P + delivered irrigation = ET + GWT + SUR`, preserving the former GWT share.

## Runtime formulation decision

The initially tested aggregate nine-member Tag-1 equality was mathematically
equivalent but timed out after 430 seconds, exceeding twice the prior v18 CBC
benchmark of 207.20 seconds. It was not promoted. The parameter-only TAL/TAU
formulation is therefore the candidate subject to a dedicated runtime A/B.

## Deterministic checks

- Cluster/national area: 295.8131 thousand km2.
- TAL cells changed: 272.
- Water coefficient cells changed: 19618.
- Maximum serialized cluster-mode water residual: 4.7E-16.
- Minimum nonnegative excess water: 0.4338451246122988 km3 per 1000 km2.
- Full-routing precipitation expected: 786.306717372 km3 (2658.12 mm) in
  2020 and 824.0806113969379 km3 in 2053, a 4.80396 percent increase.

## Known limitation

The 62 percent gross-to-field delivery loss remains outside the field-hydrology
boundary. Its partition among conveyance evaporation, drainage, seepage and
recoverable return flow is not invented; it remains documented in `GAPS.csv`.

## Validation status

Source generation, semantic diff, policy inheritance and deterministic
physical checks: **passed**. Full application generation, matrix check, CBC,
baseline comparison and promotion identity are recorded in the validation
manifest after completion.

## Completed full-chain validation

The parameter-only candidate passed application generation, preprocessing,
independent GLPK matrix validation, one full CBC optimization, result export
and baseline comparison. It solved optimally at objective 369743573.76853257, a change
of 0.44597089 (1.206162654816283034375284876355133723458400E-7%) from the verified v18
deployment-envelope baseline.

The comparable matrix is 791517 rows,
886010 columns and
12817475 nonzeros. The exact cluster
bounds add 272 rows and 244,800 nonzeros. The solve completed within the
declared 415-second cutoff; exact CBC seconds were not retained because the
first post-solve validator stopped on an overly strict rounded-CSV assertion.
The same optimal `results.txt` was post-processed without another solve.

All eight solved cluster totals equal their geographic bounds in the solver;
the exported mode-sum maximum rounding error is 0.0006 thousand km2. Full-land
precipitation is 786.30722714002144322480 km3
(2658.1217232773715674687834987700003819979574941069 mm) in 2020 and
824.08162307526707646497 km3 in 2053, an increase of
4.8040250211917444417202101320877248207501886922400%.

New generation capacity and annual emissions are unchanged. Rounded crop
production differs by at most 0.0007.
Combined gross irrigation withdrawal changes endogenously by at most
1.2966
km3/year because the optimizer can reallocate land modes and withdrawal routes;
the accounting boundary itself remains gross diversion.

Optimizer runs recorded for this repair: (1) aggregate UDC experiment, stopped
after 430 seconds and rejected; (2) exact-cluster-bounds candidate, optimal and
promoted. No unchanged control or post-promotion optimization was run.

## Promotion identity

The promoted companion live case passed identity checks for all 22 root source
JSON files. Live `data.txt` is byte-identical to the solved candidate. The
processed files differ only in unordered derived set declarations and become
byte-identical after canonical sorting. GLPK reproduced 791,517 rows, 886,010
columns, 12,817,475 matrix nonzeros and 423,240 objective nonzeros. No
post-promotion CBC optimization was run.

