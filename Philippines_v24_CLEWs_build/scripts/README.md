# Philippines v18 MUIOGO scripts

The v15 model-construction scripts are retained unchanged as provenance. The
v16-specific canonical validator checks the identity-only successor package.
The v17 land scripts build and validate the current national land account.
The v18 scripts apply and validate the current energy-input update on that
complete v17 source, followed by the policy-neutral annual generation
deployment envelopes.

These are the exact source scripts retained by the schema ledger:

- `create_philippines_v15_national_water.py` builds the water delta through
  the MUIOGO source-parameter and `UpdateCase` workflow.
- `validate_philippines_v15_national_water.py` performs deterministic checks,
  application generation, preprocessing, matrix inspection, CBC validation,
  baseline comparison and water-ledger publication.
- `build_canonical_philippines_v15_ledger.py` reproducibly assembles the
  cumulative six-table ledger from evidence retained inside the v15 package.
- `build_philippines_v15_ledger_workbook.py` regenerates the non-authoritative
  review workbook from those six CSVs.
- `validate_philippines_v15_schema_ledger.py` validates the cumulative ledger,
  retained evidence and current model archive without an earlier live case.
- `validate_philippines_v15_canonical_ledger.py` is the implementation behind
  that compatibility entry point.
- `validate_philippines_v16_canonical_ledger.py` validates the current v16
  standalone ledger and result-free archive.
- `calibrate_philippines_v16_energy_inputs.py` builds the disposable
  energy-input candidate, performs the stable-ID renames through `UpdateCase`,
  writes only the scoped source parameters and can promote a validated case.
- `validate_philippines_v16_energy_inputs.py` proves source-diff scope,
  physical inputs, generated representation, solver freshness, non-forcing
  behavior and affected-result envelopes.
- `validate_philippines_v16_energy_inputs_live.py` verifies promoted source
  identity, live generation, optimum reproduction and affected physical
  results while explicitly disclosing degenerate alternative optima.
- `document_philippines_v16_energy_inputs.py` appends the source, assumption,
  calculation, model-map, gap and change records to the canonical CSV ledger.
- `provenance.py` performs the generic six-table schema and provenance-graph
  validation.
- `validate_package.py` and `validate_provenance.py` apply the current generic
  Model-tools package, repository-pin and model-input coverage checks.
- `audit_no_forcing.py`, `estimate_resources.py`, `freeze_raw_baseline.py` and
  `validate_delivery.py` are the reusable Model-tools utilities. A raw-baseline
  freeze is not claimed for this evolved, partly calibrated v15 case.
- `data/philippines_water_precipitation_ssp245.json` is the normalized,
  hash-pinned research input.
- `data/philippines_v16_energy_inputs.json` is the normalized, hash-pinned
  energy-input and technology-rename register.
- `build_philippines_v17_land_cover.py` creates a result-free v17 source case
  from the complete v16 case and rejects changes outside the four intended
  source JSON files.
- `solve_philippines_v17_land_cover.py` executes the complete MUIOGO data-file,
  preprocessing, GLPK matrix/LP, CBC solve, CSV and viewer export chain for the
  central complete safeguarded run.
- `validate_philippines_v17_land_cover.py` checks the full solved land account,
  idle/fallow route, unchanged source sectors, and retained forest `VC`.
- `update_philippines_v17_land_cover_ledger.py` appends the complete source,
  assumption, calculation, map, gap, and change records.
- `build_philippines_v17_ledger_workbook.py` regenerates the v17 review
  workbook; the six CSVs remain authoritative.
- `validate_philippines_v17_delivery.py` verifies the final ledger reports,
  archive checksum/CRC, result exclusion, case identity, and byte identity of
  all live source JSON files in the archive.
- `build_philippines_v18_energy_inputs.py` creates the v18 editable source from
  v17, changing only the documented energy parameters and existing gas routes.
- `solve_philippines_v18_energy_inputs.py` runs the complete central v18 solve.
- `validate_philippines_v18_energy_inputs.py` checks source scope, retained land
  constraints, gas chronology and limits, and solved results.
- `update_philippines_v18_energy_ledger.py` appends the v18 records to the
  inherited cumulative ledger.
- `build_philippines_v18_ledger_workbook.py` regenerates the v18 review
  workbook.
- `validate_philippines_v18_delivery.py` verifies the current result-free
  archive, checksum, live source identity, and validation reports.
- `apply_philippines_v18_deployment_envelopes.py` applies the exact
  `TAMaxCI.SC_0` formula, records every annual calculation and rejects an
  unexpected source fingerprint.
