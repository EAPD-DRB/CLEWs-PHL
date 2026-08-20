# Philippines v16 energy-input and naming repair

On 2026-08-11 the live Philippines v16 source case received a non-forcing
energy-input correction. Three misleading `_T1` technology labels were
renamed without changing their stable IDs; offshore wind capacity factors,
geothermal availability and the onshore wind screened resource ceiling were
corrected in the source parameter JSON files.

The authoritative equation map, source locators, full-precision calculations,
before/after values and limitations are in
`../data_sources/calculation_notes/energy_inputs_v16_2026-08-11.md`. The exact
normalized input, source hashes and candidate validation are retained under
`../data_sources/snapshots/`.

## Changed source files

- `genData.json`: rename onshore wind, offshore wind and solar PV; stable
  technology IDs preserved.
- `RYT.json`: geothermal `AvailabilityFactor` 1.0 -> 0.9 and onshore-wind
  `TotalTechnologyAnnualActivityUpperLimit` 1,594.08 -> 663.84 PJ/year.
- `RYTTs.json`: scale the inherited offshore 30-timeslice profile from annual
  mean 0.19427924507532 to 0.2847380261587777.

No commodity, final demand, activity lower bound, share, user constraint,
technology ID, cost, lifetime or initial stock changed. No generated solver
file was edited.

## Validation

The disposable candidate passed deterministic checks, normal MUIOGO
generation and preprocessing, `glpsol --check`, full CBC optimization, result
export and comparison with the unchanged control. It solved optimally at
objective 369730088.2957073 in 215.64 seconds; the matrix was 791109 by 884956
with 12552173 nonzeros. All eight recorded checks passed.

Offshore construction remained zero with positive reduced cost. This is
reported deliberately: the corrected physical input improves calibration but
does not force the optimizer to select offshore wind.

The promoted live source was regenerated through the same chain and solved
optimally at objective 369730088.29570782. Source hashes exactly reproduce the
candidate, all seven live checks pass, and the objective differs from the
candidate by only 0.00000053. CBC selected a different degenerate
capacity/activity solution on the repeated solve; this is disclosed in the
live record. Final demand, annual technology emissions and the affected wind
and geothermal physical checks reproduce.
