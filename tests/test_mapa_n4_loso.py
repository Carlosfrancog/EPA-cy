"""Privacy and student-isolation checks for the two-student N4 diagnostic."""
import csv
import json
import pytest
from epa.core_engine import mapa_n4_loso as loso
from epa.core_engine.mapa_real_n4 import canonical_subject


def test_vetted_aliases_accept_aln2_without_fuzzy_matching():
    for text, sid in [("matematica", "MAT"), ("MATEMÁTICA", "MAT"),
                      ("educacao-fisica", "EDF"), ("fisica", "FIS"),
                      ("História", "HIS"), ("QUÍMICA", "QUI")]:
        assert canonical_subject(text)[0] == sid
    with pytest.raises(ValueError):
        canonical_subject("ciencias")
    with pytest.raises(ValueError):
        canonical_subject("classificacao secreta")


def test_manifest_requires_exactly_two_distinct_aliases_and_existing_files(tmp_path):
    paths = []
    for name in ("ALN1", "ALN2"):
        source = []
        for i in range(3):
            p = tmp_path / f"{name}-{i}.csv"
            p.write_text("fixture", encoding="utf-8")
            source.append(str(p))
        paths.append({"student": name, "inputs": source[0], "calibration_history": source[1], "answer_key": source[2]})
    spec = tmp_path / "manifest.json"
    spec.write_text(json.dumps({"students": paths}))
    assert {x["student"] for x in loso.read_manifest(spec)} == {"ALN1", "ALN2"}
    spec.write_text(json.dumps({"students": [paths[0], paths[0]]}))
    with pytest.raises(ValueError, match="unique"):
        loso.read_manifest(spec)
    spec.write_text(json.dumps({"students": paths+[paths[0]]}))
    with pytest.raises(ValueError, match="two"):
        loso.read_manifest(spec)



def test_manifest_accepts_utf8_bom_from_windows_powershell(tmp_path):
    profiles = []
    for name in ("ALN1", "ALN2"):
        sources = []
        for kind in ("inputs", "calibration_history", "answer_key"):
            source = tmp_path / f"{name}-{kind}.csv"
            source.write_text("synthetic fixture only", encoding="utf-8")
            sources.append(str(source))
        profiles.append({
            "student": name,
            "inputs": sources[0],
            "calibration_history": sources[1],
            "answer_key": sources[2],
        })
    manifest = tmp_path / "dois_alunos.json"
    content = json.dumps({"students": profiles}, ensure_ascii=False)
    manifest.write_text(content, encoding="utf-8-sig")
    loaded = loso.read_manifest(manifest)
    assert [p["student"] for p in loaded] == ["ALN1", "ALN2"]
    manifest.write_text(content, encoding="utf-8")
    assert [p["student"] for p in loso.read_manifest(manifest)] == ["ALN1", "ALN2"]

def test_transferred_profile_never_uses_held_out_student(monkeypatch):
    from epa.core_engine.mapa_real_n4 import features
    from epa.core_engine.mapa_n4_longitudinal import AREAS
    profiles=[{"student": name,"inputs":name,"calibration_history":name+"-hist","answer_key":name+"-key"} for name in ("ALN1","ALN2")]
    def cases(path):
        return [{"id_caso":str(i),**features(n1=5,n2=6,n3=7,grade_level=10+i//12,subject_id="MAT",area="MATEMATICA")} for i in range(36)]
    def history(path):
        label = str(path).split("-")[0]
        return [{"area": area, "grades": (3,4,5,6), "student": label} for area in AREAS for _ in range(9)]
    used=[]
    def adapter(train, y, ref):
        used.append(ref["student_marker"])
        return train, y, {"tag":ref["student_marker"]}
    monkeypatch.setattr(loso,"load_private_inputs",cases)
    monkeypatch.setattr(loso,"read_history",history)
    monkeypatch.setattr(loso,"file_digest",lambda x:"dummysha")
    monkeypatch.setattr(loso,"profile",lambda entries:{"student_marker":entries[0]["student"]})
    monkeypatch.setattr(loso,"adapt_training",adapter)
    monkeypatch.setattr(loso,"generated_synthetic_rows",lambda *a,**kw:([features(n1=5,n2=6,n3=7,grade_level=10,subject_id="MAT",area="MATEMATICA")],[7],{"generator":"SYNTHETIC"}))
    monkeypatch.setattr(loso,"predict_all",lambda *a,**kw:({"baseline_n3":[7]*36},{"baseline_n3":0}))
    monkeypatch.setattr(loso,"load_private_answer_key",lambda path, ids:{x:8 for x in ids})
    report,pred=loso.compare(profiles,"catalog.json",students=16,algorithms=("baseline_n3",))
    assert used == ["ALN2","ALN1"]
    assert report["independent_students"] == 2 and report["total_cases"] == 72
    assert report["per_student"][0]["calibration_from"] == "ALN2"
    assert report["per_student"][1]["calibration_from"] == "ALN1"
    assert "id_caso" not in json.dumps(report)
    assert len(pred) == 72 and "id_caso" in pred[0]
    assert report["equal_student_mean"][0]["mean_student_mae_control"] == 1.0


def test_reject_non_distinct_students_and_invalid_models():
    with pytest.raises(ValueError,match="two"):
        loso.compare([{"student":"ALN1"},{"student":"ALN1"}],"x")
    with pytest.raises(ValueError,match="model"):
        loso.compare([{"student":"ALN1"},{"student":"ALN2"}],"x",algorithms=("unknown",))