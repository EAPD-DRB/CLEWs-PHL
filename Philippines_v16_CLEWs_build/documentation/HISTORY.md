# Philippines model history

| Date | Stage | What happened | Evidence |
|---|---|---|---|
| 2026-07-25 | Inherited raw base | Built the pinned CLEWs Global Philippines raw model and six-ledger source map | `../model/inputs/`; `../data_sources/evidence/inherited_base/` |
| 2026-07-26 | v13 | Added environmental-emission calibration with retained generation and validation records | `../data_sources/evidence/stock_turnover/` |
| 2026-07-28 | v14 | Added stock-turnover evolution and retained all 3,253 changed cells | `../data_sources/evidence/stock_turnover/` |
| 2026-08-04 | v15 | Added and validated the national-water formulation; promoted `Philippines_v15/BASE_V15` | `MODEL_FIXES_WATER_2026-08-04.md`; `../diagnostics/national_water_validation.json` |
| 2026-08-05 | Provenance recovery | Rebuilt one cumulative, self-contained six-ledger package and retained all available evidence | `../data_sources/calculation_notes/CANONICAL_LEDGER_RECONSTRUCTION_2026-08-05.md` |
| 2026-08-05 | Package alignment | Adopted the current Model-tools package layout, promoted exact retained raw inputs/configuration, and repointed their existing map rows | `../config/`; `../model/inputs/`; `../data_sources/MODEL_MAP.csv` |
| 2026-08-05 | v16 migration | Created the identity-only Philippines v16 successor and a compact result-free portable case; model parameters remain unchanged | `MIGRATION_V16.md`; `../muio/Philippines_v16_v16.0.0_MUIO.zip` |
