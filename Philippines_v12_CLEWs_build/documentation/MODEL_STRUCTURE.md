# Philippines v12 model structure

Philippines v12 is one integrated model assembled from three lineages. This
file explains the current structure; `HISTORY.md` explains the sequence of
changes.

| System | Main model objects | Connection to the rest of v12 |
|---|---|---|
| Historical energy | Power, fuels, transport, households, industry and other inherited v10 systems | Supplies electricity and other energy services |
| Fisheries v2.3 | Vessel motive power, aquaculture operations and fish processing | Uses liquid fuel and electricity; processing is removed one-for-one from aggregate Industry useful-service demand |
| Land–agriculture–water | Crop-land options, eight land clusters, land cover, precipitation, surface water and groundwater | Groundwater pumping uses agricultural electricity; irrigation and inherited water uses share raw water commodities |
| Environmental accounting | Exact in-model `ENV_LAND`; diagnostic `ENV_WATER` with authoritative Pivot publication; native emissions | Derived case adds seven parallel land stocks, an eight-mode land terminal and exact equality; diagnostic case retains a three-mode water terminal in the graph and publishes solved by-mode production/use residuals into its Pivot rows |

The new nexus connects to the inherited system through the MUIO commodities
`PHL_AGR_ELE`, `PHL_WTR_SUR`, `PHL_WTR_GWT`, `PHL_WTR_PRC`,
`PHL_WTR_EVT`, and `PHL_LND`. The upstream raw names are retained in the
build inputs where applicable; `MODEL_DATA_MAP.csv` records important
name mappings.

## Crop representation

The crop groups are rice, coconuts, maize, vegetables, sugar cane and other
crops. Each has high- and low-input, irrigated and rain-fed choices. Cluster
allocation technologies then apply spatial yield, water and land
coefficients.

The vegetable group uses tomato as its GAEZ agronomic proxy. “Other crops”
aggregates the remaining selected crops. These are structural modelling
choices and are not claims that the underlying crops are identical.

## Important accounting boundaries

- Direct crop production does not consume a liquid-fuel commodity.
- Irrigated crops consume a common agricultural-water commodity.
- That common water can be produced from surface water or groundwater.
- Groundwater pumping consumes agricultural electricity.
- Because water is pooled, the present model does not identify which crop
  caused a particular unit of groundwater-pumping electricity.
- The inherited `PHL_AGR_MOT_LIQ` demand is aggregate agricultural motive
  power and is not allocated to individual crops.
- `ENV_LAND` is an exact constrained technology in the derived
  `Philippines_v12_ENV_LAND` case and the diagnostic case.
- `ENV_WATER` is an unforced terminal technology in
  `Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC`. It remains visible in the
  Dynamic Graph, while its linked Results Pivot rows are replaced after each
  solve with the authoritative reporting residual. Raw solver CSVs retain the
  optimizer-selected activity.
- Parallel land-stock outputs preserve the original land services and connect
  the six land-cover and 24 crop-land technologies to `ENV_LAND`.
- `ENV_WATER` mode 1 is atmospheric water vapor; only modes 2 and 3 form the
  derived liquid-water residual.
- The groundwater-irrigation technology does not consume the raw
  `PHL_WTR_GWT` commodity, so its activity does not reduce the reported raw
  groundwater residual.
- The 30-mode cluster water coefficients cannot be represented exactly by the
  installed technology-level user-defined constraint. `ENV_WATER` is
  therefore not forced by a balance constraint; the Results Pivot publication
  supplies the exact reporting account instead.
- Native `CO2e` and `PM2_5` emissions are aggregated without adding factors.
