import copy
from pathlib import Path

import pytest

from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset, write_dataset
from epa.core_engine.student_timeline import build_snapshots
from epa.core_engine.mapa import CLASSES, FEATURES, evaluate, feature_vector, run

CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"


@pytest.fixture(scope="module")
def dataset():
    return build_dataset(load_catalog(CATALOG), students=48, seed=100, start_year=2020)


def test_features_exclude_target_and_student_identifiers(dataset):
    row = build_snapshots(dataset, cutoff=1)[0]
    assert len(FEATURES) == len(feature_vector(row))
    assert "target_final_subject_outcome" not in FEATURES
    assert "student_id" not in FEATURES


def test_no_future_period_affects_early_features(dataset):
    original = build_snapshots(dataset, cutoff=1)[0]
    changed = copy.deepcopy(dataset)
    for r in changed["period_records"]:
        if (r["enrollment_id"] == original["enrollment_id"]
                and r["subject_id"] == original["subject_id"] and r["term"] > 1):
            r["assessment_grade"] = 0.0
            r["present_sessions"] = 0
            r["absences_total"] = r["scheduled_sessions"]
            r["absences_excused"] = 0
            r["absences_unexcused"] = r["scheduled_sessions"]
            r["attendance_rate"] = 0.0
    later = next(s for s in build_snapshots(changed, cutoff=1)
                 if s["enrollment_id"] == original["enrollment_id"]
                 and s["subject_id"] == original["subject_id"])
    assert feature_vector(original) == feature_vector(later) or all(
        (a == b or (a != a and b != b)) for a, b in zip(
            feature_vector(original), feature_vector(later)))


def test_three_cutoffs_train_and_report_every_class(dataset):
    for cutoff in (1, 2, 3):
        report = evaluate(build_snapshots(dataset, cutoff=cutoff), cutoff=cutoff, seed=321)
        assert report["train_students"] + report["test_students"] == 48
        assert len(report["results"]) == 3
        assert set(report["train_class_counts"]) == set(CLASSES)
        assert sum(report["test_class_counts"].values()) == report["test_observations"]
        for model in report["results"]:
            assert len(model["confusion_matrix"]) == 3
            assert all(len(row) == 3 for row in model["confusion_matrix"])
            assert sum(map(sum, model["confusion_matrix"])) == report["test_observations"]
            assert 0 <= model["f1_macro"] <= 1


def test_deterministic_scores(dataset):
    s = build_snapshots(dataset, cutoff=2)
    assert evaluate(s, cutoff=2, seed=321) == evaluate(s, cutoff=2, seed=321)


def test_invalid_cutoff_and_too_few_students(dataset):
    with pytest.raises(ValueError, match="cutoff"):
        evaluate(build_snapshots(dataset, cutoff=1), cutoff=4)
    few = [s for s in build_snapshots(dataset, cutoff=1)
           if s["student_id"] in {"SYN00000001", "SYN00000002"}]
    with pytest.raises(ValueError, match="eight students"):
        evaluate(few, cutoff=1)


def test_full_manifest_checked_before_training(tmp_path, dataset):
    pytest.importorskip("duckdb")
    folder = tmp_path / "dataset"
    write_dataset(dataset, folder, seed=100, catalog_digest="a" * 64)
    report = run(folder, seed=321)
    assert report["schema_version"] == "epa.mapa.benchmark.v1"
    assert len(report["baselines"]) == 3
    assert report["dataset_classification"] == "SYNTHETIC"
    f = folder / "period_records.parquet"
    f.write_bytes(f.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="digest mismatch"):
        run(folder, seed=321)
