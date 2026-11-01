from pathlib import Path
import pytest
from epa.atlas.catalog import load_catalog
from epa.genesis.cohorts import build_cohorts
from epa.genesis.v2 import validate_dataset
from epa.core_engine.student_timeline import build_snapshots
from epa.core_engine.mapa_research import evaluate_protocol

CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"


def test_cohorts_are_disjoint_and_temporally_evaluable():
    data = build_cohorts(load_catalog(CATALOG), students_per_cohort=12,
                         seed=11, start_year=2020, cohort_years=3)
    validate_dataset(data)
    years = {}
    for row in data["enrollments"]:
        years.setdefault(row["academic_year"], set()).add(row["student_id"])
    assert set(years) == {2020, 2021, 2022}
    assert len(set.union(*years.values())) == 36
    assert not (years[2020] & years[2021] or years[2021] & years[2022])
    for cutoff in (1, 2, 3):
        report = evaluate_protocol(build_snapshots(data, cutoff=cutoff), cutoff=cutoff,
                                   seed=7, n_splits=2)
        assert report["temporal_holdout"]["status"] == "evaluated"
        assert report["temporal_holdout"]["train_students"] == 24
        assert report["temporal_holdout"]["test_students"] == 12


def test_cohort_generator_is_reproducible():
    catalog = load_catalog(CATALOG)
    args = dict(students_per_cohort=8, seed=5, start_year=2020, cohort_years=2)
    assert build_cohorts(catalog, **args) == build_cohorts(catalog, **args)


def test_invalid_cohort_scale():
    with pytest.raises(ValueError):
        build_cohorts(load_catalog(CATALOG), students_per_cohort=1, seed=0, start_year=2020)
