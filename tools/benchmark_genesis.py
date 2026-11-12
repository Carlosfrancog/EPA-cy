"""Reproducible *local* wall-time / memory comparison of GENESIS engines.

Run from repository root (after compiling Rust release). This tool never
deletes or overwrites existing datasets; it writes into a new run directory.

Data validation compares every candidate to Python v3 with DuckDB EXCEPT ALL
and validates the SHA256 digest of each generated Parquet file.

Usage:
  python tools/benchmark_genesis.py --students 120 --repeats 3 --warmups 1

Benchmark results are machine-specific engineering evidence, NOT validation
of ML predictive quality or general scientific performance.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

try:
    import psutil
except ImportError as exc:
    raise SystemExit(
        'Install benchmark dependencies: python -m pip install -e ".[research,streaming,benchmark]"'
    ) from exc

from tools.compare_genesis_parquet import ENTITIES, compare, sha256_file

REPO = Path(__file__).resolve().parents[1]
ENGINE_NAMES = ("python_v2_duckdb", "python_v3_pyarrow", "rust_pyarrow_bridge", "rust_native_parquet")
MANIFEST = "epa.benchmark.genesis.v1"


def commands(*, output: Path, students: int, seed: int, catalog: Path,
             engine: str, batch_students: int, row_group_rows: int,
             rust_binary: Path) -> list[str]:
    shared = ["--catalog", str(catalog), "--output", str(output),
              "--students", str(students), "--seed", str(seed)]
    if engine == "python_v2_duckdb":
        return [sys.executable, "-m", "epa.genesis.v2", *shared]
    if engine == "python_v3_pyarrow":
        return [sys.executable, "-m", "epa.genesis.v3", *shared,
                "--batch-students", str(batch_students),
                "--row-group-rows", str(row_group_rows)]
    if engine == "rust_pyarrow_bridge":
        return [sys.executable, "-m", "epa.genesis.rust_bridge", *shared,
                "--row-group-rows", str(row_group_rows)]
    if engine == "rust_native_parquet":
        return [str(rust_binary), "generate-parquet",
                str(catalog), str(output), str(students), str(seed),
                str(row_group_rows)]
    raise ValueError(f"unknown engine: {engine}")


def build_rust_binary() -> Path:
    # Building is explicitly excluded from measured generator runtime.
    subprocess.run(
        ["cargo", "build", "--locked", "--release", "--manifest-path",
         "engines/genesis-rs/Cargo.toml"], cwd=REPO, check=True,
    )
    ext = ".exe" if os.name == "nt" else ""
    path = REPO / "engines" / "genesis-rs" / "target" / "release" / ("genesis-rs" + ext)
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def run_one(command: list[str], *, log_prefix: Path, sample_seconds: float) -> dict:
    """Measure complete process tree peak RSS; elapsed excludes benchmark setup.

    Observed peak is sampled, not guaranteed true absolute peak. Child process
    CPU time and I/O are not reported. psutil may miss short-lived processes.
    """
    log_prefix.parent.mkdir(parents=True, exist_ok=True)
    stdout_path = Path(str(log_prefix) + ".stdout.txt")
    stderr_path = Path(str(log_prefix) + ".stderr.txt")
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        start = time.perf_counter_ns()
        with subprocess.Popen(command, cwd=REPO, stdout=stdout, stderr=stderr) as process:
            root = psutil.Process(process.pid)
            peak_rss = 0
            observed_samples = 0
            while True:
                try:
                    processes = [root] + root.children(recursive=True)
                    rss = 0
                    for proc in processes:
                        try:
                            rss += proc.memory_info().rss
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            continue
                    peak_rss = max(peak_rss, rss)
                    observed_samples += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                if process.poll() is not None:
                    break
                time.sleep(sample_seconds)
            return_code = process.wait()
        wall_seconds = (time.perf_counter_ns() - start) / 1e9
    return {
        "return_code": return_code,
        "wall_seconds": wall_seconds,
        "observed_peak_rss_bytes": peak_rss,
        "rss_samples": observed_samples,
        "stdout_log": str(stdout_path.relative_to(log_prefix.parent.parent)),
        "stderr_log": str(stderr_path.relative_to(log_prefix.parent.parent)),
    }


def describe_dir(dataset: Path) -> dict:
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    artifacts = manifest["artifacts"]
    sizes = {}
    total = 0
    for entity in ENTITIES:
        p = dataset / f"{entity}.parquet"
        expected = artifacts[entity]
        if expected["path"] != p.name or sha256_file(p) != expected["sha256"]:
            raise ValueError(f"invalid artifact integrity for {p}")
        sizes[entity] = p.stat().st_size
        total += sizes[entity]
    return {
        "schema_version": manifest["schema_version"],
        "catalog_sha256": manifest["catalog_sha256"],
        "seed": manifest["generator_seed"],
        "row_counts": {entity: artifacts[entity]["row_count"] for entity in ENTITIES},
        "bytes_per_entity": sizes,
        "total_parquet_bytes": total,
    }


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * p
    low, high = math.floor(pos), math.ceil(pos)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def summary(samples: list[dict]) -> dict:
    times = [item["metrics"]["wall_seconds"] for item in samples]
    rss = [item["metrics"]["observed_peak_rss_bytes"] for item in samples]
    sizes = [item["dataset"]["total_parquet_bytes"] for item in samples]
    return {
        "runs": len(samples),
        "wall_median_seconds": statistics.median(times),
        "wall_p95_seconds": percentile(times, .95),
        "wall_min_seconds": min(times),
        "wall_max_seconds": max(times),
        "sampled_peak_rss_max_bytes": max(rss),
        "parquet_bytes_median": statistics.median(sizes),
    }


def benchmark(args: argparse.Namespace) -> Path:
    if not (1 <= args.students <= 2000):
        raise ValueError("pilot benchmark must use 1..2000 students (v2 compatibility)")
    if not (1 <= args.repeats <= 20 and 0 <= args.warmups <= 10):
        raise ValueError("repeats 1..20, warmups 0..10 required")
    if args.row_group_rows < 1 or args.batch_students < 1 or args.sample_ms < 1:
        raise ValueError("invalid buffering or sampling parameters")
    engines = list(args.engines)
    if not engines or len(set(engines)) != len(engines):
        raise ValueError("engines must be distinct and non-empty")
    if "python_v3_pyarrow" not in engines:
        raise ValueError("include python_v3_pyarrow as parity reference")
    catalog = args.catalog.resolve()
    if not catalog.is_file():
        raise FileNotFoundError(catalog)
    root = args.output_root.resolve()
    if root.exists() or root.is_symlink():
        raise FileExistsError(f"benchmark output already exists: {root}")
    rust_binary = build_rust_binary() if any(name.startswith("rust_") for name in engines) else Path("")
    root.mkdir(parents=True, exist_ok=False)
    data_root = root / "datasets"
    logs_root = root / "logs"
    data_root.mkdir()
    logs_root.mkdir()
    report = {
        "schema_version": MANIFEST,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "catalog": str(catalog),
        "catalog_file_sha256": sha256_file(catalog),
        "generator_seed": args.seed,
        "students": args.students,
        "warmups": args.warmups,
        "repeats": args.repeats,
        "batch_students": args.batch_students,
        "row_group_rows": args.row_group_rows,
        "rss_sample_ms": args.sample_ms,
        "platform": {
            "os": platform.platform(),
            "python": sys.version.split()[0],
            "cpu_logical_count": os.cpu_count(),
            "architecture": platform.machine(),
            "psutil": psutil.__version__,
        },
        "rust_binary": str(rust_binary) if rust_binary else None,
        "measurements": [],
        "summaries": {},
        "limitations": [
            "Includes generator process startup, Python imports, and filesystem cache effects.",
            "Excludes Rust release compilation and comparison validation duration.",
            "Memory is sampled RSS across live process trees, not a true peak allocation.",
            "Compression codecs and row-group boundaries may differ among engines.",
            "No GPU, CPU energy, deterministic thread pinning, or confidence intervals.",
            "All academic records are synthetic and do not validate ML models.",
        ],
    }
    # Interleave engines per repetition to mitigate monotonic thermal/cache effects.
    # Preserve an identical seed/catalog for every engine in each comparison group.
    try:
        total = args.warmups + args.repeats
        for round_idx in range(total):
            warmup = round_idx < args.warmups
            round_label = f"{'warmup' if warmup else 'trial'}-{round_idx:02d}"
            reference: Path | None = None
            for engine in engines:
                target = data_root / f"{round_label}-{engine}"
                command = commands(
                    output=target, students=args.students, seed=args.seed,
                    catalog=catalog, engine=engine,
                    batch_students=args.batch_students,
                    row_group_rows=args.row_group_rows, rust_binary=rust_binary,
                )
                metrics = run_one(command, log_prefix=logs_root / f"{round_label}-{engine}",
                                  sample_seconds=args.sample_ms / 1000)
                if metrics["return_code"] != 0:
                    raise RuntimeError(f"{engine} failed ({metrics['return_code']}): check {metrics['stderr_log']}")
                dataset = describe_dir(target)
                if engine == "python_v3_pyarrow":
                    reference = target
                else:
                    if reference is None:
                        raise RuntimeError("Python v3 must be first engine to verify parity")
                    if compare(reference, target) != 0:
                        raise RuntimeError(f"mismatched Parquet records: {engine} vs python_v3_pyarrow")
                item = {"round": round_idx, "warmup": warmup,
                        "engine": engine, "metrics": metrics, "dataset": dataset,
                        "parity_pass": True}
                report["measurements"].append(item)
                print(f"{round_label} {engine}: {metrics['wall_seconds']:.3f}s "
                      f"RSS~{metrics['observed_peak_rss_bytes'] / (1024**2):.1f}MiB",
                      flush=True)
        for engine in engines:
            samples = [x for x in report["measurements"] if x["engine"] == engine and not x["warmup"]]
            report["summaries"][engine] = summary(samples)
        report["status"] = "PASS"
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        # Retain existing outputs for independent verification; never delete.
        (root / "benchmark.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return root / "benchmark.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=REPO / "examples/atlas.demo.json")
    parser.add_argument("--output-root", type=Path,
                        default=REPO / "data" / ("bench-" + uuid.uuid4().hex[:12]))
    parser.add_argument("--students", type=int, default=120)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--row-group-rows", type=int, default=4096)
    parser.add_argument("--batch-students", type=int, default=1000)
    parser.add_argument("--sample-ms", type=int, default=25)
    parser.add_argument("--engines", nargs="+", choices=ENGINE_NAMES,
                        default=list(ENGINE_NAMES))
    args = parser.parse_args()
    if args.engines[0] != "python_v3_pyarrow":
        parser.error("list python_v3_pyarrow first; it is the comparison reference")
    output = benchmark(args)
    print(f"PASS: evidence saved to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
