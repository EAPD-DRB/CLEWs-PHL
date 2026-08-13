# Philippines v18 known limitations

The authoritative itemized register is `../data_sources/GAPS.csv`. The most
material limits are:

- part of the inherited energy sector lacks its original bibliography;
- the original v13 workbook and source/result bytes are absent, although their
  hashes, formulas, selected values, derived stocks and validation survive;
- the national water ceilings are potential-flow sensitivities, not dependable
  yield, environmental-flow-adjusted availability or groundwater safe yield;
- there is no aquifer stock, head, drawdown, salinity, basin allocation,
  transfer or groundwater-storage state;
- public/power groundwater electricity, irrigation diversion and public-water
  demand remain uncalibrated;
- AQUASTAT national gross/net ratios are validation benchmarks, not a
  crop-, scheme-, season-, or region-specific irrigation-efficiency parameter;
- `CRPCON` is whole coconut with husk; v16 has no copra commodity or processing
  conversion, so coconut results must not be reported as copra tonnes; and
- national land-cover classes have not yet been overlaid with the eight yield
  clusters, so v17 applies national base-year equalities only;
- idle/fallow cropland inherits the existing `LOTHTOT` other-land hydrology
  proxy pending measured coefficients;
- forest `VC=-10` remains a policy-benefit signal with national cumulative
  safeguards but without parcel-level gross transitions,
  restoration/conversion costs or lags, or completed benefit sensitivity
  cases; and
- only the SSP2-4.5 ensemble median is installed; p10/p90 are retained evidence.
- the 2030–2053 technology deployment bands are judgmental physical envelopes,
  not forecasts, and need later pipeline, interconnection, permitting, finance,
  construction-workforce and transmission evidence; and
- geothermal greenfield expansion and existing-field repowering share the
  single `PHL_POW_GEO_OLD` cost, performance and lifetime representation.

These are disclosed limitations, not missing links to an earlier model ledger.
