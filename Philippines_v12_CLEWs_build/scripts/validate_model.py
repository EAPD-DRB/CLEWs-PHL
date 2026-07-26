#!/usr/bin/env python3
"""Validate the packaged raw Philippines build and integrated MUIO v12 case."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
INPUTS = ROOT / "model/inputs/clewsy"
DIAGNOSTICS = ROOT / "diagnostics"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


checks: list[dict[str, str]] = []


def check(category: str, name: str, passed: bool, finding: str, evidence: str) -> None:
    checks.append(
        {
            "category": category,
            "check": name,
            "status": "PASS" if passed else "FAIL",
            "finding": finding,
            "evidence": evidence,
        }
    )


def positive_equal_locks() -> list[tuple[str, tuple[str, ...], float]]:
    pairs = (
        (
            "TotalTechnologyAnnualActivityLowerLimit.csv",
            "TotalTechnologyAnnualActivityUpperLimit.csv",
        ),
        (
            "TechnologyActivityByModeLowerLimit.csv",
            "TechnologyActivityByModeUpperLimit.csv",
        ),
        ("TotalAnnualMinCapacity.csv", "TotalAnnualMaxCapacity.csv"),
        (
            "TotalAnnualMinCapacityInvestment.csv",
            "TotalAnnualMaxCapacityInvestment.csv",
        ),
    )
    locks: list[tuple[str, tuple[str, ...], float]] = []
    for lower_name, upper_name in pairs:
        lower_rows = read_rows(INPUTS / lower_name)
        upper_rows = read_rows(INPUTS / upper_name)
        if not lower_rows or not upper_rows:
            continue
        dimensions = [
            field for field in lower_rows[0] if field not in {"REGION", "VALUE"}
        ]
        upper = {
            tuple(row[field] for field in dimensions): float(row["VALUE"])
            for row in upper_rows
        }
        for row in lower_rows:
            key = tuple(row[field] for field in dimensions)
            value = float(row["VALUE"])
            if (
                value > 0
                and key in upper
                and math.isclose(value, upper[key], abs_tol=1e-12)
            ):
                locks.append((f"{lower_name}/{upper_name}", key, value))
    return locks


def main() -> None:
    raw_solution = (ROOT / "model/data.sol").read_text(
        encoding="utf-8", errors="replace"
    ).splitlines()
    raw_status = raw_solution[0] if raw_solution else ""
    check(
        "solver",
        "Authoritative upstream raw solve is optimal",
        raw_status.startswith("Optimal"),
        raw_status or "Missing solution status",
        "model/data.sol",
    )

    years = sorted(int(float(row["VALUE"])) for row in read_rows(INPUTS / "YEAR.csv"))
    check(
        "structure",
        "Horizon is continuous from 2020 through 2053",
        years == list(range(2020, 2054)),
        f"{years[0]}-{years[-1]} ({len(years)} years)",
        "model/inputs/clewsy/YEAR.csv",
    )

    duplicate_count = 0
    nonfinite_count = 0
    row_count = 0
    input_files = sorted(INPUTS.glob("*.csv"))
    for path in input_files:
        rows = read_rows(path)
        row_count += len(rows)
        if not rows:
            continue
        dimensions = [field for field in rows[0] if field != "VALUE"] or list(rows[0])
        seen: set[tuple[str, ...]] = set()
        for row in rows:
            key = tuple(row[field] for field in dimensions)
            if key in seen:
                duplicate_count += 1
            seen.add(key)
            # One-column set files (TECHNOLOGY, FUEL, etc.) legitimately store
            # string identifiers in VALUE. Numeric finiteness applies only to
            # indexed parameter tables.
            if "VALUE" in row and len(row) > 1:
                try:
                    if not math.isfinite(float(row["VALUE"])):
                        nonfinite_count += 1
                except ValueError:
                    nonfinite_count += 1
    check(
        "integrity",
        "Sparse OSeMOSYS indices are unique",
        duplicate_count == 0,
        f"{duplicate_count} duplicates across {row_count} rows",
        f"{len(input_files)} CSV input files",
    )
    check(
        "integrity",
        "All numeric input values are finite",
        nonfinite_count == 0,
        f"{nonfinite_count} non-finite or invalid values",
        "model/inputs/clewsy",
    )

    land_rows = read_rows(
        ROOT / "geospatial/summary_stats/PHL_LandCover_byCluster_summary.csv"
    )
    area = sum(float(row["sqkm"]) for row in land_rows)
    check(
        "geospatial",
        "Eight clusters retain the complete national land-cell area",
        len(land_rows) == 8 and math.isclose(area, 295_813.1, abs_tol=0.2),
        f"{len(land_rows)} clusters; {area:,.1f} km2",
        "geospatial/summary_stats/PHL_LandCover_byCluster_summary.csv",
    )

    crops = {
        row["FUEL"] for row in read_rows(INPUTS / "AccumulatedAnnualDemand.csv")
    }
    expected_crops = {"CRPCON", "CRPMZE", "CRPOTH", "CRPRCP", "CRPSGC", "CRPTOM"}
    check(
        "agriculture",
        "Six explicit crop-output demands are represented",
        crops == expected_crops,
        ", ".join(sorted(crops)),
        "model/inputs/clewsy/AccumulatedAnnualDemand.csv",
    )

    locks = positive_equal_locks()
    check(
        "no-forcing",
        "Raw nexus has no positive lower-equals-upper locks",
        not locks,
        f"{len(locks)} equality locks",
        "four activity/capacity lower-upper parameter pairs",
    )

    audit = json.loads(
        (DIAGNOSTICS / "v12_hybrid_audit.json").read_text(encoding="utf-8")
    )
    check(
        "preservation",
        "Hybrid preservation/connectivity audit passes",
        audit["overall_status"] == "PASS",
        audit["overall_status"],
        "diagnostics/v12_hybrid_audit.json",
    )

    for run_name in ("Base_v12", "PEP_v12"):
        results = (
            REPO / f"WebAPP/DataStorage/Philippines_v12/res/{run_name}/results.txt"
        )
        status = (
            results.read_text(encoding="utf-8", errors="replace").splitlines()[0]
            if results.exists()
            else "Missing"
        )
        check(
            "solver",
            f"Integrated MUIO {run_name} solve is optimal",
            status.startswith("Optimal"),
            status,
            f"WebAPP/DataStorage/Philippines_v12/res/{run_name}/results.txt",
        )

    with (DIAGNOSTICS / "validation_checks.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(checks[0]))
        writer.writeheader()
        writer.writerows(checks)

    failures = [item for item in checks if item["status"] == "FAIL"]
    summary = {
        "status": "PASS" if not failures else "FAIL",
        "check_count": len(checks),
        "pass_count": len(checks) - len(failures),
        "failure_count": len(failures),
        "failures": failures,
    }
    (DIAGNOSTICS / "validation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
