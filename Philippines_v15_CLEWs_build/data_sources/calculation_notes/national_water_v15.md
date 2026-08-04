# Philippines v15 national-water source trace

This note routes every installed water value from evidence through calculation to the live JSON source and solver equation. It documents the v15 water delta; parameters inherited unchanged from v14 are traced to `SRC_PHL_V14_CASE` and the legacy register in `docs/philippines_v14_stock_turnover/`.

## Observation classification

- Initial stock: none. The 20.2 km3/year groundwater value is annual national potential flow, not aquifer storage.
- Final demand: unchanged. Public water, cooling water and crop demands retain the v14 source paths.
- Continuing constraints: ERA5 1991-2020 precipitation normal, one SSP2-4.5 ensemble-median relative path, and national surface/groundwater potential-flow sensitivities.
- Benchmarks only: ERA5 annual context, p10/p90 projections, PSA abstraction and stress, historical regional groundwater figures, local groundwater studies and MGB categorical screening.

## Source hierarchy

1. World Bank CCKP ERA5 climatology supplies the 2658.12 mm/year 2020 anchor.
2. World Bank CCKP CMIP6 SSP2-4.5 ensemble-median anomalies supply relative 2030 and 2050 multipliers; IPCC AR6 supports the requested 4.5 W/m2-equivalent framing.
3. DEPDev's water-sector policy note supplies 125.79 km3/year surface and 20.2 km3/year groundwater potential; PDP Chapter 12 independently confirms the groundwater and total figures.
4. The v14 source case supplies inherited full-precision land/hydrology ratios and the national land activity envelope.
5. The v15 manifest, validation report and full-precision water ledger prove the source rows, equations and solved balances.

## Source-to-equation mapping

| Physical behavior | Source JSON | Generated representation | Active equation/effect |
|---|---|---|---|
| Groundwater irrigation consumes raw groundwater | `genData.json`; `RYTCM.json` | IAR=1 for DEMAGRGWTPHL / PHL_WTR_GWT / mode 1 | EBb4 annual commodity balance prevents irrigation water from being created from electricity alone |
| National precipitation/hydrology follows ERA5 + SSP2-4.5 median | `RYTCM.json` | 960 BASE rows across eight classes, 30 modes and four water ratios | EBb4 uses the scaled IAR/OAR coefficients; inherited hydrological shares remain unchanged |
| Gross surface withdrawal is capped | `genData.json`; `RYCn.json`; `RYTCn.json` | WATER_SUR_AVAIL, Tag 0, UCC annual series, CAM=1 for three routes | UDC1 inequality; exact activity sum because every route is single-mode with raw-water IAR=1 |
| Gross groundwater withdrawal is capped | `genData.json`; `RYCn.json`; `RYTCn.json` | WATER_GWT_POTENTIAL, Tag 0, UCC annual series, CAM=1 for three routes | UDC1 inequality; exact activity sum; potential flow only, not stock/depletion |
| Annual publication | `documentation/national_water_ledger.json` | full-precision activity, EBb4, UDC residual and dual records | Authoritative post-solve ledger; ENV_WATER remains an unforced diagnostic |

## Full installed annual paths

All volumes are km3/year. The combined factor is ERA5 rebase times the SSP2-4.5 median multiplier.

