#!/usr/bin/env python3
"""Finalize solved Philippines v18 land-water documentation and schema ledger."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
CHANGE_ID = "CHG_PHL_V18_LAND_WATER_CLOSURE_20260813"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def write_table(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)


def append_unique(path: Path, rows: list[dict[str, str]]) -> None:
    fields, existing = table(path)
    key = fields[0]
    duplicates = {row[key] for row in existing} & {row[key] for row in rows}
    if duplicates:
        raise AssertionError(f"duplicate {path.name} IDs: {sorted(duplicates)}")
    write_table(path, fields, existing + rows)


def update_change(package: Path, report: dict[str, Any]) -> None:
    path = package / "data_sources" / "CHANGES.csv"
    fields, rows = table(path)
    found = 0
    for row in rows:
        if row["change_id"] != CHANGE_ID:
            continue
        found += 1
        row["resolve_status"] = "resolved"
        row["notes"] = (
            "Parameter-only exact geographic cluster bounds solved optimally at objective "
            f"{report['candidate']['objective']} ({report['candidate']['objective_percent_change']}% versus baseline). "
            "The aggregate UDC experiment timed out after 430 seconds and was rejected. "
            "Power capacity and annual emissions are unchanged; all land receives hydrology; "
            "no crop/mode, irrigated-area, source-share or withdrawal-total result is fixed."
        )
    if found != 1:
        raise AssertionError(f"expected one {CHANGE_ID}, found {found}")
    write_table(path, fields, rows)


def update_map_evidence(package: Path) -> None:
    path = package / "data_sources" / "MODEL_MAP.csv"
    fields, rows = table(path)
    targets = {
        "MAP_PHL_V18_LAND_HYDROLOGY_BOUNDS",
        "MAP_PHL_V18_WATER_COEFFICIENT_CLOSURE",
    }
    found = set()
    for row in rows:
        if row["map_id"] in targets:
            found.add(row["map_id"])
            for evidence in (
                "SRC_PHL_V18_LAND_WATER_BUILD",
                "SRC_PHL_V18_LAND_WATER_VALIDATION",
            ):
                if evidence not in row["evidence_ids"].split(";"):
                    row["evidence_ids"] += ";" + evidence
    if found != targets:
        raise AssertionError(f"missing aggregate map rows: {sorted(targets - found)}")
    write_table(path, fields, rows)


def update_text_files(case: Path, package: Path, report: dict[str, Any]) -> None:
    objective = report["candidate"]["objective"]
    percent = report["candidate"]["objective_percent_change"]
    validation_section = f"""

## Completed full-chain validation

The parameter-only candidate passed application generation, preprocessing,
independent GLPK matrix validation, one full CBC optimization, result export
and baseline comparison. It solved optimally at objective {objective}, a change
of {report['candidate']['objective_delta']} ({percent}%) from the verified v18
deployment-envelope baseline.

The comparable matrix is {report['candidate']['matrix']['rows']} rows,
{report['candidate']['matrix']['columns']} columns and
{report['candidate']['matrix']['matrix_nonzeros']} nonzeros. The exact cluster
bounds add 272 rows and 244,800 nonzeros. The solve completed within the
declared 415-second cutoff; exact CBC seconds were not retained because the
first post-solve validator stopped on an overly strict rounded-CSV assertion.
The same optimal `results.txt` was post-processed without another solve.

All eight solved cluster totals equal their geographic bounds in the solver;
the exported mode-sum maximum rounding error is 0.0006 thousand km2. Full-land
precipitation is {report['checks']['precipitation_km3']['2020']} km3
({report['checks']['precipitation_depth_mm_2020']} mm) in 2020 and
{report['checks']['precipitation_km3']['2053']} km3 in 2053, an increase of
{report['checks']['precipitation_change_2020_2053_percent']}%.

New generation capacity and annual emissions are unchanged. Rounded crop
production differs by at most {report['checks']['maximum_crop_production_difference']}.
Combined gross irrigation withdrawal changes endogenously by at most
{report['checks']['maximum_combined_baseline_gross_irrigation_withdrawal_difference_km3']}
km3/year because the optimizer can reallocate land modes and withdrawal routes;
the accounting boundary itself remains gross diversion.

