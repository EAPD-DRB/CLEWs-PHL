# Philippines v33 CLEWs model

Philippines v33 is the validated gas-delivery successor to Philippines v32.
It retains the complete inherited model and provenance through v30, the v31
non-road transport repair, and the v32 spatial rice-yield calibration.

## What changed since v30

- v31 repairs non-road transport units, efficiencies, costs, and source tracing.
- v32 applies source-traceable spatial rice yields without fixing endogenous
  production, activity, or market shares.
- v33 repairs domestic and imported gas-delivery costs and mappings while
  preserving endogenous fuel choice.
- The historical comparison register now includes sourced benchmarks for
  industrial heat, household cooking, services heating, and fuel processing.

## Validation

The deterministic pre-flight and four-scenario validation records for the
transport, rice-yield, and gas-delivery changes are retained in
`documentation/` and summarized in `diagnostics/`. The v33 BASE,
COAL_PHASEOUT, RE, and EV cases reached optimal solutions. Historical
observations are benchmark-only values and do not force endogenous outcomes.

## Delivered model

- Portable editable case: `muio/Philippines_v33_v33.0.0_MUIO.zip`
- Case identity: `Philippines_v33`
- Horizon: 2020–2053
- Runtime solver matrices, logs, results, and populated views: excluded

