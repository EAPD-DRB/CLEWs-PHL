# Portable Philippines v19 MUIO case

`Philippines_v19_v19.0.0_MUIO.zip` is the complete editable v19 source. It is
the exact working v18.0.1 baseline from commit `2735feb` plus only the
documented PM2.5 coverage patch. The later 2020-2025 deployment-cap experiment
is excluded.

Extract `Philippines_v19` into `MUIOGO/WebAPP/DataStorage/`, regenerate the
solver input, and run `BASE`. The accepted candidate solved optimally within
600 seconds. Runtime results are excluded from the archive. Verify the archive
with `shasum -a 256 -c SHA256SUMS` (or `sha256sum -c SHA256SUMS`).

The v15-v18 archives are retained as chronology and evidence; the cumulative
v19 ledger is complete and does not depend on their installed cases.
