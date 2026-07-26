#!/usr/bin/env python3
"""Run MUIO's existing ImportTemplate against a prepared Philippines workbook."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--case", default="Philippines_v12_raw_CLEWs")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    importer_path = repo / "API/Classes/Case/ImportTemplate.py"
    storage = repo / "WebAPP/DataStorage"
    target = storage / args.case
    if target.exists():
        raise SystemExit(f"Refusing to overwrite existing case: {target}")

    staging = storage / f".{args.case}.one_off_import.xlsx"
    if staging.exists():
        raise SystemExit(f"Refusing to overwrite existing staging file: {staging}")

    before = sha256(importer_path)
    shutil.copy2(args.workbook.resolve(), staging)
    sys.path.insert(0, str(repo / "API"))
    from Classes.Case.ImportTemplate import ImportTemplate

    request = {
        "osy-version": "5.4",
        "osy-casename": args.case,
        "osy-desc": "Raw, uncalibrated Philippines CLEWs Global full-nexus model.",
        "osy-date": "2026-07-25",
        "osy-currency": "USD",
        "osy-template": staging.name,
        "osy-data": True,
    }
    response = ImportTemplate(staging.name).importProcess(request)
    after = sha256(importer_path)
    if before != after:
        raise RuntimeError("ImportTemplate.py changed during the one-off import")
    if response.get("status_code") != "success":
        raise RuntimeError(json.dumps(response, default=str, indent=2))
    if not target.is_dir():
        raise RuntimeError(f"Importer reported success but did not create {target}")
    print(json.dumps({"response": response["message"], "importer_sha256": after}, indent=2))


if __name__ == "__main__":
    main()
