# Fisheries (FSH) sector — input and Global-result-parity documentation

**Case:** `Philippines_v10` · **Fisheries version:** v2.3 · **Date:** 25 July 2026

Version 2 replaces the bottom-up fleet-fuel estimate used in v1 with a
top-down Philippine Department of Energy (DOE) energy balance and makes the
Fisheries/Industry boundary explicit. Version 2.3 targets parity with the
*results* of an uncalibrated CLEWs Global build: the sector contains normal
demand, stock, cost, efficiency, lifetime, availability and emissions data,
but no exact historical activity pins, special deployment dates or
Fisheries-only constraints. Technology choice and capacity investment are
endogenous in every model year.

The machine-readable inputs are in
`../../evidence/fisheries/FSH_calibration_data_v2.3.csv`. The associated
Industry deduction is in
`../../evidence/fisheries/FSH_industry_carveout_v2.3.csv`. The explicit
parameter comparison is in `FSH_GLOBAL_PARITY_v2.3.md`.

## 1. Accounting boundary

The model separates two statistical boundaries:

| Model service | Statistical boundary | Included energy |
|---|---|---|
| `PHL_FSH_MOT` | DOE Fishery | Fishing-vessel propulsion |
| `PHL_FSH_AQC` | DOE Fishery | Aquaculture pumping, aeration, hatcheries and other on-farm operations |
| `PHL_FSH_PRO` | Industry | Ice, cold storage, canning, freezing, drying and fishmeal |

Feed milling remains in Industry and is not included in `PHL_FSH_AQC`.
Processing remains represented explicitly by the FSH technologies because it
is useful for scenario analysis, but the same useful-service amount is
deducted directly from `PHL_INDU_OTH`; otherwise processing would be counted
twice.

The DOE Fishery total therefore calibrates `MOT + AQC`, not all three FSH
services. `PRO` is calibrated separately and reconciled against Industry.

## 2. DOE anchor and carrier balance

The 2023 DOE Situationer reports Fishery final energy consumption of **240.0
ktoe**, or **10.04832 PJ** using 1 ktoe = 0.041868 PJ. The detailed 2023 energy
balance reports Fishery petroleum use of 1.33 ktoe gasoline, 101.62 ktoe diesel
and 0.70 ktoe fuel oil: **103.65 ktoe** in total.

The model's liquid commodity is a generic petroleum/biofuel blend. A further
**2.145 ktoe** of biodiesel is allocated to Fishery in proportion to its diesel
use. This is an inference, not a separately reported Fishery datum. Electricity
is the residual required to match the reported Fishery total.

| Carrier | ktoe | PJ | Treatment |
|---|---:|---:|---|
| Petroleum | 103.650 | 4.3396 | DOE detailed balance |
| Allocated biodiesel | 2.145 | 0.0898 | Proportional allocation assumption |
| **Generic liquid total** | **105.795** | **4.429425** | Input to `PHL_PRO_LIQ` commodity chain |
| **Electricity** | **134.205** | **5.618895** | Residual to the 240.0 ktoe Fishery total |
| **Fishery total** | **240.000** | **10.048320** | DOE control total |

The 2023 balance is normalized to the model's 2020 base year. This avoids using
the pandemic-distorted 2020 Fishery observation and is consistent with the
2023 production basis used elsewhere in the FSH calibration. It means the
model's “2020” should be read as a representative recent operating year for
this sector.

Primary sources:

- Philippine DOE, *2023 Philippine Energy Situationer and Key Energy
  Statistics*: https://prod-cms.doe.gov.ph/documents/d/eppb/2023-energy-supply-and-demand-situationer-pdf
- Philippine DOE, *2024 Philippine Energy Situationer and Key Energy
  Statistics*, containing the detailed 2023/2024 balance tables:
  https://prod-cms.doe.gov.ph/documents/d/guest/2024-philippine-energy-situationer-and-key-energy-statistics-pdf

## 3. Base-year service calibration

### 3.1 Operational Fishery services

The carrier balance is allocated as follows:

- Aquaculture receives **0.352 PJ liquid** and all **5.618895 PJ electricity**.
  The liquid amount retains the non-feed on-farm diesel estimate from v1; the
  large electric residual covers pumps, aerators, hatcheries and other farm
  systems. This allocation is the principal remaining base-year assumption.
- Motive power receives the remaining **4.077425 PJ liquid** and zero
  electricity. This matches the DOE balance's diesel-dominated Fishery fuel
  mix and the lack of material electric-fleet deployment in the base year.

