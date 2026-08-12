# Fisheries sector — CLEWs Global result-parity record

**Case:** `Philippines_v10` · **Fisheries version:** v2.3 · **Date:** 25 July 2026

## Target

The Fisheries sector is designed to have the same *kinds and meanings* of
inputs as a sector in an uncalibrated CLEWs Global country model. It does not
replicate the upstream data-gathering workflow or sources. Philippine evidence
and transparent estimates are acceptable where Global would normally populate
a parameter.

The comparison references are the raw CLEWs-style country inputs in:

- `Fiji_CLEWs_Global/model/inputs`
- `Philippines_v12_CLEWs_build/model/inputs/clewsy`

Those packages establish the relevant result pattern: exogenous demands,
technology input/output ratios, costs, operating lives, availability/capacity
factors where applicable, emissions, and residual capacity for existing
equipment. They do not establish exact historical activity locks as a normal
sector-building input.

## Parameter parity matrix

| Model meaning | Fisheries implementation | Parity status |
|---|---|---|
| Useful-service demand | `AAD` for motive, aquaculture and processing services | Present |
| Technology conversion | Mode-specific `IAR` and `OAR` | Present |
| Existing stock | Estimated `RC` for the five technologies with material 2020 stock | Present |
| Technical availability | `AF = 1` for end-use converters | Present; matches the normal unrestricted converter meaning |
| Capacity conversion | `CAU = 31.536 PJ/GW-year` | Present |
| Investment cost | Annual `CC` series | Present |
| Fixed operating cost | Annual `FC` series | Present |
| Variable cost | Carrier costs enter through the existing upstream fuel and electricity chains | Present; no duplicate FSH fuel adder |
| Asset lifetime | `OL` of 8, 12 or 15 years by equipment class | Present |
| Direct emissions | Technology-specific `EAR` for liquid technologies | Present |
| Demand projection | Transparent exogenous paths through 2053 | Present |
| Historical technology activity locks | None: `TAL = 0`, `TAU = 999999` | Deliberately absent, consistent with an uncalibrated build |
| Special deployment rules | None: `TAMinCI = 0`, `TAMaxCI = 999999` | Deliberately absent |
| Fisheries-only user constraints | None | Deliberately absent |

## Residual-capacity method

There is no complete public 2020 Philippine equipment-capacity inventory for
fishing propulsion, aquaculture machinery, and fish processing. Therefore,
`RC` is an **estimated effective installed stock**, not an exact census:

```
2020 residual capacity =
    observed useful service / (31.536 PJ/GW-year × assumed historical utilization)
```

The historical-utilization assumptions are 12% for fishing propulsion, 30%
for aquaculture equipment, and 45% for processing equipment. These assumptions
are used only to estimate stock. They are not entered as `AF`; the model may
operate inherited stock below its technical maximum or leave it idle.

| Technology | 2020 RC (GW useful) | Basis | Retirement |
|---|---:|---|---|
| `PHL_FSH_MOT_LIQ` | 0.384804460 | Observed liquid motive service; 12% utilization | Straight line to zero in 2028, matching 8-year life |
| `PHL_FSH_MOT_ELE` | 0 | Negligible material electric fishing fleet assumed in 2020 | — |
| `PHL_FSH_AQC_LIQ` | 0.011274593 | Observed liquid aquaculture service; 30% utilization | Straight line to zero in 2035 |
| `PHL_FSH_AQC_ELE` | 0.516446353 | Observed electric aquaculture service; 30% utilization | Straight line to zero in 2035 |
| `PHL_FSH_PRO_LIQ` | 0.055051722 | Estimated liquid processing service; 45% utilization | Straight line to zero in 2035 |
| `PHL_FSH_PRO_ELE` | 0.055091760 | Estimated electric processing service; 45% utilization | Straight line to zero in 2035 |

This stock estimate supplies historical information of the same model meaning
as CLEWs Global `ResidualCapacity`. It does **not** require the optimizer to
reproduce the historical carrier split. New investment is allowed from 2020
for every alternative.

As a physical-scale check, the BFAR 2020 profile reports 267,807 registered
municipal fishing vessels and 5,557 commercial vessels. The estimated motive
stock is about 1.41 kW useful per registered vessel when averaged across both
motorized and non-motorized registrations, so it should be interpreted as
effective national stock rather than surveyed engine nameplate capacity.
BFAR has also fulfilled a request for vessel-horsepower data through its FOI
system; that dataset is the preferred future replacement if its attachment is
obtained.

Evidence:

- [BFAR archive — Philippine Fisheries Profile 2020](https://www.bfar.da.gov.ph/media-resources/publications/archives-philippine-fisheries-profile/)
- [Philippine Statistics Authority — Fisheries Situation Report, January–December 2020](https://psa.gov.ph/content/fisheries-situation-report-january-december-2020)
- [BFAR FOI — engine horsepower of registered fishing vessels, 1995–2020](https://www.foi.gov.ph/requests/data-on-the-engine-horsepower-of-registered-commercial-municipal-fishing-vessels-in-1995-to-2020/)

## Sector boundary

Fish processing is represented explicitly in Fisheries but was originally
contained inside aggregate `PHL_INDU_OTH`. Both demands are useful-service
commodities measured in PJ, so double counting is removed by a direct
one-for-one useful-service disaggregation:

```
revised PHL_INDU_OTH SAD =
    original PHL_INDU_OTH SAD − PHL_FSH_PRO AAD
```

This is an input-data boundary adjustment, not a model constraint. It replaces
the earlier carve-out based on a saved solution's aggregate Industry energy
intensity. The full annual series is in
`../../evidence/fisheries/FSH_industry_carveout_v2.3.csv`.

## What the model remains free to decide

The model must meet the three exogenous Fisheries service demands, just as it
must meet demands elsewhere. It remains free to:

- use or idle residual equipment;
- select liquid or electric technologies;
- invest in either option from the first model year;
- retire inherited stock through the declared residual-capacity path; and
- choose different Fisheries outcomes in Base and PEP when system conditions
  make that cost-effective.

No Fisheries result is required to match an observed annual activity or
carrier share.
