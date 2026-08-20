# Philippines v18 generation deployment envelopes

Date: 2026-08-13

Case: `Philippines_v18`

Parameter changed: `RYT.json` → `TAMaxCI` → `SC_0` only

## Physical behavior and non-forcing classification

This change asks whether the Philippine construction, financing, permitting,
equipment-supply and grid-connection ecosystem could commission a technology's
modeled capacity in one year. It does not constrain which technology the model
chooses or how available capacity is dispatched.

The active local equation is:

`NCC1: NewCapacity[r,t,y] <= TotalAnnualMaxCapacityInvestment[r,t,y]`.

`CAa1` and `CAa2` retain vintage accumulation and residual capacity; `CAa4` and
`CAb1` retain the capacity/activity limits. No capacity minimum, generation
minimum, technology share, activity bound, cross-technology construction cap,
or PEP capacity total is added.

Evidence is classified as follows:

- DOE annual installed capacities are observations used to calculate
  demonstrated net annual additions. They are evidence for a continuing
  real-world construction constraint, not activity targets.
- Current Philippine project sizes are capability evidence, not modeled
  commitments unless already present as a finite v18 allowance.
- Vietnam's 2021 wind commissioning is an international upper-bound
  reasonableness check only.
- The expansion envelopes are judgmental, deliberately generous upper bounds.
  They are neither forecasts nor targets.
- Residual capacity is an initial physical stock with an inherited retirement
  schedule.

## Equation-first implementation

Every v18 source cell through 2025 is preserved. From 2026:

`TAMaxCI[t,y] = max(committed[t,y], expansion[t,y]) + residual_retirement[t,y] + recycled_allowance[t,y]`

where:

- `committed` is a finite, already sourced v18 project allowance; the v18
  source has no such finite allowance after 2025, so this component is zero;
- `residual_retirement = max(0, RC[t,y-1] - RC[t,y])`;
- `recycled_allowance = TAMaxCI[t,y-OperationalLife[t]]` only for allowances
  established from 2026 onward.

The 2026 recycling boundary is essential. Pre-2026 values of 9999 or 999999
are model defaults, not physical permitted capacity; recycling them would
silently remove the new constraint. The full permitted amount is recycled,
following the v14 method, so replacement of a replacement remains possible.

## Technology roles

- Physical generation able to enter: onshore wind, offshore wind, solar PV,
  coal, coal CCS, NGCC, NGCC CCS, large hydro, hydrogen generation, biomass
  CCS, nuclear SMR and conventional nuclear.
- Combined existing-field repowering and greenfield representation:
  `PHL_POW_GEO_OLD`, because it is the only geothermal technology.
- Inherited physical stock only: `_OLD` coal, gas, oil and biomass CHP. These
  receive zero new entry from 2026; their residual-capacity trajectories are
  unchanged and remain usable until retirement.
- All pass-throughs, fuel conversions, accounting devices and demands are
  unaffected. No behavior is inferred from a name prefix alone; the affected
  IDs, residual stocks, operational lives and generated rows are checked.

## Expansion headroom before replacement (GW/year)

| Technology | 2026–2029 | 2030–2039 | 2040–2053 |
|---|---:|---:|---:|
| `PHL_POW_PP_WON` | 1.5 | 3.0 | 5.0 |
| `PHL_POW_PP_SPV` | 4.0 | 7.0 | 10.0 |
| `PHL_POW_PP_COAL` | 2.0 | 2.5 | 3.0 |
| `PHL_POW_PP_COAL_CCS` | 2.0 | 2.5 | 3.0 |
| `PHL_POW_PP_NGCC` | 2.0 | 2.5 | 3.0 |
| `PHL_POW_PP_NGCC_CCS` | 2.0 | 2.5 | 3.0 |
| `PHL_POW_GEO_OLD` | 0.15 | 0.25 | 0.35 |
| `PHL_POW_PP_HY_LA` | 1.0 | 1.5 | 2.0 |
| `PHL_POW_PP_BIOM_CCS` | 0.20 | 0.30 | 0.40 |
| `PHL_POW_PP_H2` | 0 | 1.0 | 2.0 |

Special entry schedules are retained exactly as requested:

- offshore wind: 0 in 2026–2027, 1.0 in 2028–2030, 2.0 in 2031–2039,
  and 4.0 thereafter;
