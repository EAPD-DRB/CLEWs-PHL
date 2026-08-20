# Philippines v19: additional PM2.5 coverage

## Outcome

V19 adds source-traceable endogenous PM2.5 factors for 52 existing
technologies. Forty-six technologies receive their first PM2.5 link, and six
liquid-road technologies retain their exhaust factor with class-specific
non-exhaust wear added.

Only `genData.json` and `RYTEM.json` differ from v18. CO2e and every unaffected
PM2.5 row are unchanged. No technology, commodity, emission, constraint, cost,
demand, exogenous inventory, or historical calibration is added.

The inherited baseline is the exact v18.0.1 archive from Git commit `2735feb`,
pulled at 10:09:18 EDT on 2026-08-19 (SHA-256
`c3f4ee25d2e8c3315ced1be4bf819673859be45079536abb2cfbc40a65d1dc55`).
It retains the established 2026-onward deployment envelopes. The later
experiment extending additional deployment caps into 2020-2025 is not part of
v19.

## Coverage added

- Industry process heat, including existing CCS variants.
- Service-sector stationary heat.
- Agriculture coal/biomass heat and liquid-fuel motive power.
- Household natural-gas cooking.
- Existing CCS power technologies.
- Domestic coal extraction and imported-coal handling.
- Tyre, brake, and road-surface wear for all existing road-vehicle classes and
  powertrains.

The authoritative factor register is
`../data_sources/evidence/pm25_v19/FACTOR_SELECTION.csv`; full derivations and
limitations are in
`../data_sources/calculation_notes/pm25_coverage_v19_2026-08-19.md`.

## Evidence and uncertainty

Six retained EMEP/EEA guidebook chapters provide the Tier 1 central factors.
Exact tables, pages, source units, published 95% bounds, URLs, and file hashes
are recorded. They are transparent fallback factors, not a claim of Philippine
technology-specific calibration. Remaining evidence gaps are explicit in
`GAPS.csv`.

## Validation

`../data_sources/snapshots/pm25_coverage_v19_validation.json` records passing
checks for source-file scope, unchanged identifiers and non-PM rows, all 52
factor series and scenario inheritance, retained-source hashes, generated
`data.txt`, and the full GLPK matrix. The exact candidate solved optimally
within the 600-second acceptance limit: 471.112 seconds end-to-end, 351.70 CBC
wall-clock seconds, objective 369739249.45411736. Annual CO2e results are
identical to the untouched v18 comparison; PM2.5 totals rise only because of
the newly covered activities.
