# Philippines v12 build report

## 1. Objective and build boundary

The requested build had two preservation requirements:

1. retain the strong Philippines v10 energy system;
2. retain the fisheries system so that fisheries remains explicitly
   represented.

The country build therefore uses a documented hybrid boundary. All retained
v10 technology definitions and parameter records match the current v10
source. The Fisheries block was refreshed to v2.3 after the initial v12 build,
as documented in `FISHERIES_V23_IMPORT.md`. Only the eight placeholder
supply/allocation technologies listed below and their six exclusive land-class
commodities were retired:

- `PHL_MIN_PRC`
- `PHL_LND`
- `PHL_LND_OTH`
- `PHL_LND_GRS`
- `PHL_LND_BLT`
- `PHL_LND_WAT`
- `PHL_LND_FOR`
- `PHL_LND_CRP`

The v10 land calibration is archived inside the v12 case as
`LAND_CALIBRATION_v10_RETIRED.md` and is not active.

## 2. Upstream country build

The raw Philippines system was generated with the pinned CLEWs Global
workflow recorded in `sources/source_lock.json`.

Country configuration:

| Setting | Value |
|---|---|
| Country / ISO3 | Philippines / PHL |
| Model horizon | 2020–2053 |
| Administrative level | 0 |
| Projected CRS | EPSG:8857 |
| Climate pathway | RCP4.5 |
| Spatial clusters | 8 |
| Wet season | June–November |
| Dry season | December–May |
| Time zone | UTC+8 |
| Cross-border trade | Off |
| Transmission expansion | Off |
| Added policy targets | None |
| Added historical forcing | None |

The season definition follows PAGASA’s national climate description. GADM
4.1 supplies the admin-0 boundary. The processed land-cell area is 295,813.1
km²; no external country-area total was imposed.

## 3. Land, agriculture, and water representation

### Spatial land system

Eight clusters retain the following land-cell areas:

| Cluster | Area (km²) |
|---:|---:|
| 1 | 9,111.5 |
| 2 | 23,681.7 |
| 3 | 103,214.9 |
| 4 | 27,387.2 |
| 5 | 27,179.9 |
| 6 | 18,706.9 |
| 7 | 18,385.0 |
| 8 | 68,146.0 |
| **Total** | **295,813.1** |

Each cluster allocates activity among 30 modes: 24 crop-land options and six
land-cover classes. Cluster-specific coefficients represent potential crop
yield, irrigation water, precipitation, evapotranspiration, surface runoff,
and groundwater recharge.

### Crop groups

FAOSTAT 2020 harvested area selected the leading crop groups. The first five
are explicit outputs and the remaining selected crops are aggregated into
`OTH`.

| Output | Representation |
|---|---|
| `CRPRCP` | Rice |
| `CRPCON` | Coconuts |
| `CRPMZE` | Maize |
| `CRPTOM` | Other vegetables using the GAEZ tomato proxy |
| `CRPSGC` | Sugar cane |
| `CRPOTH` | Other selected crops |

Additional structural GAEZ mappings used to calculate the other-crops
potential are banana for other tropical fruits, plantains, and mango; para
rubber for natural rubber; and cassava for cassava. These are transparent
agro-climatic proxies, not result-fitting adjustments.

2020 production is the crop-output demand anchor. Demand then follows the
bundled SSP2 population trajectory; GDP elasticity is zero in this raw
configuration. The six demands are accumulated annual demands, leaving the
model free to select land options and clusters.

### Water and energy connections

The raw nexus commodities were mapped to inherited v10 commodities where the
physical meaning is the same:

| Raw commodity | v10/v12 commodity |
|---|---|
| `AGRELCPHLXX02` | `PHL_AGR_ELE` |
| `WTRSURPHL` | `PHL_WTR_SUR` |
| `WTRGRCPHL` | `PHL_WTR_GWT` |
| `WTRPRCPHL` | `PHL_WTR_PRC` |
| `WTREVTPHL` | `PHL_WTR_EVT` |
| `LTOT` | `PHL_LND` |

Groundwater irrigation consumes agricultural electricity. Surface irrigation
consumes surface water. Both produce the irrigation-water commodity used by
cluster crop modes. Cluster activity also supplies the surface-water and
groundwater commodities already used by the v10 cooling/public-water chains.

## 4. Technical corrections

The packaged patches and full replacement files document every correction.
The corrections are technical or structural; none tunes results to
observations.

1. Limited the diagnostic dendrogram sample to 750 land cells. Actual
   clustering still uses all cells.
2. Replaced non-NaN-aware built-in min/max handling in spatial normalization
   and handled constant-value columns.
