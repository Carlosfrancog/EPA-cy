"""Student-group statistical evaluation, distinct from repeated-record bootstrap."""
import json
from pathlib import Path
import numpy as np
import pytest

duckdb = pytest.importorskip("duckdb")
from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset, write_dataset
from epa.core_engine.mapa_feature_export import export
from epa.core_engine.mapa_statistical_evaluator import (
    cluster_bootstrap, reliability, run, SCHEMA
)

CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"


@pytest.fixture
def features(tmp_path):
    data = build_dataset(load_catalog(CATALOG), students=16, seed=11, start_year=2020)
    source = tmp_path / "source"
    write_dataset(data, source, seed=11, catalog_digest="a" * 64)
    path = source / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest.update(schema_version="epa.genesis.dataset.rust_native.v1",
                    students=16, generator_seed=11)
    path.write_text(json.dumps(manifest))
    destination = tmp_path / "feature-data"
    export(source, destination)
    return destination


def test_cluster_bootstrap_resamples_students_and_pairs_models():
    # Each of eight students supplies two correlated observations.
    groups = np.asarray([f"SYN{i:08d}" for i in range(8) for _ in range(2)])
    y = np.asarray(["approved", "failed"] * 8)
    good = y.copy()
    bad = np.asarray(["recovery"] * len(y))
    result = cluster_bootstrap(y, {"good": good, "bad": bad},
                               groups, repetitions=60, seed=7)
    assert result["independent_clusters"] == 8
    assert result["macro_f1_intervals"]["good"]["lower"] == pytest.approx(2 / 3)
    assert result["paired_macro_f1_differences"]["good__minus__bad"]["lower"] > 0
    assert result == cluster_bootstrap(y, {"good": good, "bad": bad},
                                       groups, repetitions=60, seed=7)


def test_reliability_table_counts_observations_and_is_not_calibration_fit():
    y = np.asarray(["approved", "failed", "recovery"])
    probabilities = np.asarray([[0.9, 0.05, 0.05],
                                [0.03, 0.02, 0.95],
                                [0.1, 0.8, 0.1]])
    report = reliability(y, probabilities)
    assert sum(part["count"] for part in report["top_label"]["bins"]) == 3
    for label in ("approved", "failed", "recovery"):
        assert sum(part["count"] for part in report["one_vs_rest"][label]["bins"]) == 3
    assert report["top_label"]["ece"] >= 0


def test_statistical_evaluator_reports_grouped_uncertainty_and_provenance(features):
    report = run(features, max_students=12, seeds=(8,),
                 algorithms=("majority", "logistic_regression"),
                 bootstrap_repetitions=50)
    assert report["schema_version"] == SCHEMA
    assert report["selected_students"] == 12
    assert len(report["protocols"]) == 3
    for block in report["protocols"]:
        assert block["train_students"] + block["test_students"] == 12
        assert block["uncertainty"]["independent_clusters"] == block["test_students"]
        assert "majority__minus__logistic_regression" in block["uncertainty"]["paired_macro_f1_differences"]
        for result in block["results"]:
            assert 0 <= result["f1_macro"] <= 1
            assert result["log_loss"] >= 0
            assert "one_vs_rest" in result["reliability"]


def test_invalid_bootstrap_configuration_and_repeated_seeds(features):
    with pytest.raises(ValueError, match="bootstrap"):
        run(features, max_students=12, seeds=(8,), bootstrap_repetitions=10)
    with pytest.raises(ValueError, match="seed"):
        run(features, max_students=12, seeds=(8, 8))
