# Philippines v12 model history

This is the chronological index. Historical records are preserved with their
original wording, including old filenames and relative paths. Those old paths
show where files were at the time; use the links below to find them now.

| Date | Stage | What happened | Record |
|---|---|---|---|
| Before v12 | v7–v9 energy development | Power costs and targets, transport and housing updates accumulated in the historical energy model | The original description remains in the active `genData.json` |
| 17 July 2026 | v10 scaffold | Fisheries Phase 1, energy-system fixes, and a placeholder land formulation were documented | `../../WebAPP/DataStorage/Philippines_v12/documentation/history/v10/MODEL_FIXES_2026-07-17.md` and `../../WebAPP/DataStorage/Philippines_v12/documentation/history/v10/LAND_CALIBRATION_v10_RETIRED.md` |
| 20 July 2026 | Fisheries v2.1 | Fisheries formulation revised | `../../WebAPP/DataStorage/Philippines_v12/documentation/history/fisheries/MODEL_FIXES_2026-07-20.md` |
| 25 July 2026 | Fisheries v2.2 | A clean formulation was documented; this was later superseded | `../../WebAPP/DataStorage/Philippines_v12/documentation/history/fisheries/MODEL_FIXES_2026-07-25_v2.2.md` |
| 25 July 2026 | Fisheries v2.3 | Global-result-parity formulation introduced and imported | `history/fisheries/DATA_SOURCE_REGISTER_v2.3_2026-07-25.md`, `history/fisheries/SOURCE_PACKAGE_README_v2.3.md`, and `history/v12_build/FISHERIES_V23_IMPORT_PACKAGE_RECORD_2026-07-25.md` |
| 25 July 2026 | v12 hybrid build | v10 energy retained, current Fisheries imported, placeholder land retired, and the CLEWs Global nexus grafted in | `history/v12_build/BUILD_REPORT_2026-07-25.md` and `../../WebAPP/DataStorage/Philippines_v12/documentation/history/v12_build/MODEL_BUILD_2026-07-25.md` |
| 25 July 2026 | Folder cleanup | Current guidance, data sources, assumptions and calculations were separated from dated historical evidence; no parameter value was changed | `MOVED_FILES.md` |
| 25 July 2026 | Scenario display fix | Replaced leaked internal IDs in the Base and PEP case display metadata with `BASE`, `COAL_PHASEOUT`, `RE` and `EV`; internal scenario IDs and parameter values were unchanged | Active `genData.json` and `view/resData.json` |
| 25 July 2026 | Environmental accounting | Added validated reporting-only water, land and native-emissions accounts; an in-model terminal was rejected because the installed technology-level UDC cannot exactly represent mode-dependent cluster water coefficients | `ENVIRONMENTAL_ACCOUNTING.md` and `history/environmental_accounting/IMPLEMENTATION_2026-07-25.md` |
| 25 July 2026 | Independent land-domain accounting | Reassessed land separately from water and added the exact derived-case `ENV_LAND` terminal; water remains reporting-only | `ENVIRONMENTAL_ACCOUNTING.md` and `history/environmental_accounting/ENV_LAND_IMPLEMENTATION_2026-07-25.md` |
| 26 July 2026 | Unforced water-terminal experiment | Added a separate diagnostic case containing unforced `ENV_WATER` and reconciled its activity against the reporting reference | `ENVIRONMENTAL_ACCOUNTING.md` and `history/environmental_accounting/ENV_WATER_DIAGNOSTIC_2026-07-26.md` |
| 26 July 2026 | Authoritative water Pivot publication | Kept `ENV_WATER` in the Dynamic Graph and published the reporting residual into its linked Results Pivot variables while preserving raw solver CSVs and backed-up solver views | `ENVIRONMENTAL_ACCOUNTING.md` and `history/environmental_accounting/ENV_WATER_PIVOT_PUBLICATION_2026-07-26.md` |

## Current versus historical

The current Fisheries formulation is **v2.3**. References to v2.2 inside the
dated v2.2 record are deliberately preserved because changing them would
rewrite history. The active case description and current documentation point
to v2.3.

The current land–agriculture–water block is the v12 CLEWs Global-derived
system. The v10 placeholder land calibration is deliberately retained as a
retired historical record and must not be used to describe v12.

The current environmental-accounting architecture is hybrid. `ENV_LAND` is an
exact terminal in the derived `Philippines_v12_ENV_LAND` case. `ENV_WATER`
remains authoritative reporting-only accounting until a mode-aware
formulation is implemented and revalidated. The diagnostic case retains the
terminal in its model topology and publishes the reporting result into Pivot
after optimization.
