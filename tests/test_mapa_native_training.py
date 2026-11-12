"""MAPA native training: regression, provenance and probability tests."""
import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("duckdb")
from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset, write_dataset
from epa.core_engine.mapa_feature_export import export
from epa.core_engine.mapa_native_training import run, verify, scores

CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"


@pytest.fixture
def features(tmp_path):
    from epa.genesis.v2 import build_dataset
    data = build_dataset(load_catalog(CATALOG), students=20, seed=42, start_year=2020)
    source = tmp_path / "input"
    write_dataset(data, source, seed=42, catalog_digest="a" * 64)
    path = source / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest.update(schema_version="epa.genesis.dataset.rust_native.v1",
                    generator_seed=42, students=20)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    target = tmp_path / "features"
    export(source, target)
    return target


def test_grouped_training_is_reproducible_and_scores_probabilities(features):
    a = run(features, max_students=12, seed=13)
    b = run(features, max_students=12, seed=13)
    assert a["selected_students"] == 12
    assert a["feature_manifest_sha256"] == b["feature_manifest_sha256"]
    assert len(a["protocols"]) == 3
    for block_a, block_b in zip(a["protocols"], b["protocols"]):
        assert block_a["train_students"] + block_a["test_students"] == 12
        assert block_a["test_observations"] > 0
        for model_a, model_b in zip(block_a["results"], block_b["results"]):
            assert model_a["model"] == model_b["model"]
            assert model_a["f1_macro"] == model_b["f1_macro"]
            assert model_a["brier_multiclass"] == model_b["brier_multiclass"]
            assert model_a["log_loss"] == model_b["log_loss"]
            assert 0 <= model_a["brier_multiclass"] <= 2


def test_tampered_artifact_fails_closed(features):
    file = features / "N2.parquet"
    file.write_bytes(file.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="digest"):
        verify(features)


def test_rejects_student_limit(features):
    with pytest.raises(ValueError, match="student cap"):
        run(features, max_students=5001)


def test_scores_use_fixed_multiclass_order():
    truth = np.asarray(["approved", "failed", "recovery"])
    prediction = truth.copy()
    prob = np.asarray([[1,0,0],[0,0,1],[0,1,0]], dtype=float)
    s = scores(truth, prediction, prob)
    assert s["f1_macro"] == 1
    assert s["brier_multiclass"] == 0
    with pytest.raises(ValueError, match="invalid predicted"):
        scores(truth, prediction, prob * 0.9)
