# Philippines Fisheries v2.3 data source register

## Build identity

- Country / ISO3: Philippines / PHL
- Sector: Fisheries
- Imported model version: v2.3
- Model horizon: 2020–2053
- Register date: 25 July 2026

## Exact named sources

| Source ID | Provider | Product | Edition/reference | Variable or evidence used | Geography | Model use | Transformation | Quality | Official URL | License/reuse note | Suggested review owner |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FSH-DOE-2023 | Philippine Department of Energy | *2023 Philippine Energy Situationer and Key Energy Statistics* | 2023, p. 14, Figure 11 and accompanying paragraph | Fishery final energy control total: 240.0 ktoe | Philippines | Base-year motive + aquaculture energy anchor | Converted with 1 ktoe = 0.041868 PJ; normalized to the model’s 2020 representative base year | Official national statistic | https://prod-cms.doe.gov.ph/documents/d/eppb/2023-energy-supply-and-demand-situationer-pdf | Public government publication; exact reuse terms were not recorded in the v2.3 bundle | DOE Energy Policy and Planning Bureau |
| FSH-DOE-2024 | Philippine Department of Energy | *2024 Philippine Energy Situationer and Key Energy Statistics* | p. 34, “2023 Energy Balance Table,” Fishery row | 2023 Fishery petroleum: gasoline 1.33, diesel 101.62, fuel oil 0.70 ktoe | Philippines | Liquid-carrier total and residual electricity derivation | Petroleum summed; 2.145 ktoe biodiesel allocated by assumption; electricity calculated as residual to 240.0 ktoe | Official petroleum data plus documented inference | https://prod-cms.doe.gov.ph/documents/d/guest/2024-philippine-energy-situationer-and-key-energy-statistics-pdf | Public government publication; exact reuse terms were not recorded in the v2.3 bundle | DOE Energy Policy and Planning Bureau |
| FSH-DOE-2024-REVISION | Philippine Department of Energy | *2024 Philippine Energy Situationer and Key Energy Statistics* | p. 14, Figure 10, “AFF Energy Demand Mix, by Sub-sector” | Fishery energy: revised 2023 value 170.8 ktoe and 2024 value 193.3 ktoe | Philippines | Data-vintage diagnostic; not used in v2.3 | No model transformation; exposes a conflict with the active 240.0-ktoe control total | Official later-vintage national statistic | https://prod-cms.doe.gov.ph/documents/d/guest/2024-philippine-energy-situationer-and-key-energy-statistics-pdf | Public government publication; exact reuse terms were not recorded in the v2.3 bundle | DOE Energy Policy and Planning Bureau |
| FSH-BFAR-PROFILE-2020 | Bureau of Fisheries and Aquatic Resources | *Philippine Fisheries Profile 2020* | 2020, pp. 21, 47 and 51 | 39,090 registered fisherfolk engaged in fish processing; 267,807 registered municipal and 5,557 commercial fishing vessels | Philippines | Vessel counts are a physical-scale check on estimated motive residual capacity; the processing count is contextual evidence only | National counts compared with effective GW stock; no count is used as a direct nameplate-capacity or energy input | Official sector profile | https://www.bfar.da.gov.ph/wp-content/uploads/2023/01/2020-Fisheries-Profile.pdf | Public government publication; exact reuse terms were not recorded in the v2.3 bundle | BFAR Planning, Monitoring and Evaluation Division |
| FSH-PSA-2020 | Philippine Statistics Authority | *Fisheries Situation Report, January–December 2020* | 2020 | Fisheries-sector context cited with stock evidence | Philippines | Plausibility/context review; no parameter is copied directly from this report | None documented | Official national statistic | https://psa.gov.ph/content/fisheries-situation-report-january-december-2020 | Public government publication; exact reuse terms were not recorded in the v2.3 bundle | PSA Fisheries Statistics Division |
| FSH-BFAR-FOI-HP | Bureau of Fisheries and Aquatic Resources / Freedom of Information Philippines | *Data on the engine horsepower of registered commercial & municipal fishing vessels in 1995 to 2020* | Request covering 1995–2020 | Vessel horsepower dataset requested and reportedly fulfilled | Philippines | Preferred future replacement for effective-stock estimates | Attachment was not obtained and no values from it are used in v2.3 | Candidate national source, not an active input | https://www.foi.gov.ph/requests/data-on-the-engine-horsepower-of-registered-commercial-municipal-fishing-vessels-in-1995-to-2020/ | FOI portal terms apply; attachment licensing was not assessed | BFAR Fisheries Regulatory and Licensing Division |
| FSH-GLOBAL-COMPARATORS | CLEWs Global/MUIO local build packages | `Fiji_CLEWs_Global/model/inputs` and `Philippines_v12_CLEWs_build/model/inputs/clewsy` | Local build state, 25 July 2026 | Presence and meaning of demand, conversion, stock, cost, life, availability and emissions parameters | Whole-country comparator models | Parameter-semantics parity only | Structural comparison; comparator numerical values are not copied into Fisheries | Modelled comparator evidence | Local workspace paths | Repository licenses apply | SFU CLEWs Global development team |

