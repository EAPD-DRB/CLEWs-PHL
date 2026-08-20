# Philippines MUIO import

## Version and checksum record

Use `../config/upstream_versions.json`.

## Separate statuses

| Stage | Status | Solver status | Evidence |
|---|---|---|---|
| Authoritative upstream raw model | retained | CBC 2.10.12 | `../data_sources/evidence/inherited_base/build_snapshot/diagnostics/validation_summary.json` |
| Complete MUIO import | passed | n/a | `../data_sources/evidence/inherited_base/build_snapshot/documentation/MUIO_IMPORT.md` |
| Final MUIO model | passed | optimal | `../data_sources/snapshots/power_allocation_v21_validation.json` |

## Representation and parity

The exact upstream base configuration and populated CSV inputs are exposed at
`../config/config.yaml` and `../model/inputs/`. They are byte copies of the
retained inherited-base snapshot. The active v21 MUIO case is
`MUIOGO/WebAPP/DataStorage/Philippines_v21`. The raw CLEWs Global CSVs remain
inherited-base evidence rather than a claim that later MUIO edits were
round-tripped back into the raw build workflow.

The v13, v14 and v15 changes are MUIO evolutions layered on that raw base. Their
source records, calculations, assumptions, exact changed cells, maps, scripts
and validation artifacts are all inside this package. They are not claimed to
be regenerated CLEWs Global CSVs.

The inherited import evidence reports no non-default import errors or unsupported
non-default rows. The v21 accepted solve is optimal. Its exact source changes,
generated-data identity, matrix dimensions, historical comparison, and
no-forcing checks are retained under
`../data_sources/snapshots/power_allocation_v21_*`.

## Restore

Use the installed `MUIOGO/WebAPP/DataStorage/Philippines_v21` source case, then
generate and preprocess `BASE` through the normal application chain. A v21
release archive was deliberately not built during this focused promotion.
Regenerated solver-input identity and retained completed-run evidence are in
`../data_sources/snapshots/power_allocation_v21_promotion_identity.json`.