Useful activity equals final energy divided by the technology input-to-output
ratio (`IAR`):

| Service/technology | Final input (PJ) | IAR | Useful activity (PJ) |
|---|---:|---:|---:|
| `MOT_LIQ` | 4.077425 | 2.80 | 1.456223214 |
| `MOT_ELE` | 0 | 1.30 | 0 |
| `AQC_LIQ` | 0.352000 | 3.30 | 0.106666667 |
| `AQC_ELE` | 5.618895 | 1.15 | 4.885995652 |
| **Operational Fishery** | **10.048320** | — | **6.448885533** |

The motive-liquid IAR changes from 3.7 to **2.8**, representing about 36%
shaft efficiency. This is appropriate for a fuel balance that is more than 96%
diesel by energy; v1's gasoline-heavy 27% blended efficiency was inconsistent
with the DOE carrier data. The motive PM2.5 factor is correspondingly changed
to **9.1e-5 Mt/PJ useful**, using 1.4 g PM2.5/kg diesel and 43.1 MJ/kg.

### 3.2 Processing service

Processing stays at the documented v1 final-energy estimate but is explicitly
classified as Industry:

| Technology | Final input (PJ) | IAR | Useful activity (PJ) |
|---|---:|---:|---:|
| `PRO_LIQ` | 1.250 | 1.60 | 0.781250000 |
| `PRO_ELE` | 0.860 | 1.10 | 0.781818182 |
| **Processing total** | **2.110** | — | **1.563068182** |

The processing estimate remains lower-confidence: it is based on ice making,
cold storage, canning and drying activity assumptions rather than a national
fish-processing energy survey.

## 4. Residual stock without historical forcing

CLEWs Global country outputs normally include `ResidualCapacity` where
existing equipment stock is represented. Fisheries therefore includes
estimated 2020 residual stock even though a complete national equipment census
is unavailable. The estimate has the correct parameter meaning:

```
RC = observed useful service / (CAU × assumed historical utilization)
```

The utilization assumptions—12% for motive, 30% for aquaculture and 45% for
processing—are used only to estimate the amount of installed stock. They are
not retained as annual technical limits. `AF = 1` for all end-use converters,
matching the normal unrestricted converter semantics in the Global comparison
models. Consequently, the optimizer can operate inherited equipment at any
lower level or leave it idle.

| Technology | 2020 RC (GW useful) | Retirement |
|---|---:|---|
| `MOT_LIQ` | 0.384804460 | Straight line to zero in 2028 (8-year life) |
| `MOT_ELE` | 0 | No material 2020 electric fleet assumed |
| `AQC_LIQ` | 0.011274593 | Straight line to zero in 2035 (15-year life) |
| `AQC_ELE` | 0.516446353 | Straight line to zero in 2035 |
| `PRO_LIQ` | 0.055051722 | Straight line to zero in 2035 |
| `PRO_ELE` | 0.055091760 | Straight line to zero in 2035 |

Every Fisheries end-use technology remains open in every model year:

| Parameter | Value |
|---|---:|
| `TAL` | 0 |
| `TAU` | 999999 |
| `TAMinCI` | 0 |
| `TAMaxCI` | 999999 |

There are no Fisheries-only user-defined constraints or historical-activity
targets. The aggregate useful-service requirements remain exogenous through
`AAD`, as in other demand sectors. Without a demand, a cost-minimizing model
would rationally choose zero Fisheries service.

`CAU = 31.536 PJ/GW-year` for all FSH end-use technologies. Capital costs,
fixed costs, operating lives, efficiencies and emission factors remain the
documented engineering inputs used for endogenous choice. See
`FSH_GLOBAL_PARITY_v2.3.md` for the complete comparison and stock evidence.

## 5. Industry carve-out

`PHL_INDU_OTH` and `PHL_FSH_PRO` are both useful-service commodities measured
in PJ. The clean accounting treatment is therefore a direct service
disaggregation, not a coefficient derived from a saved model solution:

```
revised PHL_INDU_OTH SAD =
    original PHL_INDU_OTH SAD − PHL_FSH_PRO AAD
```

This reduces 2020 `PHL_INDU_OTH` SAD from **207.489160 to 205.926092 PJ** and
2053 SAD from **434.381986 to 430.236205 PJ**. The complete auditable series is
in `../../evidence/fisheries/FSH_industry_carveout_v2.3.csv`. This is an
input-boundary correction, not a
Fisheries activity constraint.

