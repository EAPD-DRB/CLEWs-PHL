# Philippines v30 CLEWs model

Philippines v30 is the validated crop-yield and renewable-land successor to
Philippines v29. It retains the complete inherited model and provenance while
making the crop and land representation physically explicit.

## What changed

- Crop systems consume shared physical cropland and irrigation service directly.
- Twelve evidenced crop-by-water systems remain active; twelve unsupported
  input-level duplicates remain available as mode slots but are operationally disabled.
- Crop yields retain only the 2020 Philippine initialization and then follow
  the FAO FOFA2050 Philippines Business As Usual trajectory.
- Population, solar PV, and onshore wind consume the existing built-up-land
  class during optimization.
- The obsolete policy-only idle-cropland cap was removed, leaving cultivated
  and idle cropland endogenous in every scenario.

## Validation

The complete static and four-scenario matrix gate passed. CBC solved BASE,
COAL_PHASEOUT, RE, and EV optimally under the hard 300-second deadline.
Result validation confirmed national land closure, the exact endogenous
built-land identity, and zero activity in unsupported crop modes.

The complete standalone source ledger is under `data_sources/`. Implementation
documentation and result summaries are under `documentation/` and
`diagnostics/`.

## Delivered model

- Portable editable case: `muio/Philippines_v30_v30.0.0_MUIO.zip`
- Case identity: `Philippines_v30`
- Horizon: 2020–2053
- Runtime solver matrices, logs, results, and populated views: excluded

