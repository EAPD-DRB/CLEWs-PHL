# Philippines v24 CLEWs model

Philippines v24 is the agriculture repair successor to the validated v23
Package 1 model, and is built from `Philippines_v23` only. It restores
crop-mode and cluster yield differentiation around achieved national yields,
replaces sentinel agriculture-water activity bounds with the already-enforced
national water envelopes, and moves the inventory-calibrated crop GHG account
into ordinary EAR coefficients. It adds no activity target, share constraint,
or user-defined constraint.

Crop output per modeled land activity uses PSA achieved national anchors for
2020–2024 where a compatible series exists, growing at 1.0%/year from 2025.
GAEZ crop coefficients are used only as relative cluster, water-regime and
input-level patterns, normalized around those anchors; their absolute
potential-yield levels are not imported. Maize and vegetables retain their
GAEZ irrigation response; coconut, sugarcane and the other-crop aggregate keep
irrigated output at parity with the corresponding rainfed input level, because
this package lacks a defensible Philippine irrigation response for them.

`DEMAGRSURPHL` and `DEMAGRGWTPHL` no longer carry `TAU=999999`. Their TAUs
equal the corresponding already-enforced national annual water envelopes in
`RYCn.json`, so the change is a transparent redundant guardrail. All eight
crop-cluster technologies now report CO2e, using the retained Philippine
inventory average for managed-soil N2O plus rice water-regime factors from the
IPCC 2019 Refinement. CO2e carries zero penalty and non-binding limits, so the
EARs improve accounting without creating a hidden crop target.

Only `genData.json`, `RYT.json`, `RYTCM.json` and `RYTEM.json` differ from v23.
Generated `data.txt`, `data_processed.txt`, and LP files were never edited.

## Validation

The source equation gate passed 22 checks, and the generic physical gate passed
under BASE, COAL_PHASEOUT, RE and EV before generation. All four scenarios
solved to proven optimality:

| Scenario | Status | Objective | Change from v23 | Solve time |
|---|---|---:|---:|---:|
| BASE | Optimal | 369,764,275.245 | -50,621.382 (-0.013688%) | 248.52 s |
| COAL_PHASEOUT | Optimal | 369,782,569.891 | -50,621.381 (-0.013688%) | 424.83 s |
| RE | Optimal | 369,775,964.365 | -50,621.381 (-0.013688%) | 374.76 s |
| EV | Optimal | 369,749,398.429 | -50,621.381 (-0.013689%) | 567.24 s |

Each scenario adds 6,528 rows, 6,528 columns and 476,544 nonzeros relative to
its verified v23 counterpart. The conserved national `PHL_LND` commodity
balance holds at about 295.813 model land units every year, with maximum
absolute residuals of 0.0009–0.0018 across the rounded CSV exports. The first
concurrent RE and EV attempts reached 600 s and 660 s without optimal
solutions; those complete run directories were preserved outside the candidate
and the results above come from sequential retries.

The machine-readable qualification is
`documentation/agriculture_v24_four_scenario_validation.json`; it passed with
zero failures and permits sealing and content-preserving promotion. See
`documentation/MODEL_FIXES_AGRICULTURE_V24_2026-08-25.md` for the full
equation map, run inventory, and limitations.

## Delivered model

- Portable editable case: `muio/Philippines_v24_v24.0.0_MUIO.zip`
- Archive checksum: `muio/SHA256SUMS`
- Case identity: `Philippines_v24`
- Horizon: 2020–2053
- Runtime solver files and results: excluded
- Sensitivity runs: none

The six CSVs under `data_sources/` are the authoritative, cumulative schema
ledger, carrying unique v24 records with no missing or broken v24
cross-references. `GAPS.csv` explicitly retains crop-specific long-run
productivity projections, irrigation stock vintages and non-rice allocation,
input-specific fertilizer N2O, and transition-specific land-use-change GHG as
future upgrades.

The v22 and v23 archives under `muio/` are retained as chronology only; those
two versions were never published as their own build packages in this
repository, and the cumulative v24 ledger and evidence are complete without
installing them.