Optimizer runs recorded for this repair: (1) aggregate UDC experiment, stopped
after 430 seconds and rejected; (2) exact-cluster-bounds candidate, optimal and
promoted. No unchanged control or post-promotion optimization was run.
"""
    for path in (
        case / "documentation" / "MODEL_FIXES_LAND_WATER_CLOSURE_2026-08-13.md",
        package / "data_sources" / "calculation_notes" / "land_water_closure_v18_2026-08-13.md",
    ):
        text = path.read_text(encoding="utf-8")
        if "## Completed full-chain validation" not in text:
            path.write_text(text.rstrip() + validation_section + "\n", encoding="utf-8")
    shutil.copy2(
        case / "documentation" / "MODEL_FIXES_LAND_WATER_CLOSURE_2026-08-13.md",
        package / "documentation" / "MODEL_FIXES_LAND_WATER_CLOSURE_2026-08-13.md",
    )

    case_readme = case / "README.md"
    case_text = case_readme.read_text(encoding="utf-8")
    addition = (
        "\n\nLand-water closure repair: the eight hydrological clusters are fixed "
        "to their existing geographic areas, every cluster-mode conserves water, "
        "and gross irrigation withdrawal is converted to delivered field water at "
        "the documented 0.38 efficiency. Crop and land-cover modes remain endogenous."
    )
    if "Land-water closure repair:" not in case_text:
        case_readme.write_text(case_text.rstrip() + addition + "\n", encoding="utf-8")

    readme = package / "README.md"
    text = readme.read_text(encoding="utf-8")
    marker = "## Delivered model"
    addition = """V18 also closes the inherited land-water accounting. Every unit of
fixed national land passes through one of the eight existing hydrological
clusters, and every cluster-mode conserves precipitation plus delivered
irrigation. The documented 0.38 irrigation efficiency now sits between gross
withdrawal and field delivery. Crop and land-cover modes remain endogenous.

"""
    if "V18 also closes the inherited land-water accounting" not in text:
        text = text.replace(marker, addition + marker)
    text = text.replace("Philippines_v18_v18.0.0_MUIO.zip", "Philippines_v18_v18.0.1_MUIO.zip")
    text = text.replace("Validated run: `DEPLOYMENT_ENVELOPE_V18_BASE`", "Validated run: `LAND_WATER_CLOSURE_V18_BASE`")
    text += f"""

## Land-water closure validation

The corrected BASE run solved optimally at objective {objective}. Full-land
precipitation is 2,658.12 mm in 2020 and follows the installed SSP2-4.5 signal
to a 4.804% increase by 2053. The authoritative records are
`data_sources/snapshots/land_water_closure_build_manifest.json` and
`land_water_closure_validation.json`; the rejected aggregate-UDC runtime test
is disclosed in `land_water_closure_runtime_incident.json`.
"""
    readme.write_text(text, encoding="utf-8")

    reproduce = package / "documentation" / "REPRODUCE.md"
    reproduce.write_text(
        """# Reproduce and validate Philippines v18.0.1

1. Restore the validated v18 deployment-envelope source.
2. Run `python scripts/apply_philippines_v18_land_water_bounds.py` against that
   source and a disposable target/package. The script gates exact source hashes.
3. Run `python scripts/validate_philippines_v18_land_water_closure.py` once on
   the disposable candidate. Reuse the retained deployment candidate as the
   unchanged baseline; do not rerun it.
4. Run `python scripts/validate_provenance.py . --stage build` and regenerate
   `PHILIPPINES_V18_CANONICAL_SCHEMA_LEDGER.xlsx`.
5. Promote only `RYT.json`, `RYTCM.json`, and the documented records. Regenerate
   and preprocess the live solver input, compare it byte-for-byte with the solved
   candidate, and run `glpsol --check`. Do not solve again when identical.
6. Build `Philippines_v18_v18.0.1_MUIO.zip` without `res/`, `data.txt`,
   `data_processed.txt`, `lp.lp`, or `results.txt`; validate CRC, checksum and
   live/archive source identity.

