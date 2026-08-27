# Philippines v22 FIT accounting correction (r9)

## Outcome and physical classification

This disposable candidate retains `PHL_POW_CHP_BIOM_FIT_OLD` as a closed
physical 250 MW legacy stock. Its capacity, no-new-build setting, crop-residue
activity ceiling, efficiency, cooling-water input, emissions and electricity
output are unchanged. The eligible stock is a continuing contractual fact;
its generation and dispatch are endogenous benchmark-only outcomes.

The v21 formulation subtracted feed-in-tariff receipts from variable cost. In
2020, the plant coefficient was -85.3229135965 MUSD/PJ electricity. Combined
with the generic upstream biomass charge, the complete route had a negative
marginal system cost of approximately -21.3 MUSD/PJ. A domestic tariff paid by
customers to a generator is a transfer, not a physical resource cost, unless
the model also represents the payer and a distributional or fiscal objective.

## Source formulation

The correction is deliberately narrow:

- add commodity `COM_v22fit` / `PHL_PRO_BIOM_FIT_RESIDUE`;
- use mode 2 of existing `PHL_PRO_PROC_BIOM` to supply that commodity at
  3.9493417760415483 MUSD/PJ biomass;
- replace the FIT plant's generic biomass input with `COM_v22fit` at its
  unchanged 4.000666667 PJ/PJ input ratio;
- set the FIT plant variable cost to the 0.0001 numerical epsilon; and
- include the plant in the existing `RENEWABLES` definition with coefficients
  copied exactly from its physical twin, `PHL_POW_CHP_BIOM_OLD`.

The physical-cost identity is

`3.9493417760415483 × 4.000666667 = 15.8 MUSD/PJ electricity`.

No technology, demand, activity floor, build requirement, generation target,
dispatch share or user-defined constraint is added. All existing demand rows,
demand profiles, capacity bounds and timeslice values are preserved. The new
commodity has zero final demand, one producing mode and one consuming mode;
the existing supply technology retains 999999 annual build and activity
headroom, so the link creates no deterministic demand shortfall. Feed-in-
tariff receipts will be calculated from solved activity and published after
each successful solve without feeding back into the optimization.

## Why the RE numerical incident was attributed to FIT accounting

The original r8 RE LP had SHA-256
`0a99d5dfdc5ab384de97f0e397836d33290ef82ba2d5095103d38a98826d476d`.
An equilibrium-scaled CBC diagnostic on that unchanged LP suffered numerical
breakdown and was interrupted: its log reached objective 1.4834939e25, primal
infeasibility 6.8099553e25 and dual infeasibility 1.6596205e21.

A second diagnostic changed only the 612 objective coefficients for FIT
biomass activity, copying the ordinary biomass plant coefficients. The row
set, column set, bounds and constraint-matrix coefficients were unchanged.
That LP, SHA-256
`6ef6bddfb933ddf758263628a6e502360bb681795ca928680b6c1ba9d3a7b87e`,
solved optimally at objective 369835290.97118282 in 175232 iterations and
124.08 wall seconds. This generated-file test is diagnostic only and cannot
be promoted. The accepted remedy is reproduced above in source parameters.

## Evidence and validation status

Source edits are reproducible through
`scripts/apply_philippines_v22_fit_accounting.py`. Deterministic checks are in
`scripts/validate_philippines_v22_fit_accounting.py` and
`fit_accounting_r9_deterministic_gate.json`. The source calculation, model
mapping, boundary assumption, evidence source, gap and change record are in
the six CSV schema ledgers under `data_sources/`.

The deterministic and matrix gates passed. BASE first solved optimally in
97.03 seconds. COAL_PHASEOUT, RE and EV were then solved concurrently and all
returned proven optima in 136.03, 121.76 and 150.79 seconds, respectively.
The exact objectives and LP hashes are recorded in
`FIT_ACCOUNTING_R9_VALIDATION_SUMMARY.json`. The candidate has therefore
passed the four-scenario solve gate, but it has deliberately not been promoted
to a live case; promotion and live regenerated-input identity checks are the
next paused step.

## Deferred limitations

This correction does not address the broader biofuel, reliability, solar
timing, cooling-water, T&D-loss, availability or pre-2026 build-envelope
issues. The underlying 15.8 MUSD/PJ residue collection assumption remains an
inherited ERC-anchored judgement and is not a plant-specific engineering-cost
estimate. FIT incidence and financing remain outside the model and are
recorded in `GAPS.csv`.

## Promotion (2026-08-21)

The validated r9 source was promoted to `Philippines_v22`. All 22 root source
JSON files and all six schema-ledger CSVs were byte-identical before final
promotion documentation. The live application-generated `data.txt` is
byte-identical to the solved BASE candidate. Preprocessed data are equivalent
after canonicalizing unordered derived-set declarations, and GLPK reproduced
the exact 553001-row, 584981-column, 8108623-nonzero matrix. No post-promotion
CBC optimization was run.
