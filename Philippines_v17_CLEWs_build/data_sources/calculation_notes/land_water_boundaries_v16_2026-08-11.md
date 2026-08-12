# Philippines v16 land and water source boundaries

This note closes three provenance ambiguities without changing a model input,
constraint, commodity, technology, activity, result, or equation.

## PSA crop observations

The retained PSA OpenSTAT snapshot is the authoritative 2020 national source
for the selected palay, corn, coconut, and sugar-cane production and area
observations. This provenance update does not alter crop coefficients. Observed
areas remain initial-stock inputs or validation benchmarks according to their
physical meaning; they are not crop-activity targets.

## AQUASTAT boundary

Two different FAO comparisons must not be spliced together:

| Selection | Withdrawal | Net requirement | Ratio | Permitted use |
|---|---:|---:|---:|---|
| AQUASTAT 2012 Table 4, Philippines, 2006 | 65.590 km3/year irrigation withdrawal | 33.280 km3/year | 50.739%, published as 51% | Internally comparable historical gross/net check |
| Current AQUASTAT dissemination, Philippines, 2020 | 67.85109005 km3/year agricultural withdrawal, variable 4250 | 33.280 km3/year, variable 4260 | 49.049% | Broader boundary benchmark only |

Variable 4260 is a net irrigation requirement: delivery losses are excluded.
Variable 4250 is agricultural withdrawal and is broader than irrigation alone.
The current pair therefore must not be treated as a direct national irrigation
efficiency estimate. The reviewed value 67.965 km3/year was not reproduced as
a single current FAO Philippines observation; it is not entered as a source
value. No Philippines-specific FAO reliability warning was located in the
reviewed official material, so the ledger records FAO's general country-data
and boundary limitations without attributing a country-specific caveat. The
provenance update does not install or change an irrigation-efficiency value.

## Coconut product boundary

PSA labels the production observation `Coconut (w/ husk)`. Philippines v16
therefore defines `CRPCON` as whole coconut with husk at the farm-gate crop
boundary. It is not copra.

The Philippine Coconut Authority's tall-variety brochure reports mean fruit
weights and copra per nut whose central-value ratios span approximately 4.65 to
5.28 kg whole fruit per kg copra. Dwarf-variety examples widen the practical
central-value range to approximately 4.50 to 5.28. This confirms that treating
whole-fruit tonnes as copra tonnes creates a several-fold mass error, but it
does not justify one universal conversion coefficient. Variety, maturity,
moisture, processing yield, and product definition must be specified.

No copra commodity or conversion process is represented in v16. If a future
study needs copra, add a separately sourced processing conversion and demand
boundary; do not silently rescale `CRPCON`.

## Calibration gate

Before promoting further land/water calibration, the change must:

1. preserve the PSA product and area definitions;
2. keep AQUASTAT gross/net comparisons as benchmarks unless a compatible
   scheme- or crop-specific efficiency source is installed; and
3. keep whole coconut and copra as distinct mass boundaries.

These observations do not authorize crop-area, production-share, irrigation-
share, or water-withdrawal pins.