| Year | SSP2-4.5 multiplier | Combined hydrology factor | Modeled precipitation | Surface UCC | Groundwater UCC |
|---:|---:|---:|---:|---:|---:|
| 2020 | 1 | 1.08461281153075 | 786.306717372 | 125.79 | 20.2 |
| 2021 | 1.00101226585298 | 1.08571072804356 | 787.102668811964 | 125.917332921646 | 20.2204477702302 |
| 2022 | 1.00202453170596 | 1.08680864455638 | 787.898620251928 | 126.044665843293 | 20.2408955404604 |
| 2023 | 1.00303679755894 | 1.0879065610692 | 788.694571691892 | 126.171998764939 | 20.2613433106905 |
| 2024 | 1.00404906341192 | 1.08900447758201 | 789.490523131856 | 126.299331686585 | 20.2817910809207 |
| 2025 | 1.0050613292649 | 1.09010239409483 | 790.28647457182 | 126.426664608231 | 20.3022388511509 |
| 2026 | 1.00607359511788 | 1.09120031060765 | 791.082426011783 | 126.553997529878 | 20.3226866213811 |
| 2027 | 1.00708586097086 | 1.09229822712046 | 791.878377451747 | 126.681330451524 | 20.3431343916113 |
| 2028 | 1.00809812682383 | 1.09339614363328 | 792.674328891711 | 126.80866337317 | 20.3635821618415 |
| 2029 | 1.00911039267681 | 1.09449406014609 | 793.470280331675 | 126.935996294816 | 20.3840299320716 |
| 2030 | 1.01012265852979 | 1.09559197665891 | 794.266231771639 | 127.063329216463 | 20.4044777023018 |
| 2031 | 1.01177122307385 | 1.09738003088403 | 795.562509146652 | 127.27070215046 | 20.4377787060918 |
| 2032 | 1.01341978761791 | 1.09916808510915 | 796.858786521665 | 127.478075084456 | 20.4710797098817 |
| 2033 | 1.01506835216196 | 1.10095613933427 | 798.155063896678 | 127.685448018453 | 20.5043807136716 |
| 2034 | 1.01671691670602 | 1.10274419355939 | 799.451341271691 | 127.89282095245 | 20.5376817174616 |
| 2035 | 1.01836548125008 | 1.10453224778451 | 800.747618646704 | 128.100193886447 | 20.5709827212515 |
| 2036 | 1.02001404579413 | 1.10632030200963 | 802.043896021717 | 128.307566820444 | 20.6042837250415 |
| 2037 | 1.02166261033819 | 1.10810835623474 | 803.34017339673 | 128.514939754441 | 20.6375847288314 |
| 2038 | 1.02331117488225 | 1.10989641045986 | 804.636450771743 | 128.722312688438 | 20.6708857326214 |
| 2039 | 1.0249597394263 | 1.11168446468498 | 805.932728146756 | 128.929685622435 | 20.7041867364113 |
| 2040 | 1.02660830397036 | 1.1134725189101 | 807.229005521769 | 129.137058556431 | 20.7374877402012 |
| 2041 | 1.02825686851442 | 1.11526057313522 | 808.525282896782 | 129.344431490428 | 20.7707887439912 |
| 2042 | 1.02990543305847 | 1.11704862736034 | 809.821560271795 | 129.551804424425 | 20.8040897477811 |
| 2043 | 1.03155399760253 | 1.11883668158546 | 811.117837646808 | 129.759177358422 | 20.8373907515711 |
| 2044 | 1.03320256214658 | 1.12062473581058 | 812.414115021821 | 129.966550292419 | 20.870691755361 |
| 2045 | 1.03485112669064 | 1.1224127900357 | 813.710392396834 | 130.173923226416 | 20.903992759151 |
| 2046 | 1.0364996912347 | 1.12420084426082 | 815.006669771847 | 130.381296160413 | 20.9372937629409 |
| 2047 | 1.03814825577875 | 1.12598889848594 | 816.30294714686 | 130.58866909441 | 20.9705947667308 |
| 2048 | 1.03979682032281 | 1.12777695271105 | 817.599224521873 | 130.796042028406 | 21.0038957705208 |
| 2049 | 1.04144538486687 | 1.12956500693617 | 818.895501896886 | 131.003414962403 | 21.0371967743107 |
| 2050 | 1.04309394941092 | 1.13135306116129 | 820.191779271899 | 131.2107878964 | 21.0704977781007 |
| 2051 | 1.04474251395498 | 1.13314111538641 | 821.488056646912 | 131.418160830397 | 21.1037987818906 |
| 2052 | 1.04639107849904 | 1.13492916961153 | 822.784334021925 | 131.625533764394 | 21.1370997856806 |
| 2053 | 1.04803964304309 | 1.13671722383665 | 824.080611396938 | 131.832906698391 | 21.1704007894705 |

## Groundwater boundary

PDP and DEPDev support a 20.2 km3/year national potential-flow benchmark. PIDS regional/local studies and the MGB layer demonstrate spatial heterogeneity, but do not supply the aquifer area, saturated thickness, storage coefficient, initial head, admissible drawdown, natural discharge and observed head series needed for a stock/depletion model. Accordingly v15 installs a national flow sensitivity only and records aquifer stock as a high-priority gap.

## Validation

The live case is `Philippines_v15/BASE_V15`. CBC status is optimal with objective 369630979.6246426; matrix 791109 rows, 884956 columns and 12533783 nonzeros. Maximum withdrawal-accounting residual is 0.000003900000010048643 km3/year and the minimum raw-water balance surplus is -3.8517124e-13 km3/year (numerical zero). Final demand and emissions are unchanged from v14.
