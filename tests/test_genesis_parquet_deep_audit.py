"""Tiny DuckDB Parquet fixture verifies the GENESIS deep audit catches defects."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from epa.genesis.parquet_deep_audit import ENTITIES, audit


def _file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(path: Path, *, bad_attendance: bool = False):
    path.mkdir()
    db = duckdb.connect(":memory:")
    try:
        grade = 0.8 if bad_attendance else 0.9
        statements = {
            "students": """SELECT 'SYN00000001'::VARCHAR AS student_id,
                'SYNTHETIC'::VARCHAR AS data_classification""",
            "classes": """SELECT 'C2020-6-S01-T01'::VARCHAR AS class_id,
                'SCHOOL001'::VARCHAR AS school_id,
                2020::INTEGER AS academic_year, 6::INTEGER AS grade_level""",
            "enrollments": """SELECT 'SYN00000001-2020'::VARCHAR AS enrollment_id,
                'SYN00000001'::VARCHAR AS student_id,
                'C2020-6-S01-T01'::VARCHAR AS class_id, 2020::INTEGER AS academic_year,
                6::INTEGER AS grade_level, 'ENROLLED'::VARCHAR AS status""",
            "subject_offerings": """SELECT 'C2020-6-S01-T01-MAT'::VARCHAR AS offering_id,
                'C2020-6-S01-T01'::VARCHAR AS class_id,
                'MAT'::VARCHAR AS subject_id,
                'MATEMATICA'::VARCHAR AS knowledge_area""",
            "period_records": f"""SELECT 'SYN00000001-2020'::VARCHAR AS enrollment_id,
                'SYN00000001'::VARCHAR AS student_id,
                'C2020-6-S01-T01'::VARCHAR AS class_id,
                2020::INTEGER AS academic_year, 6::INTEGER AS grade_level,
                'MAT'::VARCHAR AS subject_id, 'MATEMATICA'::VARCHAR AS knowledge_area,
                1::INTEGER AS term, 7.5::DOUBLE AS assessment_grade,
                20::INTEGER AS scheduled_sessions, 18::INTEGER AS present_sessions,
                2::INTEGER AS absences_total, 1::INTEGER AS absences_excused,
                1::INTEGER AS absences_unexcused, {grade}::DOUBLE AS attendance_rate,
                'SYNTHETIC'::VARCHAR AS data_classification""",
        }
        artifacts = {}
        for name in ENTITIES:
            file = path / f"{name}.parquet"
            db.execute(f"COPY ({statements[name]}) TO '{str(file).replace(chr(39), chr(39) * 2)}' (FORMAT PARQUET)")
            artifacts[name] = {"path": file.name, "row_count": 1, "sha256": _file_sha(file)}
    finally:
        db.close()
    (path / "manifest.json").write_text(json.dumps({
        "schema_version": "epa.genesis.dataset.rust_native.v1",
        "classification": "SYNTHETIC",
        "generator_seed": 1, "students": 1,
        "catalog_sha256": "example-catalog-hash", "artifacts": artifacts,
    }), encoding="utf-8")
    return path


def test_deep_audit_accepts_valid_minimal_dataset(tmp_path):
    report = audit(_fixture(tmp_path / "valid"))
    assert report["status"] == "PASS"
    assert not any(report["checks"].values())
    assert report["counts"]["period_records"] == 1
    assert report["distribution"]["term_counts"] == {"1": 1}


def test_deep_audit_rejects_semantic_inconsistency_even_with_valid_hash(tmp_path):
    report = audit(_fixture(tmp_path / "bad", bad_attendance=True))
    assert report["status"] == "FAIL"
    assert report["checks"]["invalid_period_values"] == 1
    assert all(item["sha256_verified"] for item in report["integrity"].values())


def test_deep_audit_rejects_tampered_parquet(tmp_path):
    path = _fixture(tmp_path / "tampered")
    with (path / "students.parquet").open("ab") as f:
        f.write(b"tamper")
    with pytest.raises(ValueError, match="sha256 mismatch"):
        audit(path)


def test_deep_audit_rejects_unsafe_memory_limit(tmp_path):
    with pytest.raises(ValueError, match="memory_limit"):
        audit(_fixture(tmp_path / "bad-memory"), memory_limit="512MB'; DROP TABLE students;--")
