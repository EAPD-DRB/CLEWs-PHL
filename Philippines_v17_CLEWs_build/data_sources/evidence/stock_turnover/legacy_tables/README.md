# Philippines v14 stock-and-turnover data provenance

Generated: 2026-07-28T21:24:40.362433+00:00

This directory is generated from
`scripts/philippines_v14_stock_turnover_inputs.json` by
`scripts/create_philippines_v14_stock_turnover.py`. The same files are copied
into the case `data_sources/` directory.

The trace chain is:

`DATA_SOURCE_REGISTER.csv` → `CALCULATIONS.csv` and `ASSUMPTIONS.csv` →
`MODEL_DATA_MAP.csv` → `PARAMETER_CHANGE_LOG.csv` → source JSON →
generated solver data and `documentation/validation_results.json`.

Important interpretation:

- Observed 2020 activity is never kept as a TAL/TAU calibration pin.
- Where no official physical stock maps cleanly to a model class, the
  validated v13 BASE `TotalCapacityAnnual` that served the observed activity
  is transferred once into an initial effective stock. This retains time-slice,
  availability and capacity-to-activity effects without retaining the activity
  constraint.
- The 2020 investment closure applies only to explicitly classified physical
  stocks. The six zero-cost sectoral electricity pass-through technologies
  retain their inherited unconstrained-capacity convention.
- Full-horizon `TAMaxCI` adoption ceilings limit how fast any one technology
  can take over. They do not constrain activity, prescribe fuel shares or
  expire after a historical calibration window. They are not a hard aggregate
  class-sales cap; that limitation is explicit in the model-data map. For
  non-road technologies, the ceilings recursively restore an allowed vintage
  when its operational life ends, so the formulation does not create an
  artificial late-horizon capacity shortage.
- The stranded `PHL_POW_HEAT`/`PHL_POW_HEAT1` branch is removed. It had no
  sink or demand and made geothermal electricity activity appear one-for-one
  as useful heat. Documented Philippine direct geothermal use is a much
  smaller standalone bathing/swimming service and is outside the present
  national model boundary until a defensible demand and delivery chain is
  added.
- Land, water-resource, environmental-accounting and policy-scenario
  constraints are outside this historical-bound removal and are preserved.

Input hashes:

- specification: `61739d40ae8b97b0ac8da3fea73844e604a195e4e24b5c9c67dece8c2cf33f5b`
- local OSeMOSYS/MUIO formulation: `537d448b0252097065e47b84a72b1ec6dd008bb3bf6f84fce42ee377fc179736`
- EDGAR project workbook: `c8601bf26acce39d6e661a9f5bcb4801c4de401a5b73ce212f9115cca5ba63f8`
- validated v13 BASE results: `42d2ce3010109cf1600afce807cad07877c10da9639a2f15972d95b88d520579`
- validated v13 2020 TotalCapacityAnnual:
  `eb3da5482f195893e185ef6ec9e7559ae41faf31c3dff35bb87b8d81fb707770`

Validation status is deliberately separate. Consult the case
`documentation/VALIDATION_V14_2026-07-27.md`; generation alone is not solver
validation.
