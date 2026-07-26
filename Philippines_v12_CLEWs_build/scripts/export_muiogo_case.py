#!/usr/bin/env python3
"""Create a portable MUIO case backup using MUIO's backup layout."""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_folder", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    case_folder = args.case_folder.resolve()
    if not (case_folder / "genData.json").is_file():
        raise SystemExit(f"Not a MUIO case folder: {case_folder}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.output, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(case_folder.rglob("*")):
            if not path.is_file() or path.name == "lp.lp":
                continue
            arcname = PurePosixPath(case_folder.name) / path.relative_to(case_folder)
            archive.write(path, str(arcname))
    print(f"Portable MUIO case backup: {args.output} ({args.output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
