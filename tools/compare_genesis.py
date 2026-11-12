"""Compare GENESIS v2 and v3 *logical* Parquet table contents.

Usage:
    python tools/compare_genesis.py data/tgi2-experimento-001 data/bench-v3-120-001

Uses EXCEPT ALL in both directions, so duplicate rows count and table order does not.
Physical parquet hashes may differ between writers and are NOT compared.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

ENTITIES = (
    "students", "classes", "enrollments", "subject_offerings", "period_records"
)


def compare(v2: Path, v3: Path) -> int:
    m2 = json.loads((v2 / "manifest.json").read_text(encoding="utf-8"))
    m3 = json.loads((v3 / "manifest.json").read_text(encoding="utf-8"))
    if m2["schema_version"] != "epa.genesis.dataset.v2":
        raise ValueError("first dataset is not GENESIS v2")
    if m3["schema_version"] != "epa.genesis.dataset.v3":
        raise ValueError("second dataset is not GENESIS v3")
    if m2["generator_seed"] != m3["generator_seed"]:
        raise ValueError("seeds differ; comparison would not be equivalent")
    if m2["catalog_sha256"] != m3["catalog_sha256"]:
        raise ValueError("catalog hashes differ")
    expected_students = m2["artifacts"]["students"]["row_count"]
    if m3["students"] != expected_students:
        raise ValueError("student counts differ")

    failures = 0
    db = duckdb.connect(":memory:")
    try:
        for name in ENTITIES:
            p2 = str((v2 / f"{name}.parquet").resolve())
            p3 = str((v3 / f"{name}.parquet").resolve())
            cols2 = [r[0] for r in db.execute("DESCRIBE SELECT * FROM read_parquet(?)", [p2]).fetchall()]
            cols3 = [r[0] for r in db.execute("DESCRIBE SELECT * FROM read_parquet(?)", [p3]).fetchall()]
            if set(cols2) != set(cols3):
                print(f"FAIL {name}: column sets differ: {cols2} vs {cols3}")
                failures += 1
                continue
            # V2/V3 schemas expose matching column names; explicitly align order.
            column_sql = ", ".join('"' + c.replace('"','""') + '"' for c in cols2)
            # No untrusted interpolation: fixed column identifiers are quoted;
            # parquet paths are bound separately for each query.
            forward = db.execute(
                f"SELECT COUNT(*) FROM ("
                f"SELECT {column_sql} FROM read_parquet(?) "
                f"EXCEPT ALL SELECT {column_sql} FROM read_parquet(?)"
                f")", [p2,p3]
            ).fetchone()[0]
            reverse = db.execute(
                f"SELECT COUNT(*) FROM ("
                f"SELECT {column_sql} FROM read_parquet(?) "
                f"EXCEPT ALL SELECT {column_sql} FROM read_parquet(?)"
                f")", [p3,p2]
            ).fetchone()[0]
            n2 = db.execute("SELECT COUNT(*) FROM read_parquet(?)", [p2]).fetchone()[0]
            n3 = db.execute("SELECT COUNT(*) FROM read_parquet(?)", [p3]).fetchone()[0]
            ok = (forward == 0 and reverse == 0 and n2 == n3)
            failures += not ok
            print(f"{'PASS' if ok else 'FAIL'} {name}: v2={n2}, v3={n3}, "
                  f"only_v2={forward}, only_v3={reverse}")
    finally:
        db.close()
    return int(bool(failures))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("v2", type=Path)
    p.add_argument("v3", type=Path)
    args = p.parse_args()
    raise SystemExit(compare(args.v2, args.v3))
