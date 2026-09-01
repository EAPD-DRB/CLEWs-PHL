# Philippines vIS2 agriculture and land spatialization

Date: 2026-09-01
Parent: Philippines vIS1.5
Status: candidate; BASE and three policy scenarios validated; not promoted

## Equation-first classification

The retained GADM province-cell intersections and CLEWs adjusted cluster areas are continuing physical land constraints. Official 2020 irrigated-palay harvested area allocates the inherited 20.06-thousand-km2 irrigation residual stock and is an initial-stock observation. Provincial crop area and production otherwise remain validation benchmarks. No crop activity, crop production, crop share, source share, irrigation use, or node outcome is fixed.

The eight national cluster technologies are replaced by 29 nonzero node-cluster intersections. Rainfed and irrigated rice OARs are recalculated from the retained PSA/GADM node-cluster allocation, with the parent yield trajectory preserved after 2020. `TAU=TAL` is split by the retained province-node geometry and reconciles to every parent cluster within relative tolerance 1e-09. OFF remains an explicit residual node.

Each absolute parent `TAMLL` mode/year floor is allocated by the same node share as `TAU` and `TAL`; it is never copied at national magnitude into each clone. The epsilon-disabled modes [2, 7, 9, 12, 13, 14, 15, 17, 18, 20, 21, 23] are removed from each clone's generated `MODEperTECHNOLOGY` by clearing their IAR/OAR/EAR/EACR coefficients. For the 18 retained modes, `TAMUL=0` suppresses redundant LU1 rows because nonnegative activity and annual AAC2 already imply each mode cannot exceed total `TAU`.

Land is not an investable technology. `TAMaxCI=TAMinCI=0` fixes `NewCapacity` at zero. A nonbinding formulation envelope, `RC=1.001*TAU/min(YearSplit)` and `TAMaxC=1.001*RC`, preserves the unchanged CAa4/CAb1 equations with at least 0.1% timeslice headroom. The physical land statement remains in annual `TAL=TAU`; the residual-capacity value is explicitly not interpreted as additional physical land.

The national irrigation-service technology and commodity are replaced by four node technologies and commodities. Their residual capacities sum to the unchanged 20.06. Capital cost, variable cost, lifetime, build freedom after 2020, and all irrigated-mode service coefficients are inherited. National crop markets, national raw agricultural water, and the vIS1.5 national surface/groundwater UDCs remain unchanged.

## Validation contract

Before solving: exact 81-province join; land and irrigation reconciliation; every clone's summed mode floors within its total activity; parent-to-clone `TAMLL` reconciliation using relative tolerance 1e-09; structural absence of disabled modes; 0.1% CAa4 headroom; application generation and preprocessing; `glpsol --check`; and direct LP proof that all 986 land `NewCapacity` variables are fixed at zero. Then run one BASE optimization with a 500-second timeout and stop. No policy solve, seal, or promotion is authorized.

## BASE validation

CBC status: `Optimal - objective value 912347.42687709`. Runtime: 237.018 seconds under 500 seconds. Objective: 912347.42687709, -0.170744% versus vIS1.5. Early primal-infeasibility declaration: False; CBC continued afterward: False. No policy scenario, seal, or promotion was run.

The source preflight passed 194 checks. `glpsol --check` generated a 634,831-row, 825,920-column matrix with 15,024,202 matrix nonzeros, down from rejected r2's 699,907 rows, 1,062,560 columns and 22,749,070 nonzeros. All 29 generated land mode sets contain exactly the 18 retained modes; no land LU1 upper rows survive. The LP contains all 986 expected `NCC1` rows with `NewCapacity <= 0`, and the optimal result has maximum absolute land `NewCapacity` of zero. Full solver output sums annual land activity to 295.81310015 thousand km2 (the final digits reflect printed solver precision).

CBC's first presolved optimum was 912,406.4; postsolve reported 0.0041647 primal infeasibility over 14 rows and entered normal cleanup. It never printed `Primal infeasible - objective value`, never printed `Presolved problem not optimal, resolve after postsolve`, and did not restart. Cleanup reached the final optimal objective 912,347.4269 after 222,665 reported iterations and 236.85 CBC wall-clock seconds.

National crop-market production is unchanged within 0.0001 at CSV publication precision, as expected from unchanged final demands. The 2020 irrigated-rice land activity remains 20.06 thousand km2 and matches the observed node stocks. Rainfed-rice activity changes from 10.8810 in vIS1.5 to 9.4308 thousand km2, versus the 14.6544173 observed benchmark: the shortfall worsens from 25.75% to 35.65%. The node model concentrates 9.1512 of 9.4308 in Luzon and leaves Visayas and OFF rainfed activity at zero. This is disclosed as an endogenous calibration result, not repaired with a node share or activity target.

