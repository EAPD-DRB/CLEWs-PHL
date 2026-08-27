# ENV_WATER diagnostic case documentation

The canonical documentation is kept in the v12 build package:

- `../../../../Philippines_v12_CLEWs_build/documentation/ENVIRONMENTAL_ACCOUNTING.md`
- `../../../../Philippines_v12_CLEWs_build/documentation/CURRENT_MODEL.md`
- `../../../../Philippines_v12_CLEWs_build/data_sources/`

This case contains:

- exact in-model `ENV_LAND` modes 1-8;
- unforced diagnostic `ENV_WATER` modes 1-3; and
- no `BAL_ENV_WATER` constraint.

The reporting ledger excludes `ENV_WATER` consumption when calculating the
reference residual, then compares that reference with terminal activity.

The current Results Pivot contains the authoritative postprocessed reference
rather than the unforced solver terminal values. See
`environmental_water_pivot_publication.json` and the canonical evidence
directory. Raw solver CSVs remain unchanged.
