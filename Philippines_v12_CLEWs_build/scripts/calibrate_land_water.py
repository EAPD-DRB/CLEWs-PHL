#!/usr/bin/env python3
"""Scale crop yields and irrigation withdrawals toward observed Philippine values.

`KNOWN_LIMITATIONS.md` records that the land-agriculture-water block was never
calibrated to observed land allocation, yields or irrigation withdrawals. This
script applies two corrections to the clewsy input CSVs and reports what it
changed. It writes to an output directory and never edits the inputs in place.

Correction 1 -- crop yields (OutputActivityRatio).
    The yields the build inherits are GAEZ agro-climatically attainable
    potential. Used as if they were observed actual yields, the model produces
    the right national output on the wrong area: it grows rice on roughly half
    the observed harvested area while sugarcane occupies about five times its
    own. Each crop's yield is scaled by
    (solved area) / (observed harvested area), which moves attainable toward
    actual and leaves relative cluster and mode differences intact.

Correction 2 -- irrigation withdrawal (InputActivityRatio, AGRWATPHL).
    High-input irrigated rice draws about 740 m3/ha/yr against a requirement in
    the thousands, and total agricultural withdrawal comes out near 2.7 km3/yr
    against AQUASTAT's 67.965. All AGRWATPHL input ratios are scaled by one
    factor to meet the national total.

Correction 3 -- base-year land cover (TechnologyActivityByMode{Lower,Upper}Limit).
    The build reads a complete seven-class land-cover table and then discards
    most of it: the mode lower-limit loop in clewsy.py skips Cropland, Forest and
    Other agricultural land, so 164,254 km2 -- 55% of the country -- never
    reaches the model and Forest absorbs the whole unallocated residual at
    179,780 km2 against 72,260 observed. This writes base-year limits for every
    class from the NAMRIA accounts, and forces the land resource to the national
    total so unconstrained land cannot simply leave the accounts.

Both factors are ratios to an observed target, so they are only as good as the
target. Every default below is stated in TARGETS and OBSERVED_AREA_KKM2 so it
can be replaced with a sourced value; nothing is hidden in the code.

Usage:
    python scripts/calibrate_land_water.py --inputs model/inputs/clewsy \\
        --output model/inputs/clewsy_calibrated
    python scripts/calibrate_land_water.py --inputs model/inputs/clewsy \\
        --output /tmp/out --report /tmp/out/report.json
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

# Crop yields. Values are 10^3 km2 of harvested area.
#   solved: area the uncalibrated model allocates in 2020
#   observed: PSA 2020 harvested area
# The scale factor is solved / observed: >1 raises the yield, <1 lowers it.
# CRPOTH has no single observed counterpart and is left alone.
# `solved` numerators are the result of a four-pass fixed-point iteration, not the
# raw first-solve areas: because the model reallocates crops across eight yield
# clusters, a single national factor cannot be computed analytically. Each pass
# multiplies the previous factor by (solved / target). Pass ratios for reference:
# palay 1.052 -> 0.998, corn 1.223 -> 0.873 -> 1.053, coconut 1.022 -> 1.001,
# sugarcane 1.000 throughout, vegetables 1.033 -> 0.996.
OBSERVED_AREA_KKM2 = {
    "CRPRCP": {"solved": 24.156, "observed": 47.189,
               "note": "palay 4,718,896 ha, PSA OpenSTAT 2020"},
    "CRPMZE": {"solved": 10.990, "observed": 25.538,
               "note": "corn 2,553,781 ha, PSA OpenSTAT 2020"},
    "CRPCON": {"solved": 31.687, "observed": 36.513,
               "note": "coconut 3,651,289 ha w/ husk, PSA OpenSTAT 2020"},
    "CRPSGC": {"solved": 22.181, "observed": 3.991,
               "note": "sugarcane 399,086 ha fresh cane, PSA OpenSTAT 2020"},
    "CRPTOM": {"solved": 12.625, "observed": 5.912,
               "note": "vegetables + root crops 591,243 ha, PSA summed. The demand "
                       "of 5.4996 Mt matches that whole table, not tomatoes (0.222 Mt)"},
}

# Base-year land cover, km2, from the PSA/NAMRIA Land Asset Accounts (Table 1, 2020
# closing stock; PSA Special Release 2024-203; NAMRIA Land Cover Map 2020). Replaces
# the GAEZ v4 concordance, whose LCType10 put 55.5% of the country in one class and
# which gave grassland and barren no data at all. NAMRIA's total is within 0.024% of
# the model's control total of 295,813.1 km2, so the swap is areal-neutral.
# Cluster modes: 25 Barren, 26 Built-up, 27 Forest, 28 Grassland, 29 Other ag, 30 Water.
LAND_MODES = {
    25: {"km2": 1595.0, "pin": "floor", "name": "Barren and sparsely vegetated"},
    26: {"km2": 10264.9, "pin": "equality", "name": "Built-up land"},
    27: {"km2": 72319.4, "pin": "equality", "name": "Forest land"},
    28: {"km2": 69741.0, "pin": "floor", "name": "Grassland and woodland"},
    29: {"km2": 2287.9, "pin": None, "name": "Other agricultural land"},
    30: {"km2": 6319.8, "pin": "equality", "name": "Water bodies"},
}
LAND_RESOURCE_TOTAL_KKM2 = 295.8131
CLUSTER_AREA = {
    "LNDAGRPHLC01": 9111.5, "LNDAGRPHLC02": 23681.7, "LNDAGRPHLC03": 103214.9,
    "LNDAGRPHLC04": 27387.2, "LNDAGRPHLC05": 27179.9, "LNDAGRPHLC06": 18706.9,
    "LNDAGRPHLC07": 18385.0, "LNDAGRPHLC08": 68146.0,
}

# Agricultural water withdrawal, km3/yr (10^9 m3/yr).
#   observed: FAO AQUASTAT Philippines agricultural withdrawal
#   solved: what the model withdraws in 2020 BEFORE the water correction
#
# The two baselines matter and are easy to get wrong. Correction 1 raises
# irrigated area from about 1.9 to 2.5 Mha, which by itself lifts withdrawal
# from 2.710 to 6.313 km3/yr at the uncorrected rates. So the factor needed
# depends on whether the yield correction is also being applied:
#   both corrections  -> baseline 6.313, factor about 10.9  (the tested case)
#   irrigation only   -> baseline 2.710, factor about 25.5
# `solved_after_yields` is used by default because the default applies both.
#
# AQUASTAT's 69 km3/yr is disputed -- lower estimates near 30 km3/yr exist -- so
# treat this as the number most in need of a sourcing decision.
TARGETS = {
    "AGRWATPHL": {
        "solved": 2.710,
        "solved_after_yields": 4.716,
        "observed": 67.965,
        "note": "FAO AQUASTAT variable 4250, Agricultural water withdrawal, 2023, "
                "symbol A (official). The apparent conflict with a '~30 km3' figure "
                "is resolved: that is variable 4260, the NET irrigation requirement "
                "(33.280), and FAO's own water requirement ratio of 51% links the "
                "two -- 33.280/65.590 = 50.7%. Anyone quoting 30 km3 for WITHDRAWAL "
                "has mislabelled the net requirement. Citation: Frenken & Gillet "
                "(2012), Irrigation water requirement and water withdrawal by "
                "country, FAO AQUASTAT Reports, Philippines row. FAO itself flags "
                "the PHL number as weak and says more research is needed.",
    },
}

MODE_LL_FILE = "TechnologyActivityByModeLowerLimit.csv"
MODE_UL_FILE = "TechnologyActivityByModeUpperLimit.csv"
RESOURCE_LL_FILE = "TotalTechnologyAnnualActivityLowerLimit.csv"
LAND_RESOURCE_TECH = "MINLNDTOT"
YIELD_FILE = "OutputActivityRatio.csv"
WATER_FILE = "InputActivityRatio.csv"
FUEL_COL = "FUEL"
VALUE_COL = "VALUE"


def scale_factors(*, with_yields: bool = True) -> dict[str, float]:
    """Commodity -> multiplicative factor, derived from the tables above.

    Args:
        with_yields: whether the yield correction is being applied alongside.
            It changes the irrigation baseline -- see the note on TARGETS.
    """
    out = {}
    for code, t in OBSERVED_AREA_KKM2.items():
        out[code] = t["solved"] / t["observed"]
    key = "solved_after_yields" if with_yields else "solved"
    for code, t in TARGETS.items():
        out[code] = t["observed"] / t[key]
    return out


def write_land_pins(inputs: Path, out: Path, years: list[str]) -> dict:
    """Write base-year land-cover limits and the land-resource floor.

    National class totals are apportioned pro rata to cluster area. That assumes
    each class is uniformly distributed across the eight yield clusters, which is
    certainly false for Built-up; NAMRIA publishes no cluster-level tabulation, so
    the assumption is adopted and recorded rather than hidden.
    """
    total = sum(CLUSTER_AREA.values())
    base = years[0]
    ll_rows, ul_rows = [], []
    for cl, area in CLUSTER_AREA.items():
        share = area / total
        for mode, spec in LAND_MODES.items():
            if spec["pin"] is None:
                continue
            v = spec["km2"] * share / 1000.0          # km2 -> 10^3 km2
            ll_rows.append(["GLOBAL", cl, mode, base, repr(v)])
            if spec["pin"] == "equality":
                ul_rows.append(["GLOBAL", cl, mode, base, repr(v)])
    _merge(inputs / MODE_LL_FILE, out / MODE_LL_FILE, ll_rows,
           ["REGION", "TECHNOLOGY", "MODE_OF_OPERATION", "YEAR", "VALUE"])
    _merge(inputs / MODE_UL_FILE, out / MODE_UL_FILE, ul_rows,
           ["REGION", "TECHNOLOGY", "MODE_OF_OPERATION", "YEAR", "VALUE"])
    _merge(inputs / RESOURCE_LL_FILE, out / RESOURCE_LL_FILE,
           [["GLOBAL", LAND_RESOURCE_TECH, y, repr(LAND_RESOURCE_TOTAL_KKM2)]
            for y in years],
           ["REGION", "TECHNOLOGY", "YEAR", "VALUE"])
    return {"mode_lower_limits": len(ll_rows), "mode_upper_limits": len(ul_rows),
            "land_resource_floor_kkm2": LAND_RESOURCE_TOTAL_KKM2}


def _merge(src: Path, dst: Path, new_rows: list[list], header: list[str]) -> None:
    """Append rows to a csv, replacing any existing row with the same key."""
    existing = []
    if src.is_file():
        with src.open(newline="") as fh:
            rd = csv.reader(fh)
            head = next(rd, None) or header
            existing = [r for r in rd if r]
    else:
        head = header
    keyn = len(header) - 1                      # every column but VALUE is the key
    newkeys = {tuple(str(x) for x in r[:keyn]) for r in new_rows}
    kept = [r for r in existing if tuple(r[:keyn]) not in newkeys]
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(head)
        w.writerows(kept + [[str(x) for x in r] for r in new_rows])


def rescale(path: Path, factors: dict[str, float], out_path: Path) -> dict:
    """Copy one CSV, multiplying VALUE where FUEL has a factor."""
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit(f"{path} has no data rows")
    missing = {FUEL_COL, VALUE_COL} - set(rows[0])
    if missing:
        raise SystemExit(f"{path} is missing column(s) {sorted(missing)}")

    touched: dict[str, int] = {}
    for r in rows:
        f = factors.get(r[FUEL_COL])
        if f is None:
            continue
        try:
            r[VALUE_COL] = repr(float(r[VALUE_COL]) * f)
        except ValueError:  # a blank or non-numeric cell stays as it is
            continue
        touched[r[FUEL_COL]] = touched.get(r[FUEL_COL], 0) + 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return touched


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--inputs", required=True, type=Path,
                    help="clewsy input CSV directory to read")
    ap.add_argument("--output", required=True, type=Path,
                    help="directory to write the corrected CSVs to")
    ap.add_argument("--report", type=Path, help="optional JSON summary path")
    ap.add_argument("--yields-only", action="store_true",
                    help="apply correction 1 and leave irrigation alone")
    ap.add_argument("--irrigation-only", action="store_true",
                    help="apply correction 2 alone (uses the higher baseline factor)")
    args = ap.parse_args()

    if args.output.resolve() == args.inputs.resolve():
        raise SystemExit("refusing to overwrite the inputs; choose a new --output")
    if args.yields_only and args.irrigation_only:
        raise SystemExit("--yields-only and --irrigation-only are mutually exclusive")

    factors = scale_factors(with_yields=not args.irrigation_only)
    if args.yields_only:
        factors = {k: v for k, v in factors.items() if k in OBSERVED_AREA_KKM2}
    elif args.irrigation_only:
        factors = {k: v for k, v in factors.items() if k in TARGETS}

    summary: dict[str, dict] = {}
    for name in (YIELD_FILE, WATER_FILE):
        src = args.inputs / name
        if not src.is_file():
            raise SystemExit(f"missing input {src}")
        summary[name] = rescale(src, factors, args.output / name)

    # every other input file is copied through unchanged, so the output
    # directory is a complete, usable input set rather than two loose files
    years = sorted({r["YEAR"] for r in csv.DictReader(
        (args.inputs / YIELD_FILE).open(newline="")) if r.get("YEAR")})
    summary["land_pins"] = write_land_pins(args.inputs, args.output, years)

    copied = 0
    written = {YIELD_FILE, WATER_FILE, MODE_LL_FILE, MODE_UL_FILE, RESOURCE_LL_FILE}
    for src in sorted(args.inputs.glob("*.csv")):
        if src.name in written:
            continue
        (args.output / src.name).write_bytes(src.read_bytes())
        copied += 1

    print(f"wrote {args.output}  ({copied} files copied unchanged)")
    print(f"{'commodity':12}{'factor':>10}{'rows':>8}  target")
    for code, f in sorted(factors.items()):
        rows = sum(s.get(code, 0) for s in summary.values())
        meta = OBSERVED_AREA_KKM2.get(code) or TARGETS[code]
        print(f"{code:12}{f:>10.4f}{rows:>8}  {meta['note']}")

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(
            {"factors": factors, "rows_changed": summary,
             "yield_targets": OBSERVED_AREA_KKM2, "water_targets": TARGETS},
            indent=2) + "\n")
        print(f"report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
