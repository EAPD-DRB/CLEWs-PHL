# Philippines v15: current model

## Identity and status

- Country / ISO3: Philippines / PHL
- Case / run: `Philippines_v15` / `BASE_V15`
- Model horizon: 2020-2053
- Upstream raw build: retained and pinned; CBC result recorded
- MUIO import: complete
- Final MUIO status: optimal, objective 369630979.62464261
- Intended use: whole-country CLEWs structural and sensitivity analysis
- Unsuitable uses: observed water-share claims, basin allocation, groundwater
  depletion analysis, or policy ranking without further calibration

## Current representation

The v15 portable case is `../muio/Philippines_v15_v15.0.0_MUIO.zip`. It is the
v14 stock-turnover model plus a national precipitation pathway, a corrected
groundwater input link, and annual surface-water and renewable-groundwater
potential-flow ceilings. The final model is a MUIO evolution; `../config/` and
`../model/inputs/` retain the exact upstream raw base from which that lineage
began. Later changes are recorded cumulatively in the same six ledgers and in
the current archive, not by references to an earlier package.

## Interpretation boundary

Solver success establishes technical validity. The inherited energy sector and
several water demands remain incompletely sourced or uncalibrated as stated in
`KNOWN_LIMITATIONS.md` and `../data_sources/GAPS.csv`.
