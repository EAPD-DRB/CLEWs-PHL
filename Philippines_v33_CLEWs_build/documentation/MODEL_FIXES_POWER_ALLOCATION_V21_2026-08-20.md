# Philippines v21 endogenous power-allocation repair

Date: 2026-08-20  
Baseline: `Philippines_v20`  
Accepted candidate: `.Philippines_v21-power-allocation-candidate-r4`  
Promoted case: `Philippines_v21`

## Outcome

V21 improves endogenous historical electricity allocation while remaining a
single-region model. It adds three compact power representations and one final
electricity service commodity:

- off-grid oil generation, with the official 2020 stock and optional replacement;
- aggregate off-grid hydro/solar/wind, with the official 2020 stocks and optional replacement;
- the closed 250 MW FIT-eligible biomass tranche; and
- off-grid customer electricity sales, reallocated from existing national final demand.

It also restores the retained physical seasonal hydro profile. No observed
technology generation, generation share, activity equality, realized capacity
addition, deviation penalty, or sensitivity case is imposed.

The accepted candidate solved optimally in 155.89 seconds, compared with
148.45 seconds for the source-matched v20 result. Technology WAPE improves in
every benchmark year: 13.60% to 6.48% in 2020, 16.59% to 7.86% in 2021,
22.51% to 14.90% in 2022, 31.36% to 23.96% in 2023, and 39.43% to 33.46% in
2024. Total-generation errors are reported separately and are not what WAPE
measures.

## Equation-first classification

| Information | Classification | Treatment |
|---|---|---|
| End-2020 installed fleet | Initial stock | Exact national stocks are split into grid/off-grid and FIT/non-FIT representations without changing their sum |
| Electricity sold to off-grid customers | Genuine exogenous final demand | Reallocated from existing housing, services and industry electricity demand; national final demand is conserved |
| Off-grid gross generation, own use and losses | Physical accounting driver | Used only to convert sales demand to required gross activity through `OAR` |
| Dependable capacity and seasonal renewable profiles | Continuing physical driver | Enter `AF` and `CF` |
| Crop production and residue coefficients | Continuing physical resource driver | Define a biomass-fuel activity ceiling |
| FIT eligibility and tariff | Continuing contractual/economic driver | Enter the FIT tranche's variable cost; no generation is required |
| Demonstrated off-grid additions | Continuing construction-capability evidence | Used for optional `TAMaxCI` upper bounds, never minima |
| DOE technology generation and shares | Historical benchmark only | Retained outside the solver for validation |

Technology roles are explicit. The two off-grid routes are physical conversions
with initial stock and optional new vintages. The FIT biomass route is a closed
legacy physical stock. The off-grid electricity commodity is a final service,
not a pass-through or accounting target.

## Active equations and source mapping

- `NCC1_TotalAnnualMaxNewCapacityConstraint` applies `RYT.json:TAMaxCI` to optional new capacity.
- `CAa1`/`CAa2` accumulate residual and endogenous vintages using `RT.json:OL`.
- `CAa4_Constraint_Capacity` and `CAb1_PlannedMaintenance` apply `RYT.json:AF`, `RYTTs.json:CF`, and `RYTs.json:YS` to activity.
- `EBa`/`EBb` commodity balances apply `RYC.json:SAD`, `RYCTs.json:SDP`, and `RYTCM.json:OAR` to off-grid service.
- `AAC2_TotalAnnualTechnologyActivityUpperLimit` applies the crop-residue ceiling in `RYT.json:TAU` to the FIT biomass tranche.
- `OC1_OperatingCosts` applies `RYTM.json:VC`, including the biomass FIT credit and residue collection cost.

Permanent changes are confined to source files: `genData.json`, `RT.json`,
`RYC.json`, `RYCTs.json`, `RYT.json`, `RYTCM.json`, `RYTEM.json`, `RYTM.json`,
and `RYTTs.json`. Generated `data.txt`, `data_processed.txt`, and `lp.lp` were
never edited.

## Source changes

### Off-grid service and oil

DOE reports 1,618 GWh gross off-grid generation and 1,286 GWh customer sales
in 2020. V21 creates `PHL_POW_ELE_OFFGRID_FINAL`, moves 4.6296 PJ of 2020
sales demand out of the existing national end-use commodities, and preserves
their sector shares. The gross-to-sales output ratio is 1,286/1,618 in 2020,
with corresponding independently reported ratios in 2021-2022 and the 2022
ratio thereafter.

