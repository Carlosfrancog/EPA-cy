from pathlib import Path

import pytest

from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset, write_dataset
from epa.core_engine.student_timeline import build_snapshots
from epa.core_engine.mapa import FEATURES
from epa.core_engine.lupa import explain_snapshots, run

CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"


@pytest.fixture(scope="module")
def data():
    return build_dataset(load_catalog(CATALOG), students=24, seed=101, start_year=2020)


def test_heldout_importance_has_only_allowlisted_features(data):
    rows = build_snapshots(data, cutoff=1)
    result = explain_snapshots(rows, cutoff=1, seed=10, repeats=1)
    assert result["algorithm"] == "random_forest"
    assert result["train_students"] + result["test_students"] == 24
    assert {f["name"] for f in result["features"]} == set(FEATURES)
    assert "student_id" not in {f["name"] for f in result["features"]}
    assert sum(result["class_support"].values()) == result["test_observations"]


def test_deterministic_explanation(data):
    rows = build_snapshots(data, cutoff=2)
    assert explain_snapshots(rows, cutoff=2, seed=12, repeats=1) == explain_snapshots(
        rows, cutoff=2, seed=12, repeats=1)


def test_invalid_cutoff(data):
    with pytest.raises(ValueError, match="invalid protocol"):
        explain_snapshots(build_snapshots(data, cutoff=1), cutoff=4, seed=1)


def test_full_integrity_verification(tmp_path, data):
    pytest.importorskip("duckdb")
    folder = tmp_path / "dataset"
    write_dataset(data, folder, seed=101, catalog_digest="a" * 64)
    result = run(folder, seed=12, repeats=1)
    assert result["schema_version"] == "epa.lupa.explainability.v1"
    assert [r["cutoff_term"] for r in result["explanations"]] == [1, 2, 3]
    (folder / "students.parquet").write_bytes((folder / "students.parquet").read_bytes() + b"x")
    with pytest.raises(ValueError, match="digest mismatch"):
        run(folder, seed=12, repeats=1)
