# Philippines v12: current model

This is the plain-language description of the model that is active now.
Dated build notes and superseded formulations are retained under `history/`;
they are evidence of how the model evolved, not instructions for the current
model.

## What v12 contains

| Component | Origin | Current status |
|---|---|---|
| Energy system | Philippines v10 | Retained as the historical donor system |
| Fisheries | Philippines v10 Fisheries **v2.3** | Current formulation |
| Land, agriculture and water | CLEWs Global country workflow | New in v12; structurally integrated but not historically calibrated |

The source case is `WebAPP/DataStorage/Philippines_v12`. It contains 172
technologies, 92 commodities and three constraints, covers 2020–2053, and
uses the inherited 30-timeslice structure.

The derived accounting case is
`WebAPP/DataStorage/Philippines_v12_ENV_LAND`. It preserves the source case
and adds one eight-mode `ENV_LAND` technology, seven parallel land-stock
commodities and one exact land-balance equality, for totals of 173
technologies, 99 commodities and four constraints.

Its scenario display names are `BASE`, `COAL_PHASEOUT`, `RE`, and `EV`.
Internal `SC_*` identifiers remain in the parameter files as stable keys.

Fisheries v2.3 represents ordinary estimated residual stock with lifetime
retirement, availability factors of 1, open activity and investment bounds,
and a direct useful-service carve-out from Industry for fish processing. The
older v2.2 formulation is retained only in the history folders.

The land–agriculture–water block contains six crop groups, four production
options per crop, eight spatial clusters, land-cover accounting, and
surface-water and groundwater irrigation. Its crop demands, land availability,
water coefficients and production options came from the upstream country
workflow without historical tuning.

## Environmental accounts

The current delivery uses an exact in-model `ENV_LAND` terminal for Base and
PEP in the derived case. Its modes report forest, grassland, other land,
barren/savannah, built-up land, inland water bodies, cropland and unallocated
modeled land. Water vapor and raw groundwater/surface-water residuals remain
reporting-only, and native emissions use the existing mechanism.

The full account dictionary, equations, validation and interpretation limits
are in `ENVIRONMENTAL_ACCOUNTING.md`. The water accounts are not in-model
terminal technologies because the installed user-defined constraint cannot
represent the cluster technologies' mode-dependent water coefficients
exactly.

## Where to answer questions

- Start with `../data_sources/DATA_SOURCES.md` for the source register.
- Use `../data_sources/ASSUMPTIONS.csv` for analyst choices.
- Use `../data_sources/CALCULATIONS.csv` for formulas and transformations.
- Use `../data_sources/MODEL_DATA_MAP.csv` to connect a model name or
  parameter to its source, assumption and calculation.
- Use `../data_sources/calculation_notes/` for detailed records of calculations
  that the model actually uses.
- Use `HISTORY.md` to understand when and why the formulation changed.
- Use `KNOWN_LIMITATIONS.md` before making claims from the model.
- Use `ENVIRONMENTAL_ACCOUNTING.md` before interpreting water, land or
  native-emission accounts.

## Interpretation boundary

The v10 energy system and Fisheries v2.3 are inherited. The new nexus block is
a technically valid starting representation, not an independently calibrated
history of Philippine land use, yields, irrigation withdrawals or water
balances. Model results must be described with that distinction intact.

Environmental residual-water results are solution-specific diagnostics. They
must not be described as sustainable yield or unique water availability.
