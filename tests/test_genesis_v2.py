import hashlib
import json
from pathlib import Path

import pytest

from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset, validate_dataset, write_dataset

CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"


@pytest.fixture(scope="module")
def dataset():
    return build_dataset(load_catalog(CATALOG), students=12, seed=42,
                         start_year=2020, classes_per_grade=3, school_count=2)


def test_longitudinal_history_and_classes(dataset):
    enrollments = [r for r in dataset["enrollments"] if r["student_id"] == "SYN00000001"]
    assert len(enrollments) == 7
    assert [r["grade_level"] for r in enrollments] == list(range(6, 13))
    assert len({r["class_id"] for r in enrollments}) >= 2
    history = [r for r in dataset["period_records"]
               if r["student_id"] == "SYN00000001" and r["subject_id"] == "HIS"]
    assert len(history) == 7 * 4
    assert {(r["grade_level"], r["term"]) for r in history} == {
        (level, term) for level in range(6, 13) for term in range(1, 5)
    }


def test_all_offered_subjects_have_four_periods(dataset):
    offered = {(r["class_id"], r["subject_id"]) for r in dataset["subject_offerings"]}
    for enrollment in dataset["enrollments"]:
        subjects = {subject for class_id, subject in offered if class_id == enrollment["class_id"]}
        observed = {(r["subject_id"], r["term"]) for r in dataset["period_records"]
                    if r["enrollment_id"] == enrollment["enrollment_id"]}
        assert observed == {(s, t) for s in subjects for t in range(1, 5)}


def test_attendance_reconciles_for_every_term_and_all_years(dataset):
    for row in dataset["period_records"]:
        assert row["scheduled_sessions"] == row["present_sessions"] + row["absences_total"]
        assert row["absences_total"] == row["absences_excused"] + row["absences_unexcused"]
        assert abs(row["attendance_rate"] - row["present_sessions"] / row["scheduled_sessions"]) < 1e-6


def test_generator_is_deterministic_and_seed_sensitive(dataset):
    catalog = load_catalog(CATALOG)
    assert build_dataset(catalog, students=12, seed=42, start_year=2020,
                         classes_per_grade=3, school_count=2) == dataset
    other = build_dataset(catalog, students=12, seed=43, start_year=2020)
    assert other["period_records"] != dataset["period_records"]


def test_corrupt_attendance_is_rejected(dataset):
    rows = {name: [dict(r) for r in values] for name, values in dataset.items()}
    rows["period_records"][0]["absences_total"] += 1
    with pytest.raises(ValueError, match="incoherent attendance"):
        validate_dataset(rows)


def test_v2_parquet_and_immutable_manifest(tmp_path, dataset):
    duckdb = pytest.importorskip("duckdb")
    dest = tmp_path / "v2"
    manifest = write_dataset(dataset, dest, seed=42, catalog_digest="a" * 64)
    assert manifest["schema_version"] == "epa.genesis.dataset.v2"
    assert set(manifest["artifacts"]) == set(dataset)
    for entity, artifact in manifest["artifacts"].items():
        file = dest / artifact["path"]
        assert artifact["sha256"] == hashlib.sha256(file.read_bytes()).hexdigest()
        assert duckdb.sql(f"SELECT count(*) FROM read_parquet('{file}')").fetchone()[0] == len(dataset[entity])
    assert json.loads((dest / "manifest.json").read_text()) == manifest
    with pytest.raises(FileExistsError):
        write_dataset(dataset, dest, seed=42, catalog_digest="a" * 64)
