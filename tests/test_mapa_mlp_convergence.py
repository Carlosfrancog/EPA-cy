"""Synthetic nested-group convergence experiment contract tests."""
from pathlib import Path

import pytest

from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset
from epa.core_engine.student_timeline import build_snapshots
from epa.core_engine.mapa import FEATURES
from epa.core_engine.mapa_mlp_convergence import evaluate_cutoff, mlp, SCHEMA

CATALOG = Path(__file__).resolve().parents[1] / "examples/atlas.demo.json"


def test_experimental_imputer_keeps_empty_history_columns():
    estimator = mlp(seed=13, max_iter=2)
    assert estimator.named_steps["simpleimputer"].keep_empty_features is True


def test_nested_grouped_validation_never_selects_on_outer_test():
    rows = build_snapshots(
        build_dataset(load_catalog(CATALOG), students=24, seed=13, start_year=2020),
        cutoff=1,
    )
    result = evaluate_cutoff(rows, cutoff=1, seed=13, budgets=(2, 4))
    assert result["train_students"] + result["validation_students"] == result["outer_train_students"]
    assert result["outer_train_students"] + result["outer_test_students"] == 24
    assert result["selected_max_iter"] in (2, 4)
    assert len(result["trials"]) == 2
    assert result["features"] == list(FEATURES)
    assert result["final_fit"]["features_out"] == len(FEATURES)
    assert 0 <= result["heldout_f1_macro"] <= 1
    assert sum(result["heldout_class_support"].values()) > 0


def test_rejects_wrong_cutoff():
    rows = build_snapshots(
        build_dataset(load_catalog(CATALOG), students=24, seed=13, start_year=2020),
        cutoff=1,
    )
    with pytest.raises(ValueError, match="invalid synthetic snapshots"):
        evaluate_cutoff(rows, cutoff=2, seed=13)
