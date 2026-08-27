# Philippines v31 non-road transport repair

Date: 2026-08-26  
Parent: `Philippines_v30`  
Status: implemented, fast-gated, and solved across all four scenarios

V31 repairs the objective-dominating shipping unit error and the related ammonia, aviation and rail template inconsistencies in one bounded transport release. It does not alter road transport.

## Shipping

Shipping activity remains billion tonne-km and the 2020 activity remains 393.988. `CAU` changes from 0.1 to 100 billion tonne-km per thousand vessels-year. `RC` and `TAMaxCI` are divided by 1,000, leaving the feasible activity envelope unchanged. The resulting 2020 residual capacity is 3.94000394 thousand vessels, inside the PSA freight-service bracket of 3.609 thousand cargo+tanker vessels and 4.237 thousand when tugs/dredgers are included. Liquid input remains 33.095 PJ in 2020, close to DOE inland-water transport's 31.929 PJ.

The conventional capital cost is not the suggested unsupported $15 million midpoint. It is the complete MARINA 2020-2024 count-weighted acquisition mean for cargo, tanker, tug and dredger vessels: USD 2219.05 million / 406 = USD 5.465640 million per vessel, or 5465.640394 MUSD per thousand vessels. The inherited 1.5% fixed-O&M ratio is retained and explicitly marked as an assumption. Costs are constant in real terms through 2053, removing decade resets and terminal zeros.

Ammonia shipping uses the same total heat rate as liquid shipping, split into 0.0798 PJ ammonia and 0.0042 PJ pilot liquid per billion tonne-km. Pilot-oil direct emissions are included at 5% of the liquid-ship factor. Its capital cost is 6422.127463 MUSD per thousand vessels, the DNV 17.5% midpoint premium over the Philippine conventional-vessel basis.

## Aviation and rail

Aviation is normalized to aircraft-km by dividing annual activity and `CAU` by ten and multiplying `IAR` and `VC` by ten. This leaves fleet capacity, fuel use, upstream emissions and variable-cost totals invariant. The 2020 fuel result remains about 9.76 PJ versus DOE's 9.157 PJ. Capital cost is held at the inherited real 89 MUSD/aircraft through 2053, eliminating the decade sawtooth and free terminal years.

Rail already uses train-km energy intensities. `CAU` changes from 1 to 0.1, and `RC` and `TAMaxCI` are multiplied by ten. Activity and energy remain unchanged; the implied utilization is 100,000 train-km/trainset-year. A harmonized national rolling-stock register remains an explicit sensitivity gap.

## Solver boundary

The blocking v31 pre-flight runs inherited structural and land checks plus transport-specific checks for finite values, valid inheritance, declared inputs/outputs/emissions, positive terminal capital costs, exact reciprocal rescaling, fleet plausibility, ammonia heat-rate and pilot-emission accounting, 2020 DOE energy invariants, annual capacity headroom, and complete provenance. It hashes all model JSON and canonical CSV ledger inputs, but generates no LP and invokes no optimizer. The measured fast-gate runtime was 6.27 seconds internally and 6.96 seconds wall-clock.

After that gate passes, `prepare_philippines_v31_matrix.py` generates and GLPK-checks only the selected scenario and writes a matrix record tied to the fast-gate input fingerprint. `run_philippines_v31.py` blocks CBC if the gate, fingerprint, matrix record, or LP hash differs. The four-scenario matrix audit is retained separately as `deep_matrix_audit_v31.json`; it is optional diagnostic work, not blocking pre-flight.

## Solved validation

All four scenarios solved to optimality inside the fixed 300-second limit. Objectives are 816,774.34 MUSD (BASE), 832,681.24 (COAL_PHASEOUT), 826,050.66 (RE), and 793,751.53 (EV), reductions of 444-466 times from v30. Shipping contributes 6.8-7.1% of the discounted objective. BASE 2050 shipping capital investment is 5,565.48 MUSD, and 2020 shipping energy remains 33.095 PJ. Final CBC cleanup terminates with no reported primal or dual infeasibility on the final iteration.

Ammonia shipping is structurally usable and has the same total heat rate as liquid shipping, but is selected only at numerical trace levels in these four scenarios because it is not economically competitive under the inherited fuel system. This is an economic result rather than the former 43,527-times heat-rate lockout.

CBC's proposed perturbation diagnostic remains about 1.10-1.17 million percent, above the suggested 10,000% threshold. The cause is the inherited epsilon-scale objective coefficients outside this transport repair. It is recorded as a numerical-conditioning advisory in `validation_transport_v31.json`; optimal termination and final cleanup pass, but dual/shadow-price interpretation should remain cautious until the epsilon policy is separately reviewed.
