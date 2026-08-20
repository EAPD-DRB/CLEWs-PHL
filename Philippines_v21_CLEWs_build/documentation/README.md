# Philippines v21 documentation

- `MODEL_FIXES_POWER_ALLOCATION_V21_2026-08-20.md`: compact non-forcing
  off-grid oil/renewable service, physical FIT biomass tranche, restored hydro
  profile, failed-candidate history, deterministic feasibility gate, accepted
  solve, promotion identity, and technology-level validation.

- `MODEL_FIXES_POWER_HISTORY_V20_2026-08-20.md`: history audit, equation-first
  design, exact AF and gas-contract calculations, rejected diagnostic,
  accepted solve, promotion identity, historical metrics, and stopping rule.

- `MODEL_FIXES_POWER_INVESTMENT_CLEANUP_2026-08-17.md`: 2020 information
  cutoff, removal of all 20 observed-addition pins, full-horizon legacy-stock
  entry closure, coal construction envelope, scenario-zero semantics,
  full-chain validation, result effects and the disclosed fossil-trade gap.

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
- `MODEL_FIXES_LAND_WATER_CLOSURE_2026-08-13.md`: geographic land routing, irrigation boundary, cluster water conservation, runtime A/B and full-chain validation.

- `MODEL_FIXES_FOSSIL_BORDER_PRICES_2026-08-18.md`: official 2020-2024 coal and crude border-price sources, exact conversions and cells, equation mapping, non-forcing classification, candidate solve, promotion identity and disclosed homogeneous-fuel-pool limitations.
