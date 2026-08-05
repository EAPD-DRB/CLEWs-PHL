# Reproduce and validate Philippines v15

1. Use the exact repository pins in `../config/upstream_versions.json` to repeat
   the inherited CLEWs Global raw build. The retained active configuration and
   input CSVs are at `../config/config.yaml` and `../model/inputs/`.
2. Restore the current editable model by extracting
   `../muio/Philippines_v15_v15.0.0_MUIO.zip` under
   `MUIOGO/WebAPP/DataStorage/`.
3. For the v15 national-water delta, place the retained generator and validator
   from `../scripts/` at their documented MUIOGO-relative locations and follow
   `../scripts/README.md`. The old v14 A/B comparison needs the historical
   baseline; the current cumulative-ledger validation does not.
4. Validate the self-contained provenance package with:

   `python scripts/validate_provenance.py . --stage build`

5. Run `python scripts/validate_philippines_v15_schema_ledger.py` to verify all
   retained evidence, the current archive and the absence of external-version
   dependencies. Regenerate the review workbook with
   `python scripts/build_philippines_v15_ledger_workbook.py`.

The completed solve, source fingerprints and exact water equations are retained
in `../diagnostics/`; rerunning the solver is optional unless model data change.
