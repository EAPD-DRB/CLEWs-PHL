# Philippines v25 VariableCost evidence

This package records the source-only build of `Philippines_v25` on 2026-08-25.
It reuses Claude's complete source package under `claude_source_package/` and
adds only the boundary corrections needed for the combined candidate.

## Crop boundary

The PSA detailed palay table gives cash cost components separately. The v25
resource-cost boundary starts with cash cost and subtracts fuel/oil, irrigation
fees, land tax, rentals and crop-loan interest. Fuel and irrigation are already
represented by the model's energy/water system; land scarcity is endogenous;
and financing is not a social resource cost. Non-cash and imputed costs were
already outside this cash boundary. The resulting net-cash/total-cost shares
are 0.518504758479 irrigated and
0.495905931287 rainfed. Applied to the inherited 2021 palay
basis, the costs are 6.476124 and
6.917888 PHP/kg respectively.

The same regime shares scale Claude's non-rice proposals. That preserves her
crop unit values, yields and exchange-rate arithmetic. It remains a proxy: PSA
does not publish national crop-by-crop cost structures for all modeled crops.

PSA source: `DB/2B/AA/CR/0012B5EAPC0.px`, Type = irrigated/non-irrigated,
Geolocation = Philippines, Item = all, Cropping Season = Average, Year = 2022.

## Roads

Claude's Philippine liquid-vehicle maintenance estimate remains the absolute
anchor for each vehicle class. Instead of scaling each drivetrain by purchase
price, v25 applies DOE/Argonne repair multipliers: LIQ/NG 1.00, PHEV 0.86,
BEV 0.67 and fuel-cell H2 0.67. The multiplier evidence is light-duty; its use
for buses and trucks is explicitly LOW-confidence extrapolation.

## Power and land

The power block is byte-for-value identical to Claude's proposal. The 40
previously omitted active land modes (25, 26, 28, 29 and 30 in eight clusters)
are explicitly classified as KEEP. They are non-crop land-cover/hydrology
routes, not crop modes; assigning crop cost would be wrong. Their inherited
0.0001 numerical cost remains unchanged, as does mode 27's -10 forest policy
incentive.

## Status

This is an unsolved candidate. No data generation, preprocessing, LP build,
GLPK check, CBC optimization, CSV extraction or viewer generation was run.
`V25_APPLIED.csv` is the complete cell-level change ledger and
`V25_LAND_MODE_CLASSIFICATION.csv` closes the 40-mode classification gap.
