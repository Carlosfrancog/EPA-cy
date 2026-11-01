import copy
import json
from pathlib import Path

import pytest
from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset, write_dataset
from epa.core_engine.student_timeline import (
    build_snapshots, read_verified_v2, run, student_profile,
)

CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"


@pytest.fixture(scope="module")
def dataset():
    return build_dataset(load_catalog(CATALOG), students=7, seed=42, start_year=2020)


def select(rows, student="SYN00000001", year=2021, subject="HIS"):
    return next(x for x in rows if x["student_id"] == student
                and x["academic_year"] == year and x["subject_id"] == subject)


def features(row):
    # Strictly exclude target and metadata when checking temporal invariance.
    return (row["current"], row["prior_same_subject"], row["prior_years_observed"])


def test_cutoffs_and_prior_subject_history(dataset):
    for cutoff in (1, 2, 3):
        row = select(build_snapshots(dataset, cutoff=cutoff))
        assert row["known_term_count"] == cutoff
        assert row["current"]["term_count"] == cutoff
        assert row["prior_same_subject"]["term_count"] == 4
        assert row["prior_years_observed"] == 1
        assert row["target_usage"] == "LABEL_ONLY_NOT_FEATURE"
    first = select(build_snapshots(dataset, cutoff=1), year=2020)
    assert first["prior_same_subject"] is None
    assert first["prior_years_observed"] == 0


def test_future_grades_and_absences_never_change_early_features(dataset):
    baseline = select(build_snapshots(dataset, cutoff=1))
    modified = copy.deepcopy(dataset)
    for row in modified["period_records"]:
        if (row["student_id"] == baseline["student_id"]
                and row["academic_year"] == baseline["academic_year"]
                and row["subject_id"] == baseline["subject_id"] and row["term"] > 1):
            row["assessment_grade"] = 0.0
            row["present_sessions"] = 0
            row["absences_total"] = row["scheduled_sessions"]
            row["absences_unexcused"] = row["scheduled_sessions"]
            row["absences_excused"] = 0
            row["attendance_rate"] = 0.0
    newer = select(build_snapshots(modified, cutoff=1))
    assert features(newer) == features(baseline)
    # The final outcome is a label, NOT a prediction input.
    assert "target_final_subject_outcome" not in newer["current"]


def test_future_year_never_enters_current_or_prior_features(dataset):
    baseline = select(build_snapshots(dataset, cutoff=2))
    modified = copy.deepcopy(dataset)
    for row in modified["period_records"]:
        if row["student_id"] == baseline["student_id"] and row["academic_year"] > 2021:
            row["assessment_grade"] = 0.0
    newer = select(build_snapshots(modified, cutoff=2))
    assert features(newer) == features(baseline)


def test_profile_tracks_grades_and_absences_without_future_terms(dataset):
    profile = student_profile(dataset, "SYN00000001", cutoff_year=2021, cutoff_term=2)
    assert len([r for r in profile["records"] if r["subject_id"] == "HIS"]) == 6
    assert all(r["academic_year"] < 2021 or r["term"] <= 2 for r in profile["records"])
    assert profile["overall"]["scheduled_sessions"] == (
        profile["overall"]["present_sessions"] + profile["overall"]["absences_total"]
    )
    with pytest.raises(ValueError, match="unknown student"):
        student_profile(dataset, "nonexistent", cutoff_year=2021, cutoff_term=2)


def test_parquet_manifest_digest_and_schema_protected(tmp_path, dataset):
    pytest.importorskip("duckdb")
    folder = tmp_path / "genesis-v2"
    write_dataset(dataset, folder, seed=42, catalog_digest="b" * 64)
    loaded = read_verified_v2(folder)
    assert len(loaded["period_records"]) == len(dataset["period_records"])
    report = run(folder, cutoff=1)
    assert report["prediction_cutoff_term"] == 1
    assert len(report["snapshots"]) > 0
    path = folder / "period_records.parquet"
    path.write_bytes(path.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="digest mismatch"):
        read_verified_v2(folder)


def test_rejects_invalid_cutoff(dataset):
    with pytest.raises(ValueError, match="cutoff"):
        build_snapshots(dataset, cutoff=4)
