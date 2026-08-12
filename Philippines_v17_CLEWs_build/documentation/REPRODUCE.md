# Reproduce and validate Philippines v17

1. Use the exact repository pins in `../config/upstream_versions.json` to repeat
   the inherited CLEWs Global raw build. The retained active configuration and
   input CSVs are at `../config/config.yaml` and `../model/inputs/`.
2. Restore the current editable model by extracting
   `../muio/Philippines_v17_v17.0.0_MUIO.zip` under
   `MUIOGO/WebAPP/DataStorage/`.
3. To rebuild v17 from a current v16 working case, run
   `python scripts/build_philippines_v17_land_cover.py`; the exact input is
   `data_sources/snapshots/land_cover_2020.json`.
4. Validate the self-contained provenance package with:

   `python scripts/provenance.py data_sources --stage build --model-inputs model/inputs`

5. Run `python scripts/validate_philippines_v17_delivery.py` to verify the
   retained evidence reports, current archive, result exclusion, and live/archive
   source identity. Regenerate the review workbook with
   `python scripts/build_philippines_v17_ledger_workbook.py`.

The completed land solve and validation are retained in
`../data_sources/snapshots/land_cover_validation.json`; generated solver files
are deliberately absent from the portable archive.
