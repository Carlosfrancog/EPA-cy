"""DuckDB MAPA feature export tests against the GENESIS v2 snapshot oracle.

The fixture uses logically equivalent v2 Parquet with a native manifest schema;
it is NOT a substitute for an actual Rust binary end-to-end integration test.
"""
import hashlib
import json
from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")
from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset, write_dataset
from epa.core_engine.student_timeline import build_snapshots
from epa.core_engine.mapa import FEATURES, feature_vector
from epa.core_engine.mapa_feature_export import export, SCHEMA
from epa.genesis.parquet_deep_audit import quoted_path

CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"


def fixture_native_contract(tmp_path, *, students=9, seed=42):
    data = build_dataset(load_catalog(CATALOG), students=students, seed=seed, start_year=2020)
    folder = tmp_path / "source"
    write_dataset(data, folder, seed=seed, catalog_digest="a" * 64)
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = "epa.genesis.dataset.rust_native.v1"
    manifest["generator_seed"] = seed
    manifest["students"] = students
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return data, folder


@pytest.mark.parametrize("seed", [1, 42, 20261029])
def test_snapshots_are_equivalent_to_legacy_v2(tmp_path, seed):
    data, source = fixture_native_contract(tmp_path, seed=seed)
    output = tmp_path / "features"
    report = export(source, output)
    assert report["schema_version"] == SCHEMA
    assert report["feature_names"] == list(FEATURES)
    with duckdb.connect(":memory:") as connection:
        for cutoff in (1, 2, 3):
            cursor = connection.execute(
                "SELECT * FROM read_parquet(?) ORDER BY enrollment_id, subject_id",
                [str(output / f"N{cutoff}.parquet")]
            )
            names = [c[0] for c in cursor.description]
            actual = [dict(zip(names, row)) for row in cursor.fetchall()]
            reference = build_snapshots(data, cutoff=cutoff)
            assert len(actual) == len(reference)
            for expected, got in zip(reference, actual):
                for key in ("student_id", "enrollment_id", "class_id", "academic_year",
                            "grade_level", "subject_id", "cutoff_term", "known_term_count",
                            "prior_years_observed", "target_final_subject_outcome",
                            "target_usage", "data_classification"):
                    assert got[key] == expected[key], (seed, cutoff, key)
                for feature, value in zip(FEATURES, feature_vector(expected)):
                    observed = got[feature]
                    if value != value:  # missing prior history mapped to NULL/NaN
                        assert observed is None
                    else:
                        assert abs(float(observed) - value) <= 1e-6, (
                            seed, cutoff, feature, value, observed
                        )


def test_rejects_tampering_and_keeps_output_immutable(tmp_path):
    _, source = fixture_native_contract(tmp_path)
    destination = tmp_path / "features"
    export(source, destination)
    with pytest.raises(FileExistsError, match="immutable"):
        export(source, destination)
    path = source / "period_records.parquet"
    path.write_bytes(path.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="sha256"):
        export(source, tmp_path / "other")


def test_rejects_wrong_source_schema(tmp_path):
    _, source = fixture_native_contract(tmp_path)
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["schema_version"] = "epa.genesis.dataset.v2"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Rust native"):
        export(source, tmp_path / "features")


def test_rejects_missing_academic_term(tmp_path):
    _, source = fixture_native_contract(tmp_path)
    original = source / "period_records.parquet"
    modified = tmp_path / "modified.parquet"
    with duckdb.connect(":memory:") as connection:
        connection.execute(
            f"COPY (SELECT * FROM read_parquet({quoted_path(original)}) WHERE NOT "
            f"(student_id = 'SYN00000001' AND term = 4)) "
            f"TO {quoted_path(modified)} (FORMAT PARQUET)"
        )
        new_count = connection.execute(
            "SELECT COUNT(*) FROM read_parquet(?)", [str(modified)]
        ).fetchone()[0]
    original.write_bytes(modified.read_bytes())
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifacts"]["period_records"]["row_count"] = new_count
    manifest["artifacts"]["period_records"]["sha256"] = hashlib.sha256(original.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="incomplete"):
        export(source, tmp_path / "features")