The official 0.569224 GW off-grid oil stock and 0.403166 GW dependable capacity
are split from the unchanged national oil stock. The off-grid oil route uses
the inherited oil efficiency, fuel, emissions, cost and 40-year life. Its
2020 `TAMaxCI` is zero because the end-2020 register is the initial condition;
from 2021 it has an optional 0.10 GW/year construction ceiling. DOE reported
31 MW of off-grid diesel additions in 2022, so 0.10 GW/year is deliberately
headroom above demonstrated delivery, not an observed-build equality.

### Off-grid renewables

The official off-grid stocks—30.595 MW hydro, 7.230 MW solar and 16 MW wind—are
represented by one aggregate route to avoid three extra technologies. Its
timeslice profile is the capacity-weighted combination of the three retained
profiles; its dependable ratio is 53.375/53.825. The aggregate route has no
2020 new capacity and an optional 0.02 GW/year ceiling from 2021. This is
anchored to the retained 16 MW recent wind entry and cross-checked against the
2021 off-grid plant list. The ceiling binds from 2021 onward and is therefore
material; it is disclosed as judgmental construction aggregation.

V21 does not represent the 89.492 GWh of off-grid coal reported in 2022. The
2022 modeled off-grid mix is therefore oil plus renewables only; this is a
known compact-model limitation.

### Biomass

The DOE-reported 250 MW FIT-subscribed biomass tranche is split from the
unchanged 0.4474 GW legacy biomass stock. Its new capacity is zero throughout.
The route uses the existing generic biomass commodity, but annual activity is
limited by independently calculated rice-husk, bagasse, coconut-husk and
coconut-shell energy:

`residue PJ = crop Mt × residue fraction × LHV GJ/t × availability`.

In 2020 the resource ceiling is 220.44 PJ biomass input, equivalent to
55.10 PJ activity. The 0.25 GW stock can produce only 5.029 PJ, so the resource
ceiling is physical but nonbinding. The FIT tariff is converted from PHP/kWh
with official annual exchange rates and offset against inherited biomass supply
cost. The explicit residue collection/handling judgment is 15.8 MUSD/PJ of
electricity, anchored to ERC's published biomass fuel component. No observed
biomass generation enters the calculation.

### Hydro and the former 19 PJ limit

The former 19.08 PJ result came from the inherited v20 timeslice capacity-factor
profile, not from electricity demand. With residual capacity, year-slice
weights, availability and the active capacity equations, that profile imposed
an annual physical maximum near 19 PJ and its constraint bound.

V21 restores the older retained seasonal design values—0.3834 wet and 0.1447
dry—and rescales them only to preserve their original full-precision annual
mean of 0.26438418 under the current 30-slice year weights. Grid hydro is also
set to the DOE dependable/nameplate ratio after removing the off-grid stock.
The resulting 2020 grid-hydro activity is 29.1567 PJ. No observed hydro PJ was
used to calculate this profile. A plant/reservoir inflow model remains absent.

## Historical approaches checked

- V9-v11 had used positive `TAL=TAU` activity pins for oil, biomass and hydro.
  V14 removed them; none is restored.
- The 20 realized 2021-2025 power investment equalities were removed in the
  retained investment cleanup. None is restored.
- Earlier cross-technology and exact aggregate constraints caused major CBC
  regressions. V21 adds no user-defined constraint family.
- No prior physical hydro rebuild was found. The 19 PJ profile had been
  diagnosed, but not replaced with independently retained seasonal factors.
- No retained three-grid implementation was found. Full Luzon-Visayas-Mindanao
  balances remain deferred because they require regional demands and network limits.

## Deterministic gate and optimizer ledger

The final validator proves exact stock conservation, exact demand reallocation,
profile normalization, no generation bounds, no investment minima, the crop
residue identity, and positive off-grid service headroom for every year and
every timeslice through 2053.

This gate was added after r2 exposed a preventable process failure. R2 set
`TAMaxCI=0` on both off-grid replacement routes while their residual stocks
retired and demand grew. The first annual contradiction occurs in 2034, with a
5.0519 PJ service shortfall. This should have been detected before CBC; the
failed workflow and correction are retained explicitly.

Four optimizer runs occurred, none a sensitivity:

| Candidate | Result | Disposition |
|---|---|---|
| r1, five-technology formulation | Timed out at 1,000s | Rejected for usability |
| r2, compact but closed replacement | Timed out at 320s; later proved infeasible | Rejected; deterministic design failure |
| r3, compact with overly loose build limits | Optimal in 157.04s | Rejected because 0.6144 GW of same-year renewable build displaced historical oil |
| r4, DOE-anchored build envelopes | Optimal in 155.89s | Accepted |

