# Non-Fisheries provenance reconstruction — 30 July 2026

## Scope

This migration converts the active Philippines v12 provenance records to the
canonical six-ledger schema. Fisheries is explicitly out of scope. Its legacy
files were neither interpreted nor changed.

## Evidence policy

- Each populated non-Fisheries raw-input CSV row has one exact `MODEL_MAP`
  record carrying the package-relative file, physical CSV line, coordinates,
  value and best recoverable model unit.
- The Philippines repository snapshot is the immediate source of every
  retained value. External sources are added only where the package or an
  authoritative provider supplies a defensible product/variable locator.
- Missing original files, queries, units, access dates and bibliographic
  links are recorded in `GAPS.csv`; no locator or date was invented.
- Existing legacy ledgers were copied to
  `documentation/history/provenance_legacy_2026-07-30/` before replacement.

## Mechanical checks

- Protected input files hashed: 72
- Protected input aggregate SHA-256 before and after:
  `b0fc7ddcbd28919169ba28b76b64f925afddcce4deb06178e9e1532c357143aa`
- Populated raw-input CSV files mapped: 36
- Fisheries raw-input rows excluded: 0
- Canonical ledger rows:
  - `SOURCES.csv`: 16
  - `CALCULATIONS.csv`: 13
  - `ASSUMPTIONS.csv`: 10
  - `MODEL_MAP.csv`: 68619
  - `GAPS.csv`: 8
  - `CHANGES.csv`: 1

The reconstruction script aborts if any file under `model/inputs/` or
`config/` changes. Passing ledger validation proves schema, reference and raw
input-file coverage; it does not prove that unresolved historical citations
have been recovered.
