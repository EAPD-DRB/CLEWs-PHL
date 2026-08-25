# Philippines v16 energy-input and naming repair

On 2026-08-11 this live source case received a non-forcing energy-input
correction:

- `TEC_1wdli`, `TEC_bl1d7` and `TEC_1k064` retain their stable IDs but are now
  named `PHL_POW_PP_WON`, `PHL_POW_PP_WOF` and `PHL_POW_PP_SPV`; the misleading
  `_T1` suffix and “tier 1” descriptions are removed.
- Offshore wind's inherited 30-timeslice profile is uniformly scaled from a
  YearSplit-weighted annual mean of 0.19427924507532 to the NREL Philippine
  development-zone capacity-weighted net mean of 0.2847380261587777.
- Geothermal `AvailabilityFactor` is restored from 1.0 to 0.9.
- Onshore wind's annual activity ceiling is reduced from 1,594.08 to 663.84
  PJ/year, equal to the NREL/USAID restricted-screen total of 184.4 TWh/year.

Only `genData.json`, `RYT.json` and `RYTTs.json` changed. No commodity, demand,
lower bound, share, user constraint, technology ID, cost, lifetime or stock
changed. All policy-scenario null overrides are preserved and inherit the
`SC_0` physical inputs.

The disposable full-chain validation solved optimally at objective
369730088.2957073 in 215.64 seconds. Offshore construction remained endogenous
and zero with a positive reduced cost; no build was forced. Full source
citations, formulas, parameter-to-equation mappings, hashes, checks and known
limits are in the canonical Philippines v16 schema ledger package under
`Philippines_v16_CLEWs_build/data_sources/`.

The promoted live `ENERGY_INPUTS_BASE` run subsequently solved optimally at
objective 369730088.29570782 in 334.14 seconds. Its source hashes match the
validated candidate and all seven live checks pass. The repeated CBC solve
selected a degenerate alternative capacity/activity optimum; this does not
alter demand, annual technology emissions or the affected physical checks.
