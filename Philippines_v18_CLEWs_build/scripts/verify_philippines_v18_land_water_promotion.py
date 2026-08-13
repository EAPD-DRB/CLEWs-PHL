#!/usr/bin/env python3
"""Verify promoted v18 source and generated artifacts without optimizing."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import types
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MODEL = REPO / "WebAPP" / "SOLVERs" / "model.v.5.4.txt"
RUN = "LAND_WATER_CLOSURE_V18_BASE"

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(REPO / "API"))

from Classes.Case.DataFileClass import DataFile  # noqa: E402
from Classes.Case.OsemosysClass import Osemosys  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def normalized_processed(path: Path) -> bytes:
    """Canonicalize unordered AMPL set declarations; preserve all other text."""
    output = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(set\s+[^:]+:=)\s*(.*);$", line)
        if not match:
            output.append(line)
            continue
        tokens = re.findall(r"\([^)]*\)|\S+", match.group(2))
        output.append(f"{match.group(1)} {' '.join(sorted(tokens))};")
    return ("\n".join(output) + "\n").encode("utf-8")


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def parse_matrix(text: str) -> dict[str, int]:
    result = {}
    for key, pattern in {
        "rows": r"Number of rows\s*=\s*([\d,]+)",
        "columns": r"Number of columns\s*=\s*([\d,]+)",
        "matrix_nonzeros": r"Number of non-zeros \(matrix\)\s*=\s*([\d,]+)",
        "objective_nonzeros": r"Number of non-zeros \(objrow\)\s*=\s*([\d,]+)",
    }.items():
        match = re.search(pattern, text)
        if not match:
            raise AssertionError(f"GLPK output missing {key}")
        result[key] = int(match.group(1).replace(",", ""))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--resume-generated", action="store_true")
    args = parser.parse_args()
    live = args.live.resolve()
    candidate = args.candidate.resolve()
    package = args.package.resolve()
    candidate_run = candidate / "res" / RUN
    live_run = live / "res" / RUN
    if live_run.exists() and not args.resume_generated:
        raise FileExistsError(f"refusing to replace live check run: {live_run}")
    live_run.mkdir(parents=True, exist_ok=args.resume_generated)

    source_mismatch = {}
    for candidate_file in sorted(candidate.glob("*.json")):
        live_file = live / candidate_file.name
        if not live_file.is_file():
            source_mismatch[candidate_file.name] = "missing"
        elif sha256(candidate_file) != sha256(live_file):
            source_mismatch[candidate_file.name] = {
                "candidate": sha256(candidate_file), "live": sha256(live_file)
            }
    if source_mismatch:
        raise AssertionError(source_mismatch)

    model = DataFile(live.name)
    started = time.monotonic()
    model.generateDatafile(RUN)
    generation_seconds = time.monotonic() - started
    started = time.monotonic()
    model.preprocessData(live_run / "data.txt", live_run / "data_processed.txt")
    preprocess_seconds = time.monotonic() - started
    if sha256(live_run / "data.txt") != sha256(candidate_run / "data.txt"):
        raise AssertionError("promoted live data.txt differs from solved candidate")
    processed_byte_identical = (
        sha256(live_run / "data_processed.txt") == sha256(candidate_run / "data_processed.txt")
    )
    candidate_normalized = normalized_processed(candidate_run / "data_processed.txt")
    live_normalized = normalized_processed(live_run / "data_processed.txt")
    processed_set_order_equivalent = candidate_normalized == live_normalized
    if not processed_set_order_equivalent:
        raise AssertionError("promoted preprocessing differs beyond unordered set declaration order")

    glpsol = Osemosys._find_solver_binary(model.glpkFolder.resolve(), "glpsol", recursive=False)
    if glpsol is None:
        raise RuntimeError("GLPK unavailable")
    started = time.monotonic()
    checked = subprocess.run(
        [
            str(glpsol), "--check", "-m", str(MODEL),
            "-d", str(live_run / "data_processed.txt"),
            "--wlp", str(live_run / "lp.lp"),
        ],
        cwd=model.glpkFolder.resolve() if model.glpsol_is_bundled else None,
        capture_output=True,
        text=True,
        timeout=150,
    )
    glpsol_seconds = time.monotonic() - started
    if checked.returncode != 0:
        raise RuntimeError((checked.stdout + "\n" + checked.stderr)[-12000:])
    matrix = parse_matrix(checked.stdout + "\n" + checked.stderr)
    expected_matrix = {
        "rows": 791517,
        "columns": 886010,
        "matrix_nonzeros": 12817475,
        "objective_nonzeros": 423240,
    }
    if matrix != expected_matrix:
        raise AssertionError(f"promoted matrix differs: {matrix} != {expected_matrix}")

    report = {
        "schema": "philippines-v18-land-water-promotion-identity-v1",
        "status": "pass",
        "live_case": str(live),
        "candidate_case": str(candidate),
        "source_json_count": len(list(candidate.glob("*.json"))),
        "source_json_byte_identical": True,
        "data_txt_byte_identical": True,
        "data_processed_txt_byte_identical": processed_byte_identical,
        "data_processed_set_order_equivalent": processed_set_order_equivalent,
        "data_processed_normalized_sha256": bytes_sha256(live_normalized),
        "preprocessing_difference": "unordered derived set declaration order only",
        "matrix": matrix,
        "glpsol_check": "pass",
        "optimizer_runs_this_step": 0,
        "post_promotion_cbc": "not run because root source JSON and data.txt are byte-identical; the only processed diff is canonicalized set order and the GLPK matrix dimensions match",
        "hashes": {
            "data_txt": sha256(live_run / "data.txt"),
            "data_processed_txt": sha256(live_run / "data_processed.txt"),
            "lp": sha256(live_run / "lp.lp"),
        },
        "timings_seconds": {
            "generate_datafile": generation_seconds,
            "preprocess_data": preprocess_seconds,
            "glpsol_check_and_lp": glpsol_seconds,
        },
    }
    output = package / "data_sources" / "snapshots" / "land_water_closure_promotion_identity.json"
    write_json(output, report)
    documentation = live / "documentation"
    documentation.mkdir(exist_ok=True)
    write_json(documentation / output.name, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
