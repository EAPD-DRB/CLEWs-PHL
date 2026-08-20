# Philippines v13 calibration changes

Date: 2026-07-27

## Purpose

This case recalibrates the inherited Philippines v12 environmental coefficients
without changing the energy-service demands, technology costs, capacity limits,
land accounting, or water diagnostic formulation.

## Source changes

- `genData.json`: PM2.5 unit changed from MTon to kt and the existing
  `PHL_TRA_SHIP_LIQ` technology was connected to PM2.5; the existing
  `PHL_HOU_COOK_OIL` technology was connected to CO2e for its LPG correction.
- `RYTEM.json`: all PM2.5 activity/change ratios were converted from MTon to kt;
  workbook-v5 technology factors were installed; liquid-navigation PM2.5 and
  cooking-oil CO2 correction links were added; and the blue-hydrogen CO2 capture
  credit was derived annually from its natural-gas input ratio.
- `RYE.json` and `RE.json`: PM2.5 penalties and limits were converted
  consistently with the new kt unit.

Cooking oil receives a -0.0102 Mt/PJ correction: processed oil still carries
the upstream 0.0733 Mt/PJ charge, and the correction nets LPG to 0.0631 Mt/PJ.
The stranded `PHL_POW_HEAT` coproduct remains a documented limitation because
no Philippine heat demand or defensible sink was available.

## Before/after formulation

All PM2.5 values below are kt per unit of technology activity. The v12 column is
the source MTon coefficient multiplied by 1,000, before physical recalibration.

| Technology | v12 equivalent kt | v13 kt |
|---|---:|---:|
| PHL_POW_PP_NGCC | 0.001 | 0.001655629139 |
| PHL_POW_PP_COAL | 0.008 | 0.04568817818 |
| PHL_POW_CHP_NG_OLD | 0.002 | 0.0028050641025 |
| PHL_POW_CHP_OIL_OLD | 0.052 | 0.15653846154 |
| PHL_POW_CHP_COAL_OLD | 0.011 | 0.12557388948 |
| PHL_POW_CHP_BIOM_OLD | 0.100 | 0.4000666667 |
| PHL_HOU_COOK_BIOM | 0.736 | 0.5 |
| PHL_HOU_COOK_COAL | 0.118 | 0.2 |
| PHL_HOU_COOK_OIL | 0.011 | 0.005 |
| PHL_TRA_CAR_LIQ | 0.00735 | 0.006867 |
| PHL_TRA_VAN_LIQ | 0.775 | 0.02725 |
| PHL_TRA_TRUL_LIQ | 0.419 | 0.0327 |
| PHL_TRA_TRUH_LIQ | 0.775 | 0.08175 |
| PHL_TRA_BUS_LIQ | 0.775 | 0.095375 |
| PHL_TRA_23WHEEL_LIQ | 0.0781 | 0.006213 |
| PHL_TRA_SHIP_LIQ | 0 | 0.0288324873096447 |
| PHL_TRA_RAILF_LIQ | 0.002475 | 4.50232558139535 |
| PHL_TRA_RAILP_LIQ | 0.002475 | 4.09302325581395 |

Fisheries ratios are not in the workbook calibration scope and were only
unit-converted: `PHL_FSH_MOT_LIQ` 0.091, `PHL_FSH_AQC_LIQ` 0.110, and
`PHL_FSH_PRO_LIQ` 0.050 kt per activity unit.

CO2e remains in MTon. `PHL_HOU_COOK_OIL` changes from no correction to
-0.0102 MTon/PJ. `PHL_POW_BH2_NG` changes from a constant -0.008 MTon/PJ to
`-0.70 × IAR(NG) × 0.055`, equal to -0.0557971 in 2020 and -0.0538462 in 2053.
PM2.5 EAR/EACR/AEL/MPEL quantities were multiplied by 1,000 and any PM2.5
penalty was divided by 1,000, preserving unit consistency.

## Calibration evidence and limitations

The PM2.5 technology ratios are the workbook v5 recommended rows. EDGAR is used
as a complete, method-consistent gridded inventory benchmark, not as
unquestioned national ground truth. Power and navigation remain explicitly
provisional in the workbook; road factors are top-down calibrated while the
underlying vehicle activity is pending reconciliation with LTO evidence.

Philippine DOE, UNFCCC BTR, EMB, PSA, LTO, PPA, and MARINA data remain the
preferred hierarchy for subsequent activity calibration. No exact positive
activity pins (`TAL = TAU`) were introduced.

## Validation status

Generation and source-preservation checks are recorded in
`calibration_generation.json`. Solver-chain and baseline-comparison results are
recorded separately in `VALIDATION_2026-07-27.md`; consult that file before
describing the case as fully validated.

The unchanged baseline is `Philippines_v12_CAL_CONTROL/BASE_CONTROL`. Generated
`data_processed.txt`, LP, CBC results, CSV outputs, timestamps, hashes, matrix
dimensions, objective comparison, emissions, capacity/activity differences,
constraint duals, and the four v13 scenario outcomes are recorded in
`validation_results.json`. BASE, COAL_PHASEOUT, RE, and EV passed the complete
application chain and solved optimal. The generic CLEWs audit did not pass
because of its underscore-ID parser false positive; its stranded
`PHL_POW_HEAT` warning is valid. Power and ship coefficients remain provisional,
and the workbook's 13.4 kt power validation cell is inconsistent with the
29.691591 kt produced by its own recommended factors in the current model.
The workbook's warning that a leading `1` is a stray 2020 EAR placeholder does
not apply to the application export: in the MathProg matrix form that `1` is
the mode index, followed by the 2020-2053 coefficient row. Source JSON and
generated-data spot checks confirm the 2020 values are the intended factors.