The aggregate nine-member UDC is not the promoted formulation: its diagnostic
CBC run exceeded 430 seconds. The promoted formulation uses the existing
source-derived cluster TAUs as matching TALs and retains endogenous modes.
""",
        encoding="utf-8",
    )

    doc_readme = package / "documentation" / "README.md"
    text = doc_readme.read_text(encoding="utf-8")
    line = "- `MODEL_FIXES_LAND_WATER_CLOSURE_2026-08-13.md`: geographic land routing, irrigation boundary, cluster water conservation, runtime A/B and full-chain validation.\n"
    if line not in text:
        doc_readme.write_text(text.rstrip() + "\n" + line, encoding="utf-8")

    history = package / "documentation" / "HISTORY.md"
    text = history.read_text(encoding="utf-8")
    row = "| 2026-08-13 | v18.0.1 land-water closure | Fixed eight geographic hydrological cluster totals, corrected gross-to-field irrigation accounting and conserved every cluster-mode; rejected the slower aggregate UDC | `MODEL_FIXES_LAND_WATER_CLOSURE_2026-08-13.md`; `../data_sources/snapshots/land_water_closure_validation.json` |"
    if row not in text:
        history.write_text(text.rstrip() + "\n" + row + "\n", encoding="utf-8")

    scripts_readme = package / "scripts" / "README.md"
    text = scripts_readme.read_text(encoding="utf-8")
    addition = """
- `apply_philippines_v18_land_water_bounds.py` applies the parameter-only
  geographic cluster bounds and conservative water-coefficient repair.
- `validate_philippines_v18_land_water_closure.py` performs deterministic,
  generation, GLPK, CBC, result and baseline checks while recording the
  rejected aggregate-UDC runtime experiment.
- `finalize_philippines_v18_land_water_closure.py` closes the schema ledger and
  documentation after the validated candidate solve.
