# Reproduce and validate Philippines v18

1. Restore the committed v17 editable case under `case/Philippines_v17`.
2. Run `python scripts/build_philippines_v18_energy_inputs.py` to create the
   result-free `case/Philippines_v18` source. The normalized inputs are in
   `data_sources/snapshots/energy_inputs_v18_2026-08-12.json`.
3. Link the case as `MUIOGO/WebAPP/DataStorage/Philippines_v18` and run
   `python scripts/solve_philippines_v18_energy_inputs.py`.
4. Run `python scripts/validate_philippines_v18_energy_inputs.py`.
5. Validate the complete ledger with
   `python scripts/validate_provenance.py . --stage build` and regenerate the
   review workbook with `python scripts/build_philippines_v18_ledger_workbook.py`.
6. Run `python scripts/validate_philippines_v18_delivery.py` to verify the
   result-free archive, checksum, source identity, and retained validation.

The portable archive excludes `res/`, `data.txt`, `data_processed.txt`,
`lp.lp`, and `results.txt`.
