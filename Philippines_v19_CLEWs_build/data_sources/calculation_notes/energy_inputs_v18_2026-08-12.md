# Philippines v18 energy-input update

## Base and scope

V18 is generated from the committed Philippines v17 source. The v17 national
land-cover partition, annual closure, forest envelope, grass reserve,
built-up path, fixed land classes, cropland floor, and idle/fallow route are
retained. Source hashes prove that all files outside the five-file energy diff
are unchanged.

## Installed values

| Input | v17 | v18 | Basis |
|---|---:|---:|---|
| Geothermal availability | 0.90 | 0.70 | Defensible interim resource ceiling at the v16 dependable-capacity benchmark; the installed-capacity benchmark is 0.637. |
| Onshore wind annual CF | 0.176535 | 0.219731 | NREL restricted Philippines screen: 184.4 TWh / (95.8 GW × 8.76). The timeslice shape is retained and scaled. |
| Coal capital cost | 2,200 | 1,604.789 MUSD/GW | BNEF Philippines 2025 benchmark. |
| Nuclear SMR capital cost | inherited declining path from 4,482 | 8,000 MUSD/GW | NREL 2024 ATB reference central value used in the retained NREL projection. |
| Nuclear SMR life | 60 | 60 years | Confirmed; the proposed 40-year change is not supported as an operating-life correction. |
| Large-hydro life | 100 | 60 years | IRENA uses an average 60-year plant lifetime and reports component economic lives below the inherited 100 years. |

The coal-price conversion check uses the PR diagnostic's approximately
22.1 GJ/t DOE value. The exact DOE table byte and locator remain an evidence
gap, so v18 does not turn that check into a new coal-price forecast.

## Natural gas implementation

The existing `PHL_PRO_EXTR_NG` and `PHL_PRO_IMP_NG` routes are retained. Both
produce the existing raw-gas commodity that feeds the existing processing
technology.

Domestic extraction uses DOE production as annual ceilings for 2020-2024 and
a transparent 0.8% annual decline from the 2024 observation thereafter. Its
inherited price shape is scaled to the sourced 2020 Malampaya value of
USD 7.0289/MMBtu.

Imported gas is unavailable in 2020-2022. The 2023 ceiling is observed imported
LNG consumption (21,311 mmscf); from 2024 the ceiling is the DOE-reported
8 MTPA combined operating-terminal envelope, converted with 21,240 Btu/lb.
The 2023 price is USD 13.91/MMBtu and the 2024 path anchor is the ERC-reported
USD 14.9/MMBtu landed value. These become MUSD/PJ through the exact MMBtu-to-GJ
conversion. Pre-2023 import-price cells remain inherited but cannot operate.

## Cost-price convention

The inherited model declares USD and model cost units but no price year. V18
therefore records every source reference year and uses the source-year values
directly. It does not label them constant 2020 dollars. The missing common
price-year convention is retained as a high-priority gap.

## Validation

The full MUIOGO generation, preprocessing, GLPK matrix check, CBC solve, CSV
export, and viewer export completed. The result is optimal at
369743557.68076980. LNG activity is exactly zero through 2022, all domestic and
import gas activities respect their annual ceilings, and the v17 2020 land
partition and annual land closure are reproduced.
