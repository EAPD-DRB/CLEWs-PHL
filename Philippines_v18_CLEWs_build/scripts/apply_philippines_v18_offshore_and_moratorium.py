"""Two sourced corrections to Philippines v18.0.1, applied to a COPY of the case.

Each correction carries its source and a demonstrated consequence; nothing here tunes a
parameter to reproduce an observed outcome. The script refuses to write into a case whose
name matches the packaged one, so the shipped case cannot be edited by accident.

1. OFFSHORE WIND RESOURCE.
   `PHL_POW_PP_WOF` carries a 3,949.31 PJ/yr activity placeholder -- 4.8x the screened
   national resource -- and a capacity-factor profile whose annual mean is 29.3%.
   The World Bank/ESMAP Offshore Wind Roadmap for the Philippines (April 2022) screens
   58 GW of technical potential after environmental and social exclusions, at 45-47%
   capacity factor: 58 GW x 45% = 823 PJ/yr. Fix: cap post-2020 activity at 823 PJ and
   rescale the CF profile to a 45% annual mean (seasonal shape preserved).
   Consequence when uncorrected (demonstrated on the v12 lineage): the least-cost wind
   build lands on the wrong resource and the offshore/onshore cost ordering inverts.

2. THE COAL MORATORIUM DATE.
   The COAL_PHASEOUT layer forbids new coal investment only from 2031, while the base
   deployment envelopes allow 2-2.5 GW/yr of new coal through 2030 -- so the policy
   scenario can build ~10-12 GW of new coal before its own ban starts. The DOE moratorium
   on new greenfield coal (October 2020) exempts committed projects scheduled to begin
   operations 2023-2027 (DOE, 2024). Fix: in the COAL_PHASEOUT layer only,
   `TotalAnnualMaxCapacityInvestment` for `PHL_POW_PP_COAL` is 0 from 2028; pre-2028
   cells are left EMPTY so the composition inherits the base deployment envelope
   (an explicit scenario-layer value overrides the base; None inherits).
   Consequence when uncorrected (demonstrated on the v12 lineage): the optimiser
   front-loaded 10.2 GW of new coal into the pre-ban window of the policy scenario.

Usage:
    python apply_philippines_v18_offshore_and_moratorium.py --case <path to a COPY> \
        [--report out.json]
"""
import argparse
import json
from pathlib import Path

OFFSHORE_CAP_PJ = 823.0    # ESMAP 58 GW x 45% CF
OFFSHORE_CF_MEAN = 0.45    # ESMAP screened-site annual mean
MORATORIUM_FROM = 2028     # DOE exemption covers committed projects with operations 2023-2027
OFFSHORE, COAL = "PHL_POW_PP_WOF", "PHL_POW_PP_COAL"


def load(p): return json.load(open(p))


def save(p, d): json.dump(d, open(p, "w"), indent=1)


def year_keys(row): return [k for k in row if k.isdigit()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--case", required=True, type=Path)
    ap.add_argument("--report", type=Path)
    a = ap.parse_args()
    C = a.case
    if not (C / "genData.json").is_file():
        raise SystemExit(f"not a MUIO case: {C}")
    g = load(C / "genData.json")
    if g.get("osy-casename") in ("Philippines_v18", "Philippines_v18_0_1"):
        raise SystemExit("refusing to edit the packaged case -- copy it and rename osy-casename first")
    tid = {t["Tech"]: t["TechId"] for t in g["osy-tech"]}
    sid = {s["Scenario"]: s["ScenarioId"] for s in g["osy-scenarios"]}
    rep = {}

    # --- 1a. offshore activity ceiling ---
    p = C / "RYT.json"; ryt = load(p)
    n = 0
    for rows in ryt["TAU"].values():
        for r in rows:
            if r.get("TechId") == tid[OFFSHORE]:
                for k in year_keys(r):
                    if k != "2020" and isinstance(r[k], (int, float)) and r[k] > OFFSHORE_CAP_PJ:
                        r[k] = OFFSHORE_CAP_PJ; n += 1
    rep["offshore_cap_cells"] = n

    # --- 2. moratorium in the policy layer only ---
    rows = ryt["TAMaxCI"].setdefault(sid["COAL_PHASEOUT"], [])
    row = next((r for r in rows if r.get("TechId") == tid[COAL]), None)
    if row is None:
        row = {"TechId": tid[COAL]}; rows.append(row)
    yrs = [str(y) for y in g["osy-years"]] if not isinstance(g["osy-years"][0], dict) else \
          [str(y.get("Year") or y.get("year")) for y in g["osy-years"]]
    for y in yrs:
        row[y] = 0 if int(y) >= MORATORIUM_FROM else None
    rep["moratorium"] = (f"{MORATORIUM_FROM}..{yrs[-1]} zero in COAL_PHASEOUT layer; "
                         f"{yrs[0]}..{MORATORIUM_FROM-1} left empty to inherit the base envelope")
    save(p, ryt)

    # --- 1b. offshore CF rescale to the ESMAP mean ---
    p = C / "RYTTs.json"; d = load(p)
    vals, rows_hit = [], 0
    for rows in d["CF"].values():
        for r in rows:
            if r.get("TechId") == tid[OFFSHORE]:
                vals += [r[k] for k in year_keys(r) if isinstance(r[k], (int, float)) and r[k]]
    mean = sum(vals) / len(vals) if vals else 0
    if not (0.0 < mean < OFFSHORE_CF_MEAN):
        rep["offshore_cf"] = f"SKIPPED: current mean {mean:.4f} not below target"
    else:
        f = OFFSHORE_CF_MEAN / mean
        for rows in d["CF"].values():
            for r in rows:
                if r.get("TechId") == tid[OFFSHORE]:
                    rows_hit += 1
                    for k in year_keys(r):
                        if isinstance(r[k], (int, float)):
                            r[k] = min(r[k] * f, 1.0)
        save(p, d)
        rep["offshore_cf"] = f"mean {mean:.4f} -> {OFFSHORE_CF_MEAN} (x{f:.4f}, {rows_hit} rows, shape preserved)"

    print(json.dumps(rep, indent=1))
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
