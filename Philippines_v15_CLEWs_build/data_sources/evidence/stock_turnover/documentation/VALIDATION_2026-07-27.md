# Philippines v13 calibration validation

Date: 2026-07-27

## Outcome

The fresh unchanged control and calibrated BASE run are both optimal. The
objective changed from `375930821.340544283390` to `375930821.340545535088`,
a difference of `1.25169754028e-06` (3.32959541817e-13%).

All application-chain checks passed for BASE, COAL_PHASEOUT, RE, and EV:
`DataFile.generateDatafile`, `preprocessData`, `glpsol --check`/LP generation,
CBC optimization, CSV generation, and pivot generation.

## 2020 environmental results

| Account | v12 control | v13 calibrated |
|---|---:|---:|
| PM2.5 cooking | 0.174200000 MTon | 118.360000 kt |
| PM2.5 power | 0.003300000 MTon | 29.691600 kt |
| PM2.5 road exhaust | 0.044600000 MTon | 3.879400 kt |
| PM2.5 navigation | 0.000000000 MTon | 11.359700 kt |
| PM2.5 fisheries | 0.000600000 MTon | 0.641300 kt |
| PM2.5 total represented | 0.222700000 MTon | 163.932000 kt |
| CO2e total | 97.273400000 MTon | 97.273400000 MTon |

The workbook's recommended power factors produce 29.691591 kt in the solved
model, not the 13.4 kt displayed on its EDGAR-validation sheet. This is 47.79%
above EDGAR's 20.09 kt benchmark, so the power block remains provisional.

## Policy feasibility

| Scenario | Status | Objective | Change from v13 BASE |
|---|---|---:|---:|
| COAL_PHASEOUT | Optimal | 375940123.060255 | 0.00247432% |
| RE | Optimal | 375936089.421922 | 0.00140134% |
| EV | Optimal | 375938218.984896 | 0.00196782% |

## Baseline comparison and constraint checks

The v13 matrix has 797,363 rows, 889,036 columns, and 12,560,100 matrix
nonzeros. The two added emission links account for 68 additional rows and
columns across 34 years. Objective-row nonzeros remain 422,220 because no
emissions penalty is active.

At `5e-05` result tolerance, the activity comparison has
80 changed rows:
22 are classified to the
existing unforced water diagnostic and
58 are outside that classifier.
The capacity comparison has 0 changed rows,
of which 0 are water
diagnostic rows. Full ranked differences are in `validation_results.json`.

Annual/model-period emissions limits and emissions penalties are inactive.
The 2020 and model-period CO2e and PM2.5 constraint duals are all zero.

## Checks not passed or limitations

- The generic CLEWs audit exits failed because its ID parser truncates
  `COM_env*`, `TEC_envland*`, and `TEC_envwater*`; direct and generated-data
  checks confirm the full IDs exist. Its `PHL_POW_HEAT` stranded-output warning
  is real and unchanged.
- Power and navigation PM2.5 coefficients are provisional; the road factors are
  top-down EDGAR calibrated against activity that still needs LTO reconciliation.
- The workbook's “stray 1 in 2020” warning is a parsing mistake for the
  application-generated MathProg matrix: the leading `1` is the mode index.
  Source JSON and generated data confirm the intended 2020 EAR values.
- Missing national PM2.5 sectors were not fabricated. Crop-residue burning,
  manufacturing, fugitive solid fuels, waste burning, cement, rice cultivation,
  and road resuspension remain outside the model.
- No exact positive activity pins (`TAL = TAU`) were introduced.
