"""GENESIS Rust -> verified, incremental Parquet bridge (Python/PyArrow I/O).

The scientific records are generated in Rust. This module converts the
JSONL stream into an immutable dataset using the existing v3 Parquet writer,
so the bridge is not falsely advertised as native Rust Parquet.

Usage:
  python -m epa.genesis.rust_bridge --output data/genesis-rust-bridge-3 --students 3

Requires an installed Rust toolchain and pip install -e ".[research,streaming]".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import uuid
from collections import Counter
from pathlib import Path

from epa.atlas.catalog import catalog_sha256, load_catalog
from epa.genesis.v3 import ParquetRows, _arrow_schemas

SCHEMA = "epa.genesis.dataset.rust_bridge.v1"


def generate(
    catalog_path: Path,
    destination: Path,
    *,
    students: int,
    seed: int = 20261029,
    start_year: int = 2020,
    school_count: int = 2,
    classes_per_grade: int = 3,
    row_group_rows: int = 4096,
) -> dict:
    import pyarrow as pa

    catalog_path = Path(catalog_path)
    destination = Path(destination)
    if not (1 <= students <= 2000):
        raise ValueError("pilot Rust bridge supports 1..2000 students")
    if row_group_rows < 1:
        raise ValueError("row_group_rows must be positive")
    if not (1 <= school_count <= 20 and 1 <= classes_per_grade <= 20):
        raise ValueError("invalid school/class counts")
    if not (2000 <= start_year <= 2100):
        raise ValueError("invalid start_year")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"immutable output already exists: {destination}")

    catalog = load_catalog(catalog_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = destination.parent / f".{destination.name}.tmp-{uuid.uuid4().hex}"
    stage.mkdir()
    writers: dict[str, ParquetRows] = {}
    command = [
        "cargo", "run", "--quiet", "--release", "--locked",
        "--manifest-path", "engines/genesis-rs/Cargo.toml",
        "--", "generate-jsonl", str(catalog_path), str(students),
        str(seed), str(start_year), str(school_count), str(classes_per_grade),
    ]
    try:
        schemas = _arrow_schemas(pa)
        writers = {
            entity: ParquetRows(stage / f"{entity}.parquet", schema,
                                row_group_rows=row_group_rows)
            for entity, schema in schemas.items()
        }
        counts: Counter[str] = Counter()
        # Never pipe STDERR: the toolchain may print compilation progress.
        # A separate unconsumed STDERR pipe could deadlock when buffers fill.
        with subprocess.Popen(
            command, stdout=subprocess.PIPE, text=True, encoding="utf-8",
        ) as process:
            assert process.stdout is not None
            for line_no, line in enumerate(process.stdout, 1):
                try:
                    item = json.loads(line)
                    if not isinstance(item, dict) or set(item) != {"entity", "row"}:
                        raise ValueError("unexpected JSONL envelope")
                    entity, row = item["entity"], item["row"]
                    if entity not in writers or not isinstance(row, dict):
                        raise ValueError("invalid entity or row")
                    if set(row) != set(schemas[entity].names):
                        raise ValueError(f"unexpected columns for {entity}")
                    writers[entity].add(row)
                    counts[entity] += 1
                except (ValueError, TypeError) as exc:
                    process.kill()
                    process.wait()
                    raise ValueError(f"invalid Rust JSONL line {line_no}: {exc}") from exc
            return_code = process.wait()
            if return_code != 0:
                raise RuntimeError(f"Rust generator exited with code {return_code}")

        subject_total = sum(len(grade["subjects"]) for grade in catalog["grades"])
        expected = {
            "students": students,
            "classes": len(catalog["grades"]) * school_count * classes_per_grade,
            "enrollments": students * len(catalog["grades"]),
            "subject_offerings": subject_total * school_count * classes_per_grade,
            "period_records": students * subject_total * 4,
        }
        if dict(counts) != expected:
            raise ValueError(f"row counts differ: actual={dict(counts)} expected={expected}")

        artifacts = {entity: writer.close() for entity, writer in writers.items()}
        manifest = {
            "schema_version": SCHEMA,
            "classification": "SYNTHETIC",
            "generator_engine": "rust-mt19937-jsonl-python-pyarrow-bridge",
            "generator_seed": seed,
            "catalog_sha256": catalog_sha256(catalog_path),
            "students": students,
            "start_year": start_year,
            "school_count": school_count,
            "classes_per_grade": classes_per_grade,
            "row_group_rows": row_group_rows,
            "terms_per_year": 4,
            "artifacts": artifacts,
            "scope": "synthetic research engineering; no empirical validation",
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"concurrent output publication: {destination}")
        stage.rename(destination)
        return manifest
    except BaseException:
        for writer in writers.values():
            try:
                writer.abort()
            except Exception:
                pass
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("examples/atlas.demo.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--students", type=int, required=True)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--start-year", type=int, default=2020)
    parser.add_argument("--schools", type=int, default=2)
    parser.add_argument("--classes-per-grade", type=int, default=3)
    parser.add_argument("--row-group-rows", type=int, default=4096)
    args = parser.parse_args()
    report = generate(
        args.catalog, args.output, students=args.students, seed=args.seed,
        start_year=args.start_year, school_count=args.schools,
        classes_per_grade=args.classes_per_grade,
        row_group_rows=args.row_group_rows,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
