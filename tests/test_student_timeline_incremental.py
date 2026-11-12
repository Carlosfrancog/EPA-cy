"""Regression tests for the incremental, point-in-time MAPA timeline.

The reference intentionally keeps the original scanning algorithm to detect
changes in model features, labels or snapshot order during performance work.
"""
from collections import defaultdict
from pathlib import Path

import pytest

from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset
from epa.core_engine.student_timeline import _aggregate, build_snapshots


CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"


def reference_scan(data: dict, cutoff: int) -> list[dict]:
    grouped_student = defaultdict(list)
    grouped_enrollment = defaultdict(list)
    for row in data["period_records"]:
        grouped_student[(row["student_id"], row["subject_id"])].append(row)
        grouped_enrollment[(row["enrollment_id"], row["subject_id"])].append(row)

    result = []
    for (enrollment_id, subject_id), current in sorted(grouped_enrollment.items()):
        current.sort(key=lambda row: row["term"])
        ref = current[0]
        student_id = ref["student_id"]
        year = ref["academic_year"]
        previous = [
            row for row in grouped_student[(student_id, subject_id)]
            if row["academic_year"] < year
        ]
        available = [row for row in current if row["term"] <= cutoff]
        assert len(available) == cutoff
        current_metrics = _aggregate(available)
        prior_metrics = _aggregate(previous) if previous else None
        final_mean = sum(row["assessment_grade"] for row in current) / len(current)
        target = ("approved" if final_mean >= 6.0 else
                  "recovery" if final_mean >= 4.0 else "failed")
        result.append({
            "student_id": student_id, "enrollment_id": enrollment_id,
            "class_id": ref["class_id"], "academic_year": year,
            "grade_level": ref["grade_level"], "subject_id": subject_id,
            "cutoff_term": cutoff, "known_term_count": len(available),
            "current": current_metrics,
            "prior_same_subject": prior_metrics,
            "prior_years_observed": len({row["academic_year"] for row in previous}),
            "target_final_subject_outcome": target,
            "target_usage": "LABEL_ONLY_NOT_FEATURE",
            "data_classification": "SYNTHETIC",
        })
    return result


@pytest.mark.parametrize("seed", [1, 42, 20261029])
@pytest.mark.parametrize("students", [1, 7, 24])
@pytest.mark.parametrize("cutoff", [1, 2, 3])
def test_incremental_timeline_equals_original_scanning_algorithm(seed, students, cutoff):
    data = build_dataset(
        load_catalog(CATALOG), students=students, seed=seed, start_year=2020,
    )
    assert build_snapshots(data, cutoff=cutoff) == reference_scan(data, cutoff=cutoff)


def test_future_terms_cannot_change_earlier_features():
    data = build_dataset(load_catalog(CATALOG), students=7, seed=77, start_year=2020)
    snapshots = build_snapshots(data, cutoff=1)
    before = snapshots[0]
    for row in data["period_records"]:
        if row["enrollment_id"] == before["enrollment_id"] and row["subject_id"] == before["subject_id"] and row["term"] > 1:
            row["assessment_grade"] = 0
    after = next(
        row for row in build_snapshots(data, cutoff=1)
        if row["enrollment_id"] == before["enrollment_id"] and row["subject_id"] == before["subject_id"]
    )
    assert (after["current"], after["prior_same_subject"]) == (
        before["current"], before["prior_same_subject"]
    )
