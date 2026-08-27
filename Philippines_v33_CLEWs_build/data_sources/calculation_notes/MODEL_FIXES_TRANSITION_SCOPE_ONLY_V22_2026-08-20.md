# Philippines v22 transition and scope candidate r8

This disposable candidate is intentionally narrow. It changes physical input conversion for household cooking; adds the three missing agriculture-heat input commodity memberships and ratios; collapses the redundant wind daytype losslessly; and publishes crop/land climate accounting after a successful solve. It does not contain the wider r7 biofuel, power, reliability, cooling, T&D, eligibility-date, or groundwater-pumping changes.

Observed cooking shares and the DOE 2024 agriculture/forestry/fishery total (438.8 ktoe, 18.37 PJ) and electricity share (65.6%) are validation benchmarks only. No activity or share is fixed. Oil and gas agriculture heat inherit the existing sector coefficient 1.123595506; direct electric heat uses 1.0 as a disclosed judgement because no heat-pump service is represented.

AQUASTAT's 33.28 km3 net irrigation requirement is not comparable to gross model withdrawal or loss-adjusted delivery and is not enforced. Groundwater remains unqualified pending source-specific infrastructure, safe-yield and pumping-cost data. Livestock is excluded because the model has no physical livestock sector; therefore national-agriculture climate completeness is not claimed.

Required qualification order: deterministic equation/data gate; application generation and preprocessing; GLPK matrix check; an optimal BASE solve; then optimal COAL_PHASEOUT, RE and EV solves. Nothing may be promoted unless all requested runs solve successfully and the promoted source and regenerated input are identical to the solved candidate.

## Validation outcome

The deterministic gate passed with no change to final demand, stocks, lifetimes, costs, activity/capacity/resource bounds, emissions parameters or UDC definitions. The only IAR differences were the five cooking efficiencies and the three requested agriculture-heat inputs. All affected input commodities have upstream producers. The daytype aggregation passed exact all-year/all-commodity/all-technology checks, and generated `MODEperTECHNOLOGY` membership remained identical for all 181 technologies.

GLPK generated and checked the BASE matrix at 550,995 rows, 583,111 columns and 8,099,341 matrix nonzeros. Its smaller size follows from reducing 30 timeslices to 18; no physical technology, commodity or operating mode was removed.

BASE solved first and alone: optimal objective 369,822,476.06171292 in 91.27 seconds, 0.02058% above the accepted v21 BASE. Only then were the three policy runs generated and launched concurrently. COAL_PHASEOUT was optimal at 369,839,833.34065801 in 123.34 seconds and EV was optimal at 369,820,509.51920521 in 147.40 seconds. RE timed out after 360 seconds with no result. A targeted primal-simplex diagnostic on the byte-identical RE LP also timed out, and the separately generated v21 r4 RE control timed out under default CBC. The RE problem therefore predates r8, but remains unresolved.

The repaired agriculture-heat routes no longer produce energy from nothing. BASE useful heat is 8.8668 PJ in 2020 and 17.2822 PJ in 2050. Coal grows endogenously to 4.6551 PJ in 2030 and 11.5760 PJ in 2050, confirming the disclosed relative-price artifact; no fuel share was imposed. The complete all-route publication is in each successful run's `agriculture_heat_all_routes.csv`. DOE 2024 agriculture/forestry/fishery energy remains a broader-boundary benchmark and is not forced.

There were six optimizer executions: r8 BASE; concurrent r8 COAL_PHASEOUT, RE and EV; one targeted r8 RE primal diagnostic; and one v21 RE control. Generation, preprocessing and GLPK checks were not counted as optimizer runs. Exact run status, hashes and objectives are retained in `documentation/TRANSITION_SCOPE_R8_VALIDATION_SUMMARY.json` and each run directory.

Promotion is prohibited because only three of the four required r8 scenarios are optimal. No r8 source file was copied into `Philippines_v21` or any live successor.
