# Philippines v12 Fisheries v2.3 import

The authoritative Philippines v10 Fisheries v2.3 sector was imported into the
active Philippines v12 MUIO case on 25 July 2026.

## Scope

The import replaced all v10-keyed Fisheries definitions and parameters plus
the `PHL_INDU_OTH` specified-demand row that implements the direct
fish-processing useful-service carve-out. V12-only 30-mode integration records
were retained. No non-Fisheries semantic record changed.

The 12 active data changes relative to the previous v12 state are:

- six Fisheries end-use availability-factor rows set to 1;
- five nonzero residual-capacity paths restored with lifetime-matched
  retirement; and
- one annual Industry-other demand row updated for the revised direct
  processing carve-out.

## Verification

| Check | Result |
|---|---|
| V10 v2.3 Fisheries definitions/parameter records checked | 2,115 |
| V10 v2.3 Fisheries scalar values checked | 140 |
| Fisheries mismatches | 0 |
| Non-Fisheries changes | 0 |
| Full retained-v10 preservation audit | PASS |
| Validation suite | 10/10 PASS |
| Base v12 solve | Optimal; 375,930,821.3405416 |
| PEP v12 solve | Optimal; 375,953,763.4595271 |

## Documentation and sources

Exact copies of the authoritative v2.3 documentation are in
`sources/fisheries_v2.3/`:

- `FSH_CALIBRATION.md`
- `FSH_GLOBAL_PARITY.md`
- `FSH_calibration_data.csv`
- `FSH_industry_carveout.csv`

`sources/fisheries_v2.3/DATA_SOURCE_REGISTER.md` gives government reviewers a
decision-oriented index of the exact named DOE, BFAR, and PSA publications,
their model use and transformations, assumptions/proxies, review owners, and
candidate better national datasets. It also records that the authoritative
v2.3 bundle omitted the lookup table for several symbolic parameter-source
codes; those codes are preserved but not overstated as fully resolved
citations.

Machine-readable evidence is in
`diagnostics/fisheries_v23_import_audit.json`. The detailed case-level record
is `WebAPP/DataStorage/Philippines_v12/FISHERIES_V23_IMPORT.md`.