## 6. Projection assumptions

- `MOT` remains flat at 1.456223214 PJ useful per year.
- `AQC` retains the v1 growth multiplier of 2.625, increasing linearly from
  4.992662319 PJ in 2020 to 13.10573859 PJ in 2053.
- `PRO` increases linearly from 1.563068182 PJ to 4.145781 PJ, approximately a
  3% annual-growth endpoint expressed as a linear model path.

These are scenario assumptions, not DOE forecasts. The recalibration improves
the base-year energy balance; it does not validate long-run sector growth.

## 7. Verification targets

The verifier checks all of the following:

- Fisheries useful-service demands remain at the documented input values;
- unconstrained FSH activity bounds (`TAL = 0`, `TAU = 999999`);
- unconstrained FSH investment bounds (`TAMinCI = 0`, `TAMaxCI = 999999`);
- `AF = 1` for every FSH end-use technology;
- the documented residual-capacity values and lifetime-matched retirement;
- Industry SAD carve-out endpoints;
- existing schema, scenario-inheritance and network-connectivity invariants.

The historical carrier values—4.429425 PJ liquid, 5.618895 PJ electricity,
and 10.048320 PJ total operational Fishery energy—are comparison references,
not pass/fail targets for the endogenous solution.

The regenerated Base and PEP cases both solve optimally with CBC 2.10.12:

| Case | Objective | Complete pipeline time |
|---|---:|---:|
| Base | 375,954,258.369014 | 203.78 seconds |
| PEP | 375,977,200.488000 | 316.24 seconds |

Their endogenous 2020 Fisheries choices are the same to the reported
precision:

| Technology | Activity (PJ useful) | New capacity (GW useful) |
|---|---:|---:|
| `MOT_LIQ` | 1.4562 | 0 |
| `MOT_ELE` | 0 | 0 |
| `AQC_LIQ` | 3.9143 | 0.1128 |
| `AQC_ELE` | 1.0783 | 0 |
| `PRO_LIQ` | 1.5631 | 0 |
| `PRO_ELE` | 0 | 0 |

Delivered Fisheries electricity is 1.2400 PJ in both cases. Crucially, the
endogenous aquaculture mix does not reproduce the stock-estimation evidence
of 0.1067 PJ liquid and 4.8860 PJ electric useful service. Most inherited
electric aquaculture stock is left idle while the model builds liquid
equipment. This confirms that `RC` is functioning as available historical
stock, not as a historical activity constraint.

## 8. Remaining material uncertainties

1. Fishery electricity is calculated as a residual; a direct DOE carrier row
   for Fishery would be preferable.
2. The biodiesel allocation and the motive/aquaculture liquid split are
   assumptions and should be sensitivity-tested.
3. Residual capacities are effective-stock estimates from service and
   utilization, not surveyed nameplate capacity; BFAR vessel-horsepower data
   and equipment censuses would improve them.
4. Processing energy still lacks a Philippine enterprise-survey anchor.
5. Future aquaculture and processing growth paths remain judgmental.
6. The pre-existing Agriculture sector has its own energy-balance mismatch and
   was not changed as part of this Fisheries-only recalibration.

## Changelog

- **v2.3 (2026-07-25):** Global-result parity. Restored estimated residual
  stock as ordinary historical capacity, with retirement matched to each
  operating life; normalized end-use `AF` to 1 so historical utilization is a
  stock-estimation assumption rather than an activity ceiling; retained open
  activity/investment bounds; replaced the saved-solution Industry carve-out
  coefficient with a direct useful-service disaggregation.
- **v2.2 (2026-07-25):** Fisheries-only de-calibration. Removed all
  calibration-derived FSH residual capacities and the pre-2027 electric-motive
  investment restriction. All FSH technology activities, investments and
  carrier choices are now endogenous; service demands and engineering inputs
  remain.
- **v2.1 (2026-07-20):** removed exact 2020 FSH technology-activity pins after
  controlled A/B tests identified them as the source of CBC's severe solve-time
  regression; retained service demands, carrier-balance reference values,
  residual capacities and the pre-2027 electric-motive restriction.
- **v2 (2026-07-17):** DOE-normalized operational energy; diesel-consistent
  motive efficiency and PM2.5; explicit processing/Industry boundary;
  Industry double-counting carve-out; base-year activity constraints; residual
  capacities recalculated.
- **v1 (2026-07-17):** initial bottom-up Fisheries calibration.