## What session `019f86a0-c9a4-7d51-9f5d-1eb97ee2d075` adds

The raw session log is useful forensic evidence, but it is not itself a
government data source. It establishes the following:

- The session began on 21 July by auditing an already-built Fisheries v2.1.
  The v1 bottom-up build and v2 DOE recalibration are dated 17 July and were
  already present. Therefore this log does not contain the original lookup
  table for `S4`, `S6`–`S10`, `S12`, or `S16`–`S17`.
- On 25 July the v2.3 work downloaded the exact BFAR 2020 profile linked above,
  extracted the vessel counts on pp. 47 and 51, and inspected the registered
  fish-processing count on p. 21. It also searched for BFAR vessel-horsepower
  microdata, but did not obtain a usable attachment. No horsepower values from
  the FOI request enter the model.
- The log contains no search, download, or retained bibliography that names the
  publications behind the unresolved engineering symbols. It therefore cannot
  turn those symbols into exact citations.
- The log does expose an important DOE vintage conflict. The active model
  combines the 240.0-ktoe Fishery total from the 2023 Situationer with detailed
  petroleum data from the later 2024 Situationer. The later report’s p. 14,
  Figure 10 instead gives 170.8 ktoe for 2023 and 193.3 ktoe for 2024.

If the later 170.8-ktoe value were adopted while retaining the current
105.795-ktoe generic-liquid calculation, the operational Fishery total would
be 7.1510544 PJ and the electricity residual would be 2.72162934 PJ, rather
than 10.048320 PJ and 5.618895 PJ. This is a diagnostic counterfactual, not a
change to v2.3: DOE should first confirm which vintage and carrier table are
internally consistent.

## Forensic reconstruction of legacy symbolic citations

The v2.1, v2.2, and v2.3 documentation and parameter registers were compared
with the 17 July model-fix record and the surviving build/handoff records.
This recovers the meaning of the active symbols, but not every lost
bibliographic identity. “Exact” below means that the publication, locator,
value, and role can be recovered from retained records. “Semantic only” means
that the affected value and intended evidence type are known, but the original
publication or URL is not.

| Legacy symbol | Reconstructed meaning and model use | Recovery status |
|---|---|---|
| `S4` | Supports the v1 bottom-up processing estimate (1.25 PJ liquid and 0.86 PJ electricity) and, together with `S12`, the roughly 1,050 h/year fishing-fleet utilization basis. The retained documents do not name its publication. The BFAR 2020 profile is now a **plausible but unproven candidate** because it contains both vessel counts (pp. 47 and 51) and a fish-processing livelihood count (p. 21), but it contains neither the energy estimate nor the operating-hours value. | **Semantic only.** Do not relabel `S4` as the BFAR profile unless the original citation key or calculation worksheet confirms it. |
| `S6` | Engineering evidence for direct-electric ice/refrigeration efficiency, represented by `IAR = 1.10` (about 91–92% useful efficiency). | **Semantic only; original citation lost.** |
| `S7` | Cost evidence for liquid outboard engines; used with `S8` to select about USD 45/kW-input from a stated USD 19–80/kW-input range. | **Semantic only; original citation lost.** |
| `S8` | Electric-outboard cost and deployment evidence; used in motive capital cost and, through v2.2, the former 2027 deployment assumption. | **Semantic only; original citation lost.** The deployment restriction was removed in v2.3. |
| `S9` | Electric-motive engineering evidence: 87% drivetrain efficiency, 90% battery/charger efficiency, and motor/battery cost components. | **Semantic only; original citation lost.** |
| `S10` | Diesel PM2.5 evidence: 1.4 g PM2.5/kg fuel, used in the three liquid-technology emission-factor calculations. | **Semantic only; original citation lost.** |
| `S12` | Fishing-fleet operating-hours evidence used with `S4` for the historical 12% utilization estimate (about 1,050 full-load-equivalent h/year). | **Semantic only; original citation lost.** |
| `S16` | Diesel-engine/genset efficiency evidence used for 36% fishing-shaft efficiency and 30% aquaculture genset/motor efficiency. | **Semantic only; original citation lost.** |
| `S17` | Equipment-life evidence: 1,500–4,000 engine hours and 3,000+ LFP cycles, informing 8-year liquid-motive and 12-year electric-motive lives. | **Semantic only; original citation lost.** |
| `S18` | `FSH-DOE-2023`: Philippine DOE, *2023 Philippine Energy Situationer and Key Energy Statistics*, p. 14, Figure 11 and text reporting 240.0 ktoe Fishery energy use in 2023. | **Exact.** |
| `S19` | `FSH-DOE-2024`: Philippine DOE, *2024 Philippine Energy Situationer and Key Energy Statistics*, p. 34, “2023 Energy Balance Table,” Fishery row: gasoline 1.33, diesel 101.62, and fuel oil 0.70 ktoe. | **Exact.** |

