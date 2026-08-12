# Philippines v17 documentation

- `MODEL_FIXES_LAND_COVER_2026-08-12.md`: PSA/NAMRIA source mapping,
  reconciliation, national land equality, idle/fallow mode, deferred forest
  dynamics, and full-chain validation.

- `MODEL_FIXES_WATER_2026-08-04.md`: equation-first design, source changes,
  baseline, solver validation and known limitations.
- `MODEL_FIXES_ENERGY_INPUTS_2026-08-11.md`: renewable naming, offshore and
  onshore wind, geothermal availability, source calculations and validation.
- `../data_sources/`: canonical source, calculation, assumption, model-map,
  gap and change ledgers.
- `../diagnostics/national_water_manifest.json`: full-precision generation and
  source-fingerprint manifest.
- `../diagnostics/national_water_validation.json`: complete application-chain
  and baseline-comparison evidence.
- `../diagnostics/national_water_ledger.json`: authoritative full-precision
  annual water publication.
- `../diagnostics/schema_ledger_build.json`: generic provenance validation.
- `../diagnostics/schema_ledger_live.json`: semantic validation against the
  promoted `Philippines_v15/BASE_V15` case.
- `../diagnostics/package_provenance_validation.json`: independent validation
  of the copied six-table ledger and retained hashes in this repository.

The inherited raw build, detailed historical provenance and v13/v14 evolution
records are retained inside this v17 package under `../data_sources/evidence/`.
The separate older folders are historical conveniences, not dependencies.
