# Philippines v16 non-forcing calibration review — 2026-08-07

## Status and scope

This is a read-only audit finding. No model parameter was changed, no solver
input was regenerated, and no candidate or policy scenario was solved.

The review tested the inherited annual capacity-investment bounds against the
non-forcing calibration rule. It focused on positive
`TotalAnnualMinCapacityInvestment` (`TAMinCI`) values and their corresponding
`TotalAnnualMaxCapacityInvestment` (`TAMaxCI`) values in `RYT.json`.

## Confirmed finding

`SC_0` (`BASE`) contains 20 positive `TAMinCI` cells across seven power
technologies in 2021-2025. In every cell, `TAMaxCI` is identical. The active
formulation therefore requires annual new capacity to equal the listed value;
these are exact investment pins, not merely lower limits.

The three policy scenarios use null inheritance for these cells. None overrides
any of the 20 pairs, so the same effective pins apply in all four scenarios:

- `BASE` (`SC_0`)
- `COAL_PHASEOUT` (`SC_3hgjb`)
- `RE` (`SC_w03qj`)
- `EV` (`SC_huc7i`)

The complete set of effective pins is:

| Technology | Year | Exact new capacity (GW) | Audit disposition |
|---|---:|---:|---|
| `PHL_POW_CHP_OIL_OLD` | 2021 | 0.1798 | Reconstruct any cutoff-date commitment; remove the exact maximum |
| `PHL_POW_CHP_OIL_OLD` | 2022 | 0.0973 | Reconstruct any cutoff-date commitment; remove the exact maximum |
| `PHL_POW_CHP_OIL_OLD` | 2024 | 0.0112 | Provisionally remove |
| `PHL_POW_PP_SPV_T1` | 2021 | 0.3024 | Partial support only; rebuild project by project |
| `PHL_POW_PP_SPV_T1` | 2022 | 0.3049 | Partial support only; rebuild project by project |
| `PHL_POW_PP_SPV_T1` | 2023 | 0.1568 | Provisionally remove |
| `PHL_POW_PP_SPV_T1` | 2024 | 1.0012 | Provisionally remove |
| `PHL_POW_PP_SPV_T1` | 2025 | 0.2749 | Provisionally remove |
| `PHL_POW_PP_NGCC` | 2025 | 0.8800 | Provisionally remove |
| `PHL_POW_PP_HY_LA` | 2022 | 0.0159 | Provisionally remove |
| `PHL_POW_PP_HY_LA` | 2023 | 0.0468 | Provisionally remove |
| `PHL_POW_PP_HY_LA` | 2024 | 0.0352 | Provisionally remove |
| `PHL_POW_PP_COAL` | 2021 | 0.7250 | Reconstruct any cutoff-date commitment; remove the exact maximum |
| `PHL_POW_PP_COAL` | 2022 | 0.7694 | Partial support only; rebuild project by project |
| `PHL_POW_PP_COAL` | 2024 | 0.6000 | Provisionally remove |
| `PHL_POW_GEO_OLD` | 2022 | 0.0037 | Provisionally remove |
| `PHL_POW_GEO_OLD` | 2025 | 0.0357 | Provisionally remove |
| `PHL_POW_CHP_BIOM_OLD` | 2022 | 0.0820 | Reconstruct any cutoff-date commitment; remove the exact maximum |
| `PHL_POW_CHP_BIOM_OLD` | 2023 | 0.0060 | Provisionally remove |
| `PHL_POW_CHP_BIOM_OLD` | 2024 | 0.0099 | Provisionally remove |

Even where an irreversible commitment could justify a minimum, the matching
maximum is not supported by that rationale: it also prohibits any additional
endogenous investment in the same technology and year.

## Provenance assessment

The internal case documentation does not provide a row-level source,
cutoff-date project ledger, or calculation for these 20 values.
`genData.json` contains the inherited note “v8 lower limit PPs generation
2021-2024 official stats,” but that note does not explain exact new-capacity
equalities, does not map projects to cells, and does not cover the 2025 values.
The inherited source gap also records that row-level energy bibliography is
missing.

