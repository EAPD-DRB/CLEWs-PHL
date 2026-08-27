# Philippines v29 crop-land implementation

Date: 2026-08-26  
Parent: `Philippines_v28`  
Status: source implementation; CBC intentionally not run pending user review

## Structural change

The 24 `LND<crop><input><water>TOT` pass-through technologies and their 24 dedicated land commodities are deleted. Their agronomic choices remain exactly where the productive behavior already lived: modes 1-24 of each of the eight `LNDAGRPHLC01-08` technologies.

`LNDCROPTOT` now maps national land to one physical `PHL_CROPLAND` commodity. Every crop mode consumes it 1:1. `LNDOTHTOT` mode 2 consumes the same commodity and represents endogenous idle/fallow land. The obsolete v28 4 percent fallow-service rule is removed. Total 2020 cropland is initialized at 125.2805 thousand km2; the optimizer chooses cultivated versus idle area and every crop choice, with no post-2020 cropland floor.

`PHL_AGR_IRRIGATION` supplies one shared `PHL_IRRIGATION_SERVICE` commodity. All twelve irrigated crop modes consume it 1:1 and all rainfed modes consume none. Existing service capacity is 20.06 thousand km2, new 2020 investment is disabled because that stock is the historical initialization, and investment is optional from 2021. Crop-specific `AGRWATPHL` withdrawals are retained separately.

The global mode set remains 30; no solver equation or user-defined constraint is added.

## Crop costs

V29 replaces the v25 universal palay-share proxy and the same-cost high/low pairs. Costs are 2021 net resource cost per hectare: real paid, in-kind and imputed inputs and labour are included; land rent/tax, finance, and separately represented irrigation charges are excluded. Low input removes the source-reported fertilizer, pesticide and named chemical-treatment components. Values are constant in real terms after 2021.

| Cost class | MUSD per 1000 km2 |
|---|---:|
| coconut_high | 32.411659 |
| coconut_low | 10.870787 |
| maize_high | 47.197970 |
| maize_low | 36.257868 |
| other_high | 222.483984 |
| other_low | 170.804195 |
| rice_irrig_high | 91.597970 |
| rice_irrig_low | 75.307614 |
| rice_rain_high | 78.542132 |
| rice_rain_low | 68.986802 |
| sugarcane_high | 82.869441 |
| sugarcane_low | 52.961078 |
| vegetables_high | 373.934876 |
| vegetables_low | 295.770177 |

Rice, corn, cassava, mango, papaya and harvested-area weights come from the retained PSA OpenSTAT snapshot. Vegetables use a 2020-area-weighted Ampalaya/Cabbage/Eggplant/Tomato basket. Sugarcane uses SRA plant/ratoon direct costs and the reported national plant:ratoon area ratio. Coconut uses PCA unfertilized and multinutrient five-year budgets, rebased from 2010 to 2021 with Philippine CPI. The broad other-crops mode follows its retained area composition, using papaya for tropical fruit/plantain, annualized DA-roadmap rubber establishment, direct PSA cassava, and direct PSA mango.

These are better national economic coefficients, not a claim that the inherited high/low yields or crop GHG factors are calibrated. Those gaps remain explicit.

## Historical-calibration rule

Observed values initialize physical 2020 land and available irrigation stock. There is no crop activity target, crop share, cultivated-area target, fallow share, irrigation-use target, or new UDC. A future solve must be interpreted as an endogenous model result rather than reproduction by construction.

## Review and run boundary

The v29 pre-flight replaces obsolete v28 gates for 24 totalizers, 30 dedicated land commodities, productive-area arithmetic, and the 4 percent fallow service. It checks the new physical flows, shared irrigation reachability, source-backed costs, scenario inheritance, complete standalone provenance, and the real generated GLPK matrix. CBC must not be launched until the user approves this source implementation.