Surface-water resource activity remains nonbinding: 59.241483 in 2020 and 64.741103 in 2053 against caps beginning at 125.79; groundwater activity is numerical zero against 20.2. Irrigation activity remains 20.06 through 2053, whereas vIS1.5 expands to 22.2733 by 2050. Adjacent energy changes are small model-period substitutions: service heat shifts 11.0334 from oil to gas; old-coal activity changes by +7.5118 in Luzon, -5.4441 in Visayas and -2.0675 in Mindanao. CO2e changes by -1.0558 in 2020, -1.0744 in 2030, +0.2347 in 2050 and +0.2339 in 2053. These are result changes, not additional calibrations.

## Concurrent policy-scenario validation

COAL_PHASEOUT, RE and EV were generated separately and passed `glpsol --check`, exact 18-mode land-set inspection and all 986 zero-land-investment LP bounds. Their CBC optimizations then ran concurrently in isolated run directories with independent 500-second deadlines. Shared viewer output was not generated concurrently.

All three deadlines expired and CBC was terminated at approximately 500.13 seconds. No run produced `results.txt`, so none is reported as a policy result and no CSV extraction occurred. No run printed `Primal infeasible - objective value` or `Presolved problem not optimal, resolve after postsolve`.

- COAL_PHASEOUT reached a presolved optimum of approximately 929,588.48. Postsolve primal infeasibility was 0.00012397 over 11 rows; cleanup had reached objective 929,373.25 with remaining dual infeasibility when terminated.
- RE remained in its first simplex pass at about 225,103 printed iterations, objective 926,781.37 and an incomplete primal-infeasibility line when terminated. It never declared the problem infeasible.
- EV reached a presolved optimum of approximately 893,789.73. Postsolve primal infeasibility was 0.00005119 over three rows; cleanup remained at approximately 0.00013132 primal infeasibility over three rows when terminated.

Concurrent resource contention makes these wall-clock times unsuitable as single-run runtime regressions. No additional optimization, seal or promotion was performed.

## Authorized 900-second policy reruns

The three incomplete 500-second attempts were retained as audit records. At the user's direction, clean run identities with `_900S` suffixes were generated and checked, then optimized concurrently with independent 900-second deadlines. All three finished optimally. None printed an early `Primal infeasible - objective value`, a postsolve restart, or a later infeasibility declaration. CSV extraction was finalized sequentially from the completed solver artifacts; the finalization step did not launch an optimizer.

| Scenario | Objective | CBC wall-clock | vIS1.5 objective | Change from vIS1.5 |
| --- | ---: | ---: | ---: | ---: |
| COAL_PHASEOUT | 929308.22767132 | 572.85 s | 930888.33838039 | -1580.11070907 (-0.169742%) |
| RE | 928003.71197998 | 781.26 s | unavailable: retained vIS1.5 RE timed out | not computable |
| EV | 893760.65227254 | 725.60 s | 895327.00417196 | -1566.35189942 (-0.174947%) |

All three policy results retain zero land `NewCapacity`. Model-period CO2e is 7479.3383 in COAL_PHASEOUT, 7387.3490 in RE and 9879.7461 in EV, versus 10534.4224 in vIS2 BASE. Electric-transport model-period activity is 0.9295, 0.9461 and 6049.9553 respectively, versus 0.9806 in BASE. The coal policy's directly capped old coal-CHP routes fall from 53.58 in 2039 to exactly zero from 2040 onward; other coal power routes remain available, so the scenario must not be described as eliminating every coal use. Aggregate activity of the three conventional coal power-plant routes over 2040-2053 falls from 17012.1 in BASE to 5393.49 under COAL_PHASEOUT.

The successful runs do not make this staging directory sealable: it also contains the three terminated 500-second attempts. Promotion, if requested later, requires a clean candidate inventory. Concurrent runtimes are validation wall-clock measurements, not uncontended runtime benchmarks.

## Schema-ledger audit before repository hand-off

The six canonical tables were audited after validation. The vIS2 source rows were corrected to use the canonical `SOURCES.csv` columns rather than legacy field names. They now record provider, product, edition, reference period, geography, variable, unit, exact locator, URL, access date, licence, checksums and retained local evidence for the PSA palay/corn query, PSA major-crop validation query and GADM/CLEWs province-cluster ledger.

The ledger now explicitly records the within-province crop-allocation assumption and calculation, the inherited source of the 20.06-thousand-km2 irrigation stock, the inherited cropping-intensity calculation, disabled-mode coefficient removal, and complete parent-to-clone parameter inheritance. All vIS2 source, assumption and calculation references resolve; all vIS2 evidence paths exist; keys are unique; and all six CSV files parse against their declared headers. This documentation-only repair does not alter model inputs or results and did not trigger another optimization.
