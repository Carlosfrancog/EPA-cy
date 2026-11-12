"""Audit diagnostics must preserve the MAPA feature contract and separate history."""
from pathlib import Path

import numpy as np
import pytest

from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset
from epa.core_engine.mapa import FEATURES
from epa.core_engine.student_timeline import build_snapshots
from tools.audit_mapa_warnings import SCHEMA, audit_features, audit_cutoff, run

CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"


def test_missing_history_is_explicit_and_not_leakage():
    data = build_dataset(load_catalog(CATALOG), students=8, seed=13, start_year=2020)
    rows = build_snapshots(data, cutoff=1)
    report = audit_features(rows)
    columns = {feature["name"]: feature for feature in report["features"]}
    assert list(columns) == list(FEATURES)
    assert columns["current_mean_grade"]["missing_count"] == 0
    assert columns["prior_mean_grade"]["missing_count"] > 0
    assert columns["prior_mean_grade"]["missing_count"] < report["observations"]
    assert columns["prior_term_count"]["missing_count"] == 0


def test_mlp_diagnostics_respect_grouped_holdout_and_warn_semantics():
    data = build_dataset(load_catalog(CATALOG), students=8, seed=13, start_year=2020)
    rows = build_snapshots(data, cutoff=1)
    result = audit_cutoff(rows, cutoff=1, seed=42)
    assert result["train_students"] + result["test_students"] == 8
    assert result["mlp"]["imputer_features_in"] == len(FEATURES)
    assert 0 <= result["mlp"]["final_loss"]
    assert 1 <= result["mlp"]["n_iter"] <= result["mlp"]["max_iter_config"]
    assert result["mlp"]["converged_before_iteration_cap"] == (
        result["mlp"]["n_iter"] < result["mlp"]["max_iter_config"]
    )
    assert all(w["category"] for w in result["mlp"]["warnings"])


def test_small_audit_report_has_no_student_rows():
    report = run(students=8, seed=13, cutoffs=(1,), catalog=CATALOG)
    assert report["schema_version"] == SCHEMA
    assert report["classification"] == "SYNTHETIC"
    assert len(report["cutoffs"]) == 1
    assert all("student_id" not in f for f in report["cutoffs"][0]["features"])


def test_rejects_invalid_audit_config():
    with pytest.raises(ValueError):
        run(students=7, seed=1, cutoffs=(1,), catalog=CATALOG)
    with pytest.raises(ValueError):
        run(students=8, seed=1, cutoffs=(4,), catalog=CATALOG)
