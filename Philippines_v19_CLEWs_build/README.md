# Philippines v19 CLEWs model

Philippines v19 is the validated PM2.5-coverage successor to the working
Philippines v18.0.1 model. It starts from the exact archive at Git commit
`2735feb`, pulled at 10:09:18 EDT on 2026-08-19 (SHA-256
`c3f4ee25d2e8c3315ced1be4bf819673859be45079536abb2cfbc40a65d1dc55`).
The later experiment extending additional deployment caps into 2020-2025 is
not included.

## What changed

V19 adds endogenous PM2.5 activity-emission ratios for 52 existing
technologies. Forty-six receive their first PM2.5 link; six liquid-road
technologies retain their inherited exhaust coefficient and add class-specific
tyre, brake, and road-surface wear.

Only `genData.json` and `RYTEM.json` differ from the exact v18 baseline. No
technology, commodity, emission definition, demand, cost, capacity, activity
bound, user constraint, `TAMaxCI`, solver setting, exogenous emission, or CO2e
coefficient changed.

The authoritative sources, equations, assumptions, technology-level mappings,
limitations, and change record are in the six cumulative CSV ledgers under
`data_sources/`. The v19 workbook is a formatted review copy; the CSVs remain
authoritative. The complete inherited ledger and evidence are carried forward,
so this package does not require an earlier package to interpret it.

## Validation

The exact candidate solved optimally within the 600-second acceptance limit:
471.112 seconds end-to-end, 351.70 CBC wall-clock seconds, objective
369739249.45411736. Annual CO2e results are unchanged from the untouched v18
comparison. PM2.5 totals increase from 97.9903 to 120.6157 kt in 2020, 123.1661
to 165.2740 kt in 2030, and 168.0710 to 249.2109 kt in 2053 because additional
activities are now covered.

See `documentation/MODEL_FIXES_PM25_COVERAGE_2026-08-19.md` and
`data_sources/snapshots/pm25_coverage_v19_validation.json`.

## Delivered model

- Portable editable case: `muio/Philippines_v19_v19.0.0_MUIO.zip`
- Archive checksum: `muio/SHA256SUMS`
- Case identity: `Philippines_v19`
- Horizon: 2020-2053
- Runtime solver files and results: excluded

Extract `Philippines_v19` under `MUIOGO/WebAPP/DataStorage/`, regenerate the
solver input through MUIOGO, and run `BASE`. The scripts directory contains the
PM2.5 builder, validator, bounded solver runner, ledger builder, and delivery
checks.
