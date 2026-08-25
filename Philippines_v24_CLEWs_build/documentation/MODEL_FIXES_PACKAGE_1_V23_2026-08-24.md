# Philippines v23 Package 1 — physical possibility and adequacy

## Intended behavior and classification

Philippines v23 starts from the latest validated Philippines v22 source,
including its EV/truck-turnover repair. Existing physical stocks remain initial
stocks; household and service electricity remain exogenous final demands; the
25% planning reserve and technology/resource availability are continuing
physical or planning constraints; observed generation, dispatch, market shares
and realized investment remain validation benchmarks. No activity, dispatch,
fuel-share, technology-share or build outcome is forced.

Technologies were classified from their equations and mappings, not their name
prefix. `PHL_POW_TD` is the physical national grid link; sector T&D objects are
capacity-free adapters and retain that treatment. Import and extraction objects
are supply boundaries, the disabled biofuel processor is a conversion, the
household charcoal proxy is a retiring physical stock, and the reserve object
is an accounting constraint over physical capacity and grid throughput.

## Source formulation changes

Permanent model changes are confined to `genData.json`, `RT.json`, `RYT.json`,
`RYTM.json`, `RYTCM.json`, `RYTTs.json`, `RYCTs.json`, `RYCn.json` and
`RYTCn.json`:

- Add `PHL_PRO_IMP_BIOF`, a 1:1 positive-cost biofuel import boundary at
  24.5 MUSD/PJ. Disable the undefined input-free `PHL_PRO_PROC_BIOF` with
  `TAMaxCI = TAU = 0` for 2020–2053.
- Reclassify `PHL_HOU_COOK_COAL` as a closed charcoal-stove proxy consuming
  `PHL_PRO_BIOM` at `IAR = 5`. Its existing stock may retire, but new capacity
  is zero for the horizon.
- Prevent CCS entry before 2030. Close coal hydrogen and new coal agriculture
  heat for the full horizon.
- Replace unlimited 2020–2025 power and national-grid construction cells with
  finite, disclosed annual delivery envelopes. The 2020 additions are zero;
  2021–2025 ceilings are retained in `MAP_PHL_V23_BUILD` and the source
  snapshot. Sector T&D adapters are unchanged.
- Set the national-grid input ratio to
  `(83,243 + 9,742) / 83,243 = 1.117030861453816`.
- Rotate the ordinary solar trace by UTC+8 without changing annual weighted
  energy. Night brackets and all worst-day solar values are zero.
- Replace cooling-water input factors for twelve thermal technologies using
  disclosed NREL withdrawal medians and exact unit conversion. Plant-level
  cooling-system mapping remains a known limitation.
- Set prospective thermal availability to disclosed values from 0.80 to 0.90;
  retain DOE dependable/nameplate ratios for existing fleets. No peak-slice CF
  haircut is used.
- Apply the observed peak-to-average ratio
  `1.3156012421871928` only to fixed household and service electricity. The
  profile increment is reallocated within the unchanged worst-day block and
  every annual profile sums exactly to one. Agriculture motive-power and
  processing service profiles are unchanged.
- Add `PHL_POW_RESERVE_MARGIN`:
  `-sum(capacity_credit[t] * TotalCapacityAnnual[t,y]) +
  0.05214680215417272 * TotalTechnologyAnnualActivity[PHL_POW_TD,y] <= 0`.
  The coefficient is `peak_to_average * 1.25 / 31.536`. Endogenous grid
  throughput therefore raises the requirement automatically. Variable solar
  and wind receive zero credit in this conservative screen.

All source facts, assumptions, calculations, model mappings, gaps and change
status are recorded in the six-table schema ledger under `data_sources/` and
the hashed source snapshot
`data_sources/snapshots/philippines_v23_package1_sources_2026-08-24.json`.

## Pre-flight gate and prevented policy failure

The generic source-only gate now checks specified and accumulated annual
demand, recursively propagated commodity requirements, every-year/every-slice
optimistic capacity/service envelopes, and active user-defined-constraint
intervals. It is generic: it contains no Philippine technology names or fixed
years. The separate Package 1 validator checks case-specific intent and exact
cells.

