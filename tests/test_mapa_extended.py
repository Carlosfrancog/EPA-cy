from pathlib import Path
import pytest
from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset
from epa.core_engine.student_timeline import build_snapshots
from epa.core_engine.mapa_extended import evaluate, candidates

CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"


@pytest.fixture(scope="module")
def rows():
    data = build_dataset(load_catalog(CATALOG), students=24, seed=13, start_year=2020)
    return build_snapshots(data, cutoff=1)


def test_mlp_uses_grouped_split_and_three_class_metrics(rows):
    result = evaluate(rows, cutoff=1, seed=42)
    assert result["train_students"] + result["test_students"] == 24
    assert result["results"][0]["model"] == "mlp"
    assert result["results"][0]["status"] == "evaluated"
    assert len(result["results"][0]["confusion_matrix"]) == 3
    assert sum(result["test_class_counts"].values()) == sum(
        sum(row) for row in result["results"][0]["confusion_matrix"])


def test_repeatability(rows):
    assert evaluate(rows, cutoff=1, seed=42) == evaluate(rows, cutoff=1, seed=42)


def test_xgb_is_not_required_for_default_run():
    assert list(candidates(42)) == ["mlp"]
