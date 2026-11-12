"""Compare Rust JSONL stream with GENESIS v3 Python row generator.

No Parquet or ML training; compares logical rows in deterministic emission order.
Uses bounded memory, and reports first 10 field mismatches, then fails.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import subprocess
from collections import Counter
from pathlib import Path

from epa.atlas.catalog import load_catalog
from epa.genesis.v3 import school_rows, student_rows


def reference_rows(catalog: dict, *, students: int, seed: int, start_year: int,
                   schools: int, classes_per_grade: int):
    yield from school_rows(catalog, start_year=start_year, school_count=schools,
                           classes_per_grade=classes_per_grade)
    for number in range(1, students + 1):
        yield from student_rows(catalog, number, seed=seed, start_year=start_year,
                                school_count=schools, classes_per_grade=classes_per_grade)


def same_values(expected: dict, actual: dict, *, tolerance: float) -> list[str]:
    messages = []
    if set(expected) != set(actual):
        return [f"columns differ: expected={sorted(expected)} actual={sorted(actual)}"]
    for key, value in expected.items():
        received = actual[key]
        if isinstance(value, float) and isinstance(received, (float, int)):
            if not math.isclose(value, received, rel_tol=0, abs_tol=tolerance):
                messages.append(f"{key}: Python={value!r}, Rust={received!r}")
        elif value != received or type(value) is not type(received):
            messages.append(f"{key}: Python={value!r}, Rust={received!r}")
    return messages


def compare(*, catalog_path: Path, students: int, seed: int,
            start_year: int, schools: int, classes_per_grade: int,
            tolerance: float) -> int:
    catalog = load_catalog(catalog_path)
    command = [
        "cargo", "run", "--quiet", "--release", "--manifest-path",
        "engines/genesis-rs/Cargo.toml", "--", "generate-jsonl",
        str(catalog_path), str(students), str(seed), str(start_year),
        str(schools), str(classes_per_grade),
    ]
    counter = Counter()
    mismatches = 0
    first_errors: list[str] = []
    process = subprocess.Popen(command, stdout=subprocess.PIPE, encoding="utf-8")
    try:
        assert process.stdout is not None
        expected_iter = reference_rows(
            catalog, students=students, seed=seed, start_year=start_year,
            schools=schools, classes_per_grade=classes_per_grade,
        )
        for idx, (expected, line) in enumerate(
            itertools.zip_longest(expected_iter, process.stdout), start=1
        ):
            if expected is None or line is None:
                mismatches += 1
                first_errors.append(f"row {idx}: stream length differs")
                break
            entity, expected_row = expected
            try:
                item = json.loads(line)
                actual_entity, actual_row = item["entity"], item["row"]
            except (ValueError, KeyError, TypeError) as exc:
                mismatches += 1
                first_errors.append(f"row {idx}: invalid JSONL: {exc}")
                break
            counter[entity] += 1
            errors = [] if entity == actual_entity else [
                f"entity: Python={entity}, Rust={actual_entity}"
            ]
            errors += same_values(expected_row, actual_row, tolerance=tolerance)
            if errors:
                mismatches += 1
                if len(first_errors) < 10:
                    first_errors.append(f"row {idx} {entity}: " + "; ".join(errors))
        if mismatches:
            process.kill()
        exit_code = process.wait(timeout=120)
        for error in first_errors:
            print("FAIL", error)
        for entity, count in sorted(counter.items()):
            print(f"{entity}: {count} rows compared")
        if mismatches or exit_code != 0:
            print(f"FAIL: {mismatches} mismatched rows, Rust exit={exit_code}")
            return 1
        print(f"PASS: {sum(counter.values())} logical rows match Python GENESIS v3")
        return 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("examples/atlas.demo.json"))
    parser.add_argument("--students", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--start-year", type=int, default=2020)
    parser.add_argument("--schools", type=int, default=2)
    parser.add_argument("--classes-per-grade", type=int, default=3)
    parser.add_argument("--float-tolerance", type=float, default=1e-10)
    args = parser.parse_args()
    return compare(
        catalog_path=args.catalog, students=args.students, seed=args.seed,
        start_year=args.start_year, schools=args.schools,
        classes_per_grade=args.classes_per_grade,
        tolerance=args.float_tolerance,
    )


if __name__ == "__main__":
    raise SystemExit(main())
