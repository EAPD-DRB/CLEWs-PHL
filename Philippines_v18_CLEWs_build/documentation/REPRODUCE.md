# Reproduce and validate Philippines v18.0.1

1. Restore the validated v18 deployment-envelope source.
2. Run `python scripts/apply_philippines_v18_land_water_bounds.py` against that
   source and a disposable target/package. The script gates exact source hashes.
3. Run `python scripts/validate_philippines_v18_land_water_closure.py` once on
   the disposable candidate. Reuse the retained deployment candidate as the
   unchanged baseline; do not rerun it.
4. Run `python scripts/validate_provenance.py . --stage build` and regenerate
   `PHILIPPINES_V18_CANONICAL_SCHEMA_LEDGER.xlsx`.
5. Promote only `RYT.json`, `RYTCM.json`, and the documented records. Regenerate
   and preprocess the live solver input, compare it byte-for-byte with the solved
   candidate, and run `glpsol --check`. Do not solve again when identical.
6. Build `Philippines_v18_v18.0.1_MUIO.zip` without `res/`, `data.txt`,
   `data_processed.txt`, `lp.lp`, or `results.txt`; validate CRC, checksum and
   live/archive source identity.

The aggregate nine-member UDC is not the promoted formulation: its diagnostic
CBC run exceeded 430 seconds. The promoted formulation uses the existing
source-derived cluster TAUs as matching TALs and retains endogenous modes.
