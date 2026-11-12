"""Rust-only GENESIS scalability probe with immutable outputs and streaming integrity checks.

This deliberately does NOT compare datasets to Python v3 above its 2k limit.
Run from repo root:
  python tools/benchmark_genesis_rust_scale.py --students 5000 --seed 20261029

A successful run verifies each file digest, manifest row counts, and schema.
Measured sampled RSS is not guaranteed peak. Output is never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    import psutil
except ImportError as exc:
    raise SystemExit('Install psutil: python -m pip install -e ".[benchmark]"') from exc

REPO = Path(__file__).resolve().parents[1]
ENTITIES = ("students", "classes", "enrollments", "subject_offerings", "period_records")
SCHEMA = "epa.benchmark.genesis_rust_scale.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_counts(catalog: Path, students: int, schools: int, sections: int) -> dict[str, int]:
    contents = json.loads(catalog.read_text(encoding="utf-8"))
    years = len(contents["grades"])
    subjects = sum(len(grade["subjects"]) for grade in contents["grades"])
    return {
        "students": students,
        "classes": years * schools * sections,
        "enrollments": students * years,
        "subject_offerings": subjects * schools * sections,
        "period_records": students * subjects * 4,
    }


def verify_dataset(path: Path, expected: dict[str, int], *, students: int, seed: int,
                   row_group_rows: int, catalog_sha256: str) -> dict:
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("schema_version") != "epa.genesis.dataset.rust_native.v1"
            or manifest.get("classification") != "SYNTHETIC"
            or manifest.get("generator_seed") != seed
            or manifest.get("students") != students
            or manifest.get("row_group_rows") != row_group_rows
            or manifest.get("catalog_sha256") != catalog_sha256):
        raise ValueError("invalid dataset manifest")
    if set(manifest.get("artifacts", {})) != set(ENTITIES):
        raise ValueError("unexpected artifact set")
    sizes = {}
    for entity in ENTITIES:
        artifact = manifest["artifacts"][entity]
        filename = entity + ".parquet"
        if artifact.get("path") != filename or artifact.get("row_count") != expected[entity]:
            raise ValueError(f"row count / path mismatch: {entity}")
        file_path = path / filename
        if sha256_file(file_path) != artifact.get("sha256"):
            raise ValueError(f"sha256 mismatch: {entity}")
        sizes[entity] = file_path.stat().st_size
    return {"row_counts": expected, "parquet_bytes_by_entity": sizes,
            "total_parquet_bytes": sum(sizes.values()), "sha256_verified": True}


def run_command(command: list[str], *, stdout_path: Path, stderr_path: Path,
                sample_ms: int) -> dict:
    peak_rss = 0
    samples = 0
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        start = time.perf_counter()
        with subprocess.Popen(command, cwd=REPO, stdout=stdout, stderr=stderr) as process:
            root = psutil.Process(process.pid)
            while True:
                try:
                    procs = [root] + root.children(recursive=True)
                    rss = 0
                    for proc in procs:
                        try:
                            rss += proc.memory_info().rss
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            pass
                    peak_rss = max(peak_rss, rss)
                    samples += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                if process.poll() is not None:
                    break
                time.sleep(sample_ms / 1000)
            returncode = process.wait()
        duration = time.perf_counter() - start
    return {"wall_seconds": duration, "observed_peak_rss_bytes": peak_rss,
            "rss_samples": samples, "return_code": returncode}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--students", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--catalog", type=Path, default=REPO / "examples/atlas.demo.json")
    parser.add_argument("--row-group-rows", type=int, default=4096)
    parser.add_argument("--sample-ms", type=int, default=25)
    parser.add_argument("--schools", type=int, default=2)
    parser.add_argument("--classes-per-grade", type=int, default=3)
    parser.add_argument("--output-root", type=Path,
                        default=REPO / "data" / ("rust-scale-" + uuid.uuid4().hex[:12]))
    args = parser.parse_args()
    if not 1 <= args.students <= 100_000:
        parser.error("students must be 1..100000")
    if not 1 <= args.row_group_rows <= 100_000 or args.sample_ms < 1:
        parser.error("invalid row group or sample interval")
    if not 1 <= args.schools <= 20 or not 1 <= args.classes_per_grade <= 20:
        parser.error("schools/sections must be 1..20")
    catalog = args.catalog.resolve()
    if not catalog.is_file():
        parser.error("catalog does not exist")
    root = args.output_root.resolve()
    if root.exists() or root.is_symlink():
        parser.error("immutable output root already exists")
    subprocess.run(["cargo", "build", "--locked", "--release", "--manifest-path",
                    "engines/genesis-rs/Cargo.toml"], cwd=REPO, check=True)
    binary = REPO / "engines/genesis-rs/target/release" / ("genesis-rs.exe" if os.name == "nt" else "genesis-rs")
    root.mkdir(parents=True)
    dataset = root / "dataset"
    report_path = root / "benchmark.json"
    report = {
        "schema_version": SCHEMA, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FAIL", "students": args.students, "seed": args.seed,
        "row_group_rows": args.row_group_rows, "sample_ms": args.sample_ms,
        "schools": args.schools, "classes_per_grade": args.classes_per_grade,
        "platform": {"os": platform.platform(), "python": sys.version.split()[0],
                     "logical_cpus": os.cpu_count()},
        "catalog_sha256": sha256_file(catalog),
        "validation_scope": "manifest counts and file hashes only; no Python dataset parity above 2000",
        "limitations": [
            "A single run is diagnostic, not a statistically robust benchmark.",
            "Sampled process-tree RSS can miss short-lived allocation spikes.",
            "No row-by-row parity against Python above 2000 students.",
            "Datasets are synthetic and do not validate predictive models.",
        ],
    }
    try:
        result = run_command(
            [str(binary), "generate-parquet", str(catalog), str(dataset),
             str(args.students), str(args.seed), str(args.row_group_rows),
             "2020", str(args.schools), str(args.classes_per_grade)],
            stdout_path=root / "generator.stdout.txt",
            stderr_path=root / "generator.stderr.txt",
            sample_ms=args.sample_ms,
        )
        report["metrics"] = result
        if result["return_code"] != 0:
            raise RuntimeError("generator exited unsuccessfully; see generator.stderr.txt")
        report["dataset"] = verify_dataset(
            dataset, expected_counts(catalog, args.students, args.schools,
                                     args.classes_per_grade),
            students=args.students, seed=args.seed,
            row_group_rows=args.row_group_rows, catalog_sha256=report["catalog_sha256"])
        report["status"] = "PASS"
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        with report_path.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(f"{report['status']}: evidence saved to {report_path}", flush=True)


if __name__ == "__main__":
    main()
