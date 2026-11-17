"""EPIC77 regression tests for training on A/B/C partitions (synthetic fixtures)."""
import pytest
from epa.core_engine.mapa_protocol_runner import evaluate, _rows_for_planning, AVAILABILITY
from epa.core_engine.mapa_validation_protocols import plan_splits


def synthetic_snapshots():
    # Validate the training adapter without needing real students or private datasets.
    rows=[]
    for i in range(9):
        for year in (2020,2021,2022):
            rows.append({"student_id":f"SYN{i:03d}","academic_year":year,
                         "cutoff_term":3,"data_classification":"SYNTHETIC",
                         "target_final_subject_outcome":("approved" if i%2 else "recovery"),
                         "current":{"mean_grade":4+i/4,"attendance_rate":.9,
                                    "absences_total":2,"absences_unexcused":1,"scheduled_sessions":60},
                         "prior_same_subject":None,"prior_years_observed":0})
    return rows


def test_grouped_protocol_fits_three_classifiers_and_is_reproducible():
    rows=synthetic_snapshots()
    a=evaluate(rows,cutoff=3,protocol="A_grouped",folds=3,seed=12)
    assert a==evaluate(rows,cutoff=3,protocol="A_grouped",folds=3,seed=12)
    assert a["status"]=="evaluated" and len(a["folds"])==3
    assert len(a["models"])==3
    assert all(x["overlapping_students"]==0 for x in a["folds"])


def test_b_temporal_availability_excludes_2021_from_2022_training():
    rows=synthetic_snapshots()
    b=evaluate(rows,cutoff=3,protocol="B_out_of_time",test_year=2022)
    assert b["status"]=="evaluated"
    assert b["folds"][0]["train_years"]==[2020]
    assert b["folds"][0]["test_years"]==[2022]
    assert b["folds"][0]["overlapping_students"]==9
    assert b["availability_contract"]==AVAILABILITY


def test_c_same_cohort_is_explicitly_unavailable():
    r=evaluate(synthetic_snapshots(),cutoff=3,protocol="C_unseen_future",test_year=2022)
    assert r["status"]=="not_identifiable"
    assert r["split_reason"]=="no_unseen_future_students"
    assert not r["models"]


def test_c_new_future_student_is_evaluated():
    rows=synthetic_snapshots()
    other={**rows[0],"student_id":"SYNNEW","academic_year":2022}
    rows.append(other)
    c=evaluate(rows,cutoff=3,protocol="C_unseen_future",test_year=2022)
    assert c["status"]=="evaluated"
    assert c["folds"][0]["overlapping_students"]==0
    assert c["folds"][0]["test_students"]==1


def test_reject_inconsistent_cutoff_and_unknown_labels():
    rows=synthetic_snapshots()
    with pytest.raises(ValueError,match="cutoff"):
        evaluate(rows,cutoff=2,protocol="A_grouped")
    rows[0]["target_final_subject_outcome"]="leak"
    with pytest.raises(ValueError,match="labels"):
        evaluate(rows,cutoff=3,protocol="A_grouped")


def test_label_availability_not_inferred_as_current_year():
    rows=synthetic_snapshots()
    metadata=_rows_for_planning(rows)
    assert metadata[0]["label_available_year"]==2021
    assert metadata[0]["academic_year"]==2020
    assert all("target_final_subject_outcome" not in r for r in metadata)


def test_planner_does_not_treat_unlabeled_prior_student_as_new():
    # A seen student is never new even if its historical label was not available for fitting.
    rows=[{"student_id":"SYNOLD", "academic_year":2021,"label_available_year":2022,
           "data_classification":"SYNTHETIC"},
          {"student_id":"SYNTRAIN", "academic_year":2020,"label_available_year":2020,
           "data_classification":"SYNTHETIC"},
          {"student_id":"SYNOLD", "academic_year":2022,"label_available_year":2022,
           "data_classification":"SYNTHETIC"}]
    assert plan_splits(rows,protocol="C_unseen_future",test_year=2022)["status"]=="not_identifiable"

def test_optional_class_metrics_preserve_b_f1_and_temporal_partition():
    from epa.core_engine.mapa import CLASSES
    import numpy as np

    rows = synthetic_snapshots()
    old = evaluate(rows, cutoff=3, protocol="B_out_of_time", test_year=2022, seed=12)
    new = evaluate(rows, cutoff=3, protocol="B_out_of_time", test_year=2022,
                   seed=12, include_class_metrics=True)
    assert new["class_order"] == list(CLASSES)
    assert new["folds"][0]["train_indices_sha256"] == old["folds"][0]["train_indices_sha256"]
    assert new["folds"][0]["test_indices_sha256"] == old["folds"][0]["test_indices_sha256"]
    assert new["folds"][0]["train_years"] == [2020]
    assert new["folds"][0]["test_years"] == [2022]
    assert new["models"] == old["models"]
    assert "class_metrics_enabled" not in old
    for previous, current in zip(old["folds"][0]["model_scores"], new["folds"][0]["model_scores"]):
        assert previous["f1_macro"] == current["f1_macro"]
        assert previous["accuracy"] == current["accuracy"]
        assert set(current["recall_by_class"]) == set(CLASSES)
        cm = np.asarray(current["confusion_matrix"])
        assert cm.shape == (3, 3)
        assert cm.sum() == sum(current["class_support"].values())
        assert cm.sum(axis=1).tolist() == [current["class_support"][c] for c in CLASSES]
        assert np.allclose(np.diag(cm) / np.maximum(cm.sum(axis=1), 1),
                           [current["recall_by_class"][c] for c in CLASSES])


def test_optional_class_metrics_respect_protocol_c_not_identifiable():
    report = evaluate(synthetic_snapshots(), cutoff=3, protocol="C_unseen_future",
                      test_year=2022, include_class_metrics=True)
    assert report["status"] == "not_identifiable"
    assert report["folds"] == [] and report["models"] == []
    assert report["class_metrics_enabled"] is True
