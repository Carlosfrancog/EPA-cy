from pathlib import Path
import pytest
from epa.atlas.catalog import load_catalog
from epa.genesis.cohorts import build_cohorts
from epa.genesis.v2 import build_dataset
from epa.core_engine.student_timeline import build_snapshots
from epa.core_engine.mapa_research_extended import evaluate

CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"


def test_mlp_grouped_cv_with_synthetic_history():
    data = build_dataset(load_catalog(CATALOG), students=24, seed=13, start_year=2020)
    report = evaluate(build_snapshots(data, cutoff=1), cutoff=1, seed=17, folds=2)
    assert report["algorithms"] == ["mlp"]
    assert len(report["folds"]) == 2
    assert all(x["status"] == "evaluated" for x in report["folds"])
    assert report["temporal_holdout"]["status"] == "not_identifiable"


def test_mlp_temporal_on_disjoint_cohorts():
    data = build_cohorts(load_catalog(CATALOG), students_per_cohort=8,
                         seed=11, start_year=2020, cohort_years=3)
    report = evaluate(build_snapshots(data, cutoff=2), cutoff=2, seed=17, folds=2)
    assert report["temporal_holdout"]["status"] == "evaluated"
    model = report["temporal_holdout"]["models"][0]
    assert model["model"] == "mlp"
    assert model["status"] == "evaluated"
    assert model["f1_macro_cluster_interval"]["status"] == "estimated"


def test_incompatible_cutoff_rejected():
    data = build_dataset(load_catalog(CATALOG), students=8, seed=1, start_year=2020)
    with pytest.raises(ValueError):
        evaluate(build_snapshots(data, cutoff=1), cutoff=2, folds=2)
