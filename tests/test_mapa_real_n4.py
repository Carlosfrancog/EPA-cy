"""Leakage boundaries and deterministic scoring for a PRIVATE single-student dataset."""
import csv
from pathlib import Path
import numpy as np
import pytest
from epa.core_engine import mapa_real_n4 as bench


def fixture_rows():
    return [{"id_caso": f"case-{i:02d}", **bench.features(n1=5, n2=6, n3=7,
        grade_level=10 + i//12, subject_id="MAT", area="MATEMATICA")} for i in range(36)]


def write_csv(path, names, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def test_private_inputs_reject_label_and_extra_columns(tmp_path):
    records = [{"id_caso": f"x{i}", "serie": f"{i//12 + 1}M", "ano_letivo":2020+i//12,
                "disciplina":"Matemática", "N1":5,"N2":6,"N3":7} for i in range(36)]
    f = tmp_path / "input.csv"
    write_csv(f, list(records[0]), records)
    assert len(bench.load_private_inputs(f)) == 36
    for r in records:
        r["N4"] = 8
    write_csv(f, list(records[0]), records)
    with pytest.raises(ValueError, match="ONLY"):
        bench.load_private_inputs(f)


def test_answer_key_separate_and_rejects_duplicates(tmp_path):
    f = tmp_path / "answers.csv"
    write_csv(f, ["id_caso", "N4_real"], [{"id_caso":"case-00", "N4_real":"8"}])
    assert bench.load_private_answer_key(f, {"case-00"}) == {"case-00":8.0}
    write_csv(f, ["id_caso", "N4_real"], [{"id_caso":"case-00", "N4_real":"8"},
                                    {"id_caso":"case-00", "N4_real":"7"}])
    with pytest.raises(ValueError,match="mismatch"):
        bench.load_private_answer_key(f, {"case-00"})


def test_predictions_exclude_targets_and_have_reproducible_seed():
    real = fixture_rows()
    train = [bench.features(n1=float(i%8),n2=float((i+1)%8),n3=float((i+2)%8),
             grade_level=10+i%3,subject_id="MAT",area="MATEMATICA") for i in range(90)]
    y = [float((i+3)%8) for i in range(90)]
    names = ("baseline_n3","baseline_mean","linear","ridge","random_forest","mlp")
    p1,_ = bench.predict_all(train,y,real,seed=42,algorithms=names)
    p2,_ = bench.predict_all(train,y,real,seed=42,algorithms=names)
    for model in names:
        assert np.allclose(p1[model],p2[model])
        assert np.isfinite(p1[model]).all()
    assert p1["baseline_n3"] == [7.0]*36
    assert p1["baseline_mean"] == [6.0]*36
    train[0]["N4"] = 10
    with pytest.raises(ValueError,match="leaked"):
        bench.predict_all(train,y,real,seed=42,algorithms=("linear",))


def test_retrospective_metrics_single_student():
    real = fixture_rows()
    targets = {r["id_caso"]: 8.0 for r in real}
    predictions = {"baseline_n3": [7.0]*36, "baseline_mean": [6.0]*36}
    out = bench.score_predictions(predictions,real,targets,{"baseline_n3":0,"baseline_mean":0})
    assert out["independent_students"] == 1
    assert out["model_metrics"][0]["mae"] == 1.0
    assert out["model_metrics"][1]["rmse"] == 2.0


def test_canonical_subject_catalog_gaps():
    assert bench.canonical_subject("Física")== ("FIS", "NATUREZA")
    assert bench.canonical_subject("Educação Física")[0] == "EDF"
    with pytest.raises(ValueError):
        bench.canonical_subject("Unknown")


def test_original_genesis_generates_n4_training_without_real_labels():
    catalog = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"
    x, y, prov = bench.generated_synthetic_rows(catalog, students=16, seed=103)
    assert prov["generator"] == "epa.genesis.v3.student_rows"
    assert prov["generator_calibration"] == "NONE_ORIGINAL"
    assert prov["generator_classification"] == "SYNTHETIC"
    assert prov["synthetic_records"] == len(y) == len(x) == 16 * 3 * 10
    assert all("N4" not in row and "MF" not in row for row in x)
    assert all(0 <= score <= 10 for score in y)
    x2,y2,_ = bench.generated_synthetic_rows(catalog, students=16, seed=103)
    assert x == x2 and y == y2