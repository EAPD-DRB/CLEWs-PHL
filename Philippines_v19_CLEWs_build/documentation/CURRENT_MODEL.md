# Current model: Philippines v19

The canonical editable case is `Philippines_v19`. It is an exact copy of the
working Philippines v18.0.1 source at Git commit `2735feb`, with only the
validated PM2.5 coverage patch applied. Its inherited archive SHA-256 is
`c3f4ee25d2e8c3315ced1be4bf819673859be45079536abb2cfbc40a65d1dc55`.

V19 changes only `genData.json` technology-to-emission membership and
`RYTEM.json` PM2.5 `EmissionActivityRatio`/zero companion rows for 52 existing
technologies. It changes no `TAMaxCI`, demand, cost, capacity, activity bound,
user constraint, solver setting, CO2e factor, or model identifier set. The
later 2020-2025 deployment-cap experiment is excluded.

The canonical validation run solved optimally at objective
369739249.45411736 in 471.112 seconds end-to-end, below the 600-second
acceptance limit. The portable archive is
`../muio/Philippines_v19_v19.0.0_MUIO.zip`. The six authoritative provenance
CSVs are complete cumulative ledgers; the v19 workbook is a review copy.
