# Philippines v31 provenance cleanup — 2026-08-27

## Purpose

Reconcile inherited irrigation, crop-cost and yield narratives with the model structure that is actually active in Philippines v31. This is a documentation-only correction. It changes no model coefficient, scenario matrix or solved result.

## Active v31 interpretation

- `PHL_AGR_IRRIGATION` pools 2.006 Mha of maintained irrigation service across all irrigated crop modes. It is not rice-only capacity. Use is endogenous and 2020 new construction is disabled.
- Active full-cost rice modes use per-hectare net resource costs of 91.597970 irrigated and 78.542132 rainfed. Irrigation service is represented separately at 0.609137. The v16 cost-per-kilogram and v25 palay cash-share methods are historical and inactive.
- Low-input crop modes are disabled by the v30 single-management assumption until paired Philippine yield, cost and physical-input observations exist.
- Active crop yields retain normalized GAEZ spatial multipliers and follow FAO FOFA business-as-usual indices after the observed anchor period. The v16 uniform-yield statement and v24 generic 1% future path are historical and inactive.

## Reconciled records

`ASSUMPTIONS.csv` retains the historical v16, v24, v25 and v29 records, but their notes now identify the assumptions that supersede them in v31. `GAPS.csv` now reports only current evidence and calibration gaps:

- one shared irrigation-stock composition, reliability and retirement gap replaces three overlapping rice-only or stock-allocation rows;
- the spatial rice-calibration row records the actual v31 BASE 2020 outcome: 1.505206 Mha irrigated rice, zero rainfed rice and 19.294856 Mt irrigated paddy, with the total 2.006000 Mha shared irrigation service fully used;
- future rice costs are described on the active per-hectare resource-cost boundary;
- subnational yield and water-allocation gaps acknowledge the active heterogeneous cluster coefficients;
- the active FAO FOFA yield path replaces the stale v24 1% statement;
- the obsolete unsolved-v25 validation gap is removed because v31 has already passed its solve and validation gate;
- the water-cost gap distinguishes upstream delivery placeholders from the separately priced irrigation service.

## Validation boundary

The cleanup does not assert that the v31 rice result is calibrated. It makes the remaining defect explicit: current spatial yield coefficients allow production to concentrate in the best clusters, so the national yield/area anchor is not reproduced ex post. Any corrective model change requires paired area, production, cropping-intensity, cost and water-regime evidence. A benchmark comparison may flag the deviation but must not impose an activity, area-share or irrigation-retention bound.

The six CSV ledgers remain authoritative. The generated XLSX review view must be regenerated after these CSV changes and the v31 fast provenance gate must pass.
