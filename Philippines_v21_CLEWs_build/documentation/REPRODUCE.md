# Reproduce and validate Philippines v21

1. Start from the source-matched `Philippines_v20` case and run
   `scripts/apply_power_allocation_v21_compact.py` on a disposable v21 copy.
   Before any optimization, run
   `scripts/validate_power_allocation_v21_compact.py`; it checks exact stock and
   demand conservation plus every-year and every-timeslice off-grid
   stock/vintage/service feasibility.
2. Generate and preprocess through MUIOGO, then run GLPK `--check` against
   `WebAPP/SOLVERs/model.v.5.4.txt`. The accepted matrix has 821,091 rows,
   911,143 columns, and 13,210,825 matrix nonzeros. If a new result is actually
   required, run one CBC optimization with at least the retained 500-second
   budget. Accepted r4 is optimal at 369746369.55929643 in 155.89 CBC seconds.
3. Rebuild the DOE comparison with
   `scripts/compare_power_allocation_v21.py`, update the six ledgers with
   `scripts/update_philippines_v21_power_ledger.py`, validate them with
   `scripts/provenance.py data_sources --stage build`, and rebuild the review
   workbook with `scripts/build_philippines_v21_ledger_workbook.py`.

The accepted candidate and promoted live case already have byte-identical
source JSON and generated `data.txt`; therefore reproducing the retained result
does not require another live solve. Four formulation runs are recorded (r1 and
r2 timeouts, r3 rejected diagnostic, r4 accepted), and none is a sensitivity.
