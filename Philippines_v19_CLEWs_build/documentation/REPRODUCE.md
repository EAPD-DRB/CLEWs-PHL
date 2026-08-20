# Reproduce and validate Philippines v19.0.0

1. Check out Git commit `2735feb` and verify
   `Philippines_v18_CLEWs_build/muio/Philippines_v18_v18.0.1_MUIO.zip` against
   SHA-256 `c3f4ee25d2e8c3315ced1be4bf819673859be45079536abb2cfbc40a65d1dc55`.
2. Extract that archive as `case/Philippines_v18`, copy the complete case to
   `case/Philippines_v19`, and run
   `python3 Philippines_v19_CLEWs_build/scripts/apply_philippines_v19_pm25_coverage.py`.
   The script requires exact source JSON identity before applying the patch.
3. Expose `case/Philippines_v19` under MUIOGO `WebAPP/DataStorage`, then run
   `solve_philippines_v19_pm25.py --muiogo <MUIOGO path> --timeout 600`.
4. Run `validate_philippines_v19_pm25.py`, passing the v18 and v19 case paths,
   generated run directory, untouched-v18 `AnnualTechnologyEmission.csv`, and
   solve report. The retained canonical validation used the exact candidate
   hashes recorded in the PM2.5 build snapshot.
5. Run `update_philippines_v19_pm25_ledger.py`,
   `build_philippines_v19_ledger_workbook.py`, and
   `package_philippines_v19.py`. Rerun the ledger updater and workbook builder
   after the archive manifest exists so the archive record is included.
6. Run the canonical schema-ledger, provenance, PM2.5, and v19 delivery
   validators. Confirm the archive excludes `res/`, `data.txt`,
   `data_processed.txt`, `lp.lp`, and `results.txt`.

The accepted solve completed optimally in 471.112 seconds end-to-end (351.70
CBC wall-clock seconds), below the 600-second limit. Runtime results are not
distributed; their hashes and derived comparison metrics are retained in
`../data_sources/snapshots/pm25_coverage_v19_validation.json`.
