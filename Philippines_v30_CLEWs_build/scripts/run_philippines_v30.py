#!/usr/bin/env python3
"""Run one preflighted Philippines v30 scenario with streamed CBC output."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pty
import re
import select
import subprocess
import sys
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP" / "DataStorage"
CASE = "Philippines_v30"
RUNS = {
    "BASE": "BASE_V30", "COAL_PHASEOUT": "COAL_PHASEOUT_V30",
    "RE": "RE_V30", "EV": "EV_V30",
}
MAX_SECONDS = 300


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=RUNS, required=True)
    parser.add_argument("--timeout", type=int, default=MAX_SECONDS)
    parser.add_argument("--review-approved", action="store_true")
    parser.add_argument("--basis-in", type=Path)
    parser.add_argument("--basis-out", type=Path)
    args = parser.parse_args()
    if not args.review_approved:
        raise SystemExit("CBC blocked: explicit --review-approved is required.")
    if args.timeout != MAX_SECONDS:
        raise SystemExit(f"V30 CBC deadline is fixed at exactly {MAX_SECONDS} seconds.")

    case = STORAGE / CASE
    run_name = RUNS[args.scenario]
    run = case / "res" / run_name
    preflight_path = case / "documentation" / "preflight_v30.json"
    if not preflight_path.is_file():
        raise SystemExit("CBC blocked: missing v30 preflight report.")
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    matrices = preflight.get("checks", {}).get("scenario_matrices", {})
    if preflight.get("status") != "pass" or preflight.get("optimizer_runs") != 0 or preflight.get("cbc_invoked") is not False or run_name not in matrices:
        raise SystemExit("CBC blocked: full four-scenario v30 preflight did not pass cleanly.")
    required = ("data.txt", "data_processed.txt", "lp.lp", "glpsol_check.log")
    missing = [name for name in required if not (run / name).is_file()]
    if missing:
        raise SystemExit(f"CBC blocked: missing matrix artifacts {missing}")
    if sha256(run / "lp.lp") != matrices[run_name]["lp_sha256"]:
        raise SystemExit("CBC blocked: LP hash differs from the preflighted matrix.")

    command = ["cbc", str(run / "lp.lp"), "-printingOptions", "all", "-sec", str(MAX_SECONDS), "-timeMode", "elapsed"]
    if args.basis_in:
        if not args.basis_in.is_file():
            raise SystemExit(f"CBC blocked: basis input does not exist: {args.basis_in}")
        command.extend(["basisIn", str(args.basis_in)])
    command.append("solve")
    if args.basis_out:
        args.basis_out.parent.mkdir(parents=True, exist_ok=True)
        command.extend(["basisOut", str(args.basis_out)])
    command.extend(["solu", str(run / "results.txt")])
    started = time.monotonic()
    timed_out = False
    with (run / "cbc.log").open("w", encoding="utf-8") as log:
        master_fd, slave_fd = pty.openpty()
        process = subprocess.Popen(command, stdout=slave_fd, stderr=slave_fd, close_fds=True)
        os.close(slave_fd)

        def hard_stop() -> None:
            nonlocal timed_out
            if process.poll() is None:
                timed_out = True
                process.kill()

        timer = threading.Timer(MAX_SECONDS, hard_stop)
        timer.daemon = True
        timer.start()
        while True:
            ready, _, _ = select.select([master_fd], [], [], 0.5)
            if ready:
                try:
                    chunk = os.read(master_fd, 65536)
                except OSError:
                    chunk = b""
                if chunk:
                    decoded = chunk.decode("utf-8", errors="replace")
                    log.write(decoded)
                    log.flush()
                    sys.stdout.write(decoded)
                    sys.stdout.flush()
                elif process.poll() is not None:
                    break
            elif process.poll() is not None:
                break
        returncode = process.wait()
        os.close(master_fd)
        timer.cancel()
    elapsed = time.monotonic() - started

    header = ""
    if (run / "results.txt").is_file():
        with (run / "results.txt").open(encoding="utf-8", errors="replace") as handle:
            header = handle.readline().strip()
    log_text = (run / "cbc.log").read_text(encoding="utf-8", errors="replace")
    if header.startswith("Optimal - objective value"):
        status = "optimal"
    elif timed_out or header.startswith("Stopped on time") or "Stopped on time limit" in log_text:
        status = "timed_out"
    elif header.startswith("Infeasible") or "proven infeasible" in log_text.lower() or "primal infeasible" in log_text.lower():
        status = "infeasible"
    else:
        status = "failed"
    match = re.search(r"objective value\s+([-+0-9.eE]+)", header)
    report = {
        "status": status, "case": CASE, "run": run_name, "scenario": args.scenario,
        "review_approved": True, "deadline_seconds": MAX_SECONDS, "elapsed_seconds": elapsed,
        "hard_deadline_triggered": timed_out, "cbc_returncode": returncode,
        "basis_in": str(args.basis_in) if args.basis_in else None,
        "basis_out": str(args.basis_out) if args.basis_out else None,
        "objective": float(match.group(1)) if match else None, "solution_header": header,
        "hashes": {name: sha256(run / name) for name in ("lp.lp", "results.txt", "cbc.log") if (run / name).is_file()},
    }
    (run / "optimization_record.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("\n" + json.dumps(report, indent=2))
    return 0 if status in {"optimal", "timed_out"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
