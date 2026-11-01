"""GENESIS v2: reproducible SYNTHETIC student timelines (not empirical evidence).

Separate from v1 so the existing Rails laboratory remains compatible.
Grain: student × enrollment/academic year × offered subject × term.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from epa.atlas.catalog import catalog_sha256, load_catalog

SCHEMA = "epa.genesis.dataset.v2"
PERIODS = (1, 2, 3, 4)
AREAS = ("MATEMATICA", "LINGUAGENS", "NATUREZA", "HUMANAS")


def stable_seed(*parts: object) -> int:
    return int.from_bytes(hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).digest()[:8], "big")


def bounded(value: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, value))


def build_dataset(catalog: dict, *, students: int, seed: int, start_year: int,
                  classes_per_grade: int = 3, school_count: int = 2) -> dict[str, list[dict]]:
    if not 1 <= students <= 2000:
        raise ValueError("v2 MVP supports 1..2000 students")
    if not 1 <= classes_per_grade <= 20 or not 1 <= school_count <= 20:
        raise ValueError("invalid school/class count")
    if not 2000 <= start_year <= 2100:
        raise ValueError("invalid academic start year")
    grades = sorted(catalog["grades"], key=lambda g: g["grade_level"])
    data: dict[str, list[dict]] = {
        "students": [], "classes": [], "enrollments": [],
        "subject_offerings": [], "period_records": [],
    }
    for index, grade in enumerate(grades):
        year = start_year + index
        level = grade["grade_level"]
        for school in range(1, school_count + 1):
            for section in range(1, classes_per_grade + 1):
                class_id = f"C{year}-{level}-S{school:02d}-T{section:02d}"
                data["classes"].append({
                    "class_id": class_id, "school_id": f"SCHOOL{school:03d}",
                    "academic_year": year, "grade_level": level,
                })
                for subject in grade["subjects"]:
                    data["subject_offerings"].append({
                        "offering_id": f"{class_id}-{subject['id']}",
                        "class_id": class_id, "subject_id": subject["id"],
                        "knowledge_area": subject["area"],
                    })

    for number in range(1, students + 1):
        student = f"SYN{number:08d}"
        data["students"].append({"student_id": student, "data_classification": "SYNTHETIC"})
        person_rng = random.Random(stable_seed(seed, student, "profile"))
        strengths = {area: person_rng.uniform(-1.65, 1.65) for area in AREAS}
        baseline = person_rng.uniform(-0.7, 0.7)
        trend = person_rng.uniform(-0.27, 0.27)
        attendance_propensity = person_rng.uniform(0.78, 0.985)
        for year_index, grade in enumerate(grades):
            year = start_year + year_index
            level = grade["grade_level"]
            # Stable cohort association, with deterministic occasional class changes.
            school = 1 + (number - 1) % school_count
            section = 1 + (stable_seed(seed, student, year, "section") % classes_per_grade)
            class_id = f"C{year}-{level}-S{school:02d}-T{section:02d}"
            enrollment_id = f"{student}-{year}"
            data["enrollments"].append({
                "enrollment_id": enrollment_id, "student_id": student,
                "class_id": class_id, "academic_year": year,
                "grade_level": level, "status": "ENROLLED",
            })
            for subject in grade["subjects"]:
                subject_id = subject["id"]
                subject_rng = random.Random(stable_seed(seed, student, subject_id, "longitudinal"))
                subject_bias = subject_rng.uniform(-0.48, 0.48)
                for term in PERIODS:
                    rng = random.Random(stable_seed(seed, student, year, subject_id, term))
                    score = round(bounded(
                        6.1 + baseline + strengths[subject["area"]] + subject_bias
                        + trend * (year_index + (term - 1) / 4)
                        + rng.gauss(0, 0.95), 0, 10,
                    ), 2)
                    sessions = rng.randint(16, 25)
                    # Distinct per-subject/per-term attendance, but correlated within student.
                    probability = bounded(
                        attendance_propensity + rng.gauss(0, 0.065)
                        - max(0, 5.0 - score) * 0.009, 0.30, 1.0,
                    )
                    present = sum(rng.random() < probability for _ in range(sessions))
                    absences = sessions - present
                    excused = sum(rng.random() < 0.23 for _ in range(absences))
                    data["period_records"].append({
                        "enrollment_id": enrollment_id, "student_id": student,
                        "class_id": class_id, "academic_year": year,
                        "grade_level": level, "subject_id": subject_id,
                        "knowledge_area": subject["area"], "term": term,
                        "assessment_grade": score, "scheduled_sessions": sessions,
                        "present_sessions": present, "absences_total": absences,
                        "absences_excused": excused,
                        "absences_unexcused": absences - excused,
                        "attendance_rate": round(present / sessions, 6),
                        "data_classification": "SYNTHETIC",
                    })
    validate_dataset(data)
    return data


def validate_dataset(data: dict[str, list[dict]]) -> None:
    students = {row["student_id"] for row in data["students"]}
    classes = {row["class_id"] for row in data["classes"]}
    offerings = {(row["class_id"], row["subject_id"]) for row in data["subject_offerings"]}
    enrollments = {row["enrollment_id"]: row for row in data["enrollments"]}
    if len(students) != len(data["students"]) or len(classes) != len(data["classes"]):
        raise ValueError("duplicate student or class")
    if len(offerings) != len(data["subject_offerings"]):
        raise ValueError("duplicate offering")
    if len(enrollments) != len(data["enrollments"]):
        raise ValueError("duplicate enrollment")
    if any(e["student_id"] not in students or e["class_id"] not in classes for e in enrollments.values()):
        raise ValueError("dangling enrollment")
    seen = set()
    for row in data["period_records"]:
        key = (row["enrollment_id"], row["subject_id"], row["term"])
        enrollment = enrollments.get(row["enrollment_id"])
        if key in seen or enrollment is None:
            raise ValueError("duplicate period or unknown enrollment")
        seen.add(key)
        if (row["class_id"], row["subject_id"]) not in offerings:
            raise ValueError("subject is not offered in class")
        if any(row[col] != enrollment[col] for col in ("student_id", "class_id", "academic_year", "grade_level")):
            raise ValueError("period/enrollment mismatch")
        if row["term"] not in PERIODS or not 0 <= row["assessment_grade"] <= 10:
            raise ValueError("invalid assessment")
        if not (row["scheduled_sessions"] > 0
                and row["scheduled_sessions"] == row["present_sessions"] + row["absences_total"]
                and row["absences_total"] == row["absences_excused"] + row["absences_unexcused"]):
            raise ValueError("incoherent attendance")
        if abs(row["attendance_rate"] - row["present_sessions"] / row["scheduled_sessions"]) > 1e-6:
            raise ValueError("incoherent attendance rate")
    expected = {
        (enrollment["enrollment_id"], subject_id, term)
        for enrollment in data["enrollments"]
        for class_id, subject_id in offerings if class_id == enrollment["class_id"]
        for term in PERIODS
    }
    if expected != seen:
        raise ValueError("missing periods for enrolled subjects")


def write_dataset(data: dict[str, list[dict]], destination: Path, *, seed: int, catalog_digest: str) -> dict:
    import duckdb
    if destination.exists():
        raise FileExistsError("immutable output directory already exists")
    validate_dataset(data)
    destination.mkdir(parents=True)
    db = duckdb.connect(":memory:")
    artifacts = {}
    try:
        for name, rows in data.items():
            columns = list(rows[0]) if rows else []
            if not columns:
                raise ValueError(f"empty data entity: {name}")
            # All fields are simple scalar values with explicit type mapping.
            type_of = lambda v: ("INTEGER" if isinstance(v, int) else "DOUBLE" if isinstance(v, float) else "VARCHAR")
            declaration = ", ".join(f'"{col}" {type_of(rows[0][col])}' for col in columns)
            db.execute(f'CREATE TABLE "{name}" ({declaration})')
            placeholders = ", ".join("?" for _ in columns)
            db.executemany(f'INSERT INTO "{name}" VALUES ({placeholders})',
                           [tuple(row[column] for column in columns) for row in rows])
            path = destination / f"{name}.parquet"
            db.execute(f'COPY "{name}" TO ? (FORMAT PARQUET)', [str(path)])
            artifacts[name] = {
                "path": path.name, "row_count": len(rows),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    finally:
        db.close()
    manifest = {
        "schema_version": SCHEMA, "classification": "SYNTHETIC",
        "generator_seed": seed, "catalog_sha256": catalog_digest,
        "artifacts": artifacts, "terms_per_year": len(PERIODS),
        "scope": "synthetic research engineering; no empirical validity",
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a synthetic GENESIS v2 student timeline")
    parser.add_argument("--catalog", type=Path, default=Path("examples/atlas.demo.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--students", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--start-year", type=int, default=2020)
    parser.add_argument("--classes-per-grade", type=int, default=3)
    parser.add_argument("--schools", type=int, default=2)
    args = parser.parse_args()
    catalog = load_catalog(args.catalog)
    data = build_dataset(catalog, students=args.students, seed=args.seed,
                         start_year=args.start_year,
                         classes_per_grade=args.classes_per_grade, school_count=args.schools)
    print(json.dumps(write_dataset(data, args.output, seed=args.seed,
                                   catalog_digest=catalog_sha256(args.catalog)),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
