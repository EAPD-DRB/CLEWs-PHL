# Philippines v18.0.1 pre-industry entry and geothermal replacement, 2026-08-19

`TAMaxCI.SC_0` now enforces the complete entry schedules for technologies without an established Philippine industry:

- `PHL_POW_PP_WOF`: expansion headroom is zero through 2027, 1 GW/year in 2028-2030, 2 GW/year in 2031-2039, and 4 GW/year thereafter. The existing permitted-vintage recycling rule adds the 1 GW 2028 allowance again in 2053, yielding total `TAMaxCI=5` in that year.
- `PHL_POW_PP_NUSMR`: zero through 2034, 0.3 GW/year in 2035-2039, and 0.6 GW/year thereafter.
- `PHL_POW_PP_NU`: zero through 2034 and 1.2 GW/year thereafter.

Fifteen open/default cells in 2021-2025 were changed to zero. All later schedule cells were already correct and remain unchanged.

`PHL_POW_GEO_OLD` receives its 0.15 GW/year 2023 expansion headroom plus 0.484481960816 GW of scheduled residual-capacity retirement, giving a 2023 ceiling of 0.634481960816 GW/year. Its costs, efficiency, 0.70 availability factor, and residual-capacity profile are unchanged. Greenfield and replacement/repowering continue to share one technology and cost representation; replacement is allowed but not forced.

`PHL_POW_CHP_COAL_OLD`, `PHL_POW_CHP_NG_OLD`, `PHL_POW_CHP_OIL_OLD`, and `PHL_POW_CHP_BIOM_OLD` were verified at zero maximum investment throughout 2020-2053. Their residual-capacity trajectories remain unchanged.

Exactly 16 source cells changed. No model generation, preprocessing, LP generation, optimization, or archive repackaging was performed.
