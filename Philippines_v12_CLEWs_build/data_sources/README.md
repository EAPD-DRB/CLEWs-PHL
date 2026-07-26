# Data sources, assumptions and calculations

This folder is the main place to answer “where did this number come from?”

- `DATA_SOURCES.md` identifies publications, datasets and inherited model
  sources in plain language.
- `ASSUMPTIONS.csv` lists choices made by modellers.
- `CALCULATIONS.csv` records formulas and transformations.
- `MODEL_DATA_MAP.csv` links model entities and parameters to the relevant
  source, assumption and calculation IDs.
- `calculation_notes/` contains longer explanations for questions that cannot
  be understood from one CSV row.
- `evidence/` contains retained input tables and calculation evidence.

Environmental-accounting formulas are in
`calculation_notes/ENVIRONMENTAL_ACCOUNTING.md`. They use the source v12 JSON,
the generated `ENV_LAND` JSON and normally generated result CSVs as model
evidence; no external coefficient is introduced.

An empty source field is never meant to imply “common knowledge.” A missing
original citation is labelled as a documentation gap.
