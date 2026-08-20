# Philippines v21 known limitations

Power-allocation limitations after v21:

- the national grid is still a copperplate, so it cannot represent gas location
  value or Luzon–Visayas–Mindanao congestion;
- off-grid renewable supply is one compact hydro/solar/wind aggregate and the
  small reported 2022 off-grid coal route is omitted;
- biomass uses a closed 250 MW FIT tranche and a national crop-residue ceiling,
  not plant catchments, steam hosts, fuel contracts, or transport radii;
- hydro uses a restored retained wet/dry proxy with a 0.26438421 annual mean,
  not plant-level inflow, reservoir, run-of-river, or outage dynamics;
- exact plant GSPA quantities were not recovered; the inherited v20 domestic
  production envelope remains a disclosed maximum payment proxy in 2020–2021;
- off-grid sales after 2022 follow national PDP growth ratios because a complete
  official island-service forecast was not retained; and
- DOE 2020 national statistics include off-grid output, while the retained
  2021–2024 national summary is grid-only. The comparison applies that boundary
  explicitly rather than mixing the series.

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
- the DOE end-2020 committed-project aggregate has not been mapped at project
  level to surviving, irreversible model vintages, so no committed-capacity
  minimum is applied; and
- the current fossil-trade economics export the full domestic coal envelope in
  2022 and replace it with imports because export revenue exceeds import cost;
  coal grade, calorific value, location, plant compatibility, freight and
  terminal constraints require a separate non-forcing repair.

These are disclosed limitations, not missing links to an earlier model ledger.

- corrected fossil border prices remove the artificial coal export-and-reimport incentive, but the single homogeneous coal and crude pools cannot represent grade-, port-, plant- or refinery-specific simultaneous imports and exports; zero modeled exports and zero 2020 oil extraction remain disclosed benchmark gaps; and
- the inherited case still lacks a complete model-wide real-currency-year and deflator ledger, so the official nominal annual unit values are not presented as a full cost-base rebasing.
