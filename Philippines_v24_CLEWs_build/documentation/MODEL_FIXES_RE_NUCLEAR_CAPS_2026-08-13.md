# Philippines v18 RE nuclear commissioning ceilings

## Reason

The RE scenario retains the PEP 2023-2050 aggregate nuclear-capacity milestones of 1.2 GW in 2032, 2.4 GW in 2035 and 4.8 GW in 2050. The inherited RE `TAMaxCI` overlay nevertheless prohibited conventional nuclear throughout the horizon, while the v18 BASE deployment envelope did not allow either represented nuclear technology to commission before 2035.

## Source change

Only `RYT.json` `TotalAnnualMaxCapacityInvestment` (`TAMaxCI`) cells in scenario `SC_w03qj` change. Conventional nuclear receives a 1.20 GW/year ceiling in 2032-2034 and then inherits the unchanged BASE 1.20 GW/year ceiling from 2035. SMR receives a 0.30 GW/year ceiling in 2032-2034 and then continues to inherit the unchanged BASE ceilings of 0.30 GW/year in 2035-2039 and 0.60 GW/year from 2040.

No capacity minimum, activity bound, generation share, technology split or new constraint is introduced. `NUCLEAR_CAPACITY_TARGET` is unchanged and remains aggregate across conventional nuclear and SMR.

## Evidence and interpretation

DOE PEP 2023-2050 Volume III places construction of the first nuclear plant in Milestone 3 (2028-2032), first commercial operation in 2032, at least 1,200 MW in 2032, an additional 1,200 MW by 2035 and an additional 2,400 MW by 2050. It discusses conventional PWR and SMR options without prescribing a technology split. In OSeMOSYS, `NewCapacity` is commissioned capacity; construction starts are not represented separately.

## Validation

A disposable copy was generated and preprocessed through `DataFile.generateDatafile('TOMORROWLAND')` and `preprocessData()`. Deterministic validation confirmed that only 25 `TAMaxCI.SC_w03qj` cells changed and that no nuclear commissioning is allowed before 2032. GLPK successfully generated the complete matrix: 791,532 rows, 886,010 columns and 12,818,407 matrix nonzeros.

The single source-candidate CBC optimization completed optimal with objective 369,766,929.90727115 after 310,312 iterations and 426.77 wall-clock seconds. There was zero primal infeasibility after postsolve and cleanup. No nuclear capacity was built before 2032. The endogenous technology split was 0.9 GW conventional plus 0.3 GW SMR in 2032; cumulative capacity was 1.8 plus 0.6 GW in 2035; and 3.6 plus 1.2 GW in 2050, exactly meeting the unchanged aggregate PEP milestones. All annual construction caps were respected.

Two initial GLPK matrix-generation attempts ended before writing an LP because two stale CBC processes from the earlier failed/manual diagnosis were still consuming host memory. Those previously requested-to-stop processes were terminated; GLPK then completed normally. These matrix-generation attempts were not optimizer runs.
