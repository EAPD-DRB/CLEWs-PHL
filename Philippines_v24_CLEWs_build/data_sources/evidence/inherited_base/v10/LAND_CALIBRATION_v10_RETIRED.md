# Retired v10 land-system calibration — 17 July 2026

> **v12 status:** This file is retained only as lineage documentation. The
> seven v10 placeholder land technologies and `PHL_MIN_PRC` were retired in
> Philippines v12 and replaced by the uncalibrated, eight-cluster CLEWs Global
> land–agriculture–water system documented in `MODEL_BUILD_2026-07-25.md`.
> None of the demands, caps, or pseudo-price history described below is active
> in v12.

Before this change the six land classes existed but four of them
(`PHL_LND_LCRP/LFOR/LGRS/LOTH`) had **no demand and no consumer**, land supply
(`PHL_LND`) and precipitation (`PHL_MIN_PRC`) were uncapped (999999), and the
base year was steered with ±2 M$/unit pseudo-prices on three land techs. The
solved land areas were therefore degenerate (forest 42,538×10³ km² in 2020 —
141× the national territory) and the land→water balance (runoff/recharge/ET)
was decorative. This calibration makes the land module a real accounting layer:
every year the six classes partition exactly the national area, and
precipitation is finite.

Pre-fix copies of all case JSONs: `tmp/land-calibration-2026-07-17/pre-land-backup/`.
Re-runnable script: `tmp/land-calibration-2026-07-17/fix_land_system.py`.

## What was set

Units: areas 10³ km² (= 0.1 Mha); water 10⁹ m³ (km³).

| Class | AAD 2020→2053 | Source |
|---|---|---|
| `PHL_LND_LCRP` cropland | 111.59 flat | FAOSTAT 2020: arable 18.7477 % + permanent crops 18.6773 % of 298,170 km² land area = 55,898 + 55,688 km² (World Bank WDI mirror, AG.LND.ARBL.ZS / AG.LND.CROP.ZS / AG.LND.TOTL.K2) |
| `PHL_LND_LFOR` forest | 71.89 flat | FAO FRA 2020: 71,885.9 km² (AG.LND.FRST.K2, 24.11 % of land area) |
| `PHL_LND_LGRS` grassland | 15.0 flat | FAOSTAT 2020 permanent meadows & pastures: agricultural land 126,590 − cropland 111,586 = 15,004 km² |
| `PHL_LND_LBLT` built-up | 2.44→8.20 (kept) | modeler's original demand (NAMRIA-2010-style built-up ≈ 0.25 Mha, growing 3.4× — urbanization narrative), untouched |
| `PHL_LND_LWAT` inland water | 10.35 flat (kept) | modeler's original demand (NAMRIA-style mapped inland water ≈ 1.04 Mha), untouched |
| `PHL_LND_LOTH` other land | residual: 88.72 (2020) → 82.97 (2053) | `300.0 − Σ(others)` per year, floored to 4 decimals so the sum never exceeds the cap |

Total partitioned area = **300.0 ×10³ km²** = PH country area incl. inland
water (FAOSTAT: land 298.17 + inland water; FRA country report uses
30,000,000 ha). The residual "other land" covers what the five explicit
classes don't: shrubland (NAMRIA ~46), open/barren, marshland, fishponds,
and definitional slack between FAO land-use and NAMRIA land-cover accounting
— 83–89×10³ km² is consistent with NAMRIA's shrubs alone being ~46×10³ km².

As built-up grows (+5.76 over the horizon), the residual shrinks
one-for-one; cropland/forest/grassland are held at 2020 levels (calibration
baseline, not a projection).

## Caps (RYT.TAU, were 999999)

- `PHL_LND` (land supply): **300.0** — total land is now scarce; any future
  endogenous land user (Phase-2 aquaculture ponds, bioenergy) competes within
  the national area instead of conjuring land from nothing.
- `PHL_MIN_PRC` (precipitation): **705.0** ×10⁹ m³/yr = 300×10³ km² ×
  2.35 m/yr. 2,350 mm/yr is the rainfall the modeler already embedded in every
  land tech's IAR (each land unit consumes 2.35 water units, split into
  runoff+recharge+ET by class-specific OARs that each sum to 2.35). National
  average rainfall for PH is ~2,350 mm — the cap makes that budget finite and
  exactly sufficient when all 300 units of land are active.

Implied water balance once all land is demanded (2020): surface runoff
≈ 280, groundwater recharge ≈ 29, evapotranspiration ≈ 396 ×10⁹ m³/yr —
runoff+recharge ≈ 309 km³/yr against FAO Aquastat's ~479 km³/yr internal
renewable resources (same order; the class coefficients are the modeler's).

## Removed: 2020 pseudo-price steering (RYTM.VC)

`PHL_LND_BLT` +2, `PHL_LND_WAT` +2, `PHL_LND_FOR` −2 M$/unit in 2020 only
(all other cells 0.0001). The −2 on forest was a money pump — the solver ran
forest at 42,538×10³ km² in the old solve purely to collect negative cost.
With real demands there is nothing to steer; all three set to 0.0001 like
every other land-tech cell.

## Verification (full solve, CBC)

- All six class demands sum to exactly 300.0 in every year (script asserts
  residual > 0; floor-rounding guarantees Σ ≤ cap).
- Data file regenerated through the app's own pipeline (`DataFile.generateDatafile`
  → `preprocessData`) on a throwaway copy of the case and solved with CBC
  (2.10.13, 84 s): **Optimal, objective 375,955,097** vs 375,872,108 in the
  same-day pre-land-fix Base_v9 solve — +0.022 %, i.e. the energy system is
  unaffected (the delta is the 0.0001 land VCs on 300 units/yr plus the removed
  2020 steering credits).
- Solved land areas (10³ km², was → is):
  forest 2020 **42,538 → 71.89**, 2053 50.3 → 71.89; cropland 0 → 111.59;
  grassland 0 → 15.0; other 1.54 → 88.72 (2020) / 82.97 (2053); built-up and
  inland water unchanged on their demands (WAT no longer drifts to 40.4 by
  2053 — it was previously the cheapest runoff source).
- Total land activity exactly 300.0 every year; precipitation exactly 705.0
  (was pegged at the 99,999 numeric bound). The hydrological balance is now a
  real, finite budget.
- Existing solved results under `res/` were not modified — re-run scenarios
  from the app to regenerate them with the calibrated land system.

## Not done here (open items)

- **LULUCF / land CO2e**: land techs still carry no emission factors. Adding
  net-flux CO2e per class (afforestation sink, cropland/peat source) is a
  climate-accounting decision for the model owner — factors depend on whether
  the FOR class represents stable forest or regrowth.
- **No land-use *change* costs**: classes can swap area between years at zero
  cost. Fine while demands are exogenous; add transition costs/limits if land
  ever becomes endogenous.
- **Crop production is still not linked to LCRP** — the AGR module consumes no
  land. Phase-2 item.
- FAOSTAT (land *use*) and NAMRIA/PSA (land *cover*) disagree on cropland
  (111.6 vs 125.1×10³ km² in the PSA 2020 Land Asset Accounts: annual 59.4 +
  perennial 65.7). FAOSTAT chosen for internal consistency with the forest and
  meadows figures; swap to the NAMRIA set if the model should follow PSA
  environmental accounts instead.
