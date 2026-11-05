"""GENESIS v3 prototype: bounded-memory, deterministic, immutable Parquet datasets.

Run: python -m epa.genesis.v3 --output data/datasets/demo-v3 --students 20000
Requires: pip install -e '.[streaming]' (PyArrow is imported lazily).

Rows and canonical data digests are independent of --batch-students. Parquet
file hashes are a separate physical integrity contract. Dataset v3 is NOT
silently interchangeable with the existing v2 MAPA reader.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import random
import shutil
import uuid
from pathlib import Path
from typing import Iterator

from epa.atlas.catalog import catalog_sha256, load_catalog
from epa.genesis.v2 import AREAS, PERIODS, bounded, stable_seed

SCHEMA_VERSION = "epa.genesis.dataset.v3"
ENTITY_NAMES = ("students", "classes", "enrollments", "subject_offerings", "period_records")


def _arrow_schemas(pa):
    s, i, f = pa.string(), pa.int32(), pa.float64()
    return {
        "students": pa.schema([("student_id", s), ("data_classification", s)]),
        "classes": pa.schema([("class_id", s), ("school_id", s), ("academic_year", i), ("grade_level", i)]),
        "enrollments": pa.schema([("enrollment_id", s), ("student_id", s), ("class_id", s),
                                  ("academic_year", i), ("grade_level", i), ("status", s)]),
        "subject_offerings": pa.schema([("offering_id", s), ("class_id", s),
                                        ("subject_id", s), ("knowledge_area", s)]),
        "period_records": pa.schema([("enrollment_id", s), ("student_id", s), ("class_id", s),
                                     ("academic_year", i), ("grade_level", i), ("subject_id", s),
                                     ("knowledge_area", s), ("term", i), ("assessment_grade", f),
                                     ("scheduled_sessions", i), ("present_sessions", i),
                                     ("absences_total", i), ("absences_excused", i),
                                     ("absences_unexcused", i), ("attendance_rate", f),
                                     ("data_classification", s)]),
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ParquetRows:
    """Append row groups within one open ParquetWriter; never load whole dataset."""

    def __init__(self, path: Path, schema, *, row_group_rows: int):
        import pyarrow.parquet as pq
        self.path, self.schema = path, schema
        self.row_group_rows = row_group_rows
        self.writer = pq.ParquetWriter(str(path), schema, compression="zstd")
        self.buffer: list[dict] = []
        self.count = 0
        self.canonical = hashlib.sha256()
        self.closed = False

    def add(self, row: dict) -> None:
        if self.closed:
            raise RuntimeError("writer already closed")
        if set(row) != set(self.schema.names):
            raise ValueError(f"unexpected columns in {self.path.name}")
        normalized = {col: row[col] for col in self.schema.names}
        # Logical identity independent of row-group and student-batch boundaries.
        self.canonical.update(json.dumps(normalized, ensure_ascii=False, separators=(",", ":"),
                                         allow_nan=False).encode("utf-8") + b"\n")
        self.buffer.append(normalized)
        self.count += 1
        if len(self.buffer) >= self.row_group_rows:
            self.flush()

    def flush(self) -> None:
        if self.buffer:
            import pyarrow as pa
            table = pa.Table.from_pylist(self.buffer, schema=self.schema)
            self.writer.write_table(table, row_group_size=self.row_group_rows)
            del table
            self.buffer.clear()

    def close(self) -> dict:
        if not self.closed:
            try:
                self.flush()
            finally:
                self.writer.close()
                self.closed = True
        return {"path": self.path.name, "row_count": self.count,
                "sha256": file_sha256(self.path), "logical_sha256": self.canonical.hexdigest()}

    def abort(self) -> None:
        if not self.closed:
            self.writer.close()
            self.closed = True


def school_rows(catalog: dict, *, start_year: int, classes_per_grade: int,
                school_count: int) -> Iterator[tuple[str, dict]]:
    grades = sorted(catalog["grades"], key=lambda g: g["grade_level"])
    for offset, grade in enumerate(grades):
        year, level = start_year + offset, grade["grade_level"]
        for school in range(1, school_count + 1):
            for section in range(1, classes_per_grade + 1):
                cid = f"C{year}-{level}-S{school:02d}-T{section:02d}"
                yield "classes", {"class_id": cid, "school_id": f"SCHOOL{school:03d}",
                                  "academic_year": year, "grade_level": level}
                for subject in grade["subjects"]:
                    yield "subject_offerings", {"offering_id": f"{cid}-{subject['id']}",
                                                "class_id": cid, "subject_id": subject["id"],
                                                "knowledge_area": subject["area"]}


def student_rows(catalog: dict, number: int, *, seed: int, start_year: int,
                 classes_per_grade: int, school_count: int) -> Iterator[tuple[str, dict]]:
    """Per-record RNG reproduces v2 values independently of chunk boundaries."""
    student = f"SYN{number:08d}"
    yield "students", {"student_id": student, "data_classification": "SYNTHETIC"}
    profile = random.Random(stable_seed(seed, student, "profile"))
    strengths = {area: profile.uniform(-1.65, 1.65) for area in AREAS}
    baseline, trend = profile.uniform(-0.7, 0.7), profile.uniform(-0.27, 0.27)
    attendance_propensity = profile.uniform(0.78, 0.985)
    grades = sorted(catalog["grades"], key=lambda g: g["grade_level"])
    for offset, grade in enumerate(grades):
        year, level = start_year + offset, grade["grade_level"]
        school = 1 + (number - 1) % school_count
        section = 1 + stable_seed(seed, student, year, "section") % classes_per_grade
        cid = f"C{year}-{level}-S{school:02d}-T{section:02d}"
        eid = f"{student}-{year}"
        yield "enrollments", {"enrollment_id": eid, "student_id": student, "class_id": cid,
                              "academic_year": year, "grade_level": level, "status": "ENROLLED"}
        for subject in grade["subjects"]:
            sid = subject["id"]
            bias = random.Random(stable_seed(seed, student, sid, "longitudinal")).uniform(-0.48, 0.48)
            for term in PERIODS:
                rng = random.Random(stable_seed(seed, student, year, sid, term))
                grade_score = round(bounded(6.1 + baseline + strengths[subject["area"]] + bias
                                            + trend * (offset + (term - 1) / 4)
                                            + rng.gauss(0, 0.95), 0, 10), 2)
                sessions = rng.randint(16, 25)
                probability = bounded(attendance_propensity + rng.gauss(0, 0.065)
                                      - max(0, 5.0 - grade_score) * 0.009, 0.30, 1.0)
                present = sum(rng.random() < probability for _ in range(sessions))
                absences = sessions - present
                excused = sum(rng.random() < 0.23 for _ in range(absences))
                yield "period_records", {
                    "enrollment_id": eid, "student_id": student, "class_id": cid,
                    "academic_year": year, "grade_level": level, "subject_id": sid,
                    "knowledge_area": subject["area"], "term": term,
                    "assessment_grade": grade_score, "scheduled_sessions": sessions,
                    "present_sessions": present, "absences_total": absences,
                    "absences_excused": excused, "absences_unexcused": absences - excused,
                    "attendance_rate": round(present / sessions, 6),
                    "data_classification": "SYNTHETIC",
                }


def generate(catalog_path: Path, destination: Path, *, students: int = 20_000,
             seed: int = 20261029, start_year: int = 2020,
             classes_per_grade: int = 3, school_count: int = 2,
             batch_students: int = 1000, row_group_rows: int = 4096) -> dict:
    if students < 1 or students > 99_999_999 or batch_students < 1 or row_group_rows < 1:
        raise ValueError("invalid students/batch/row group")
    if not 1 <= classes_per_grade <= 20 or not 1 <= school_count <= 20:
        raise ValueError("invalid school/class count")
    if not 2000 <= start_year <= 2100:
        raise ValueError("invalid academic start year")
    import pyarrow as pa  # optional extra, required only when this generator is run
    catalog = load_catalog(catalog_path)
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"immutable dataset already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = destination.parent / f".{destination.name}.tmp-{uuid.uuid4().hex}"
    stage.mkdir()
    writers: dict[str, ParquetRows] = {}
    try:
        writers = {entity: ParquetRows(stage / f"{entity}.parquet", schema,
                                       row_group_rows=row_group_rows)
                   for entity, schema in _arrow_schemas(pa).items()}
        for name, row in school_rows(catalog, start_year=start_year,
                                     classes_per_grade=classes_per_grade, school_count=school_count):
            writers[name].add(row)
        for first in range(1, students + 1, batch_students):
            for number in range(first, min(first + batch_students, students + 1)):
                for name, row in student_rows(catalog, number, seed=seed, start_year=start_year,
                                              classes_per_grade=classes_per_grade,
                                              school_count=school_count):
                    writers[name].add(row)
            # No per-batch accumulation; buffers stay bounded by row_group_rows.
            gc.collect()
        artifacts = {name: writer.close() for name, writer in writers.items()}
        grades = catalog["grades"]
        subjects_per_student = sum(len(g["subjects"]) for g in grades)
        expected = {"students": students, "classes": len(grades) * school_count * classes_per_grade,
                    "enrollments": students * len(grades),
                    "subject_offerings": subjects_per_student * school_count * classes_per_grade,
                    "period_records": students * subjects_per_student * len(PERIODS)}
        if any(artifacts[k]["row_count"] != n for k, n in expected.items()):
            raise AssertionError("inconsistent entity row counts")
        manifest = {"schema_version": SCHEMA_VERSION, "classification": "SYNTHETIC",
                    "generator_seed": seed, "catalog_sha256": catalog_sha256(catalog_path),
                    "students": students, "start_year": start_year,
                    "classes_per_grade": classes_per_grade, "school_count": school_count,
                    "batch_students": batch_students, "row_group_rows": row_group_rows,
                    "terms_per_year": len(PERIODS), "artifacts": artifacts,
                    "scope": "synthetic research only; no empirical model validation"}
        (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False,
                                                      indent=2) + "\n", encoding="utf-8")
        # Atomic directory publish on the same filesystem; never overwrite.
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"dataset was concurrently published: {destination}")
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
    parser = argparse.ArgumentParser(description="EPA GENESIS v3 incremental Parquet prototype")
    parser.add_argument("--catalog", type=Path, default=Path("examples/atlas.demo.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--students", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--start-year", type=int, default=2020)
    parser.add_argument("--classes-per-grade", type=int, default=3)
    parser.add_argument("--schools", type=int, default=2)
    parser.add_argument("--batch-students", type=int, default=1000)
    parser.add_argument("--row-group-rows", type=int, default=4096)
    args = parser.parse_args()
    print(json.dumps(generate(args.catalog, args.output, students=args.students,
                              seed=args.seed, start_year=args.start_year,
                              classes_per_grade=args.classes_per_grade, school_count=args.schools,
                              batch_students=args.batch_students,
                              row_group_rows=args.row_group_rows), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
