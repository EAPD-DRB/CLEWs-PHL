# Philippines v18 CLEWs model

Philippines v18 is the current whole-country model. It begins from the complete
committed Philippines v17 source, cumulative provenance ledger, and retained
evidence. All v17 national land-cover constraints and safeguards are retained.

V18 updates the central energy inputs that had country-specific evidence or a
clear chronology correction:

- geothermal availability is 0.70;
- the onshore-wind timeslice profile has a 21.9731% annual mean, derived from
  the same NREL restricted resource screen as its 663.84 PJ/year ceiling;
- coal power capital cost is 1,604.789 MUSD/GW and the documented coal-price
  conversion check uses approximately 22.1 GJ/t;
- nuclear SMR capital cost is 8,000 MUSD/GW and its 60-year life is retained;
- large-hydro operating life is 60 years; and
- the existing domestic-gas and imported-gas routes have separate prices and
  annual limits. LNG import activity is zero through 2022 and available from
  2023. No technology or commodity was added.

V18 now also applies policy-neutral annual generation deployment envelopes
from 2026. They constrain only `TotalAnnualMaxCapacityInvestment`: capacity
choice and dispatch remain endogenous, all source cells through 2025 are
preserved, and retirement plus permitted-vintage replacement allowances prevent
the ceiling from forcing stock retirement. No minimum, share, activity bound,
aggregate construction cap, or PEP capacity total is introduced.

## Delivered model

- Portable editable case: `muio/Philippines_v18_v18.0.0_MUIO.zip`
- Archive checksum: `muio/SHA256SUMS`
- Case identity: `Philippines_v18`
- Validated run: `DEPLOYMENT_ENVELOPE_V18_BASE`
- Horizon: 2020-2053

Extract `Philippines_v18` under `MUIOGO/WebAPP/DataStorage/` and regenerate the
solver input through MUIOGO. Runtime solver files and results are excluded from
the portable archive.

## Provenance

The six CSV files under `data_sources/` are the authoritative cumulative
ledger. They contain the complete inherited v17 record plus the v18 sources,
calculations, assumptions, model mappings, gaps, and implementation record.
`data_sources/PHILIPPINES_V18_CANONICAL_SCHEMA_LEDGER.xlsx` is a formatted
review copy. The package is standalone and does not require an older package or
ledger for interpretation.

The normalized input record is
`data_sources/snapshots/energy_inputs_v18_2026-08-12.json`; the exact source
diff is in `energy_inputs_v18_build_manifest.json`; and solved validation is in
`energy_inputs_v18_validation.json`.

The deployment-envelope record is
`data_sources/snapshots/deployment_envelopes_v18_2026-08-13.json`; the exact
source diff is in `deployment_envelope_build_manifest.json`; and static and
solved validation are in `deployment_envelope_static_validation.json` and
`deployment_envelope_validation.json`.

## Validation

The deployment-envelope BASE run solved optimally at objective
369743573.32256168, 15.64275390 or 0.0000042307% above the unchanged v18
control. The new source change is limited to `RYT.json` `TAMaxCI.SC_0`.
Technology IDs, commodity IDs, user constraints, and all other source JSON are
unchanged. The solved 2020 land partition exactly reproduces v17 and the annual
national land account remains closed at 295.8131 thousand km2.

See `documentation/MODEL_FIXES_DEPLOYMENT_ENVELOPES_2026-08-13.md` and
`documentation/REPRODUCE.md`.