Before policy generation, the RE generic gate found two deterministic
contradictions: its 2032 and 2035 nuclear-capacity equalities required 1.2 and
2.4 GW while the first v23 builder had accidentally erased the corresponding
policy build overrides. The builder had changed only BASE 2020–2025 values but
cleared policy overrides for all years. No RE matrix or optimizer had been
launched. The helper was corrected to inherit only edited years and 35
untouched policy `TAMaxCI` cells were restored from v22. All four scenario gates
then returned zero contradictions. The incident and exact restored cells are
retained in `package1_v23_policy_inheritance_repair.json`.

The analytic gate is intentionally necessary but not sufficient. Its producer
and route intervals are optimistic and do not prove simultaneous shared-route,
trade or storage-chronology feasibility. A passing candidate still requires
one coupled optimization per scenario selected for qualification.

## Generation, matrix and optimization results

Every run was generated and preprocessed through `DataFile`, checked with
`glpsol --check`, and written to an isolated run directory. BASE was solved
first. At the user's request, COAL_PHASEOUT, RE and EV were then optimized
concurrently; shared viewer files were not generated.

| Scenario | Rows | Columns | Nonzeros | Solve seconds | Objective | Change from v22 |
|---|---:|---:|---:|---:|---:|---:|
| BASE | 554,873 | 586,648 | 8,118,754 | 165.78 | 369,951,589.021 | +0.04128% |
| COAL_PHASEOUT | 554,888 | 586,648 | 8,119,024 | 175.56 | 369,974,408.908 | +0.04275% |
| RE | 554,873 | 586,648 | 8,119,264 | 274.87 | 369,965,855.123 | +0.04222% |
| EV | 554,873 | 586,648 | 8,119,062 | 257.32 | 369,936,176.666 | +0.03505% |

All four results are proven optimal. Every reserve row is feasible in every
scenario, and the undefined biofuel processor, coal-hydrogen route and coal
agriculture-heat route have exactly zero activity. BASE reserve is binding in
2027–2029 and 2032–2053. Full hashes, residuals, objectives and run identities
are retained in `package1_v23_four_scenario_validation.json`; detailed BASE
activity, capacity, emissions and adjacent-year comparisons are retained in
`package1_v23_result_comparison.json`.

The BASE wall time rose 46.5% from 113.18 to 165.78 seconds. This is not matrix
growth: v23's presolved matrix is smaller. CBC iterations rose from 176,460 to
229,275 and cleanup iterations from 2,548 to 2,989. Evidence therefore points
to harder simplex geometry from the binding reserve coupling and interacting
adequacy corrections. Exact attribution would require a separate reserve-off
diagnostic optimization; none was spent because it is not needed to establish
feasibility or qualification.

## Checks and limitations

Passed: PyYAML environment preflight; four generic zero-solve source gates;
the 21-check Package 1 semantic/source-diff/ledger gate; four UI-path
generation and preprocessing runs; four GLPK matrix checks; four CBC optimal
solutions; reserve residuals; disabled-route activity; objective and
adjacent-year result comparisons.

Not run: a reserve-off solve-time A/B; zonal transmission or contingency
analysis; storage capacity-credit accreditation; empirical plant-level cooling
mapping; prospective-technology outage calibration; domestic biofuel or
explicit wood-to-charcoal supply chains. These are recorded in `GAPS.csv` and
must not be inferred from the national copperplate result.

Optimizer count: four—one required BASE candidate optimization and three
explicitly requested policy qualifications. The failed RE pre-flight consumed
zero optimizer runs and zero model-generation runs.

## Promotion identity

Pending source-only promotion to `Philippines_v23`. Promotion requires all
root source JSON and six schema-ledger CSV files to be byte-identical to the
qualified candidate, followed by live BASE regeneration, byte comparison of
`data.txt`, and one live GLPK matrix check. If identity holds, no live CBC
rerun is permitted or required; the disposable four-scenario results remain
the authoritative simulation records.

## Completed promotion identity (2026-08-24)

The validated source was promoted to `Philippines_v23`. All root source JSON
files and all six schema-ledger CSVs were byte-identical before adding this
promotion record. Live application-generated `data.txt` is byte-identical to
the solved BASE candidate. Preprocessed data are equivalent after
canonicalizing unordered derived-set declarations, and GLPK reproduced the
554873-row, 586648-column, 8118754-nonzero matrix. No post-promotion CBC
optimization was run; the four disposable candidate results remain the
authoritative simulation record.
