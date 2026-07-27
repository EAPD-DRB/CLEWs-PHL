# ENV_WATER Pivot publication — 26 July 2026

## Purpose

The unforced `ENV_WATER` technology remains useful in the Dynamic Graph but
its optimizer-selected activity does not reliably count residual water. This
publication makes the authoritative production-minus-ordinary-use account
visible under the existing `ENV_WATER` name in MUIO Results Pivot without
changing the optimization model or raw solver results.

## Method

The postprocessor calculates each water commodity at timeslice resolution:

```text
reference
  = production by all technologies
  - use by every technology except ENV_WATER
```

It updates only the terminal's generated view rows:

| View file | Variable | Published meaning |
|---|---|---|
| `RT.json` | `TTMPA` | Model-period `ENV_WATER` activity |
| `RYTM.json` | `TATABM` | Annual activity by water mode |
| `RYTMTs.json` | `ROA` | Timeslice activity rate |
| `RYTCMTs.json` | `ROUBT` | Timeslice water-use rate |
| `RYTCMTs.json` | `UBT` | Timeslice-weighted water use |

`PBT` and `ROPBT` remain unchanged because `ENV_WATER` has no output. All
non-`ENV_WATER` view rows remain structurally identical.

Result CSVs, solver inputs, solver outputs, parameter JSON and `genData.json`
are unchanged. The Dynamic Graph therefore retains the same terminal and
three input commodities. The four original solver-generated view files are
preserved under the evidence directory.

## Rounding treatment

MUIO result CSVs round individual rows to four decimals. A few timeslice
production-minus-use differences are consequently as low as −0.0003 even
though the solved commodity balance is nonnegative.

The publisher sets these tiny negative timeslices to zero and removes the
resulting correction from the largest positive timeslice for the same
commodity and year. Published timeslices are therefore nonnegative and retain
the authoritative annual total exactly. The largest adjustment was 0.0009 in
Base and 0.0022 in PEP.

## Validation

Publication and an independent check passed:

- maximum annual Pivot-to-reporter difference:
  `0.00000000000104`;
- maximum annual activity-to-water-use difference: `0`;
- maximum timeslice activity-rate to water-use-rate difference: `0`;
- maximum model-period reconciliation difference: `0`;
- maximum annual difference reconstructed from rounded rates:
  `0.00001935234`;
- every non-`ENV_WATER` Pivot value is unchanged; and
- the Dynamic Graph source hash and three terminal inputs are unchanged.

Example published 2020 values in `10^9 m3`:

| Run | Vapor | Groundwater | Surface water |
|---|---:|---:|---:|
| Base v12 | 404.9373 | 20.2706 | 257.4726 |
| PEP v12 | 404.9371 | 20.2706 | 257.4725 |

The published model-period terminal totals are 22,439.5632 for Base and
21,168.5896 for PEP. The complete publication took 13.5 seconds and required
no additional solve.

## Files and rerun

- Publisher: `scripts/publish_environmental_water_pivot.py`
- Evidence:
  `diagnostics/environmental_accounting/2026-07-26_env_water_pivot_published/`
- Timeslice reference:
  `diagnostics/environmental_accounting/2026-07-26_env_water_pivot_published/timeslice_reference.csv`
- Solver-view backup:
  `diagnostics/environmental_accounting/2026-07-26_env_water_pivot_published/solver_generated_view_backup/`

The `CLEWs-PHL` GitHub delivery compresses the four-file backup as
`solver_generated_view_backup.zip` because the uncompressed `RYTMTs.json`
exceeds GitHub's individual-file limit. Its contents retain the hashes in
`publication.json`; local publisher runs continue to create the directory.

After every new solve, rerun the publisher with a new evidence label. Use
`--dry-run` to validate without changing the current views.