3. Imputed only missing coastal/island raster attributes from the nearest
   valid projected land cell. Measured cells are untouched and boundary cells
   remain in the area total.
4. Added and deduplicated the exact crop proxy mappings needed by the selected
   Philippines crops.
5. Applied the documented CLEWs Global/clewsy operation-mode and packaging
   corrections, including a `setuptools<81` environment pin.
6. Removed stale Fiji-only raster cache entries from the temporary workflow
   cache before the final run.

## 5. MUIO integration and importer handling

An auxiliary full raw MUIO import was retained as
`Philippines_v12_raw_CLEWs`. Input round-trip parity was 98.6618%:
65 files were exact and three exposed importer limitations.

- MUIO does not directly import the two reserve-margin tag tables.
- The importer did not recognize the shortened
  `TechActivityByModeLowerLim` worksheet name, dropping 272 nonzero
  `TechnologyActivityByModeLowerLimit` values.

The missing lower limits are a relaxation and therefore did not explain the
auxiliary raw import’s infeasible solve. The final hybrid does not depend on
that imported parameter block: `build_v12_hybrid.py` reads the authoritative
sparse CLEWs CSVs directly, writes all 544 lower-limit rows, and retains the
272 positive structural minimum built-up/water land-cover values.

The energy system in the final case comes from v10, so unsupported reserve
margin tags from the auxiliary raw energy import are outside the hybrid graft.

## 6. Non-forcing audit

The raw nexus contains:

- no positive lower-equals-upper activity or capacity locks;
- no policy target or inherited user-defined constraint membership;
- no scenario-specific override values;
- no historical residual-capacity or activity calibration added during this
  build.

The 272 positive mode lower-limit values are minimum built-up/water
land-cover shares derived from the geospatial land-cover data. None equals an
upper limit.

The inherited v10 energy/fisheries system contains its previously documented
demands and scenario constraints. Those records were intentionally preserved
under the user’s explicit build boundary; the non-forcing audit above applies
to the newly generated nexus block.

## 7. Fisheries v2.3 replacement

The authoritative current v10 Fisheries v2.3 block was imported into v12. Its
sector boundary includes all seven Fisheries technologies, four Fisheries
commodities, and the `PHL_INDU_OTH` specified-demand row used to remove
explicit fish processing from aggregate Industry demand.

Relative to the earlier v12 state, exactly 12 active records changed: six
availability-factor rows, five nonzero residual-capacity paths, and the one
annual Industry carve-out row. The importer checked 2,115 Fisheries
definitions/parameter records and 140 scalar values against v10 v2.3 with zero
mismatches. Its before/after semantic hash confirmed zero changes outside the
Fisheries boundary.

The complete source documentation is in `sources/fisheries_v2.3/`, including
the machine-readable parameter table, annual Industry carve-out, parameter
parity note, and government-review source register. The source register also
flags the missing lookup key for several symbolic citations in the
authoritative v2.3 bundle.

## 8. Verification

### Authoritative raw solve

- Solver: CBC 2.10.12
- Status: Optimal
- Objective: 197,214.48967963
- Iterations: 11,962
- Primal/dual infeasibility: 0 / 0

### Integrated MUIO solves

| Run | Scenario stack | Status | Objective |
|---|---|---|---:|
| `Base_v12` | Base only | Optimal | 375,930,821.3405416 |
| `PEP_v12` | Base + coal phaseout + RE + EV | Optimal | 375,953,763.4595271 |

The MUIO Base matrix contains 769,139 rows, 860,236 columns, and 12,315,876
matrix nonzeros. PEP adds the inherited scenario constraints and also solves
with zero primal infeasibility.

Crop production meets all six accumulated annual demands in both integrated
runs. The largest relative difference in the four reported check years is
0.0243%, within the precision loss from MUIO’s rounded result CSVs.

The preservation audit checked:

- 130 retained technology definitions;
- 55 retained commodity definitions;
- 36,780 dimensioned parameter records;
- 2,612 scalar parameter values;
- all seven Fisheries technologies and their current v2.3 parameter records.

No mismatches were found.

## 9. Fitness and remaining work

Philippines v12 is technically valid and usable in MUIO for structural CLEWs
exploration. It is not a calibrated historical land/agriculture/water model.
Before using nexus results for policy advice, a separate calibration stage
should compare land-cover allocation, harvested area and production, crop
yields, irrigation withdrawals, groundwater/surface-water balances, and
seasonal water availability with Philippine observations.

Calibration should not alter the preserved energy/fisheries block unless a
separate, explicitly scoped review justifies those changes.
