import hashlib
import json
from pathlib import Path
import pytest
from epa.atlas.catalog import load_catalog
from epa.genesis.generate import build_rows,write_parquet

DEMO=Path(__file__).resolve().parents[1]/"examples"/"atlas.demo.json"

def test_catalog_has_seven_unique_grade_levels():
    cat=load_catalog(DEMO)
    assert [g["grade_level"] for g in cat["grades"]]==list(range(6,13))

def test_rejects_unverified_bncc_codes(tmp_path):
    data=json.loads(DEMO.read_text())
    data["grades"][0]["subjects"][0]["bncc_skill_codes"]=["EF06MA01"]
    path=tmp_path/"catalog.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="verified official"):
        load_catalog(path)

def test_stable_synthetic_longitudinal_rows():
    c=load_catalog(DEMO)
    a=build_rows(c,3,42,2020)
    b=build_rows(c,3,42,2020)
    assert a==b
    assert len({r["student_id"] for r in a})==3
    assert {r["grade_level"] for r in a}==set(range(6,13))
    assert all(0<=r["final_grade"]<=10 and 0<=r["attendance_rate"]<=1 for r in a)

def test_seed_changes_generated_values():
    c=load_catalog(DEMO)
    assert build_rows(c,2,42,2020)!=build_rows(c,2,43,2020)

def test_invalid_size_rejected():
    with pytest.raises(ValueError):
        build_rows(load_catalog(DEMO),0,42,2020)

def test_parquet_export_and_manifest(tmp_path):
    duckdb=pytest.importorskip("duckdb")
    c=load_catalog(DEMO)
    rows=build_rows(c,2,42,2020)
    output=tmp_path/"out"
    manifest=write_parquet(rows,output,"a"*64,42)
    assert manifest["row_count"]==len(rows)
    assert hashlib.sha256((output/"academic_history.parquet").read_bytes()).hexdigest()==manifest["digest"]
    con=duckdb.connect()
    assert con.execute("SELECT count(*) FROM read_parquet(?)",[str(output/"academic_history.parquet")]).fetchone()[0]==len(rows)
    with pytest.raises(FileExistsError):
        write_parquet(rows,output,"a"*64,42)
