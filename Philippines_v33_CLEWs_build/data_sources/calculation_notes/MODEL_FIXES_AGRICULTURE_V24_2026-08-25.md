# Philippines v24 agriculture repair

This release candidate is built from `Philippines_v23` only. Crop output per modeled land activity uses PSA achieved national anchors for 2020-2024 where a compatible series exists. From 2025 it grows at 1.0%/year. The historical GAEZ crop coefficients are used only as relative cluster, water-regime and input-level patterns and are normalized around those achieved anchors; their absolute potential-yield levels are not imported.

Maize and vegetables retain their GAEZ irrigation response. Coconut, sugarcane and the heterogeneous other-crop aggregate keep irrigated output at parity with the corresponding rainfed input level because this package lacks a defensible Philippine irrigation response for them. High/low modes regain a physical yield distinction. Existing costs and land-option capital costs remain unchanged; no mode is selected or prohibited by an activity bound.

`DEMAGRSURPHL` and `DEMAGRGWTPHL` no longer carry `TAU=999999`. Their TAUs equal the corresponding already-enforced national annual water envelopes in `RYCn.json`, so the change is a transparent redundant guardrail and does not force the observed 2024 AFF withdrawals. The v23 2.006 Mha rice irrigation residual stock remains flat as maintained service capacity. NIA reports 2.155026 Mha total developed irrigation in 2024, but it is not a rice-only stock and the available source does not provide a commissioning-age or rehabilitation schedule; no unsupported retirement or expansion path is installed.

All eight crop-cluster technologies now report CO2e. Managed-soil direct and indirect N2O uses the retained Philippine-inventory average of 0.0762711793781 MtCO2e per model land unit on every managed crop mode. Rice adds 0.651794528417 on rainfed modes and 0.869059371222 on irrigated modes. These reproduce the retained 2020 rice inventory total at the source service-area stocks using IPCC 2019 Refinement aggregated water-regime factors 0.45 and 0.60. CO2e has zero penalty and non-binding limits in v23, so the EARs improve accounting without creating a hidden crop target. Input-specific fertilizer factors remain a documented gap. Land-use-change emissions remain outside recurring activity EARs because they require transition-specific stock-change accounting.

Observed crop areas, crop shares, irrigated/rainfed shares, water-source shares, withdrawals and GHG totals are validation benchmarks. v24 adds no activity target, share constraint or user-defined constraint. Required validation is deterministic source checks, application generation and preprocessing, GLPK matrix inspection, one BASE optimum, the three existing policy overlays, result comparison to the verified v23 candidate, sealing, and content-preserving promotion.

## Implemented source delta and equation map

Only `genData.json`, `RYT.json`, `RYTCM.json` and `RYTEM.json` differ from v23. `RYTCM.OAR` changes 192 crop/cluster/mode rows. `RYT.TAU` changes only the two agricultural water-delivery technologies. `genData.json` adds CO2e EAR membership to the eight crop-cluster technologies and `RYTEM.EAR` supplies the mode/year factors. All input ratios, crop demands, costs, residual capacities, minimum activity/capacity rows, scenario definitions and user-defined constraints remain unchanged.

The source equation gate passed 22 checks. The standard generic physical gate passed under BASE, COAL_PHASEOUT, RE and EV before generation. An optional diagnostic invocation that reclassified 2021-2024 as a historical boundary reported 330 inherited heat-service rows on both v24 and unchanged v23; it was therefore classified as a gate-configuration artifact and retained outside the candidate rather than treated as a v24 regression.

## Generated matrix and optimization results

All four application-generated data files, preprocessing steps and GLPK matrix checks passed. Each scenario adds 6,528 rows, 6,528 columns and 476,544 nonzeros relative to its verified v23 counterpart. The added dimensions are the eight clusters times 24 crop modes times 34 years in the mode-resolved emissions equations. BASE therefore contains 563,273 rows, 594,877 columns and 8,607,675 matrix nonzeros.

| Scenario | Status | Objective | Change from v23 | Solve time | Runtime ratio |
|---|---:|---:|---:|---:|---:|
| BASE | Optimal | 369,764,275.245 | -50,621.382 (-0.013688%) | 248.52 s | 1.55 |
| COAL_PHASEOUT | Optimal | 369,782,569.891 | -50,621.381 (-0.013688%) | 424.83 s | 1.51 |
| RE | Optimal | 369,775,964.365 | -50,621.381 (-0.013688%) | 374.76 s | 1.34 |
| EV | Optimal | 369,749,398.429 | -50,621.381 (-0.013689%) | 567.24 s | 1.85 |

The objective shift is consistent to less than 0.001 model cost units across policies. Agricultural surface-water activity is 52.9431 km3 in 2020, 56.6702 in 2024 and 54.4670 in 2053, leaving respectively 72.8469, 69.6291 and 77.3659 km3 of headroom under the redundant agriculture TAU. Groundwater delivery remains zero endogenously. Both national water-constraint dual series are zero in every year and scenario.

BASE crop CO2e is 22.1403 Mt in 2020, 23.1245 Mt in 2024 and 22.5137 Mt in 2053. Mode-resolved CSV emissions reconcile to activity times EAR within 0.00043 Mt, the precision expected from rounded CSV exports. Policy cases differ slightly on degenerate non-rice crop allocations: the maximum annual spread is 0.1835 model land units and 0.0139 MtCO2e, while rice activity and agricultural water series are identical. These small differences are retained rather than forced away.

Crop-mode activity is an endogenous annual land allocation, not a conserved stock and therefore is not held at its 2020 value. The conserved national `PHL_LND` commodity balance is checked instead: production and use are about 295.813 model land units every year, with maximum absolute residuals of 0.0009-0.0018 across the four rounded CSV exports.

The endogenous solution selects irrigated high-input rice mode 19 and no rainfed rice in the reported years; BASE rice activity is 14.9452 model land units in 2020, 15.9973 in 2024 and 15.3753 in 2053. This does not reproduce the observed irrigated/rainfed split or the full source service-area stocks. It is a calibration benchmark and a remaining economics/land-option issue, not grounds for an activity or share constraint.

## Runtime incident and run inventory

The first concurrent RE and EV attempts reached 600 s and 660 s without optimal solutions. Neither reported infeasibility and both showed continuing simplex progress. Their complete run directories were moved to `.Philippines_v24-agriculture-diagnostics-20260825`, leaving the promotable candidate with only four canonical successful runs. Sequential retries were required to establish exact policy optimality and are the RE and EV results in the table above. Total optimizer inventory is six attempts: four successful canonical runs plus two preserved concurrent timeouts.

Regeneration produced byte-identical `data.txt` files and identical matrices but different LP hashes because derived Python sets were emitted in process-dependent order. A line-level comparison confirms that every preprocessed difference is set ordering only. This does not change the equations, but it can change CBC's pivot path and explains part of the runtime variation. The sealed LPs are authoritative; a future application-level reproducibility fix should sort derived sets or fix the Python hash seed. No additional v24 solve was spent searching for a favorable order.

## Schema ledger and limitations

The canonical `SOURCES.csv`, `ASSUMPTIONS.csv`, `CALCULATIONS.csv`, `MODEL_MAP.csv`, `GAPS.csv` and `CHANGES.csv` contain unique v24 records with no missing or broken v24 cross-references. `GAPS.csv` explicitly retains crop-specific long-run productivity projections, irrigation stock vintages/non-rice allocation, input-specific fertilizer N2O and transition-specific land-use-change GHG as future upgrades. The machine-readable qualification is `documentation/agriculture_v24_four_scenario_validation.json`; it passed with zero failures and permits sealing and content-preserving promotion.
