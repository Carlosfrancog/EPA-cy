"""Synthetic-only protocol A/B/C split guardrails for EPIC #77."""
import pytest
from epa.core_engine.mapa_validation_protocols import plan_splits, SCHEMA


def sample():
    rows = []
    for name in ("SYN0001", "SYN0002", "SYN0003", "SYN0004"):
        for year in (2020, 2021, 2022):
            rows.append({"student_id": name, "academic_year": year,
                         "label_available_year": year, "data_classification": "SYNTHETIC"})
    return rows


def test_grouped_folds_isolate_students_without_temporal_claim():
    rows = sample()
    a = plan_splits(rows, protocol="A_grouped", folds=2)
    assert a["schema_version"] == SCHEMA
    assert len(a["folds"]) == 2
    assert all(f["overlapping_students"] == 0 for f in a["folds"])
    assert sum(len(f["test_indices"]) for f in a["folds"]) == len(rows)
    assert "NOT out-of-time" in a["caveat"]
    assert a == plan_splits(rows, protocol="A_grouped", folds=2)


def test_temporal_b_allows_reused_students_but_not_future_training():
    rows = sample()
    rows[0]["label_available_year"] = 2022  # training label from 2020 not yet available in 2022
    b = plan_splits(rows, protocol="B_out_of_time", test_year=2022)
    fold = b["folds"][0]
    assert 0 not in fold["train_indices"]
    assert fold["overlapping_students"] == 4
    assert fold["train_years"] == [2020, 2021]
    assert fold["test_years"] == [2022]
    assert fold["training_labels_available_before_test_year"] is True


def test_temporal_c_skips_if_same_students_recur():
    out = plan_splits(sample(), protocol="C_unseen_future", test_year=2022)
    assert out["status"] == "not_identifiable"
    assert out["reason"] == "no_unseen_future_students"


def test_temporal_c_selects_only_new_students():
    rows = sample()
    rows.append({"student_id": "SYNNEW", "academic_year": 2022,
                 "label_available_year": 2022, "data_classification": "SYNTHETIC"})
    c = plan_splits(rows, protocol="C_unseen_future", test_year=2022)
    fold = c["folds"][0]
    assert fold["overlapping_students"] == 0
    assert fold["test_indices"] == [len(rows) - 1]
    assert fold["test_students"] == 1


def test_reject_real_data_and_missing_label_timestamp():
    rows = sample()
    rows[0]["data_classification"] = "REAL"
    with pytest.raises(ValueError, match="synthetic"):
        plan_splits(rows, protocol="A_grouped")
    rows = sample()
    del rows[0]["label_available_year"]
    with pytest.raises(ValueError, match="missing"):
        plan_splits(rows, protocol="B_out_of_time", test_year=2022)


def test_reject_ambiguous_temporal_config_and_small_group_count():
    with pytest.raises(ValueError, match="test_year"):
        plan_splits(sample(), protocol="B_out_of_time")
    with pytest.raises(ValueError, match="insufficient students"):
        plan_splits(sample(), protocol="A_grouped", folds=5)
    with pytest.raises(ValueError, match="unknown"):
        plan_splits(sample(), protocol="bad")


def test_temporal_with_no_training_labels_returns_explicit_skip():
    rows = [{"student_id": "SYN0001", "academic_year": 2021,
             "label_available_year": 2022, "data_classification": "SYNTHETIC"},
            {"student_id": "SYN0002", "academic_year": 2022,
             "label_available_year": 2022, "data_classification": "SYNTHETIC"}]
    b = plan_splits(rows, protocol="B_out_of_time", test_year=2022)
    assert b["status"] == "not_identifiable"
    assert b["reason"] == "insufficient_eligible_training_rows"