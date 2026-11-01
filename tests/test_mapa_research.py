from pathlib import Path
import pytest

from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset, write_dataset
from epa.core_engine.student_timeline import build_snapshots
from epa.core_engine.mapa_research import evaluate_protocol, run

CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"


@pytest.fixture(scope="module")
def data():
    return build_dataset(load_catalog(CATALOG), students=24, seed=13, start_year=2020)


def test_grouped_folds_cover_all_models_and_classes(data):
    r = evaluate_protocol(build_snapshots(data, cutoff=1), cutoff=1, n_splits=3, seed=7)
    assert len(r["folds"]) == 9
    assert {f["model"] for f in r["folds"]} == {"majority", "logistic_regression", "random_forest"}
    assert all(sum(f["class_support"].values()) == f["test_observations"] for f in r["folds"])
    assert all(len(f["confusion_matrix"]) == 3 for f in r["folds"])
    assert all(r["summaries"][i]["f1_macro_fold_distribution"]["n_folds"] == 3 for i in range(3))


def test_never_claims_temporal_validation_on_reused_students(data):
    for cutoff in (1, 2, 3):
        r = evaluate_protocol(build_snapshots(data, cutoff=cutoff), cutoff=cutoff, n_splits=2)
        assert r["temporal_holdout"]["status"] == "not_identifiable"
        assert r["temporal_holdout"]["reason"] == "same_students_across_years"


def test_rejects_incompatible_cutoffs(data):
    with pytest.raises(ValueError):
        evaluate_protocol(build_snapshots(data, cutoff=1), cutoff=2)


def test_manifest_and_three_protocols(tmp_path, data):
    pytest.importorskip("duckdb")
    folder = tmp_path / "demo"
    write_dataset(data, folder, seed=13, catalog_digest="a" * 64)
    report = run(folder, seed=7, n_splits=2)
    assert [p["cutoff_term"] for p in report["protocols"]] == [1, 2, 3]
    assert report["dataset_classification"] == "SYNTHETIC"
    assert all(p["temporal_holdout"]["status"] == "not_identifiable" for p in report["protocols"])
