# Philippines MUIO import

## Version and checksum record

Use `../config/upstream_versions.json`.

## Separate statuses

| Stage | Status | Solver status | Evidence |
|---|---|---|---|
| Authoritative upstream raw model | retained | CBC 2.10.12 | `../data_sources/evidence/inherited_base/build_snapshot/diagnostics/validation_summary.json` |
| Complete MUIO import | passed | n/a | `../data_sources/evidence/inherited_base/build_snapshot/documentation/MUIO_IMPORT.md` |
| Final MUIO model | passed | optimal | `../diagnostics/national_water_validation.json` |

## Representation and parity

The exact upstream base configuration and populated CSV inputs are exposed at
`../config/config.yaml` and `../model/inputs/`. They are byte copies of the
retained inherited-base snapshot. The active v15 MUIO case is the portable
archive, whose checksum and member inventory are recorded in
`../data_sources/evidence/CURRENT_MODEL_ARCHIVE_MANIFEST.csv`.

The v13, v14 and v15 changes are MUIO evolutions layered on that raw base. Their
source records, calculations, assumptions, exact changed cells, maps, scripts
and validation artifacts are all inside this package. They are not claimed to
be regenerated CLEWs Global CSVs.

The inherited import evidence reports no non-default import errors or unsupported
non-default rows. The v15 solve is optimal; final demand and emissions are
unchanged from v14, and the water formulation adds 68 rows and 3,264 nonzeros.

## Restore

Extract `../muio/Philippines_v15_v15.0.0_MUIO.zip` into
`MUIOGO/WebAPP/DataStorage/`, then generate and solve `BASE_V15` through the
normal application chain. Generated solver inputs/results were deliberately
excluded from the portable archive; their hashes and completed-run evidence are
retained in `../diagnostics/national_water_validation.json`.
