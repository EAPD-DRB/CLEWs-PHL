# Philippines v18 fossil-resource and export accounting — 2026-08-14

## Outcome

Domestic coal and crude-oil extraction are no longer unlimited. The source model now applies continuing annual deliverability and opening recoverable-reserve constraints to gross domestic extraction while leaving coal and oil imports open. Source-tagged domestic commodities allow extraction to serve either the existing domestic raw-fuel pool or an optional export sink; imports cannot reach the export sinks.

No observed production, export volume, import share or source share is imposed. These remain validation benchmarks.

## Equation-first classification

- `PHL_PRO_EXTR_COAL` and `PHL_PRO_EXTR_OIL` are physical extraction technologies. `TAU` constrains gross annual extraction through `AAC2_TotalAnnualTechnologyActivityUpperLimit`; `TMPAU` constrains cumulative gross extraction through `TAC2_TotalModelHorizonTechnologyActivityUpperLimit`.
- `PHL_PRO_SUP_COAL_DOM` and `PHL_PRO_SUP_OIL_DOM` are lossless pass-throughs from source-tagged domestic commodities to the existing raw-fuel pools.
- `PHL_PRO_EXP_COAL` and `PHL_PRO_EXP_OIL` are optional consume-only export/accounting technologies. Negative variable cost represents external sale revenue. They do not create a domestic commodity.
- `PHL_PRO_IMP_COAL` and `PHL_PRO_IMP_OIL` remain open backstops with `TAU = TMPAU = 999999` and still produce only the existing domestic raw-fuel pools.
- Annual observed production and trade are benchmark-only. Depletion observations are used only to reconstruct opening resource stocks.

## Source changes

Structural changes were made in `genData.json` and propagated through `UpdateCase`, which regenerated the affected parameter tables while preserving existing values. The complete changed-file allowlist is:

- `genData.json`
- `RT.json`
- `RYT.json`
- `RYTCM.json`
- `RYTM.json`
- `RYC.json`, `RYCTs.json`, `RYCn.json`, `RYTCn.json`, and `RYTTs.json` (new-object default rows only)

The two new commodities are `PHL_PRO_COAL_DOM0` and `PHL_PRO_OIL_DOM0`. The four new technologies are `PHL_PRO_SUP_COAL_DOM`, `PHL_PRO_SUP_OIL_DOM`, `PHL_PRO_EXP_COAL`, and `PHL_PRO_EXP_OIL`.

Coal extraction is capped at 353.6 PJ/y (16 Mt/y at 22.1 GJ/t), rising to 442 PJ/y for the documented 2025–2027 20 Mt/y ECC amendment. Its reconstructed opening-2020 mineable reserve is 9,244.9474715 PJ (418.323415 Mt). The often-cited DOE 470 Mt figure is in-situ resource, not the mineable reserve used here.

Oil deliverability is anchored to the operator's forward 2026 work program of three approximately 120,000-barrel cargoes, backcast at the stated 10% annual field decline. It falls to 0.458673534 PJ in the partial 2027 operating year and zero from 2028 after planned cessation. Opening-2020 2P stock is 22.522423584 PJ (3.680736 million barrels).

The detailed calculations and primary-source URLs are recorded in `fossil_resource_accounting_inputs_2026-08-14.json`.

## Validation

The latest verifiable unchanged baseline was the byte-identical PHL v18 `TOMORROWLAND` result retained at `tmp/phl-v18-re-nuclear-20260813/candidate`: optimal objective 369,766,929.90727115, CBC wall time 426.77 s, and a 791,532-row / 886,010-column / 12,818,407-nonzero matrix. It was not rerun.

The accepted disposable candidate passed deterministic topology, parameter, inheritance, annual-envelope and cumulative-stock checks; UI-path `DataFile.generateDatafile('TOMORROWLAND')`; preprocessing; GLPK model generation/LP export; and an independent LP check. Its matrix has 808,404 rows, 900,022 columns and 12,892,667 matrix nonzeros.

CBC found an optimum of 369,760,466.35339457 in 432.01 wall seconds. The objective changed by −6,463.55387658 (−0.0017480%) and runtime by +1.23%, which is not a solve-time regression. Coal extraction totals exactly 9,244.94747 PJ and exhausts the opening reserve during 2045. Oil extraction totals 22.08343449 PJ, remains within the 22.522423584 PJ opening reserve, and is zero from 2028. Every annual extraction branch satisfies extraction = domestic bridge + export; the maximum reported balance error is zero.

Two optimizations were recorded. The first was rejected after it exposed a legacy `TAU.SC_3hgjb = 999999` coal-extraction override in the active `COAL_PHASEOUT` scenario. That generated equation allowed the full coal reserve to be exported in 2022. The failed source/equation indices were identified, all non-base fossil-supply `TAU` cells were changed to inherit the base physical constraints, and the required corrective candidate was then solved once. The rejected run is retained separately as `.Philippines_v18-fossil-resource-candidate-rejected-scenario-override` and was not promoted.

## Known calibration limitation

The accepted model endogenously exports 353.6 PJ of coal and 3.35747599 PJ of crude in 2022; all other modeled domestic extraction is routed to the domestic pool. This does not reproduce observed annual export profiles. The coal result particularly reflects aggregation of different coal grades, plant compatibility and inconsistent domestic/import/export price bases; the oil result reflects crude-grade and refinery-routing aggregation. Imposing historical export volumes or shares would violate the non-forcing rule, so this gap is disclosed for a later source/technology-quality calibration.

Full hashes, matrix deltas, activity ledgers, run records and benchmark findings are in `fossil_resource_accounting_validation_2026-08-14.json`.

## Promotion identity

Only the ten source JSON files and three audit documents listed above were promoted. Every promoted source file is byte-identical to the solved candidate. Regenerating the live `TOMORROWLAND` run produced a byte-identical `data.txt` (`6187825af1e1b6b7f7cd82dfc8ee0e8e8fc6c1717a1ff2ebfaa3e4769c9e58a0`). Candidate and live `data_processed.txt` are identical after canonicalizing nondeterministic ordering in AMPL set declarations (`20f592e8ebfc99c37eddaf35e3715ca52056d6ca6601a6532e9de7f5edd9d267`). The live GLPK check reproduced the accepted 808,404 × 900,022 matrix with 12,892,667 nonzeros. No post-promotion CBC solve was run because generated-model identity was established.
