# Philippines v22 BASE EV availability and truck-turnover correction

## Intended behavior and classification

BASE is the requested full-horizon no-EV counterfactual. The eleven electric
and plug-in-hybrid vehicle technologies listed by `CO_sdx29` have zero
residual stock and receive zero annual new-capacity allowance in BASE from
2020 through 2053. COAL_PHASEOUT and RE inherit this BASE availability rule.
The existing EV scenario explicitly reopens the same technologies and retains
the existing exact policy trajectory, coefficients and equality tag.

Truck-service demand is genuine exogenous final demand. Truck capacity,
activity and powertrain mix are endogenous outcomes. Observed historical
powertrain shares remain validation benchmarks and are not imposed through
activity bounds, shares, diesel targets or new user-defined constraints.

## Deterministic contradiction in the rejected formulation

The former light- and heavy-truck `TAMaxCI` series scaled one 2020
registration flow by demand and applied the same flow separately to every
powertrain. With the inherited uniformly aged stock, the incumbent liquid
fleet retired faster than it could replace itself. Once EV and PHEV activity
were prohibited, the optimistic annual service envelope fell short for both
truck classes in 2021, 2022 and 2023. CBC presolve correctly identified the
candidate as infeasible; the later timeout was not evidence of a difficult
feasible optimum.

The generic physical gate also had a disclosed blind spot: it checked only
`SpecifiedAnnualDemand × SpecifiedDemandProfile`, while all Philippine
transport services use `AccumulatedAnnualDemand`. The gate is corrected
generically to evaluate every country's selected scenario and every nonzero
annual-demand commodity against a separate annual production envelope.

## Accepted source formulation

For each light- and heavy-truck powertrain, the annual entry envelope is:

`scheduled initial-stock retirement + max(0, service demand growth) / minimum class CAU + replacement of the technology's allowed vintage reaching operational life`.

This is the established non-road branch of the v14 stock-turnover generator.
It gives any permitted powertrain enough headroom to cover class replacement
and positive growth without prescribing which powertrain is selected. It is
an optimistic per-technology feasibility envelope, not an aggregate sales
cap or an observed technology-share trajectory.

The permanent parameter changes are confined to:

- `RYT.json / TAMaxCI`: repaired truck envelopes; BASE zero-EV investment;
  explicit EV-scenario restoration; and
- `RYTCn.json / CAM`: BASE deactivation of `CO_sdx29`; explicit restoration
  of its former effective coefficients in EV.

`RYCn.json / UCC`, the constraint equality tag, residual capacity, activity
bounds, demand, costs, efficiency, lifetime and all structural objects are
unchanged. Because every affected EV/PHEV residual-capacity series is zero,
full-horizon `TAMaxCI = 0` is sufficient to guarantee zero BASE capacity and
activity; a redundant `TAU = 0` is not added.

The correction is reproducible through
`scripts/apply_philippines_v22_ev_truck_turnover.py` using the separate v22
specification `scripts/philippines_v22_ev_truck_turnover_inputs.json`. The
historical v14 input specification is preserved unchanged.

## Validation protocol and results

The generic annual-demand gate must pass for BASE, COAL_PHASEOUT, RE and EV.
Each run is generated and preprocessed through the application path and its
GLPK matrix is checked before optimization. BASE is optimized first. Only a
proven BASE optimum authorizes concurrent optimization of the other three
scenarios in separate run directories; shared viewer files are updated only
sequentially.

The amended generic gate has two focused unit tests. It also reproduces the
rejected r2 contradiction without an optimizer: six annual shortfalls,
`PHL_TRA_FKMTL` and `PHL_TRA_FKMTH` in 2021--2023. The corresponding gaps are
−0.160685/−0.070499, −0.206608/−0.092547 and
−0.107624/−0.066136 billion vehicle-km. The unchanged canonical r9 BASE and
all four repaired candidate scenarios return zero deterministic shortfalls.

All four application-generated matrices passed the GLPK check. BASE was
optimized first and proven optimal. COAL_PHASEOUT, RE and EV were then
optimized concurrently in isolated run directories and all were proven
optimal:

| Scenario | Rows | Columns | Nonzeros | Solve seconds | Candidate objective | Change from canonical r9 |
|---|---:|---:|---:|---:|---:|---:|
| BASE | 553,001 | 584,981 | 8,108,315 | 113.18 | 369,798,931.086 | −25,426.664 (−0.00688%) |
| COAL_PHASEOUT | 553,016 | 584,981 | 8,108,585 | 159.62 | 369,816,316.153 | −25,325.014 (−0.00685%) |
| RE | 553,001 | 584,981 | 8,108,825 | 142.79 | 369,809,713.633 | −25,291.716 (−0.00684%) |
| EV | 553,001 | 584,981 | 8,108,623 | 191.08 | 369,806,562.606 | −15,827.990 (−0.00428%) |

BASE, COAL_PHASEOUT and RE have exactly zero capacity and activity for all
eleven listed EV/PHEV technologies in every model year. BASE freight service
in 2021--2023 is supplied endogenously by liquid light and heavy trucks; no
diesel activity or share was fixed. The optimizer continues to select almost
entirely liquid trucks later in BASE, with only numerical-scale NG activity.
This is a model result, not a claim that the remaining stock, utilization and
fuel-cost calibration is empirically complete.

The EV scenario still uses the original equality, coefficients and right-hand
side from 2026 onward. Its summed listed-technology activity matches every
active-year target; the largest apparent residual is 0.0001, the four-decimal
CSV output precision. The target remains an equality, not a newly introduced
floor. With the truck envelope repaired, the optimizer supplies most of the
aggregate target through electric cars and 2--3 wheelers rather than being
forced to use electric trucks as a feasibility backstop. It also selects
1.1895 activity from electric cars in 2025, when the EV scenario has already
reopened the technology but the existing aggregate constraint is not yet
active.

The objective falls slightly in every scenario because the former truck
limits forced simultaneous investment in costlier alternative powertrains.
Removing that artificial scarcity also changes upstream liquid-fuel,
biofuel, coal, electricity and water flows; these are expected coupled-model
consequences, not source changes outside `RYT.json` and `RYTCn.json`.

The full candidate record is retained in
`data_sources/snapshots/ev_truck_turnover_validation_manifest.json`, with
run-specific input, LP and result hashes. The schema ledgers record the source,
assumptions, calculations, mappings, remaining empirical gaps and change
status. Promotion identity is recorded separately after live regeneration;
no post-promotion optimizer rerun is required when the regenerated live input
is byte-identical to the solved candidate.

## Known limitations

The light/heavy truck stocks remain model-derived because aggregate LTO
utility-vehicle and truck categories do not map one-to-one to the model's van,
light-freight and heavy-freight services. The correction removes deterministic
scarcity but does not claim that an endogenous NG, hydrogen or liquid-fuel mix
reproduces history. Fuel-specific registrations, age cohorts, scrappage,
vehicle-km, load factors and refuelling-infrastructure availability remain
the required empirical upgrade.

## Promotion identity (2026-08-24)

The validated source was promoted to `Philippines_v22`. All root source JSON
files and all six schema-ledger CSVs were byte-identical to the disposable
candidate before adding this promotion record. The live application-generated
`data.txt` is byte-identical to the solved BASE candidate. Preprocessed data
are equivalent after canonicalizing unordered derived-set declarations, and
GLPK reproduced the 553,001-row, 584,981-column, 8,108,315-nonzero matrix.
No post-promotion CBC optimization was run; the four validated disposable
scenario results remain the authoritative simulation record.
