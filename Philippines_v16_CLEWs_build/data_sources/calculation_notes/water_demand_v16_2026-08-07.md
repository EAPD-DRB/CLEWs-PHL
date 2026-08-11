# Philippines v16 water-demand calibration

This change corrects three accounting boundaries while leaving production and source choices endogenous.

- The `LNDAGRPHLC01`-`LNDAGRPHLC08` crop-land technologies are physical land-to-crop conversions. Their inherited `AGRWATPHL` coefficients represented net crop water. Dividing by 0.38 expresses gross diversion per unit of irrigated land activity.
- `PHL_PUB_WAT` is delivered final demand. Its annual demand is PSA Scenario 2 population multiplied by 70 litres/person/day and 365 days. The existing public surface and groundwater pass-throughs output 0.75 units of delivered water per unit produced, representing 25 percent NRW.
- `PHL_DEM_PUB_GWT_WAT` and `PHL_DEM_PWR_GWT_WAT` are existing groundwater pass-throughs. Their new electricity inputs are 0.70 PJ/km3, from `round(0.00981 * 50 m / 0.70, 2)`. This removes the free-pumping omission without prescribing the surface-groundwater choice.

No technology, commodity, demand for irrigated area, activity bound, source share, or user-defined constraint is added. Approximately 1.7 Mha of irrigated area is a benchmark only. Food demand, yields, land coefficients, costs, and water requirements must make irrigation competitive or necessary. If the model does not select it, the mismatch should trigger inspection of those drivers rather than an imposed area target.

The permanent source files are `case/Philippines_v16/genData.json`, `case/Philippines_v16/RYTCM.json`, and `case/Philippines_v16/RYC.json`. Structural membership is generated through `UpdateCase`; numerical overlays are produced by `scripts/calibrate_philippines_v16_water_demand.py`. The disposable candidate manifest and solve summary record hashes and model-chain results; generated `data.txt`, `data_processed.txt`, `lp.lp`, and result files are not promoted as model inputs.
