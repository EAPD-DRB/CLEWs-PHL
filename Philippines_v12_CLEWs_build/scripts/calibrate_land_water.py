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
    Irrigated area is close to observed at roughly 1.9 Mha, but the water
    applied to it is not: high-input irrigated rice draws about 740 m3/ha/yr
    against a requirement in the thousands. Total agricultural withdrawal comes
    out near 2.7 km3/yr against roughly 69 km3/yr reported for the Philippines.
    All AGRWATPHL input ratios are scaled by one factor to meet the national
    total.

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
OBSERVED_AREA_KKM2 = {
    "CRPRCP": {"solved": 22.976, "observed": 46.5, "note": "palay, PSA 2020"},
    "CRPMZE": {"solved": 9.781, "observed": 25.8, "note": "corn, PSA 2020"},
    "CRPCON": {"solved": 31.014, "observed": 36.0, "note": "coconut, PSA 2020"},
    "CRPSGC": {"solved": 22.181, "observed": 4.2, "note": "sugarcane, PSA 2020"},
    "CRPTOM": {"solved": 12.218, "observed": 7.0,
               "note": "vegetables via the GAEZ tomato proxy, PSA 2020"},
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
        "solved_after_yields": 6.313,
        "observed": 69.0,
        "note": "FAO AQUASTAT, agricultural withdrawal",
    },
}

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
    copied = 0
    for src in sorted(args.inputs.glob("*.csv")):
        if src.name in (YIELD_FILE, WATER_FILE):
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
