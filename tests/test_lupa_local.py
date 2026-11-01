from pathlib import Path
import json
from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset
from epa.core_engine.student_timeline import build_snapshots
from epa.core_engine.lupa_local import inspect

CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"


def test_local_errors_are_deterministic_and_anonymous():
    data = build_dataset(load_catalog(CATALOG), students=24, seed=17, start_year=2020)
    rows = build_snapshots(data, cutoff=1)
    r = inspect(rows, cutoff=1, seed=21, max_cases=4)
    assert r == inspect(rows, cutoff=1, seed=21, max_cases=4)
    assert len(r["cases"]) <= 4
    assert sum(sum(row) for row in r["confusion_matrix"]) == r["test_observations"]
    for case in r["cases"]:
        assert case["actual"] != case["predicted"]
        assert len(case["top_sensitivities"]) == 3
        assert 0 <= case["predicted_probability"] <= 1
    body = json.dumps(r)
    assert "student_id" not in body
    assert "SYN000" not in body
