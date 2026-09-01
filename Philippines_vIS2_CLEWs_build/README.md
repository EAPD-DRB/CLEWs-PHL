# Philippines vIS2 CLEWs model

Philippines vIS2 is the agriculture-and-land spatial successor to Philippines
vIS1.5. It replaces the eight national land/yield clusters and national
irrigation-service route with 29 nonzero LUZ/VIS/MIN/OFF land intersections
and four island/residual irrigation-service stocks. National crop markets and
the vIS1.5 national surface-water and groundwater constraints remain intact.

The change is non-forcing: provincial observations initialize spatial yield
drivers and irrigation stocks but do not prescribe crop production, activity,
market shares or node shares. Absolute land-use floors are allocated rather
than duplicated, disabled modes are absent from generated mode sets, and land
new capacity is fixed to zero.

## Validation

BASE, COAL_PHASEOUT, RE and EV reached optimal solutions within their declared
deadlines. No run printed an early primal-infeasibility declaration or
postsolve restart. The schema-ledger audit resolved all vIS2 source,
assumption, calculation and model-map references and verified the retained
evidence checksums.

The archive excludes solver matrices, logs, result tables and populated views.
Compact generation and validation records are retained in `documentation/`.

## Delivered model

- Portable editable case: `muio/Philippines_vIS2_vIS2.0.0_MUIO.zip`
- Case identity: `Philippines_vIS2`
- Horizon: 2020–2053
- Runtime solver matrices, logs, results and populated views: excluded

## Important limitation

The legacy EV scenario directly imposes a technology-activity trajectory. Its
low objective should not be interpreted as a calibrated welfare result until
that forcing formulation and the completeness of EV system costs are reviewed.