"""
    if "apply_philippines_v18_land_water_bounds.py" not in text:
        scripts_readme.write_text(text.rstrip() + addition, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    case = args.case.resolve()
    package = args.package.resolve()
    snapshots = package / "data_sources" / "snapshots"
    report_path = snapshots / "land_water_closure_validation.json"
    build_path = snapshots / "land_water_closure_build_manifest.json"
    report = read_json(report_path)
    build = read_json(build_path)
    if report["status"] != "pass" or report["candidate"]["status"].split()[0] != "Optimal":
        raise AssertionError("land-water candidate is not validated optimal")

    incident = {
        "schema": "philippines-v18-land-water-runtime-incident-v1",
        "status": "rejected_timeout",
        "formulation": "aggregate Tag-1 UDC: sum cluster activity - MINLNDTOT activity = 0",
        "optimizer_run_count": 1,
        "timeout_seconds": 430,
        "result_file_written": False,
        "matrix": {"rows": 791279, "columns": 886010, "matrix_nonzeros": 12572981},
        "baseline_cbc_seconds": 207.19558720799978,
        "decision": "Do not promote; use dedicated parameter-only exact geographic bounds A/B.",
    }
    incident_path = snapshots / "land_water_closure_runtime_incident.json"
    write_json(incident_path, incident)

    build["validation_status"] = report["validation_status"] | {"promotion_identity": "not_run"}
    build["validation_report_sha256"] = sha256(report_path)
    build["runtime_incident_sha256"] = sha256(incident_path)
    build["optimizer_runs_total"] = 2
    write_json(build_path, build)
    shutil.copy2(build_path, case / "documentation" / build_path.name)
    shutil.copy2(report_path, case / "documentation" / report_path.name)
    shutil.copy2(incident_path, case / "documentation" / incident_path.name)

    source_rows = [
        {
            "source_id": "SRC_PHL_V18_LAND_WATER_BUILD", "provider": "MUIOGO Philippines v18 workflow",
            "product": "Land-water closure build manifest", "edition": "2026-08-13", "reference_period": "2020-2053",
            "geography": "Philippines", "variable": "Exact source hashes, changed cells, physical classifications and deterministic checks",
            "source_unit": "mixed model units and status", "exact_locator": "snapshots/land_water_closure_build_manifest.json",
            "url": "", "access_date": "2026-08-13", "license": "Repository license", "sha256": sha256(build_path),
            "local_file": "snapshots/land_water_closure_build_manifest.json", "notes": "Authoritative source-generation record for the promoted parameter-only formulation.",
        },
        {
            "source_id": "SRC_PHL_V18_LAND_WATER_VALIDATION", "provider": "MUIOGO Philippines v18 workflow",
            "product": "Land-water closure solve validation", "edition": "2026-08-13", "reference_period": "2020-2053",
            "geography": "Philippines", "variable": "Matrix, optimum, land, rainfall, irrigation, crops, energy and emission checks",
            "source_unit": "mixed model units and status", "exact_locator": "snapshots/land_water_closure_validation.json",
            "url": "", "access_date": "2026-08-13", "license": "Repository license", "sha256": sha256(report_path),
            "local_file": "snapshots/land_water_closure_validation.json", "notes": "One optimal bounds candidate; unchanged v18 baseline reused; no post-promotion solve.",
        },
        {
            "source_id": "SRC_PHL_V18_LAND_WATER_RUNTIME_INCIDENT", "provider": "MUIOGO Philippines v18 workflow",
            "product": "Aggregate UDC runtime incident record", "edition": "2026-08-13", "reference_period": "diagnostic run",
            "geography": "Philippines", "variable": "Rejected formulation, matrix and timeout",
            "source_unit": "status and seconds", "exact_locator": "snapshots/land_water_closure_runtime_incident.json",
            "url": "", "access_date": "2026-08-13", "license": "Repository license", "sha256": sha256(incident_path),
            "local_file": "snapshots/land_water_closure_runtime_incident.json", "notes": "Diagnostic optimizer run; no solution and no promoted source.",
        },
    ]
    append_unique(package / "data_sources" / "SOURCES.csv", source_rows)
    append_unique(
        package / "data_sources" / "CALCULATIONS.csv",
        [{
            "calculation_id": "CALC_PHL_V18_LAND_WATER_RUN",
            "formula": "application generation + preprocessing + GLPK matrix check + one bounds CBC solve + baseline comparison",
            "source_ids": "SRC_PHL_V18_LAND_WATER_BUILD;SRC_PHL_V18_LAND_WATER_VALIDATION;SRC_PHL_V18_LAND_WATER_RUNTIME_INCIDENT",
            "assumption_ids": "ASM_PHL_V18_ALL_LAND_THROUGH_HYDROLOGY;ASM_PHL_V18_IRRIGATION_BOUNDARY;ASM_PHL_V18_CLUSTER_WATER_CONSERVATION",
            "input_calculation_ids": "CALC_PHL_V18_LAND_HYDROLOGY_BOUNDS;CALC_PHL_V18_DELIVERED_IRRIGATION_OAR;CALC_PHL_V18_FIELD_IRRIGATION_IAR;CALC_PHL_V18_CLUSTER_WATER_RESIDUAL",
            "input_values": f"baseline objective={report['baseline']['objective']}; aggregate UDC timeout=430; bounds matrix={report['candidate']['matrix']}",
            "input_units": "model objective; seconds; matrix dimensions",
            "output_value": f"optimal objective={report['candidate']['objective']}; precipitation 2020={report['checks']['precipitation_km3']['2020']}; 2053={report['checks']['precipitation_km3']['2053']}",
            "output_unit": "status; model objective; km3/year",
            "script_path": "scripts/validate_philippines_v18_land_water_closure.py",
            "script_version": "v1",
            "notes": "Two optimizer runs total: rejected aggregate timeout and optimal bounds candidate. Exact bounds CBC seconds were not retained after a post-solve reporting assertion; completion before 415 seconds is verified.",
        }],
    )
    update_change(package, report)
    update_map_evidence(package)
    update_text_files(case, package, report)

    for script in (
        "apply_philippines_v18_land_water_bounds.py",
        "validate_philippines_v18_land_water_closure.py",
        "finalize_philippines_v18_land_water_closure.py",
    ):
        shutil.copy2(REPO / "scripts" / script, package / "scripts" / script)

    result = {
        "status": "pass",
        "case": str(case),
        "package": str(package),
        "objective": report["candidate"]["objective"],
        "optimizer_runs_total": 2,
        "ledger_status": "finalized_pending_promotion_identity",
    }
    output = snapshots / "land_water_closure_finalization.json"
    write_json(output, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
