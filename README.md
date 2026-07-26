# CLEWs Philippines

This repository contains the Philippines CLEWs country model for MUIO/MUIOGO,
including the model documentation, change history, source register,
assumptions, calculations, diagnostics, and portable MUIO cases.

## Current model release

The current release is **Philippines v12.0.0**:

- `Philippines_v12`: the integrated source case;
- `Philippines_v12_ENV_LAND`: the derived case with in-model land
  environmental accounting.

The release is available from
[v12.0.0](https://github.com/EAPD-DRB/CLEWs-PHL/releases/tag/v12.0.0).
The same portable archives are tracked under
`Philippines_v12_CLEWs_build/muio/`.

The historical Philippines v10 energy system and Fisheries v2.3 are retained
in v12. The new CLEWs Global-derived land, agriculture, and water block is
structurally integrated but not historically calibrated. Read
`Philippines_v12_CLEWs_build/documentation/CURRENT_MODEL.md` and
`Philippines_v12_CLEWs_build/documentation/KNOWN_LIMITATIONS.md` before using
the model.

## Use with MUIOGO

1. Install or clone [MUIOGO](https://github.com/EAPD-DRB/MUIOGO).
2. Extract the required archive from
   `Philippines_v12_CLEWs_build/muio/`.
3. Place the extracted case folder under `MUIOGO/WebAPP/DataStorage/`.
4. Start MUIOGO and open the case.

The archives contain the editable MUIO parameter JSON and view files. Solver
outputs are intentionally excluded and are regenerated when the model is
solved.

## Repository structure

The `Philippines_v12_CLEWs_build/` folder preserves the structure of the
working model package:

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
