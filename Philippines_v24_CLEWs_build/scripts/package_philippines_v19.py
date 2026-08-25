#!/usr/bin/env python3
"""Build and verify the result-free Philippines v19 portable MUIO archive."""

from __future__ import annotations

import csv
import hashlib
import zipfile
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parent
CASE = REPO / "case" / "Philippines_v19"
OUTPUT = PACKAGE / "muio" / "Philippines_v19_v19.0.0_MUIO.zip"
MANIFEST = PACKAGE / "data_sources" / "V19_MODEL_ARCHIVE_MANIFEST.csv"
CHECKSUMS = PACKAGE / "muio" / "SHA256SUMS"
EXCLUDED_NAMES = {"data.txt", "data_processed.txt", "lp.lp", "results.txt"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def included(path: Path) -> bool:
    relative = path.relative_to(CASE)
    return "res" not in relative.parts and path.name not in EXCLUDED_NAMES and not path.name.startswith(".")


def main() -> None:
    files = sorted(path for path in CASE.rglob("*") if path.is_file() and included(path))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, Path("Philippines_v19") / path.relative_to(CASE))

    with zipfile.ZipFile(OUTPUT) as archive:
        members = [info.filename for info in archive.infolist() if not info.is_dir()]
        bad = [name for name in members if "/res/" in name or Path(name).name in EXCLUDED_NAMES]
        assert not bad, bad
        assert all(name.startswith("Philippines_v19/") for name in members)
        assert len(members) == len(files)

    archive_hash = sha256(OUTPUT)
    with MANIFEST.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["archive", "sha256", "size_bytes", "member_count", "internal_root", "result_files_included", "notes"])
        writer.writerow([OUTPUT.name, archive_hash, OUTPUT.stat().st_size, len(files), "Philippines_v19/", "false",
                         "Complete editable v19.0.0 source and documentation; all res/ and generated solver/result files excluded."])

    existing = []
    if CHECKSUMS.exists():
        existing = [line for line in CHECKSUMS.read_text(encoding="utf-8").splitlines()
                    if line.strip() and OUTPUT.name not in line]
    CHECKSUMS.write_text("\n".join(existing + [f"{archive_hash}  {OUTPUT.name}"]) + "\n", encoding="utf-8")
    print(f"{OUTPUT}: {len(files)} files, {OUTPUT.stat().st_size} bytes, {archive_hash}")


if __name__ == "__main__":
    main()
