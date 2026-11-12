"""Compare any two GENESIS Parquet datasets including Rust bridge and Python v3.

Checks per-file SHA256 and row counts from manifests, then multisets (EXCEPT ALL).
Comparison is schema-aligned and independent of row order or Parquet encoding.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import duckdb

ENTITIES = ("students", "classes", "enrollments", "subject_offerings", "period_records")


def sha256_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as source:
        for piece in iter(lambda: source.read(1024 * 1024), b""):
            sha.update(piece)
    return sha.hexdigest()


def compare(left: Path, right: Path) -> int:
    a = json.loads((left / "manifest.json").read_text(encoding="utf-8"))
    b = json.loads((right / "manifest.json").read_text(encoding="utf-8"))
    if a["generator_seed"] != b["generator_seed"] or a["catalog_sha256"] != b["catalog_sha256"]:
        raise ValueError("incompatible generator seed or ATLAS catalog")
    failures = 0
    db = duckdb.connect(":memory:")
    try:
        for entity in ENTITIES:
            paths = (left / f"{entity}.parquet", right / f"{entity}.parquet")
            manifests = (a, b)
            for path, manifest in zip(paths, manifests):
                info = manifest["artifacts"][entity]
                if path.name != info["path"] or sha256_file(path) != info["sha256"]:
                    raise ValueError(f"SHA256 mismatch in {path}")
            p1, p2 = (str(p.resolve()) for p in paths)
            columns_a = [row[0] for row in db.execute("DESCRIBE SELECT * FROM read_parquet(?)", [p1]).fetchall()]
            columns_b = [row[0] for row in db.execute("DESCRIBE SELECT * FROM read_parquet(?)", [p2]).fetchall()]
            if set(columns_a) != set(columns_b):
                print(f"FAIL {entity}: differing columns")
                failures += 1
                continue
            columns = ", ".join('"' + c.replace('"', '""') + '"' for c in columns_a)
            left_only = db.execute(
                f"SELECT COUNT(*) FROM (SELECT {columns} FROM read_parquet(?) "
                f"EXCEPT ALL SELECT {columns} FROM read_parquet(?))",
                [p1, p2],
            ).fetchone()[0]
            right_only = db.execute(
                f"SELECT COUNT(*) FROM (SELECT {columns} FROM read_parquet(?) "
                f"EXCEPT ALL SELECT {columns} FROM read_parquet(?))",
                [p2, p1],
            ).fetchone()[0]
            total_a = db.execute("SELECT COUNT(*) FROM read_parquet(?)", [p1]).fetchone()[0]
            total_b = db.execute("SELECT COUNT(*) FROM read_parquet(?)", [p2]).fetchone()[0]
            ok = left_only == right_only == 0 and total_a == total_b
            ok = ok and total_a == a["artifacts"][entity]["row_count"]
            ok = ok and total_b == b["artifacts"][entity]["row_count"]
            failures += not ok
            print(
                f"{'PASS' if ok else 'FAIL'} {entity}: left={total_a} right={total_b} "
                f"only_left={left_only} only_right={right_only}"
            )
    finally:
        db.close()
    return int(bool(failures))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("left", type=Path)
    cli.add_argument("right", type=Path)
    options = cli.parse_args()
    raise SystemExit(compare(options.left, options.right))
