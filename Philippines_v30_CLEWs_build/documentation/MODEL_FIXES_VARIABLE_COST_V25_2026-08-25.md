# Philippines v25 VariableCost candidate

## Status

Built as a clean, source-only, deliberately unsolved candidate on 2026-08-25.
The deterministic source gate **passed**. No model generation,
preprocessing, LP construction, GLPK check, optimizer run, result extraction or
scenario viewer update was performed.

## Reason

The disposable vS experiment showed that replacing active 0.0001 VariableCost
placeholders can materially reduce CBC runtime and marginally improve historical
power reproduction. It also caused a large switch away from irrigated crop modes
and used vehicle purchase price as a universal maintenance proxy. V25 retains the
useful power block and corrects those two economic boundaries before any further
runtime or historical-fit claim is made.

## Equation-first classification

PSA production costs, Philippine vehicle maintenance and EIA variable O&M are
economic drivers. Historical power generation, irrigated area, water withdrawal,
crop mix and drivetrain shares remain validation benchmarks only. The change
touches `RYTM.json` `VC/SC_0`: in the active formulation VariableCost multiplies
endogenous activity in the objective and `OC1_OperatingCostsVariable`. No demand,
activity/share bound, stock, physical ratio, emission ratio, resource envelope,
scenario activation or equation changes.

Power technologies are physical conversion stocks; road technologies are physical
vehicle stocks delivering vehicle-km; crop modes convert land and water into crops;
land modes 25, 26, 28, 29 and 30 are non-crop land-cover/hydrology routes.

## Changes

* Power: 20 tech-mode rows / 680 year cells, copied exactly from Claude's sourced
  proposal, including source-convention zeros for wind and solar.
* Crops: 192 tech-mode rows / 6,528 year cells. Claude's 160 non-rice rows are
  scaled to PSA net cash resource cost; 32 existing rice rows receive the same
  boundary. The boundary excludes fuel/oil, irrigation fees, land tax, rentals and
  crop-loan interest from cash cost. It does not force irrigated area or crop mix.
* Roads: 28 tech-mode rows / 952 year cells. Claude's Philippine class-specific
  liquid anchors are retained. DOE/Argonne drivetrain repair multipliers replace
  purchase-price scaling: LIQ/NG 1.00, PHEV 0.86, BEV/FCEV 0.67.
* Land classification: 40 previously omitted active non-crop modes are now
  explicitly KEEP at 0.0001. The inherited mode-27 forest incentive remains -10.

Only `genData.json` identity/description fields and `RYTM.json` VariableCost values
differ from Philippines_v24. Complete cell-level values and provenance are under
`data_sources/variable_cost_v25_2026-08-25/`.

## Deterministic validation completed

The source gate checked candidate identity, root-source hashes, exact intended VC
cells, absence of scenario VC overrides and unintended edits, block counts, units
and magnitude envelopes, irrigated-versus-rainfed rice cost direction, all 40 land
classifications, the `dict.fromkeys` deterministic-ordering code, and absence of
solver/view artifacts.

## Not run / limitations

The next gate has intentionally not started. Generation/preprocessing, repeated
generated-data and LP hashes, GLPK matrix validation, all four CBC scenarios,
historical reproduction, irrigated-area/water response and runtime comparisons are
pending. The non-rice crop structure is still a palay-based proxy, and Argonne's
drivetrain multipliers are a low-confidence extrapolation for heavy vehicles.
