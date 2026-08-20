# CLEWs Philippines

This repository contains the Philippines CLEWs country model for MUIO/MUIOGO,
including the model documentation, change history, source register,
assumptions, calculations, diagnostics, and portable MUIO cases.

## Current model package

The current working model is **Philippines v19.0.0**. Its portable case is:

- `Philippines_v19_CLEWs_build/muio/Philippines_v19_v19.0.0_MUIO.zip`.

Version 19 starts from the exact working v18.0.1 archive at Git commit
`2735feb` and adds source-traceable endogenous PM2.5 factors for 52 existing
technologies. Only `genData.json` and `RYTEM.json` change. CO2e, costs, demands,
capacities, constraints, and `TAMaxCI` are unchanged. The later experiment
extending additional deployment caps into 2020-2025 is not included.

Version 18 starts from the complete v17 model, retains its safeguarded national
land account, and updates the documented geothermal, onshore-wind, coal, SMR,
large-hydro, and domestic/imported-gas inputs. It adds no technology or
commodity. Version 17 in turn carries forward the complete v16 calibration and
adds the land-cover constraints.

Version 15 retains the v14 stock-turnover model and adds an ERA5-rebased,
SSP2-4.5 median national precipitation pathway, a missing irrigation
groundwater input, and exact annual gross-withdrawal ceilings for national
surface-water and groundwater potential. It remains a whole-country model.

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
v19. Read `Philippines_v19_CLEWs_build/README.md` and its canonical schema
ledger before using the model.

## Use with MUIOGO

1. Install or clone [MUIOGO](https://github.com/EAPD-DRB/MUIOGO).
2. Extract the current archive into this repository as
   `case/Philippines_v19`.
3. Create a relative symlink from
   `MUIOGO/WebAPP/DataStorage/Philippines_v19` to
   `CLEWs-PHL/case/Philippines_v19`.
4. Start MUIOGO and open the case.

The ignored `case/` tree is the live local working copy; editing through
MUIOGO edits that same directory. The tracked result-free ZIP is the laptop
handoff artifact. The push and pull handoff skills maintain the ZIP, local
case, and symlink without committing the unzipped case or solver results.

For the inherited v12 diagnostic case, the included Pivot initially contains
the validated authoritative `ENV_WATER` publication. Every new solve
regenerates the solver views, so rerun
`Philippines_v12_CLEWs_build/scripts/publish_environmental_water_pivot.py`
with the installed model path and a unique evidence label before interpreting
`ENV_WATER`. Raw solver CSVs remain unchanged.

## Repository structure

The current package is under `Philippines_v19_CLEWs_build/`:

- `data_sources/`: six canonical source-trace ledgers, retained evidence and
  the review workbook;
- `documentation/`: equation-first model-change audit;
- `diagnostics/`: generation, solve, ledger and provenance validation;
- `muio/`: portable v19 MUIO case, predecessor archives, and checksums; and
- `scripts/`: retained generator, validators and normalized research input.

The ignored local `case/Philippines_v19/` directory is populated from the
current portable archive and exposed to MUIOGO through a relative symlink. It
is not part of Git history, which avoids the per-file Git size limit.

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
