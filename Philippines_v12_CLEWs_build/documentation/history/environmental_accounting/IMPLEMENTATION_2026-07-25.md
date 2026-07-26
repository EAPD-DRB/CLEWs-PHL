# Environmental-accounting implementation record — 25 July 2026

The `add-environmental-accounting` skill from the sibling `Model-tools`
repository was applied to Philippines v12.

## Decision

An exact two-terminal JSON formulation was investigated and rejected for the
installed solver. `LNDAGRPHLC01` through `LNDAGRPHLC08` each use 30 operating
modes, and their combined evapotranspiration, groundwater and surface-water
coefficients vary by mode. The largest spread is 0.447.

MUIO's UDC activity multiplier is indexed by technology and year. It cannot
represent those mode-specific coefficients. Adding an `ENV_WATER` technology
with a technology-level equality would therefore be inexact.

The delivered implementation is reporting-only. It calculates stable,
labelled `ENV_WATER` and `ENV_LAND` reporting modes from normal solved result
files and aggregates native emissions. No model JSON or generated result file
was edited.

## Added files

- `scripts/report_environmental_accounting.py`
- `documentation/ENVIRONMENTAL_ACCOUNTING.md`
- `data_sources/calculation_notes/ENVIRONMENTAL_ACCOUNTING.md`
- `diagnostics/environmental_accounting/2026-07-25_final/`

The earlier `2026-07-25_initial` diagnostic is retained as pre-final evidence;
the final directory adds the selected fresh-control file hashes.

The current READMEs, source/assumption/calculation map and limitations were
updated in their existing folder structure.

## Validation evidence

Both saved runs and both fresh unchanged controls solve optimally. Fresh
control `data.txt` hashes are identical to the saved Base and PEP inputs.
Top-level case JSON hashes are identical. The control used
`PYTHONHASHSEED=0`.

Processed-input ordering differs and CBC selects alternate cost-identical
bases. Land states and native emissions are identical. Separate groundwater
and surface-water residuals move substantially; their liquid total also moves
by up to 0.5807 `10^9 m3` in PEP. This sensitivity is retained in
`validation.json` and is not described as unchanged.

The source case remained `Philippines_v12` with 172 technologies, 92
commodities and three existing constraints. No environmental terminal
technology or new UDC was added.
