"""EPIC #77 nested synthetic ML robustness, privacy and split invariants."""
import copy
import pytest
from epa.core_engine.mapa_robustness import evaluate, _model, SCHEMA


def snapshots(n_students=18, *, cutoff=1):
    out = []
    classes = ("approved", "recovery", "failed")
    for i in range(n_students):
        for j in range(3):
            label = classes[(i + j) % 3]
            base = {"approved": 7.4, "recovery": 5.1, "failed": 2.7}[label]
            out.append({"student_id": f"SYN{i:04d}", "academic_year": 2020+j,
                        "cutoff_term": cutoff, "data_classification": "SYNTHETIC",
                        "target_final_subject_outcome": label,
                        "current": {"mean_grade": base + i*.01, "attendance_rate": .75,
                                    "absences_total": 4, "absences_unexcused": 2,
                                    "scheduled_sessions": 20},
                        "prior_same_subject": {"mean_grade": base-.4, "attendance_rate": .8, "absences_total": 3, "absences_unexcused": 1, "term_count": 4}, "prior_years_observed": j})
    return out


def test_nested_model_selection_and_holdout_structure():
    report = evaluate(snapshots(), cutoff=1, seeds=(123,), inner_folds=2)
    assert report["schema_version"] == SCHEMA
    assert report["outer_split"].startswith("student_grouped")
    assert len(report["repetitions"]) == 1
    result = report["repetitions"][0]
    assert result["outer_train_students"] + result["outer_test_students"] == 18
    assert len(result["train_indices_sha256"]) == len(result["test_indices_sha256"]) == 64
    for model in result["models"]:
        assert model["outer_test_used_for_selection"] is False
        assert model["chosen_params"] in [trial["params"] for trial in model["inner_selection"]]
        assert model["shuffled_label_control"] == "permutation_of_outer_train_only"
        assert 0 <= model["heldout"]["f1_macro"] <= 1
    assert [r["model"] for r in result["models"]] == ["majority", "logistic_regression", "random_forest"]


def test_same_seed_is_reproducible():
    a = evaluate(snapshots(), cutoff=1, seeds=(987,), inner_folds=2)
    b = evaluate(snapshots(), cutoff=1, seeds=(987,), inner_folds=2)
    assert a == b


def test_dataset_must_be_synthetic_and_cutoff_correct():
    data = snapshots()
    data[0]["data_classification"] = "REAL"
    with pytest.raises(ValueError, match="synthetic"):
        evaluate(data, cutoff=1, seeds=(1,))
    with pytest.raises(ValueError, match="matching"):
        evaluate(snapshots(), cutoff=2, seeds=(1,))


def test_rejects_invalid_budget_and_student_groups():
    with pytest.raises(ValueError, match="budget"):
        evaluate(snapshots(), cutoff=1, seeds=(1, 1))
    with pytest.raises(ValueError, match="budget"):
        evaluate(snapshots(), cutoff=1, seeds=(1,), inner_folds=1)
    with pytest.raises(ValueError, match="clusters"):
        evaluate(snapshots(n_students=4), cutoff=1, seeds=(1,))


def test_rejects_unknown_labels():
    data = snapshots()
    data[0]["target_final_subject_outcome"] = "private"
    with pytest.raises(ValueError, match="target"):
        evaluate(data, cutoff=1, seeds=(1,))


def test_selection_has_fixed_predeclared_grid():
    report = evaluate(snapshots(), cutoff=1, seeds=(123,), inner_folds=2)
    names = {m["model"]: m for m in report["repetitions"][0]["models"]}
    assert len(names["majority"]["inner_selection"]) == 1
    assert len(names["random_forest"]["inner_selection"]) == 3
    assert len(names["logistic_regression"]["inner_selection"]) == 3
    for m in names.values():
        best = max(m["inner_selection"], key=lambda t: t["inner_f1_macro_mean"])
        assert m["chosen_params"] == best["params"]