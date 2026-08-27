# Philippines v16 irrigated-rice calibration

Date: 2026-08-07  
Case/run: `Philippines_v16/BASE_V15`

## Design and source hierarchy

The physical objective is to let food demand choose rainfed or irrigated land
from realistic available stocks, annual productivity and costs. Irrigated area
is an endogenous activity, not a calibration target.

The primary source is the Philippine Statistics Authority's *Selected
Statistics on Agriculture and Fisheries 2022*. For 2020 it reports 2.01 Mha of
irrigation service area, 14.57 Mt of irrigated palay from 3.25 Mha harvested,
and 4.72 Mt of rainfed palay from 1.47 Mha harvested. Its 2021 cost tables report
12.49 PHP/kg for irrigated palay and 13.95 PHP/kg for non-irrigated palay; the
same publication gives 49.62 PHP/USD in 2020 and 49.25 in 2021. The DA-PRDP
I-BUILD manual supplies the generic indicative irrigation-system cost of
300,000 PHP/ha. A JICA Philippine irrigation appraisal supplies the 30-year
economic life. FAO independently reports 2.006 Mha equipped for irrigation in
2020 and 1.731 Mha in 2015. The FAO series is a cross-check, not the primary
input; it explains the older approximately 1.7 Mha benchmark.

## Equation mapping

`ResidualCapacity` enters `CAa2_TotalAnnualCapacity`; `CAa4` and `CAb1` make
that capacity available to activity but do not require its use. `OutputActivityRatio`
enters the annual commodity balance `EBb4`. `VariableCost` enters
`OC1_OperatingCostsVariable` and the objective. `CapitalCost` multiplies only
`NewCapacity` in `CC1_UndiscountedCapitalInvestment` and the discounted
objective. `OperationalLife` determines survival of endogenous capacity
vintages. MUIO exports these parameters from `RT.json`, `RYT.json`,
`RYTCM.json`, and `RYTM.json` through `DataFile.generateDatafile()` and
preprocessing.

The crop land-option technologies are physical capacity stocks; the eight
`LNDAGRPHLC` technologies are physical land/crop/water conversions. Food
demand is unchanged. The observations are classified as initial capacity and
physical/economic coefficients. Observed activity is benchmark-only.

## Installed calculations

- One model land unit is 0.1 Mha. `LNDRCPHITOT` residual capacity is 20.06 and
  `LNDRCPHRTOT` is 14.7 in every year. Constant residual capacity represents
  maintained national stock because no scheme age distribution is available.
- Annual physical-land productivity is `production / physical area / 10`:
  0.726321036889332 Mt per 1000 km2 irrigated and
  0.32108843537414966 rainfed. Regime multipliers of 0.8980756098785642 and
  0.42727684452644354 retain the inherited GAEZ cluster and input-level pattern.
- Production cost is 253.60406091370558 million USD/Mt irrigated and
  283.24873096446703 million USD/Mt rainfed. Each rice-mode VC is its calibrated
  rice OAR times the corresponding cost per Mt.
- New irrigated-rice capacity costs 604.5949214026602 million USD per
  1000 km2, from 300,000 PHP/ha at 49.62 PHP/USD, and has a 30-year operational
  life. Existing residual capacity is sunk.

No commodity, technology, UDC, demand, activity bound, source share or area
share was added. Policy-scenario rows remain null and inherit BASE.

## Model run

Before the cost-and-life refinement, the disposable candidate and promoted live case passed the normal application
generation, preprocessing, LP creation, CBC solve and result export. The live
case solved optimal at 369729190.46216184; its full chain took 334.65 seconds
and CBC took 281.75 wall-seconds. The source-identical disposable result was
369729190.46215844 in 216.66 seconds. The 0.0000034 objective difference is
solver tolerance. The matrix structure was unchanged because the change added
no object or indexed row. The subsequent change from 250,000 to 300,000 PHP/ha
and from 15 to 30 years has not been run; the user will run the model separately.

The model voluntarily selects 2.006 Mha of irrigated land in 2020 and through
2053, compared with 0.71313 Mha before this calibration, and constructs no new
irrigation capacity. Rainfed rice activity is 0.87965 Mha in 2020 and grows
endogenously with food demand. Selected high-yield clusters produce 16.2883 Mt
of irrigated rice in 2020, above the 14.57 Mt national benchmark; this disclosed
spatial-composition gap must be addressed with spatial evidence, not an area
constraint.

The solved candidate is retained temporarily at
`/private/tmp/phl-v16-irrigated-rice.fdLH25/DataStorage/Philippines_v16_candidate`.
Its source hashes are recorded in `irrigated_rice_calibration_manifest.json`.
The live result timestamp is 2026-08-07 13:24-13:25 local time and predates the
cost-and-life refinement. The current source inputs are `RT.json`, `RYT.json`,
`RYTCM.json`, and `RYTM.json`; generated files and result CSVs are outputs of
the normal application chain.
