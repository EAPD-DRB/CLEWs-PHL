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
