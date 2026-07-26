# Philippines v12 data sources

The new land–agriculture–water block is an uncalibrated country build from the
pinned CLEWs Global workflow. The Philippines v10 energy data remain
inherited. The current v10 Fisheries v2.3 data and documentation were imported
on 25 July 2026.

Fisheries sources, assumptions, parameter mappings, government-review
decisions, and candidate national replacements are indexed separately in
`fisheries_v2.3/DATA_SOURCE_REGISTER.md`. Exact copies of the authoritative
v2.3 calibration, parity, parameter, and Industry-carve-out files are in that
same folder.

| Component | Source | Use in v12 |
|---|---|---|
| Administrative boundary | GADM 4.1, Philippines admin level 0 | National model boundary and land-cell clipping |
| Crop suitability and potential yields | FAO Global Agro-Ecological Zones v4 | Irrigated/rain-fed, high/low-input crop option coefficients |
| Crop water deficit, evapotranspiration, and precipitation | FAO GAEZ v4 | Cluster-specific agricultural water and precipitation coefficients |
| Land cover | FAO GAEZ v4 land-cover raster | Bare, built-up, forest, grassland, other, and water-body shares |
| 2020 crop harvested area and production | FAOSTAT tables bundled by CLEWs GAEZ/CLEWs Global | Top-crop selection and 2020 crop-output demand anchors |
| Demand growth | SSP2 population series, IIASA-WiC POP, bundled by OSeMOSYS Global | Population-only growth of crop-output demand from 2020 to 2053 |
| Philippine seasons | PAGASA climate description | Wet season June–November; dry season December–May |

Crop representation:

- Rice (`RCP`)
- Coconuts (`CON`)
- Maize (`MZE`)
- Vegetables using the GAEZ tomato proxy (`TOM`)
- Sugar cane (`SGC`)
- Other crops (`OTH`), aggregating the remaining selected crops

The `OTH` demand group includes the selected crops outside the five explicit
groups. Structural GAEZ proxies used during geospatial processing are documented
in `BUILD_REPORT.md`; they do not represent historical result fitting.

Source entry points:

- GADM: <https://gadm.org/download_country.html>
- FAO GAEZ v4: <https://gaez.fao.org/>
- FAOSTAT: <https://www.fao.org/faostat/>
- PAGASA climate information: <https://www.pagasa.dost.gov.ph/information/climate-philippines>