For a consistent historical information test, this review used 31 December
2020 as the provisional cutoff because 2020 is the model's physical-stock
initialization year and endogenous investment begins afterward. DOE project
lists distinguish committed projects, which had secured financial close, from
indicative projects.

The official project-list comparison produced the following main matches and
limitations:

- Oil 2021 resembles the 179.8 MW commissioned INGRID plant, but the cutoff
  committed list described a 300 MW project. The exact value is therefore a
  later realized outcome.
- Oil 2022 resembles Isabel (86.3 MW) plus Mati/SPC (11 MW). The project basis
  is plausible, but the exact annual timing is later knowledge.
- Coal 2021 resembles Dinginin Unit 1. It was committed at the cutoff, but the
  cutoff rating was 668 MW rather than the later 725 MW value.
- Coal 2022 appears to combine Dinginin Unit 2 and Petron capacity. The entry
  has meaningful support but mixes cutoff and later information.
- Biomass 2022 can be associated with projects committed by the cutoff, but
  fixing their aggregate specifically in 2022 uses later timing information.
- The cutoff committed solar list totalled 408.57 MW. The model's annual solar
  sequence does not reproduce a traceable cutoff-date project schedule.
- Coal 2024 (600 MW) was still classified as indicative in the available 2020
  list and became committed later.
- The remaining later-year oil, gas, hydro, geothermal, biomass, and solar
  values either match later pipeline/commissioning information or could not be
  traced to an irreversible commitment known at the provisional cutoff.

These project matches are audit inferences, not a substitute for a permanent
project-level provenance ledger.

## Recommended modelling decision

1. Do not retain any of the 20 cells as an exact `TAMinCI = TAMaxCI` pair.
2. Create a dated project ledger containing technology mapping, capacity,
   status, evidence date, expected commissioning date, and the reason the
   project was irreversible at the chosen information cutoff.
3. Where that test passes, represent the commitment with only the least
   forcing formulation justified by the evidence. A commitment may justify a
   minimum; it does not normally justify the matching maximum.
4. Treat additions learned only after the cutoff as validation benchmarks, not
   constraints.
5. Decide the model's analytical perspective explicitly:
   - for a decision problem as known in 2020, retain the 2020 start and use
     post-2020 observations only for validation; or
   - for a forward-looking problem beginning in 2025, move capacity operating
     by the start of 2025 into initial stock with commissioning year and
     remaining lifetime, then optimize investment from 2025 onward.

The second option is a possible rebase, not a universal requirement. The
choice depends on the question the scenarios are intended to answer.

## External evidence consulted

- Philippine DOE, [Private Sector Initiated Power Projects archive](https://legacy.doe.gov.ph/private-sector-initiated-power-projects)
- Philippine DOE, [Luzon committed projects, December 2020](https://legacy.doe.gov.ph/sites/default/files/pdf/electric_power/luzon_committed_2020_december.pdf)
- Philippine DOE, [Luzon indicative projects, August 2020](https://legacy.doe.gov.ph/sites/default/files/pdf/electric_power/luzon_indicative_2020_august.pdf)
- Philippine DOE, [Visayas committed projects, June 2020](https://legacy.doe.gov.ph/sites/default/files/pdf/electric_power/visayas_committed_2020_june.pdf)
- Philippine DOE, [Mindanao indicative projects, August 2020](https://legacy.doe.gov.ph/sites/default/files/pdf/electric_power/mindanao_indicative_2020_august.pdf)
- Philippine DOE, [Existing power plants as of 31 December 2020](https://legacy.doe.gov.ph/electric-power/list-existing-power-plants-december-31-2020)
- [OSeMOSYS model structure and parameter definitions](https://osemosys.readthedocs.io/en/latest/manual/Structure%20of%20OSeMOSYS.html)

## Validation record

- Source inspection: passed for the 20 base-scenario pairs and policy-scenario
  inheritance.
- Internal row-level provenance: failed; no sufficient mapping was found.
- External project reconstruction: partial, as documented above.
- Source parameter changes: not performed.
- Generation and preprocessing: not run.
- GLPK matrix validation: not run.
- CBC optimization and baseline comparison: not run.

