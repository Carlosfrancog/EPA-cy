"""GENESIS v3: compatibility, RNG independence and bounded Parquet writing."""
import hashlib
import json
from pathlib import Path

import pytest

from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset
from epa.genesis.v3 import generate, student_rows

CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"


def test_v3_student_records_preserve_v2_semantics():
    catalog = load_catalog(CATALOG)
    expected = build_dataset(catalog, students=7, seed=42, start_year=2020)
    actual = {entity: [] for entity in expected}
    for number in range(1, 8):
        for entity, row in student_rows(catalog, number, seed=42, start_year=2020,
                                        classes_per_grade=3, school_count=2):
            actual[entity].append(row)
    for entity in ("students", "enrollments", "period_records"):
        assert actual[entity] == expected[entity]


def test_parquet_content_independent_of_student_batches(tmp_path):
    pa = pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq
    one = tmp_path / "one"
    two = tmp_path / "two"
    a = generate(CATALOG, one, students=17, batch_students=3, seed=123, row_group_rows=25)
    b = generate(CATALOG, two, students=17, batch_students=11, seed=123, row_group_rows=25)
    for entity in a["artifacts"]:
        aa, bb = a["artifacts"][entity], b["artifacts"][entity]
        assert aa["row_count"] == bb["row_count"]
        assert aa["logical_sha256"] == bb["logical_sha256"]
        assert aa["sha256"] == hashlib.sha256((one / aa["path"]).read_bytes()).hexdigest()
        assert bb["sha256"] == hashlib.sha256((two / bb["path"]).read_bytes()).hexdigest()
        assert pq.read_table(one / aa["path"]).to_pylist() == pq.read_table(two / bb["path"]).to_pylist()
    assert a["artifacts"]["period_records"]["row_count"] == 17 * 54 * 4
    assert json.loads((one / "manifest.json").read_text()) == a
    with pytest.raises(FileExistsError):
        generate(CATALOG, one, students=1)