The surviving named BFAR profile, PSA situation report, and BFAR FOI request
are genuine evidence retained by v2.3. However, no surviving record proves
which earlier `S1`–`S3` label belonged to which item, so those labels are not
reassigned here.

### Assumption codes are not external data sources

The `A` prefix denoted analyst assumptions or calculations. These entries can
be reconstructed from the retained parameter rows even though they do not
resolve to publications:

| Legacy symbol | Reconstructed assumption or calculation | v2.3 status |
|---|---|---|
| `A5` | Processing conversion mix: liquid processing `IAR = 1.60`; electric processing `IAR = 1.10`. | Active |
| `A7` | Aquaculture conversion assumptions: liquid `IAR = 3.30`; electric `IAR = 1.15`. | Active |
| `A8` | Electric-motive capital-cost construction and learning path. | Active |
| `A9` | Capital-cost proxies for aquaculture and processing equipment. | Active |
| `A10` | Fixed-cost proxies for Fisheries technologies. | Active |
| `A11` | Historical utilization assumptions of 30% for aquaculture and 45% for processing. | Used only to size residual stock; no longer used as technical `AF`. |
| `A12` | No scaled electric-outboard deployment before about 2027. | Removed in v2.3. |
| `A13` | Fifteen-year life for stationary aquaculture and processing equipment. | Active |
| `A14` | Base-year carrier allocation: 0.352 PJ liquid plus residual electricity to aquaculture; remaining liquid to motive. | Active |
| `A15` | Aquaculture-demand endpoint multiplier of 2.625. | Active scenario assumption |
| `A16` | Fisheries/Industry anti-double-counting boundary. In v2/v2.2 it used a saved-solution energy-equivalent deduction. In v2.3 it is the direct accounting identity `revised PHL_INDU_OTH SAD = original PHL_INDU_OTH SAD − PHL_FSH_PRO AAD`, because both terms are useful-service demands in PJ. The logged implementation changes 2020 from 207.489160 to 205.926092 PJ and 2053 from 434.381986 to 430.236205 PJ. | **Exactly reconstructed; analyst boundary rule, not a publication.** |

The annual `A16` calculation is fully reproduced in
`FSH_industry_carveout.csv`. Government review should therefore assess whether
fish processing is already contained in the aggregate Industry boundary and
whether a one-for-one useful-service disaggregation is appropriate; it should
not look for an external publication named “A16.”

## Parameters and assumptions

The exact values, interpolation rules, and row-level tags are in
`FSH_calibration_data.csv`; annual Industry deductions are in
`FSH_industry_carveout.csv`. The main transformations are:

| Decision/parameter group | Current source or assumption | Model use | Status for government review |
|---|---|---|---|
| Operational Fishery demand | DOE 2023 total and DOE detailed carrier balance, with a later DOE revision conflict | `PHL_FSH_MOT` and `PHL_FSH_AQC` accumulated annual demand | Ask DOE to reconcile 240.0 ktoe with the later 170.8-ktoe 2023 value and to provide a same-vintage carrier table; replace residual electricity if a direct Fishery electricity row is available |
| Biodiesel share | 2.145 ktoe allocated in proportion to Fishery diesel use | Generic liquid-carrier total | Explicit inference; sensitivity candidate |
| Motive/aquaculture allocation | Aquaculture receives 0.352 PJ liquid and the residual 5.618895 PJ electricity; motive receives the remaining liquid | Base-year useful-service split used to derive demand and stock | Assumption; BFAR/DOE review requested |
| Processing energy | 1.25 PJ liquid and 0.86 PJ electricity | `PHL_FSH_PRO` useful-service demand | Lower-confidence engineering estimate; replace with enterprise-survey or subsector energy data |
| Conversion efficiencies and PM2.5 | Engineering values and symbolic v2.3 source tags in the parameter CSV | `IAR` and `EAR` | Review with DOE/BFAR; see documentation gap below |
| Capital and fixed costs | Engineering estimates and symbolic v2.3 source tags | `CC` and `FC` | Review with BFAR, DTI, equipment suppliers, and operators |
| Residual capacity | Useful service divided by 31.536 PJ/GW-year and assumed historical utilization of 12%, 30%, or 45% | `RC`, retired over declared operating life | Effective-stock estimate, not a census; BFAR equipment/vessel data preferred |
| Technical availability | 1 for all Fisheries end-use converters | `AF` | Normal unrestricted converter semantics; historical utilization affects stock sizing only |
| Technology life | 8, 12, or 15 years by equipment class | `OL` and residual-stock retirement | Engineering assumption; sector review requested |
| Demand projection | Motive flat; aquaculture endpoint multiplier 2.625; processing linear to 4.145781 PJ in 2053 | Annual `AAD` paths | Scenario assumptions, not official forecasts |
| Industry boundary | Direct one-for-one subtraction of `PHL_FSH_PRO` useful demand from `PHL_INDU_OTH` useful demand | Annual `SAD` carve-out | Validate with PSA/DOE/DTI subsector accounting experts |

## Remaining documentation gap from the authoritative v2.3 bundle

`FSH_calibration_data.csv` uses symbolic citations such as `S4`, `S6`,
`S7`–`S10`, `S12`, and `S16`–`S19`, plus assumption codes such as `A5` and
`A7`–`A16`. The exact meanings of the active symbols and the exact identities
of `S18`, `S19`, and all `A` assumptions have now been reconstructed above.
The v2.3 package still does not contain the lookup table that expands `S4`,
`S6`–`S10`, `S12`, or `S16`–`S17` to publications or URLs. Those unresolved
codes must not be presented as fully traceable sources.

This gap does not prevent reproducing the imported model values—the complete
values and transformations are bundled—but it does limit source-level review
of some engineering inputs. The preferred correction remains to obtain the
original citation key from the Fisheries author. If it cannot be recovered,
replace each unresolved input with a newly selected, fully traceable source or
an explicitly labelled analyst assumption; do not silently claim that a
replacement source was the original citation.

## Government review

| Decision | Current evidence/assumption | Why it matters | Suggested reviewer | Better national data? | Status |
|---|---|---|---|---|---|
| Fishery energy total and carriers | DOE 2023/2024 Situationers; 240.0-ktoe active anchor conflicts with the later 170.8-ktoe 2023 value; electricity is residual | Sets the sector’s base-year scale and liquid/electric balance | DOE EPPB | Confirmed same-vintage Fishery total, petroleum, electricity, and biofuel rows | **High priority** |
| Motive vs aquaculture split | Documented allocation assumption | Drives service demands and estimated inherited stock | BFAR and DOE | Fleet fuel survey; aquaculture equipment-energy survey | Review requested |
| Processing energy | Bottom-up engineering estimate classified inside Industry | Affects explicit processing demand and Industry carve-out | PSA, DTI, BFAR | Establishment-level fish-processing energy survey | High priority |
| Fishing-vessel stock | Effective stock checked against vessel counts | Influences early-year capacity without forcing activity | BFAR | Vessel horsepower and operating-hours microdata | High priority |
| Aquaculture/processing stock | Effective stock from assumed utilization | Influences early-year technology choices | BFAR, PSA, DTI | Equipment census, power ratings, utilization | High priority |
| Costs, efficiencies, lives, emissions | Engineering assumptions with partially unresolved source codes | Affects endogenous technology choice | DOE, BFAR, DTI, DENR | Philippine equipment/vendor and emissions data | Review requested |
| Long-run demand paths | Judgmental linear paths | Drives future Fisheries scale | BFAR, NEDA, PSA | Official sector outlook or scenario set | Review requested |
| Fisheries/Industry boundary | Direct useful-service disaggregation | Prevents double counting | PSA and DOE | Consistent subsector energy/service accounts | Review requested |
