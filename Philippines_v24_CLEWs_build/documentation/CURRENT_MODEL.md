# Current model: Philippines v21

The canonical editable case is
`MUIOGO/WebAPP/DataStorage/Philippines_v21`. It carries the complete v20 source
and provenance forward and adds three compact technologies and one final-demand
commodity for off-grid oil, off-grid renewable service, and the closed legacy
FIT biomass tranche. It also restores the retained physical seasonal hydro
profile. Observed generation remains benchmark-only: v21 adds no generation
minimum, fixed share, realized-build equality, or deviation penalty.

The accepted r4 candidate is optimal at 369746369.55929643 and took 155.89 CBC
seconds. Candidate and live source JSON are byte-identical; regenerated
`data.txt` is byte-identical with SHA-256
`faca05cebcd93759d87428a073d0651b7c61c409848b58e6337d1da40facbc7c`.
The live GLPK check reproduces 821,091 rows, 911,143 columns, and 13,210,825
matrix nonzeros, so no second live optimization was run.

The six authoritative CSV ledgers are cumulative and self-contained;
`../data_sources/PHILIPPINES_V21_CANONICAL_SCHEMA_LEDGER.xlsx` is a review copy.
The complete validation retains all four formulation attempts and records zero
sensitivity runs under `../data_sources/snapshots/`. No v21 release archive was
built as part of this focused source promotion.
