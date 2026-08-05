# CLEWs Philippines

This repository contains the Philippines CLEWs country model for MUIO/MUIOGO,
including the model documentation, change history, source register,
assumptions, calculations, diagnostics, and portable MUIO cases.

## Current model package

The current model is **Philippines v16.0.0**, prepared on the migration branch.
Its portable case is:

- `Philippines_v16_CLEWs_build/muio/Philippines_v16_v16.0.0_MUIO.zip`.

Version 16 is an identity-only successor to v15: model parameters are
unchanged. The full v15 release is protected by Git tag `v15.0.0`.

Version 15 retains the v14 stock-turnover model and adds an ERA5-rebased,
SSP2-4.5 median national precipitation pathway, a missing irrigation
groundwater input, and exact annual gross-withdrawal ceilings for national
surface-water and groundwater potential. It remains a whole-country model;
the ceilings are sensitivities rather than basin or aquifer safe-yield limits.

The earlier **Philippines v12.0.0** package remains available on `main` with
three portable lineage cases:

- `Philippines_v12`: the integrated source case;
- `Philippines_v12_ENV_LAND`: the derived case with in-model land
  environmental accounting; and
- `Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC`: the most complete analysis
  case, with exact in-model land accounting, an unforced water terminal in
  the Dynamic Graph, and authoritative postprocessed water values in Results
  Pivot.

The original v12 two-case tagged release is available from
[v12.0.0](https://github.com/EAPD-DRB/CLEWs-PHL/releases/tag/v12.0.0).
All three v12 portable archives are tracked under
`Philippines_v12_CLEWs_build/muio/` on `main`.

The historical Philippines v10 energy system, Fisheries v2.3, and the v12
CLEWs Global-derived land, agriculture, and water block remain inherited in
v16. Read `Philippines_v16_CLEWs_build/README.md` and its canonical schema
ledger before using the model.

## Use with MUIOGO

1. Install or clone [MUIOGO](https://github.com/EAPD-DRB/MUIOGO).
2. Extract `Philippines_v16_CLEWs_build/muio/Philippines_v16_v16.0.0_MUIO.zip`.
3. Place the extracted case folder under `MUIOGO/WebAPP/DataStorage/`.
4. Start MUIOGO and open the case.

The archive contains the editable MUIO parameter JSON and view files. Solver
outputs are intentionally excluded and are regenerated when the model is
solved.

For the inherited v12 diagnostic case, the included Pivot initially contains
the validated authoritative `ENV_WATER` publication. Every new solve
regenerates the solver views, so rerun
`Philippines_v12_CLEWs_build/scripts/publish_environmental_water_pivot.py`
with the installed model path and a unique evidence label before interpreting
`ENV_WATER`. Raw solver CSVs remain unchanged.

## Repository structure

The current package is under `Philippines_v16_CLEWs_build/`:

- `data_sources/`: six canonical source-trace ledgers, retained evidence and
  the review workbook;
- `documentation/`: equation-first model-change audit;
- `diagnostics/`: generation, solve, ledger and provenance validation;
- `muio/`: portable v16 MUIO case, predecessor archive, and checksums; and
- `scripts/`: retained generator, validators and normalized research input.

The `Philippines_v12_CLEWs_build/` folder preserves the inherited build and
reproduction package:

- `config/`: pinned upstream versions and workflow configuration;
- `data_sources/`: sources, assumptions, calculations, and model-data map;
- `documentation/`: current description, limitations, and model history;
- `diagnostics/`: validation and audit records;
- `geospatial/`: country model summaries and retained derived inputs;
- `licenses/`: licenses for incorporated upstream tools and workflows;
- `model/`: retained source-model inputs;
- `muio/`: portable MUIO cases;
- `overrides/` and `patches/`: country-specific upstream changes;
- `scripts/`: build, audit, validation, and reporting scripts.

Original external datasets and generated MUIO runtime outputs are not
distributed in this repository. Compact upstream solve evidence used by the
documented validation record is retained under `model/`.