- `validate_philippines_v18_deployment_envelopes.py` proves the exact source
  allowlist, historical preservation, scenario inheritance and absence of new
  forcing constraints.
- `compare_philippines_v18_deployment_envelopes.py` compares the solved control
  and candidate, including matrix size, objective, affected results and NCC1
  duals.
- `apply_philippines_v18_power_investment_cleanup.py` removes the 20
  post-2020 observed-addition pins, closes legacy stock-only entry and applies
  the approved coal envelope from an asserted source fingerprint.
- `validate_philippines_v18_power_investment_cleanup.py` checks the exact
  62-cell source allowlist, generated scenario values, optimum, benchmark-only
  additions, fossil flows and qualified baseline comparison.
- `run_philippines_v18_power_investment_cleanup.py` runs the single budgeted
  disposable CBC optimization and retains its log and report.
- `document_philippines_v18_power_investment_cleanup.py` writes the complete
  six-table schema-ledger record, including one calculation and model-map row
  for every changed cell.
- `validate_philippines_v18_power_investment_ledger.py` verifies the exact
  cell-to-calculation-to-map correspondence, cross-references, retained hashes,
  disclosed gaps, narrative and regenerated review workbook.

The water generator and full before/after model validator retain their original
MUIOGO-relative paths and need the historical baseline to repeat that old A/B
exercise. The canonical ledger build and validation do not: all of their
inputs are inside this v15 package. The completed promoted-run evidence remains
under `../diagnostics/` and `../data_sources/snapshots/`.
- `apply_philippines_v18_land_water_bounds.py` applies the parameter-only
  geographic cluster bounds and conservative water-coefficient repair.
- `validate_philippines_v18_land_water_closure.py` performs deterministic,
  generation, GLPK, CBC, result and baseline checks while recording the
  rejected aggregate-UDC runtime experiment.
- `finalize_philippines_v18_land_water_closure.py` closes the schema ledger and
  documentation after the validated candidate solve.
- `verify_philippines_v18_land_water_promotion.py` regenerates the promoted
  input, canonicalizes unordered derived-set serialization, and checks the
  live GLPK matrix without a second optimization.
- `complete_philippines_v18_land_water_delivery.py` closes promotion lineage
  and builds the result-free v18.0.1 archive.
- `validate_philippines_v18_land_water_delivery.py` checks the final archive
  CRC, checksum, result exclusion, validation records, provenance, and
  live/archive source identity.

- `document_philippines_v18_fossil_border_prices.py` records the official fossil border-price sources, four assumptions, 20 changed-cell calculations and maps, two validation maps, gaps, change lineage and retained snapshots in the six-table canonical ledger.
- `validate_philippines_v18_fossil_border_price_ledger.py` verifies exact cell-to-calculation-to-map coverage, retained hashes, cross-references, narrative and review workbook.

## Philippines v19 PM2.5 coverage

- `apply_philippines_v19_pm25_coverage.py` gates the exact v18 JSON baseline
  and adds the 52 documented PM2.5 series.
- `solve_philippines_v19_pm25.py` performs one full-chain BASE run with a
  configurable hard timeout (600 seconds for acceptance).
- `validate_philippines_v19_pm25.py` verifies source scope, factors, retained
  evidence, generated matrix, bounded solve, unchanged CO2e, and PM2.5 totals.
- `update_philippines_v19_pm25_ledger.py` appends the v19 records to all six
  inherited authoritative CSV ledgers.
- `build_philippines_v19_ledger_workbook.py` regenerates the review workbook.
- `package_philippines_v19.py` builds the result-free portable case and archive
  manifest.
- `validate_philippines_v19_delivery.py` checks ledger references, local
  evidence hashes, workbook integrity, archive identity, and result exclusion.

## Philippines v20 power history

- `apply_power_calibration.py` applies the asserted three-file, non-forcing
  source delta.
- `validate_power_calibration.py` checks exact source scope, inheritance,
  dependable ratios, cost identity, and benchmark-only classification.
- `run_power_calibration.py` performs a disposable full-chain validation run.
- `compare_power_history.py` builds the 2020–2024 generation/capacity table and
  retained error metrics.
- `verify_power_promotion.py` proves live source and generated-model identity
  without a second optimization.
- `update_philippines_v20_power_ledger.py` appends all six authoritative ledger
  tables; `build_philippines_v20_ledger_workbook.py` regenerates the review
  workbook; and `package_philippines_v20.py` creates the result-free archive.
