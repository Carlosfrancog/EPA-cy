"""Streaming SQL audit for GENESIS native Rust Parquet datasets.

Never materializes full tables in Python. Counts defects, verifies file hashes,
and reports aggregate distributions. Does not establish Python row parity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import duckdb

ENTITIES = ("students", "classes", "enrollments", "subject_offerings", "period_records")
SCHEMA = "epa.genesis.parquet_deep_audit.v1"


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def quoted_path(path: Path) -> str:
    return "'" + str(path.resolve()).replace("'", "''") + "'"


def audit(directory: Path, *, memory_limit: str = "512MB", threads: int = 2) -> dict:
    directory = Path(directory)
    if not (1 <= threads <= 32):
        raise ValueError("threads must be 1..32")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("classification") != "SYNTHETIC":
        raise ValueError("only SYNTHETIC data supported")
    if manifest.get("schema_version") != "epa.genesis.dataset.rust_native.v1":
        raise ValueError("unsupported manifest schema")
    if not isinstance(manifest.get("students"), int) or manifest["students"] < 1:
        raise ValueError("invalid students in manifest")
    if not re.fullmatch(r"[1-9][0-9]*(?:KB|MB|GB)", memory_limit, re.IGNORECASE):
        raise ValueError("memory_limit must be a positive integer with KB/MB/GB unit")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(ENTITIES):
        raise ValueError("incomplete artifacts")
    integrity = {}
    for entity in ENTITIES:
        info = artifacts[entity]
        if info.get("path") != f"{entity}.parquet":
            raise ValueError(f"unexpected path for {entity}")
        path = directory / info["path"]
        actual_hash = digest_file(path)
        if actual_hash != info.get("sha256"):
            raise ValueError(f"sha256 mismatch: {entity}")
        integrity[entity] = {"sha256_verified": True, "bytes": path.stat().st_size}

    db = duckdb.connect(":memory:")
    try:
        db.execute(f"SET threads = {threads}")
        # DuckDB validates the memory-limit string itself.
        db.execute(f"SET memory_limit = '{memory_limit}'")
        for entity in ENTITIES:
            db.execute(
                f"CREATE VIEW {entity} AS SELECT * FROM read_parquet({quoted_path(directory / (entity + '.parquet'))})"
            )

        def number(query: str) -> int:
            return int(db.execute(query).fetchone()[0])

        def metrics(query: str, names: tuple[str, ...]) -> dict:
            return dict(zip(names, db.execute(query).fetchone()))

        checks = {}
        def check(name: str, query: str) -> None:
            checks[name] = number(query)

        counts = {entity: number(f"SELECT count(*) FROM {entity}") for entity in ENTITIES}
        for entity in ENTITIES:
            if counts[entity] != artifacts[entity].get("row_count"):
                raise ValueError(f"manifest row_count mismatch: {entity}")

        check("duplicate_students", "SELECT count(*) - count(DISTINCT student_id) FROM students")
        check("duplicate_classes", "SELECT count(*) - count(DISTINCT class_id) FROM classes")
        check("duplicate_enrollments", "SELECT count(*) - count(DISTINCT enrollment_id) FROM enrollments")
        check("duplicate_offerings", "SELECT count(*) - count(DISTINCT offering_id) FROM subject_offerings")
        check("duplicate_period_keys", """SELECT count(*) FROM (
            SELECT enrollment_id, subject_id, term
            FROM period_records GROUP BY 1,2,3 HAVING count(*) > 1
        )""")
        check("missing_enrollment_students", """SELECT count(*) FROM enrollments e
            ANTI JOIN students s ON e.student_id=s.student_id""")
        check("missing_enrollment_classes", """SELECT count(*) FROM enrollments e
            ANTI JOIN classes c ON e.class_id=c.class_id""")
        check("missing_offering_classes", """SELECT count(*) FROM subject_offerings o
            ANTI JOIN classes c ON o.class_id=c.class_id""")
        check("missing_period_enrollments", """SELECT count(*) FROM period_records p
            ANTI JOIN enrollments e ON p.enrollment_id=e.enrollment_id""")
        check("missing_period_offerings", """SELECT count(*) FROM period_records p
            ANTI JOIN subject_offerings o
            ON p.class_id=o.class_id AND p.subject_id=o.subject_id""")
        check("inconsistent_enrollment_student_class_year_grade", """SELECT count(*) FROM period_records p
            JOIN enrollments e ON p.enrollment_id=e.enrollment_id
            WHERE p.student_id != e.student_id OR p.class_id != e.class_id
              OR p.academic_year != e.academic_year OR p.grade_level != e.grade_level""")
        check("inconsistent_class_year_grade", """SELECT count(*) FROM enrollments e
            JOIN classes c ON e.class_id=c.class_id
            WHERE e.academic_year != c.academic_year OR e.grade_level != c.grade_level""")
        check("inconsistent_offering_area", """SELECT count(*) FROM period_records p
            JOIN subject_offerings o ON p.class_id=o.class_id AND p.subject_id=o.subject_id
            WHERE p.knowledge_area != o.knowledge_area""")
        check("invalid_period_values", """SELECT count(*) FROM period_records WHERE
            term NOT BETWEEN 1 AND 4
            OR assessment_grade IS NULL OR NOT isfinite(assessment_grade)
            OR assessment_grade NOT BETWEEN 0 AND 10
            OR scheduled_sessions IS NULL OR scheduled_sessions <= 0
            OR present_sessions IS NULL OR present_sessions < 0 OR present_sessions > scheduled_sessions
            OR absences_total IS NULL OR absences_total != scheduled_sessions-present_sessions
            OR absences_excused IS NULL OR absences_excused < 0 OR absences_excused > absences_total
            OR absences_unexcused IS NULL OR absences_unexcused != absences_total-absences_excused
            OR attendance_rate IS NULL OR NOT isfinite(attendance_rate)
            OR abs(attendance_rate - round(present_sessions::DOUBLE/scheduled_sessions,6)) > 0.000001
            OR data_classification IS NULL OR data_classification != 'SYNTHETIC'""")
        check("invalid_student_classification", """SELECT count(*) FROM students
            WHERE data_classification IS NULL OR data_classification != 'SYNTHETIC'""")
        check("null_primary_keys", """SELECT
            (SELECT count(*) FROM students WHERE student_id IS NULL) +
            (SELECT count(*) FROM classes WHERE class_id IS NULL) +
            (SELECT count(*) FROM enrollments WHERE enrollment_id IS NULL) +
            (SELECT count(*) FROM subject_offerings WHERE offering_id IS NULL) +
            (SELECT count(*) FROM period_records WHERE enrollment_id IS NULL OR subject_id IS NULL OR term IS NULL)""")

        distribution = metrics("""SELECT
            min(assessment_grade), max(assessment_grade), avg(assessment_grade),
            min(attendance_rate), max(attendance_rate), avg(attendance_rate),
            count(DISTINCT student_id), count(DISTINCT subject_id),
            count(DISTINCT academic_year)
            FROM period_records""", (
                "grade_min", "grade_max", "grade_mean",
                "attendance_min", "attendance_max", "attendance_mean",
                "unique_students", "unique_subjects", "unique_years"))
        distribution["term_counts"] = {
            str(term): int(n) for term, n in db.execute(
                "SELECT term, count(*) FROM period_records GROUP BY term ORDER BY term").fetchall()
        }
        distribution["by_knowledge_area"] = {
            str(area): int(n) for area, n in db.execute(
                "SELECT knowledge_area, count(*) FROM period_records GROUP BY 1 ORDER BY 1").fetchall()
        }

        expected_students = manifest.get("students")
        if counts["students"] != expected_students:
            checks["student_count_vs_manifest"] = abs(counts["students"] - expected_students)
        else:
            checks["student_count_vs_manifest"] = 0

        return {
            "schema_version": SCHEMA,
            "classification": "SYNTHETIC",
            "source_catalog_sha256": manifest.get("catalog_sha256"),
            "seed": manifest.get("generator_seed"),
            "students": expected_students,
            "counts": counts,
            "integrity": integrity,
            "checks": checks,
            "distribution": distribution,
            "status": "PASS" if all(value == 0 for value in checks.values()) else "FAIL",
            "limitations": [
                "Full SQL integrity checks and aggregate distributions; not Python v3 row parity.",
                "Single synthetic population; no evidence of predictive validity in real schools.",
                "No guarantee of bounded DuckDB peak RSS beyond configured memory limit.",
            ],
        }
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--memory-limit", default="512MB")
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    report = audit(args.dataset, memory_limit=args.memory_limit, threads=args.threads)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"{report['status']}: audit saved to {args.output}")
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
