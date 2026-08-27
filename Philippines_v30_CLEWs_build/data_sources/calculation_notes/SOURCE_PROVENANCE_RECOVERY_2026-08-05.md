# Philippines v12 source-provenance recovery — 5 August 2026

## Scope and preservation rule

This recovery fills source-ledger omissions discovered after the Philippines
model was expanded from v10. It is a documentation-only Class A change. No
file under `model/inputs/` or `config/` was edited. The superseded three-table
ledger is preserved under
`documentation/history/provenance_legacy_2026-07-30/`.

The principal forensic source is Codex task
`019f9991-7a2d-72a0-8fa1-6820178dd177`, whose raw session JSONL is:

`/Users/sato/.codex/sessions/2026/07/25/rollout-2026-07-25T09-57-55-019f9991-7a2d-72a0-8fa1-6820178dd177.jsonl`

Its SHA-256 is
`b472410035d9f1eb61e3142a3f5b9311c8ec8a872d2b6d83728fd39b18555f65`.
The extracted event index is retained as
`evidence/land_agriculture_water/workflow/WORKFLOW_SESSION_EVENTS.csv`.
The original temporary `.snakemake/log/` directory and temporary manifests
were not frozen into the handoff; their material commands, paths, workflow
identifier and outcomes survive in the session record and event index.

## Pinned workflow sources

The exact upstream revisions used by the recovered build are:

- `DeltaE/CLEWs_Global` at
  `8df78c66be104e446f84a7dbb0df1c0a4fda4080`;
- `OSeMOSYS/CLEWs_GAEZ` at
  `30ec12e6524dc9c8ce474ffe1a467508f992007f`;
- `OSeMOSYS/clewsy` at
  `6eefaf2abc6d91917c0fddfeea373db37443a8dd`;
- `OSeMOSYS/osemosys_global` at
  `036fdd07cc0dc31df1649cdc1689a8aa35a83a36`.

## GAEZ selection tables and raster cache

Six exact selection tables from the pinned `CLEWs_GAEZ` revision are retained
under `evidence/land_agriculture_water/gaez_input_tables/`. The Philippines
selection is reconstructed row by row in
`GAEZ_PHL_RASTER_CACHE_MANIFEST.csv`, including the cache filename, crop code,
GAEZ crop, metric, input level, water supply, climate model, pathway, period,
unit, download URL, file identifier, source table and physical CSV line.

The selected crop/proxy codes are `RCP` (wetland rice), `CON` (coconut),
`MZE` (maize), `TOM` (tomato), `SGC` (sugarcane), `BAN` (banana), `RUB`
(Para rubber) and `CAS` (cassava). The three metrics are yield (`yld`), crop
water deficit (`cwd`, GAEZ suffix `wde`) and evapotranspiration (`evt`, GAEZ
suffix `eta`).

The high-input selection contains 48 rasters: eight crops, three metrics and
two water modes, filtered to HadGEM2-ES, RCP4.5, 2011–2040 and available water
content 200 mm/m. The low-input selection contains 42 rasters: seven crops,
three metrics and two water modes, using CRUTS32 Historical, 1981–2010 and
available water content 200 mm/m. The low-input tables contain no Para-rubber
row, so six potential low-input `RUB` combinations do not exist and were not
downloaded. Rubber therefore contributes only high-input proxy rasters to the
`OTH` aggregation.

The final clean cache had 92 files: the 90 crop rasters above plus
`precipitation prc.tif` and `LCType_ncb.tif`. Exact pinned repository copies of
those two bundled base rasters and their checksums are retained under
`gaez_base_rasters/`. The 90 original crop-raster bytes were temporary and are
no longer available, so their original byte checksums cannot be recovered;
their exact immutable-looking GAEZ download URLs, filenames and selection
records are retained for reproducible re-download.

The build session records that an initial Fiji-seeded cache was found to be
contaminated. It was moved to quarantine, not deleted; a clean cache was
created, the selected proxies were re-downloaded and the final GeoCLEWs rule
was rerun. The clean final command was:

`/opt/anaconda3/envs/clews-global/bin/snakemake --snakefile workflow/snakefile --cores 6 --use-conda --printshellcmds --rerun-incomplete --forcerun geoclews`

It ran in `/private/tmp/clews-global-philippines-source` with workflow ID
`209301f7-622f-4e22-844b-acf54895c62e`, Snakemake 9.23.1, Python 3.11.0 and
configuration MD5 `b8783fe2d039b22e134f9f7d57703e76`.

## FAOSTAT inputs and exact Philippines rows

The exact bundled inputs are retained under
`evidence/land_agriculture_water/faostat/`:

- `FAOSTAT_2020.csv`: QCL, M49 area 608, year 2020, Element 5312
  (`Area harvested`), unit ha, 9,908 data rows;
- `FAOSTAT_production_2020.csv`: QCL, M49 area 608, year 2020, Element 5510
  (`Production`), unit t, 10,111 data rows.

`FAOSTAT_PHL_2020_SELECTION.csv` retains the exact ten selected records,
values, flags, crop proxies/model groups and physical lines in both source
files. The rows are rice, coconuts, maize, other vegetables, sugar cane, other
tropical fruits, plantains, natural rubber, cassava and mangoes/guavas/
mangosteens. The first five map to `RCP`, `CON`, `MZE`, `TOM` and `SGC`; the
last five feed `OTH` through the `BAN`, `RUB` and `CAS` spatial proxies.

## SSP2 workbook and exact selected row

The exact workbook is retained as
`evidence/land_agriculture_water/ssp2/iamc_db_POP_Countries.xlsx` (SHA-256
`e013c76eacd95a2e0f6275446e9d1e71bdfb9556eab1c6619a5b0d7914ecab35`).
The selected record is sheet `data`, Excel row 1373, range
`data!A1373:Y1373`, with criteria:

- Model: `IIASA-WiC POP`
- Scenario: `SSP2`
- Region: `PHL`
- Variable: `Population`
- Unit: `million`

The exact row is also retained in `SSP2_PHL_SELECTED_ROW.csv`. The workbook's
`Recommended Citation` sheet records SSP Public Database Version 2.0 and a
generation time of 2020-06-20 12:30:41, with citation entry point
`https://tntcat.iiasa.ac.at/SspDb/dsd?Action=htmlpage&page=citation`.

The implementation in `overrides/workflow/scripts/clewsy.py` joins the
five-year population observations to an annual left index ending in 2053,
interpolates, selects 2020–2053 and normalizes to 2020. Because 2055 is outside
that left index, pandas fills the trailing 2051–2053 observations at the 2050
value rather than interpolating toward 2055. The exact resulting annual series
is retained as `SSP2_PHL_ANNUAL_INDEX_2020_2053.csv`.

## Remaining limits

The recovery does not invent evidence that no longer exists. The following
remain unresolved:

- byte-for-byte checksums of the 90 crop raster downloads in the destroyed
  temporary cache;
- the original GADM 4.1 archive checksum;
- original upstream acquisition dates for bundled FAOSTAT, SSP and base-raster
  files, distinct from the documented build/download and recovery dates;
- unrelated inherited-v10 energy bibliography and some technology-specific
  activity/capacity unit definitions already listed in `GAPS.csv`.