The r4 matrix contains 821,091 rows, 911,143 columns and 13,210,825 matrix
nonzeros. These dimensions are descriptive only. They are not treated as a
runtime diagnosis: small changes to `TAMaxCI` or exact `TAL=TAU` values have
previously improved or destroyed CBC performance unpredictably.

## Validation results

The source-matched v20 result was reused and not rerun. R4 is optimal at
369,746,369.55929643, an objective increase of 8,411.7812 or 0.0022751%.

| Year | V20 technology WAPE | V21 technology WAPE | V20 total error | V21 total error |
|---:|---:|---:|---:|---:|
| 2020 | 13.60% | 6.48% | +2.20% | +2.29% |
| 2021 | 16.59% | 7.86% | -2.68% | -4.20% |
| 2022 | 22.51% | 14.90% | -2.94% | -4.53% |
| 2023 | 31.36% | 23.96% | -4.01% | -5.58% |
| 2024 | 39.43% | 33.46% | -6.75% | -8.27% |

The distinction matters: WAPE measures distribution across technologies;
total error measures the generation boundary/quantity. V21 improves allocation
in all five years while later grid-generation totals remain too low.

Selected 2020 results in PJ are:

| Technology | DOE | V20 | V21 |
|---|---:|---:|---:|
| Oil | 8.906 | 0 | 5.421 |
| Biomass | 4.540 | 0 | 5.030 |
| Hydro | 25.891 | 19.076 | 29.410 |
| Coal | 209.434 | 226.322 | 205.871 |

The model reproduces off-grid gross generation exactly because gross output is
the physical supply required to deliver the exogenous sales demand through
observed losses. Its technology split remains endogenous: in 2020 oil is
5.4209 PJ versus 5.3239 observed, and aggregate renewables are 0.4039 PJ versus
0.5009 observed. In 2022 oil is 5.6644 PJ versus 5.4014 observed and renewables
0.7040 PJ versus 0.6447 observed; the omitted off-grid coal output is 0.3222 PJ.

The hydro availability constraint binds in 2020 at 29.156659 PJ with dual
-7.6428744. The renewable construction ceiling binds in 2021-2024 with duals
from -7,613.59 to -6,641.38. Biomass reaches its 5.0293 PJ capacity envelope,
while the crop-residue ceiling remains slack.

## Promotion identity

All promoted source JSON files are byte-identical to r4. Live UI-path generation
and preprocessing passed, live `data.txt` is byte-identical to the solved
candidate (`SHA-256 faca05cebcd93759d87428a073d0651b7c61c409848b58e6337d1da40facbc7c`),
and the live GLPK check reproduces the matrix. No post-promotion CBC solve was
run and no disposable runtime result was copied into the live case.

## Schema-ledger completion

The cumulative six-table ledger was extended in place with 9 sources, 8
calculations, 8 assumptions, 7 model maps, 5 gaps and 1 change record. The
canonical build-stage validator passes with 192 source rows, 742 calculation
rows, 156 assumption rows, 92,580 map rows, 67 gap rows and 29 change rows; all
126 local evidence digests verify. Remaining warnings are inherited hygiene
items and blank commit fields, not v21 failures. The v21 workbook is a verified
review copy of those authoritative CSVs. A final no-optimizer validation of the
promoted live source also passes the every-year and every-timeslice replacement
envelope, with minimum annual headroom 5.7995 PJ and minimum timeslice headroom
0.004367 PJ.

## Known limitations and stopping rule

- National 2020 DOE generation includes grid, embedded, off-grid and test output;
  the 2021-2024 summary is grid-only. Validation preserves that boundary break.
- Oil remains about 3.49 PJ low nationally in 2020 because grid-connected and
  embedded oil obligations remain absent.
- Hydro is represented by a retained seasonal design envelope, not reservoir,
  inflow, outage or plant-vintage data.
- Off-grid renewables are aggregated; their modeled activity is allocated to
  hydro/solar/wind only for validation reporting.
- FIT biomass uses a plant-class tranche and crop-derived national resource
  ceiling, not plant-specific feedstock contracts or cogeneration steam demand.
- The 2021 off-grid sales value is estimated from the 2020 sales/consumption ratio.
- Later off-grid demand follows the national PDP sales growth rate.

These limitations are preferable to generation forcing or further structural
detail that would jeopardize the roughly three-minute end-to-end workflow. No
sensitivities were run; users remain responsible for scenario sensitivities.
