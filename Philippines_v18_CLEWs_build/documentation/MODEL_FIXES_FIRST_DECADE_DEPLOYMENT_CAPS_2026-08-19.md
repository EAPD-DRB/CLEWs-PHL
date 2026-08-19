# Philippines v18.0.1 first-decade deployment ceilings, 2026-08-19

## Result

The established 2026-2029 deployment bands for the ten specified existing v18 technologies now apply throughout 2020-2029. Coal was already 2 GW/year throughout the decade, and solar PV had already been corrected to 4 GW/year. This change corrects 47 additional `TAMaxCI.SC_0` cells.

| Existing v18 technology | 2020-2029 | 2030-2039 | 2040-2053 |
|---|---:|---:|---:|
| `PHL_POW_PP_WON` | 1.5 | 3.0 | 5.0 |
| `PHL_POW_PP_SPV` | 4.0 | 7.0 | 10.0 |
| `PHL_POW_PP_COAL` | 2.0 | 2.5 | 3.0 |
| `PHL_POW_PP_COAL_CCS` | 2.0 | 2.5 | 3.0 |
| `PHL_POW_PP_NGCC` | 2.0 | 2.5 | 3.0 |
| `PHL_POW_PP_NGCC_CCS` | 2.0 | 2.5 | 3.0 |
| `PHL_POW_GEO_OLD` | 0.15 | 0.25 | 0.35 |
| `PHL_POW_PP_HY_LA` | 1.0 | 1.5 | 2.0 |
| `PHL_POW_PP_BIOM_CCS` | 0.20 | 0.30 | 0.40 |
| `PHL_POW_PP_H2` | 0 | 1.0 | 2.0 |

The table states expansion headroom bands. Existing later-year residual-retirement and permitted-vintage recycling allowances remain unchanged, so some individual post-2029 `TAMaxCI` cells remain slightly above the displayed headroom.

No offshore-wind, nuclear, minimum-investment, residual-capacity, total-capacity, policy-overlay, or unlisted-technology value was changed.

## Validation status

Static comparison confirms exactly 47 source-cell changes. Application generation, preprocessing, LP generation, optimization, and portable-archive repackaging were not run. The change remains `resolve_required` pending a user rerun.
