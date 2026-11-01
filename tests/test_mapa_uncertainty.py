import numpy as np
import pytest
from epa.core_engine.mapa_uncertainty import cluster_bootstrap_f1


def test_cluster_bootstrap_is_deterministic_and_bounded():
    true = np.array(["approved", "recovery", "failed"] * 12)
    pred = true.copy()
    pred[::5] = "failed"
    students = np.repeat(np.arange(12), 3)
    a = cluster_bootstrap_f1(true, pred, students, seed=55, repetitions=120)
    b = cluster_bootstrap_f1(true, pred, students, seed=55, repetitions=120)
    assert a == b
    assert a["status"] == "estimated"
    assert a["student_clusters"] == 12
    assert 0 <= a["lower"] <= a["upper"] <= 1


def test_bootstrap_declines_sparse_student_groups():
    values = ["approved", "recovery", "failed"] * 3
    result = cluster_bootstrap_f1(values, values, [1, 1, 1, 2, 2, 2, 3, 3, 3], repetitions=100)
    assert result["status"] == "insufficient_clusters"


def test_bootstrap_rejects_misalignment():
    with pytest.raises(ValueError):
        cluster_bootstrap_f1(["approved"], [], [1], repetitions=100)