- SMR: 0 through 2034, 0.30 in 2035–2039, and 0.60 thereafter;
- conventional nuclear: 0 through 2034 and 1.20 thereafter.

## Geothermal limitation

`PHL_POW_GEO_OLD` retains its existing cost, efficiency, 0.70 availability,
40-year operational life and residual-capacity path. Scheduled residual
retirement is added to the greenfield/expansion headroom. The model can choose
replacement but is never required to do so.

Repowering and greenfield geothermal still share one cost and performance
representation. A separate repowering technology is deferred until Philippine
evidence supports distinct costs, performance and life.

## Provenance and calculations

Primary evidence is DOE's 2003–2024 capacity series. Current Philippine solar
and wind projects demonstrate scalable capability; Vietnam is used only as an
aggressive wind check. EDC and ADB support the geothermal interpretation.
Heggarty et al. (2024, doi:10.1016/j.energy.2024.130231) provides
capacity-expansion-method support for explicit maximum investment rates.

Every annual result and component is recorded in
`data_sources/snapshots/deployment_envelopes_v18_2026-08-13.json`. Every cell
also has a `CALCULATIONS.csv` row and a `MODEL_MAP.csv` row. Source observations,
calculations and judgmental assumptions remain distinct in the ledger.

## Validation record

The build manifest is
`data_sources/snapshots/deployment_envelope_build_manifest.json`.

The disposable unchanged control and minimal candidate both passed application
generation and preprocessing, explicit `glpsol --check`, and full CBC
optimization. Both matrices contain 791,245 rows, 886,010 columns, 12,572,675
matrix nonzeros and 423,240 objective nonzeros.

The control objective is 369,743,557.67980778 and the promoted live candidate
objective is 369,743,573.32184631: an increase of 15.64203852, or
0.0000042305%. CBC time fell from 294.66 seconds to 218.64 seconds; this
single-run timing is recorded but is not treated as a general performance
claim. Ten positive ceilings have
nonzero duals: onshore wind in 2050–2053, solar PV in 2037, 2038 and 2040, and
new coal in 2039, 2046 and 2050.

After promotion, the live application chain reproduced byte-identical generated
`data.txt` and solved optimally at 369,743,573.32184631. The 0.00071537 absolute
difference from the disposable result is approximately 2×10^-12 relative and
reflects nondeterministic preprocessing order/solver tolerance, not a source
change. Live CBC time was 218.64 seconds and total chain time was 268.36 seconds.

Static validation passed all of the following:

- only `RYT.json` changed in the editable case;
- the exact allowlist is 476 `TAMaxCI.SC_0` cells (17 technologies × 28 years);
- all target values through 2025 are byte-for-byte unchanged;
- scenario override rows `SC_3hgjb`, `SC_huc7i` and `SC_w03qj` are unchanged,
  so they continue to inherit the BASE envelope wherever they have no override;
- every changed cell has a calculation and model-map record;
- `TAMinCI`, `TAMinC`, `TAL` and `TAU` are unchanged; and
- every scheduled residual retirement and recycled permitted vintage is
  represented by the documented formula.

The live solved comparison reports 94 new-capacity, 109 total-capacity, 635 activity
and 94 emission cells above the 1e-7 comparison tolerance. Some non-target and
2020–2025 result cells move because the full-horizon LP has alternate optimal
investment timing and accounting solutions. No historical source cell changed,
and the objective perturbation is approximately four millionths of one percent.
These endogenous solution shifts are disclosed rather than misrepresented as
source calibration changes.

The final machine-readable results are recorded in
`data_sources/snapshots/deployment_envelope_static_validation.json` and
`data_sources/snapshots/deployment_envelope_validation.json`.

## Known limitations and follow-up evidence gaps

- The 2030–2053 scaling bands are defensible physical envelopes, not forecasts.
- Net historical annual additions can understate gross commissioning when
  retirement occurs in the same year.
- Geothermal greenfield investment and existing-field repowering still share
  one cost, performance and operational-life representation.
- Per-technology ceilings do not model a shared national construction workforce
  or cross-technology supply-chain bottleneck.
- Solver degeneracy means detailed year-by-year differences that have zero or
  negligible objective effect should not be interpreted as a unique forecast.
