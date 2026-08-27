# Philippines v18 fossil border-price correction — 2026-08-18

## Scope and reason

The inherited mode-1 coal and crude import costs were undocumented. Coal export revenue used Semirara's blended realized selling price while crude export revenue used generic Brent. These inconsistent bases created a false 2022 coal incentive: the model exported the full 353.6 PJ domestic extraction envelope and replaced it with cheaper imports.

This change corrects external economic drivers. It does not constrain production, imports, exports, dispatch or source shares. Observed trade quantities remain validation benchmarks.

## Equation-first implementation

The four affected technologies are an open coal import backstop, an optional domestic-coal export sink, an open crude import backstop and an optional Galoc export sink. Only `RYTM.json / VC / SC_0 / mode 1` changes for 2020-2024. Non-base scenarios continue to inherit `SC_0`; the 2025-2053 price path, all physical constraints and all technology mappings remain unchanged.

`VC` is exported as `VariableCost`. It enters the discounted objective through `RateOfActivity * YearSplit * VariableCost` and is accounted for by `OC1_OperatingCostsVariable`. Import costs are positive; export revenues are negative.

Coal uses Philippine customs CIF/FOB values and quantities with 22.1 GJ/t. Crude imports use the DOE crude import bill and volume as one consistent landed-cost series. Galoc exports use company-reported realized prices with 6.119 GJ/bbl. Aggregate HS 2709 values were rejected for crude because that classification combines crude and condensate.

## Deterministic result expected before solving

The landed-import-minus-export-revenue spread becomes positive in every historical year. In 2022 it changes to +3.623430538 USD/GJ for coal and +1.256934636 USD/GJ for oil. Exporting a homogeneous domestic unit and replacing it with an import is therefore uneconomic.

This should remove the full-envelope coal export. It may also produce zero modeled Galoc exports. Actual simultaneous trade reflects coal-grade and crude/refinery-compatibility differences absent from the aggregated commodity structure. That mismatch is disclosed rather than hidden with trade pins or deliberately incorrect prices.

## Source and audit ledger

Full raw values, quantities, conversions, before/after cells, source URLs, equation mapping, rejected mixed-source calculation and known limitations are recorded in `fossil_border_prices_inputs_2026-08-18.json`.

## Validation and result assessment

The static validator passed the source-file allowlist, full-precision cells, unchanged 2025-2053 path, unchanged unrelated rows, scenario inheritance, positive historical price spreads and unchanged physical topology. Application generation and preprocessing preserved the intended values. The GLPK model check and LP export passed with the same full matrix as the immediately preceding pin-free power-investment case: 808,384 rows, 900,022 columns and 12,892,647 nonzeros.

One disposable CBC optimization was run, as budgeted. It reached an optimal objective of 369,762,721.4037087 in 288.70 wall seconds and 289,475 iterations. Against the immediately preceding pin-free result in `.Philippines_v18-power-investment-20260817` (369,758,319.2749507), the objective increases by 4,402.128758, or 0.001190542%.

The target defect is removed endogenously. The baseline exported 353.6 PJ of domestic coal in each of 2022 and 2023 and replaced it with imports. The candidate exports no coal and routes both annual extraction envelopes to the domestic coal pool. The coal extraction total and reserve use remain 9,244.9475 PJ, and every annual branch balance closes exactly.

The oil result also changes: the 3.357476 PJ 2022 export disappears and domestic use takes its place. The candidate does not extract oil in 2020 because the corrected 2020 economics make imports cheaper; total oil extraction falls from 22.08343449 to 17.938402 PJ. No output constraint was added to conceal that benchmark gap.

The historical price correction propagates through the coupled perfect-foresight solution. Model-period old-coal CHP activity falls by 271.567 PJ, geothermal activity rises by 181.4572 PJ, natural-gas processing rises by 64.0949 PJ, CO2e falls by 84.7983 model units and PM2.5 falls by 34.9666. It also selects different schedules among weakly distinguished long-run capacity options: 246 `NewCapacity` cells and 470 `TotalCapacityAnnual` cells change, led by electric two/three-wheel vintages. Solar PV moves 7.6926 GW from 2025 to 2022. No capacity parameter changed, and no pins were added to suppress this sensitivity.

The complete run identity, hashes, constraint activities and duals, outcome comparison, unexpected-change review, limitations and optimizer ledger are recorded in `fossil_border_prices_validation_2026-08-18.json`.

Promotion verification passed. Live `RYTM.json` and regenerated `data.txt` are byte-identical to the solved candidate. The live preprocessor serialized 92 derived sets in a different order, but a deterministic comparison proved identical set names and member multisets with every non-set line byte-identical. The live GLPK check passed and reproduced the candidate matrix dimensions. No post-promotion CBC optimization was run.

The canonical six-table schema ledger was also updated. It contains six source records, four assumptions, one full-precision calculation and model-map row for each of the 20 changed cells, two summary/equation maps, three updated or new gaps, the resolved change record, retained input and validation snapshots, supersession of the earlier trade diagnostic, and a regenerated review workbook. The focused ledger validator passed every cross-reference and retained-hash check.

## Known limitation retained deliberately

The correction removes a false arbitrage but does not reproduce observed simultaneous imports and exports. The current single coal pool cannot distinguish lower-grade export coal from plant-compatible imported grades; the single crude pool cannot distinguish Galoc crude from refinery-compatible imports. Representing that reality would require sourced grade/location/refinery substructure, not trade pins or deliberately distorted prices. Zero modeled exports therefore remain a disclosed aggregation limitation rather than a calibrated target.
