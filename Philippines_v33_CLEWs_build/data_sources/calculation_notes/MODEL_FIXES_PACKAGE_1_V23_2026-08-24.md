# Philippines v23 Package 1 — candidate design

This candidate starts from the latest validated Philippines v22 source, including the August 24 EV/truck turnover correction. Observations are classified as initial stocks, exogenous final demands, continuing physical/planning constraints, or validation benchmarks. No activity, generation, dispatch, technology share, realized investment, or fuel share is forced.

The undefined input-free domestic biofuel processor is disabled. A separate positive-cost import technology supplies the existing biofuel commodity at the model border. The household coal-labelled stove is rewired to biomass energy, retained only as a closed charcoal initial-stock proxy, and receives no new capacity. Coal hydrogen and new coal agriculture heat are closed; CCS entry begins no earlier than 2030.

The main T&D input ratio uses DOE sales plus system losses over sales. Solar CFs are shifted from UTC to Philippine local time without changing annual energy. The DOE peak-to-average profile is applied only to fixed household and service electricity demands; fuel-neutral agriculture motive-power and processing services retain their service profiles. New thermal AFs are below one. Historical 2021-2025 unlimited power/T&D build cells are replaced by finite delivery envelopes.

Reserve is not hidden in CF. One user-defined inequality requires credited firm generation capacity to cover endogenous annual `PHL_POW_TD` activity at the DOE peak-to-average ratio plus 25 percent planning reserve. Because the RHS-equivalent term uses endogenous grid throughput, future electrification raises the requirement automatically.

Qualification order is mandatory: generic source-only physical gate; Package 1 exact-cell and semantic validation; UI-path generation and preprocessing; `glpsol --check`; one disposable BASE CBC solve; result comparison with the retained v22 canonical baseline; then source-only promotion and byte-identity checks. Policy scenarios are not optimizer prerequisites for this source-only physical package unless BASE or scenario inheritance diagnostics show a material unresolved issue.

## Final validation record

At the user's request, policy qualification became a promotion prerequisite.
The generic RE pre-flight prevented an impossible run: the initial builder had
cleared 35 untouched post-2025 policy `TAMaxCI` cells, including nuclear build
allowances needed by the 2032 and 2035 equality rows. The builder now clears
inheritance only in years actually edited; the original v22 policy values were
restored before any policy generation or optimization. Exact cells are in
`documentation/package1_v23_policy_inheritance_repair.json`.

All four corrected source gates, Package 1 semantic checks, UI-path matrices
and GLPK checks passed. CBC returned proven optimal solutions for BASE,
COAL_PHASEOUT, RE and EV. Objectives were 369951589.021, 369974408.908,
369965855.123 and 369936176.666; changes from the corresponding v22 runs were
+0.04128%, +0.04275%, +0.04222% and +0.03505%. All reserve rows were feasible
and disabled routes had zero activity. Four optimizer runs were performed:
BASE first, followed by the three explicitly requested policy runs
concurrently in isolated directories. No shared viewer output was generated.

BASE solve time rose from 113.18 to 165.78 seconds. The v23 presolved matrix is
smaller, while CBC iterations rose from 176460 to 229275. The binding reserve
coupling and interacting adequacy corrections are the evidence-based likely
cause. No extra reserve-off A/B optimization was run solely for attribution.

The comprehensive change and validation record is
`documentation/MODEL_FIXES_PACKAGE_1_V23_2026-08-24.md`; the four-scenario
hashed record is `documentation/package1_v23_four_scenario_validation.json`.

## Completed promotion identity (2026-08-24)

Live root source JSON and generated `data.txt` are byte-identical to the solved
candidate. Canonicalized processed sets and GLPK dimensions match. No live CBC
rerun was performed.
