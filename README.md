# CLEWs Philippines

This repository contains the Philippines CLEWs country model for MUIO/MUIOGO,
including the model documentation, change history, source register,
assumptions, calculations, diagnostics, and portable MUIO cases.

## Current model package

The current working model is **Philippines vIS1.2**. Its portable case is:

- `Philippines_vIS1.2_CLEWs_build/muio/Philippines_vIS1.2_vIS1.2_MUIO.zip`.

Version IS1.2 is the promoted island-power differentiated successor to v36.
Its BASE, COAL_PHASEOUT, RE, and EV scenarios passed the recorded generation,
formulation, and solver gates and reached optimal solutions.

Version 36 is the user-accepted electricity and gas-generation history
successor to v33. It preserves endogenous generation and fuel choice: observed
generation, dispatch, and market shares remain validation benchmarks rather
than forced model outcomes.

Version 33 carries the complete standalone provenance inherited through v30,
the v31 non-road transport unit and cost repair, and the v32 spatial rice-yield
calibration. It repairs domestic and imported gas-delivery costs and mappings
without fixing endogenous fuel choice. Its historical comparison register adds
sourced benchmarks for industrial heat, household cooking, services heating,
and fuel processing; these observations remain validation-only benchmarks.
All four v33 scenarios solved optimally.

Version 30 carries the complete standalone provenance inherited through v29.
It replaces unsupported crop-management plumbing with direct use of shared
physical cropland and irrigation service, retains one evidenced management
system per crop and water regime, and uses the 2020 Philippine yield
initialization followed by the FAO FOFA2050 Business As Usual trajectory.
Population, solar PV, and onshore wind now consume the existing built-up-land
class endogenously. The obsolete policy-only idle-cropland cap is removed.
All four scenarios solved optimally under a 300-second CBC deadline and passed
result-level land-account validation.

Version 24 is the agriculture repair successor to v23. It restores crop-mode
and cluster yield differentiation around PSA achieved national yields,
replaces the sentinel agriculture-water activity bounds with the
already-enforced national water envelopes, and moves the inventory-calibrated
crop GHG account into ordinary EAR coefficients. Only `genData.json`,
`RYT.json`, `RYTCM.json` and `RYTEM.json` change. BASE, COAL_PHASEOUT, RE and
EV each solved to proven optimality; the objective moves by -0.0137% in every
scenario. It adds no activity target, share constraint, or user-defined
constraint.

Versions 22 and 23 were never published as their own build packages in this
repository. Their result-free archives are retained as chronology under
`Philippines_v24_CLEWs_build/muio/`, and the cumulative v24 schema ledger and
evidence are complete without installing them. Version 23 is the Package 1
physical-possibility and adequacy model; version 22 is the transition-scope
model.

Version 21 remains available as its own package under
`Philippines_v21_CLEWs_build/`. It is the endogenous power-allocation repair
to v20, adding off-grid oil generation, aggregate off-grid hydro/solar/wind,
the closed 250 MW FIT-eligible biomass tranche, and off-grid customer
electricity sales reallocated from existing national final demand. Technology
WAPE improves in every benchmark year from 2020 to 2024.

Version 20 is the minimal endogenous power-history calibration successor to
v19, replacing AF=1 on four closed legacy power fleets with DOE 2020
dependable/nameplate ratios and representing the 2020-2021 Malampaya
take-or-pay economics. Version 19 starts from the exact working v18.0.1
archive at Git commit `2735feb` and adds source-traceable endogenous PM2.5
factors for 52 existing technologies. Version 18 starts from the complete v17
model, retains its safeguarded national land account, and updates the
documented geothermal, onshore-wind, coal, SMR, large-hydro, and
domestic/imported-gas inputs. Version 17 carries forward the complete v16
calibration and adds the land-cover constraints. Version 15 retains the v14
stock-turnover model and adds an ERA5-rebased, SSP2-4.5 median national
precipitation pathway, a missing irrigation groundwater input, and exact
annual gross-withdrawal ceilings for national surface-water and groundwater
potential. Every version remains a whole-country model.

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
v33. Read `Philippines_v33_CLEWs_build/README.md` and its canonical schema
ledger before using the model.

## Use with MUIOGO

1. Install or clone [MUIOGO](https://github.com/EAPD-DRB/MUIOGO).
2. Extract the current archive into this repository as
   `case/Philippines_vIS1.2`.
3. Create a relative symlink from
   `MUIOGO/WebAPP/DataStorage/Philippines_vIS1.2` to
   `CLEWs-PHL/case/Philippines_vIS1.2`.
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

The current portable archive and checksum are under
`Philippines_vIS1.2_CLEWs_build/muio/`. The archive contains the editable model,
its source-trace ledgers, retained evidence, and model-change documentation.

The ignored local `case/Philippines_vIS1.2/` directory is populated from the
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
