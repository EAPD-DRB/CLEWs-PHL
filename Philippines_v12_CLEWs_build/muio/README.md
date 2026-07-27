# Portable MUIO cases

The current Philippines v12.0.0 model package contains:

- `Philippines_v12_v12.0.0_MUIO.zip`: integrated source case;
- `Philippines_v12_ENV_LAND_v12.0.0_MUIO.zip`: derived environmental-land
  accounting case; and
- `Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC_v12.0.0_MUIO.zip`: most
  complete analysis case, combining exact in-model land accounting with a
  visible unforced `ENV_WATER` terminal and authoritative postprocessed
  water results in Pivot.

Extract the required folder into `MUIOGO/WebAPP/DataStorage/`. The archives
contain the editable MUIO parameter JSON and view files. Generated solver
inputs and results are excluded.

The SHA-256 checksums are recorded in `SHA256SUMS`.

## Diagnostic-case water publication

The diagnostic archive contains the validated Base and PEP Pivot publication.
After every new solve, run the publisher from this repository and pass the
installed model explicitly:

```bash
PYTHONHASHSEED=0 python \
  Philippines_v12_CLEWs_build/scripts/publish_environmental_water_pivot.py \
  --model /path/to/MUIOGO/WebAPP/DataStorage/Philippines_v12_ENV_LAND_WATER_DIAGNOSTIC \
  --label <unique-label>
```

The publisher updates only linked `ENV_WATER` Pivot rows, preserves raw
solver CSVs, and writes a backup plus validation evidence. See
`../documentation/ENVIRONMENTAL_ACCOUNTING.md` before interpreting the
account.
