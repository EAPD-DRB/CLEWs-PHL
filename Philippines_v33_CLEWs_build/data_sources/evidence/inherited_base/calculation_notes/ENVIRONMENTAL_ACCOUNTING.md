# Environmental-accounting calculations

Water and native-emission calculations are applied to normally generated
results. Land is also represented exactly in the derived
`Philippines_v12_ENV_LAND` case through parallel stocks and an aggregate
equality. The source `Philippines_v12` case remains unchanged.

## Water

For region `r` and year `y`:

```text
water_vapor[r,y]
  = production(PHL_WTR_EVT)[r,y] - use(PHL_WTR_EVT)[r,y]

groundwater_remaining[r,y]
  = production(PHL_WTR_GWT)[r,y] - use(PHL_WTR_GWT)[r,y]

surface_water_remaining[r,y]
  = production(PHL_WTR_SUR)[r,y] - use(PHL_WTR_SUR)[r,y]

liquid_water_remaining[r,y]
  = groundwater_remaining[r,y] + surface_water_remaining[r,y]
```

Production and use are summed across technology, operating mode and timeslice
from `ProductionByTechnologyByMode.csv` and
`UseByTechnologyByMode.csv`.

`PHL_WTR_EVT`, `PHL_WTR_GWT` and `PHL_WTR_SUR` all use `10^9 m3`.
Water vapor is not included in liquid water.

## Land

For every represented land technology `t`, the derived case adds a parallel
area-stock output:

```text
stock_output[t,m,y] = activity[t,m,y] × OAR_stock[t,m,y]
OAR_stock[t,1,y] = 1
```

The stock output is additional to the original crop, land-cover or service
output. It does not replace or consume that service.

`ENV_LAND` consumes one stock commodity per mode at IAR 1. Mode 8 consumes
residual `PHL_LND`. The exact aggregate equality is:

```text
activity(MINLNDTOT)[r,y] - total_activity(ENV_LAND)[r,y] = 0
```

Forest, grassland, other land, barren/savannah, built-up land and inland water
bodies equal modes 1–6. Cropland is mode 7 and equals the sum of the 24
crop-land-option activities. Mode 8 equals:

```text
production(PHL_LND)[r,y]
  - use(PHL_LND by original technologies)[r,y]
```

All land rows use `10^3 km2`. Terminal-to-source and aggregate closure use an
absolute tolerance of 0.005. Parallel stock-flow reconciliation uses 0.05
because the relevant result files sum many technology/mode/timeslice rows
rounded to four decimal places.

## Native emissions

For each native emission `e`:

```text
native_emission[r,e,y]
  = sum[t] AnnualTechnologyEmission[r,t,e,y]
```

No new factor or gas disaggregation is introduced.

## Result reconciliation

The reporter checks each environmental production and use result against:

```text
TotalAnnualTechnologyActivityByMode[t,m,y]
  × effective IAR or OAR[t,c,m,y]
```

where IAR is Input Activity Ratio and OAR is Output Activity Ratio. The
maximum accepted difference is 0.002 in the commodity unit, reflecting
four-decimal result-CSV rounding across timeslices.

The reporter also requires explicit `Optimal` status and preserves SHA-256
hashes for the selected JSON, generated-input and result evidence.
