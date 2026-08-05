# Philippines v14 CLEWs structural review

Date: 2026-07-28

Case: `Philippines_v14_STOCK_TURNOVER`

Run inspected: `BASE_V14`

## Outcome

Status: **passed — 0 failures, 0 warnings**

The review used the fixed repository version of the `clews-model-review`
auditor:

```text
.venv/bin/python \
  /Users/sato/Documents/GitHub/Model-tools/skills/clews-model-review/audit.py \
  --datastorage /Users/sato/Documents/GitHub/MUIOGO/WebAPP/DataStorage \
  Philippines_v14_STOCK_TURNOVER
```

The audited case has:

- 34 years (`2020`–`2053`);
- 174 technologies;
- 97 commodities;
- 2 emissions;
- 2 technology groups;
- 4 scenarios;
- 30 timeslices;
- one optimal saved run, `BASE_V14`.

The audit found no undefined references, orphaned structural elements,
scenario inconsistencies or other fail/warn findings. In particular,
`PHL_POW_HEAT`, `PHL_POW_HEAT1`, `COM_te2a0` and `COM_pesfw` are absent,
while `PHL_POW_GEO_OLD` retains its electricity output.

This topology result complements, but does not replace, the full generation,
matrix, solve, A/B and freshness evidence in `validation_results.json` and
`VALIDATION_V14_2026-07-27.md`.
