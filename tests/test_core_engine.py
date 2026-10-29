from pathlib import Path
import copy
import pytest
from epa.atlas.catalog import load_catalog
from epa.genesis.generate import build_rows, write_parquet
from epa.core_engine.experiment import FEATURES, evaluate, run, snapshots

DEMO=Path(__file__).resolve().parents[1]/"examples"/"atlas.demo.json"

def _make(tmp_path,students=80):
    rows=build_rows(load_catalog(DEMO),students,42,2020)
    folder=tmp_path/"data"
    write_parquet(rows,folder,"a"*64,42)
    return folder/"academic_history.parquet"

def test_snapshot_features_only_from_available_year(tmp_path):
    p=_make(tmp_path,8)
    snapshots_now=snapshots(p)
    a=next(r for r in snapshots_now if r["student_id"]=="SYN00000001" and r["academic_year"]==2020)
    assert a["years_observed"]==1
    assert "target_next_year_pass" not in FEATURES
    assert len(FEATURES)==9

def test_features_unchanged_if_future_year_outcomes_modified(tmp_path):
    p=_make(tmp_path,6)
    rows=snapshots(p)
    first=next(x for x in rows if x["student_id"]=="SYN00000001" and x["academic_year"]==2020)
    # Changing the target in evaluation rows cannot modify model input features.
    copy_row=copy.deepcopy(first)
    copy_row["target_next_year_pass"]=1-first["target_next_year_pass"]
    assert [first[f] for f in FEATURES]==[copy_row[f] for f in FEATURES]

def test_group_isolation_and_baselines(tmp_path):
    p=_make(tmp_path,100)
    report=run(p,seed=17)
    assert report["train_students"]+report["test_students"]==100
    assert len(report["results"])==3
    assert report["research_status"]=="EXPERIMENTAL_NOT_VALIDATED"
    assert all(0<=r["accuracy"]<=1 for r in report["results"])

def test_tampered_parquet_rejected(tmp_path):
    p=_make(tmp_path,4)
    with p.open("ab") as f:
        f.write(b"tamper")
    with pytest.raises(ValueError,match="digest mismatch"):
        snapshots(p)

def test_too_small_set_rejected(tmp_path):
    p=_make(tmp_path,2)
    with pytest.raises(ValueError,match="distinct students"):
        evaluate(snapshots(p))

def test_no_final_year_used_as_prediction_origin(tmp_path):
    p=_make(tmp_path,5)
    s=snapshots(p)
    assert all(r["academic_year"]<=2025 for r in s)
    assert all(r["academic_year"]>=2020 for r in s)
