# Philippines v16 COAL_PHASEOUT historical dispatch fix — 2026-08-07

## Outcome

The COAL_PHASEOUT-specific 2020-2024 activity bounds on
`PHL_POW_CHP_COAL_OLD` were removed. COAL_PHASEOUT now inherits the same
unbounded historical activity treatment as BASE, RE, and EV, while its
forward-looking coal phaseout ceiling remains unchanged from 2025 onward.

This change removes an observed historical dispatch calibration. It does not
remove coal capacity, alter residual stock, prescribe another generator's
dispatch, or weaken the policy's 2040 phaseout.

## Physical classification and equation map

- The 2020-2024 observed coal dispatch values are benchmark-only outcomes.
- `PHL_POW_CHP_COAL_OLD` is a physical legacy coal-fired electricity
  conversion technology. Its available inherited plant is represented by
  `ResidualCapacity`; dispatch is endogenous.
- The retained 2025-2040 upper-bound trajectory is the scenario's continuing
  policy constraint.
- `RYT.json:TAL` exports as
  `TotalTechnologyAnnualActivityLowerLimit` and enters
  `AAC3_TotalAnnualTechnologyActivityLowerLimit`.
- `RYT.json:TAU` exports as
  `TotalTechnologyAnnualActivityUpperLimit` and enters
  `AAC2_TotalAnnualTechnologyActivityUpperLimit`.
- Both equations constrain the annual sum of timeslice- and mode-specific
  `RateOfActivity`, weighted by `YearSplit`.

The removed lower and upper bounds left only a very narrow dispatch interval,
so they reproduced historical activity instead of calibrating the physical or
economic drivers that determine dispatch.

## Source change

Only `RYT.json` changed. Ten cells for scenario `SC_3hgjb`
(`COAL_PHASEOUT`) and technology `TEC_pyjfk`
(`PHL_POW_CHP_COAL_OLD`) were changed to `null`, invoking normal inheritance
from `SC_0` (`BASE`).

The promoted `RYT.json` is byte-identical to the solved disposable candidate;
its SHA-256 is
`ec62f8460fa589be89d403db8cab5bd09933a7bdae675f5644361a416f66ed41`.

| Year | Previous `TAL` | Previous `TAU` | New stored `TAL` | New stored `TAU` | Effective inherited bounds |
|---:|---:|---:|---|---|---|
| 2020 | 209.448 | 209.45 | `null` | `null` | 0 to 999999 |
| 2021 | 223.387 | 223.39 | `null` | `null` | 0 to 999999 |
| 2022 | 239.148 | 239.15 | `null` | `null` | 0 to 999999 |
| 2023 | 265.514 | 265.52 | `null` | `null` | 0 to 999999 |
| 2024 | 285.692 | 285.70 | `null` | `null` | 0 to 999999 |

The policy upper-bound path is unchanged: 267.84 in 2025, declining annually
to 17.86 in 2039 and zero from 2040 onward. The explicit zero `TAL` values from
2025 onward are also unchanged.

## Restoration record

If future evidence establishes that any removed quantity is a genuine
continuing physical or legal constraint, the exact previous values are in the
table above. Restoring them would require a new non-forcing classification and
validation; knowledge of historical dispatch alone is not sufficient.

## Validation

An unchanged control and the minimal candidate were run from disposable copies
through `DataFile.generateDatafile()`, preprocessing, GLPK matrix generation,
CBC optimization, CSV export, and pivot generation. Only COAL_PHASEOUT was
solved because the other three scenarios already inherited the intended
2020-2024 BASE bounds.

| Check | Unchanged control | Candidate |
|---|---:|---:|
| Solver status | Optimal | Optimal |
| Objective | 369741219.1940829 | 369740361.0258108 |
| Objective change | — | -858.1682721 (-0.00023210%) |
| Matrix rows | 791129 | 791124 |
| Matrix columns | 884956 | 884956 |
| Matrix nonzeros | 12540503 | 12540353 |
| CBC wall time | 344.42 s | 435.56 s |
| Complete application chain | 395.38 s | 497.19 s |

The five positive historical lower bounds previously generated five active
`AAC3` rows; their removal explains the five-row and 150-nonzero reductions.
Upper-bound rows remain but inherit the nonbinding value 999999.

Optimized `PHL_POW_CHP_COAL_OLD` activity changed as follows:

| Year | Control | Candidate | Difference |
|---:|---:|---:|---:|
| 2020 | 209.4500 | 276.2217 | +66.7717 |
| 2021 | 223.3900 | 258.9939 | +35.6039 |
| 2022 | 239.1480 | 251.3455 | +12.1975 |
| 2023 | 265.5200 | 279.0357 | +13.5157 |
| 2024 | 285.6920 | 256.9221 | -28.7699 |
| 2025 | 264.3330 | 266.5910 | +2.2580 |
| 2026 | 249.9900 | 249.9900 | 0.0000 |

The phaseout path from 2026 through the zero-activity result in 2040 is
unchanged. The candidate's longer CBC wall time is a 26.46 percent increase
relative to this single control run but remained inside the declared bounded
candidate budget. The model has alternative near-cost-equivalent capacity and
fuel-supply solutions, so changes outside the directly affected dispatch path
were observed; the very small objective change and preserved phaseout envelope
are consistent with degeneracy rather than an added requirement.

Result identity was checked using the distinct disposable case/run names
`COAL_PHASEOUT_CONTROL` and `COAL_PHASEOUT_CANDIDATE`. Their objective CSV
timestamps were 2026-08-07 13:37:22 and 13:45:49 EDT, respectively. Generated
`data.txt`, `data_processed.txt`, `lp.lp`, solver results, and CSV outputs were
not promoted to the live case.

## Checks not performed

- BASE, RE, and EV were not re-solved because their source and effective
  historical bounds did not change.
- No multi-run solver-timing study was performed; the runtime comparison above
  is one control/candidate pair.
