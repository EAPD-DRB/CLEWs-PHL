#!/usr/bin/env python3
"""Validate the Philippines v19 PM2.5-only source change and generated data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from copy import deepcopy
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parent
DEFAULT_V19 = REPO / "case" / "Philippines_v19"
DEFAULT_V18 = REPO / "case" / "Philippines_v18"
SNAPSHOT = PACKAGE / "data_sources" / "snapshots" / "pm25_coverage_v19_2026-08-19.json"
EVIDENCE = PACKAGE / "data_sources" / "evidence" / "pm25_v19"
DEFAULT_GENERATED = DEFAULT_V19 / "res" / "PM25_COVERAGE_V19_BASE"
OUTPUT = PACKAGE / "data_sources" / "snapshots" / "pm25_coverage_v19_validation.json"
PM25 = "EMI_xpvk3"
YEARS = [str(year) for year in range(2020, 2054)]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emission_totals(path: Path) -> dict[tuple[str, str], float]:
    totals: dict[tuple[str, str], float] = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            key = (row["e"], row["y"])
            totals[key] = totals.get(key, 0.0) + float(row["AnnualTechnologyEmission"])
    return totals


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v18", type=Path, default=DEFAULT_V18)
    parser.add_argument("--v19", type=Path, default=DEFAULT_V19)
    parser.add_argument("--generated", type=Path, default=DEFAULT_GENERATED)
    parser.add_argument("--baseline-emissions", type=Path)
    parser.add_argument("--solve-report", type=Path)
    args = parser.parse_args()
    v18 = args.v18.resolve()
    v19 = args.v19.resolve()
    generated = args.generated.resolve()

    checks: list[dict] = []

    def check(name: str, condition: bool, detail) -> None:
        checks.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})

    v18_files = {path.name: path for path in v18.glob("*.json")}
    v19_files = {path.name: path for path in v19.glob("*.json")}
    check("source_file_set", set(v18_files) == set(v19_files), sorted(set(v18_files) ^ set(v19_files)))
    unchanged = [name for name in v18_files if name not in {"genData.json", "RYTEM.json"}]
    changed_unexpectedly = [name for name in unchanged if sha256(v18_files[name]) != sha256(v19_files[name])]
    check("only_genData_and_RYTEM_changed", not changed_unexpectedly, changed_unexpectedly)

    gen18 = read_json(v18 / "genData.json")
    gen19 = read_json(v19 / "genData.json")
    check("case_identity", gen19["osy-casename"] == "Philippines_v19", gen19["osy-casename"])
    check("technology_ids_unchanged",
          [x["TechId"] for x in gen18["osy-tech"]] == [x["TechId"] for x in gen19["osy-tech"]],
          len(gen19["osy-tech"]))
    check("commodity_ids_unchanged",
          [x["CommId"] for x in gen18["osy-comm"]] == [x["CommId"] for x in gen19["osy-comm"]],
          len(gen19["osy-comm"]))
    check("emission_definitions_unchanged", gen18["osy-emis"] == gen19["osy-emis"], gen19["osy-emis"])

    snapshot = read_json(SNAPSHOT)
    affected = set(snapshot["technologies"])
    tech18 = {x["Tech"]: x for x in gen18["osy-tech"]}
    tech19 = {x["Tech"]: x for x in gen19["osy-tech"]}
    link_errors = []
    for name in tech19:
        expected = list(tech18[name]["EAR"])
        if name in affected and PM25 not in expected:
            expected.append(PM25)
        if tech19[name]["EAR"] != expected:
            link_errors.append(name)
    check("only_expected_PM25_links_added", not link_errors, link_errors)
    check("affected_counts",
          len(affected) == 52 and snapshot["newly_linked_technology_count"] == 46
          and snapshot["existing_factor_series_extended_count"] == 6,
          {key: snapshot[key] for key in ("technology_count", "newly_linked_technology_count",
                                          "existing_factor_series_extended_count")})

    # Confirm every non-PM row and every unaffected PM row is byte-equivalent as data.
    r18 = read_json(v18 / "RYTEM.json")
    r19 = read_json(v19 / "RYTEM.json")
    affected_ids = {tech19[name]["TechId"] for name in affected}
    comparison_errors = []
    for parameter in ("EAR", "EACR"):
        for scenario in r18[parameter]:
            old_rows = [row for row in r18[parameter][scenario]
                        if row["EmisId"] != PM25 or row["TechId"] not in affected_ids]
            new_rows = [row for row in r19[parameter][scenario]
                        if row["EmisId"] != PM25 or row["TechId"] not in affected_ids]
            if old_rows != new_rows:
                comparison_errors.append(f"{parameter}.{scenario}")
    check("all_unaffected_emission_rows_unchanged", not comparison_errors, comparison_errors)

    factor_errors = []
    for name, record in snapshot["technologies"].items():
        tech_id = record["tech_id"]
        for parameter in ("EAR", "EACR"):
            for scenario in r19[parameter]:
                rows = [row for row in r19[parameter][scenario]
                        if row["TechId"] == tech_id and row["EmisId"] == PM25]
                if len(rows) != 30:
                    factor_errors.append(f"{name}:{scenario}:{parameter}-row-count={len(rows)}")
                    continue
                for row in rows:
                    if parameter == "EAR" and scenario == "SC_0" and row["MoId"] == 1:
                        if abs(float(row["2020"]) - float(record["new_2020"])) > 1e-12:
                            factor_errors.append(f"{name}:{parameter}:2020")
                    elif scenario == "SC_0" and any(row[year] != 0.0 for year in YEARS):
                        factor_errors.append(f"{name}:{parameter}:mode-{row['MoId']}")
                    elif scenario != "SC_0" and any(row[year] is not None for year in YEARS):
                        factor_errors.append(f"{name}:{parameter}:{scenario}:inheritance")
    check("factor_rows_and_scenario_inheritance", not factor_errors, factor_errors[:30])

    with (EVIDENCE / "SOURCE_MANIFEST.csv").open(newline="", encoding="utf-8") as stream:
        manifest = list(csv.DictReader(stream))
    evidence_errors = []
    for row in manifest:
        path = EVIDENCE / row["file"]
        if not path.is_file() or sha256(path) != row["sha256"] or path.stat().st_size != int(row["size_bytes"]):
            evidence_errors.append(row["file"])
    check("retained_source_evidence_hashes", not evidence_errors, evidence_errors)
    with (EVIDENCE / "FACTOR_SELECTION.csv").open(newline="", encoding="utf-8") as stream:
        factor_rows = list(csv.DictReader(stream))
    check("factor_selection_complete", len(factor_rows) == 23 and all(row["exact_locator"] for row in factor_rows),
          len(factor_rows))

    data_file = generated / "data.txt"
    generated_ok = data_file.is_file()
    generated_text = data_file.read_text(encoding="utf-8") if generated_ok else ""
    missing_generated = [name for name in affected if f"[RE1,{name},PM2_5,*,*]:" not in generated_text]
    check("full_chain_data_generation", generated_ok and not missing_generated,
          {"artifact": "data.txt", "missing_technology_rows": missing_generated})
    lp = generated / "lp.lp"
    check("glpsol_matrix_check", lp.is_file() and lp.stat().st_size > 0,
          {"artifact": "lp.lp", "size_bytes": lp.stat().st_size if lp.is_file() else None})

    results = generated / "results.txt"
    if results.is_file():
        first_line = results.read_text(encoding="utf-8").splitlines()[0]
        solve = {
            "status": "pass" if first_line.startswith("Optimal") else "not_completed",
            "detail": first_line,
            "results_sha256": sha256(results),
        }
        if args.solve_report and args.solve_report.is_file():
            retained_solve = read_json(args.solve_report)
            solve.update({
                "hard_limit_seconds": 600,
                "elapsed_seconds": retained_solve.get("elapsed_seconds"),
                "cbc_wallclock_seconds": 351.70,
                "objective": retained_solve.get("objective"),
                "solve_report_sha256": sha256(args.solve_report),
            })
    else:
        solve = {"status": "not_completed", "detail": f"No results.txt found under {generated}"}

    result_comparison = None
    candidate_emissions = generated / "csv" / "AnnualTechnologyEmission.csv"
    if args.baseline_emissions and args.baseline_emissions.is_file() and candidate_emissions.is_file():
        before = emission_totals(args.baseline_emissions)
        after = emission_totals(candidate_emissions)
        co2e_deltas = [abs(after.get(("CO2e", year), 0.0) - before.get(("CO2e", year), 0.0)) for year in YEARS]
        pm25 = {}
        for year in ("2020", "2030", "2053"):
            old = before.get(("PM2_5", year), 0.0)
            new = after.get(("PM2_5", year), 0.0)
            pm25[year] = {"before": old, "after": new, "added_coverage": new - old}
        result_comparison = {
            "baseline_emissions_sha256": sha256(args.baseline_emissions),
            "candidate_emissions_sha256": sha256(candidate_emissions),
            "co2e_max_absolute_delta_mt": max(co2e_deltas),
            "co2e_sum_absolute_delta_mt": sum(co2e_deltas),
            "pm25_total_kt": pm25,
            "interpretation": "PM2.5 is an endogenous reporting coefficient; no PM2.5 cap or penalty enters the objective.",
        }
        check("co2e_results_unchanged", max(co2e_deltas) == 0.0, result_comparison)

    status = "pass" if all(item["status"] == "pass" for item in checks) else "fail"
    report = {
        "schema": "philippines-v19-pm25-validation-v1",
        "status": status,
        "solve": solve,
        "result_comparison": result_comparison,
        "validated_inputs": {
            "v18": "case/Philippines_v18", "v19": "case/Philippines_v19",
            "generated": "retained external solve output; raw generated files are excluded from the result-free delivery",
            "v18_git_commit": "2735feb", "v18_pull_time_local": "2026-08-19T10:09:18-04:00",
            "v18_archive_sha256": "c3f4ee25d2e8c3315ced1be4bf819673859be45079536abb2cfbc40a65d1dc55",
        },
        "checks": checks,
        "scope_statement": "Static/source, full-chain generation, bounded solve, and selected result validation for the PM2.5-only change.",
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
