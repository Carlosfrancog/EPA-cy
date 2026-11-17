"""Validation of privacy, temporal scope and real N4 feature isolation."""
import csv
from pathlib import Path
import pytest
from epa.core_engine.mapa_n4_longitudinal import (
    read_history, profile, adapt_training, normalize_subject, AREA_BY_SUBJECT,
)
from epa.core_engine.mapa_real_n4 import features


def row(area, sid="MAT", base=6):
    return features(n1=base - 1, n2=base, n3=base + 1,
                    grade_level=10, subject_id=sid, area=area)


def sample():
    areas = ["MATEMATICA", "NATUREZA", "HUMANAS", "LINGUAGENS"]
    xs = [row(area, sid={"MATEMATICA":"MAT", "NATUREZA":"CIE", "HUMANAS":"HIS", "LINGUAGENS":"POR"}[area], base=5+i) for i,area in enumerate(areas)]
    ys=[5.8,6.8,7.8,8.8]
    p={a:{"cases":9, "grade_mean":8.3, "mean_abs_step":2.2} for a in areas}
    return xs,ys,p


def test_typo_aliases_and_knowledge_area_mapping():
    for text in ("matematica", "Matemática"):
        assert AREA_BY_SUBJECT[normalize_subject(text)] == "MATEMATICA"
    assert AREA_BY_SUBJECT[normalize_subject("ciências")] == "NATUREZA"
    assert AREA_BY_SUBJECT[normalize_subject("historia")] == "HUMANAS"
    for typo in ("educacao fisica", "eduacacao fisica", "eduacaco fisica"):
        assert AREA_BY_SUBJECT[normalize_subject(typo)] == "LINGUAGENS"


def test_all_four_terms_change_and_derived_features_remain_consistent():
    xs,ys,p=sample()
    out,targets,audit=adapt_training(xs,ys,p)
    assert audit["kind"]=="EXPERIMENTAL_FOUR_TERM_MOMENT_ADAPTER"
    assert out[0]["N1"] != xs[0]["N1"]
    assert out[0]["N2"] != xs[0]["N2"]
    assert targets[0] != ys[0]
    assert out[0]["mean_123"] == pytest.approx((out[0]["N1"]+out[0]["N2"]+out[0]["N3"])/3)
    assert all(0 <= x <= 10 for z,y in zip(out,targets) for x in (z["N1"],z["N2"],z["N3"],y))


def test_deterministic_and_zero_strength_returns_original():
    xs,ys,p=sample()
    assert adapt_training(xs,ys,p) == adapt_training(xs,ys,p)
    out,targets,_=adapt_training(xs,ys,p,strength=0)
    assert all(out[i]["N1"] == xs[i]["N1"] for i in range(len(xs)))
    assert targets==ys


def test_reject_target_as_feature_and_overpowered_calibration():
    xs,ys,p=sample()
    with pytest.raises(ValueError,match="future label"):
        adapt_training([{**xs[0],"N4":8}]+xs[1:],ys,p)
    with pytest.raises(ValueError,match="strength"):
        adapt_training(xs,ys,p,strength=0.9)


def write_history(path,items):
    fields=["id_caso","serie","ano_letivo","disciplina","N1","N2","N3","N4"]
    with path.open("w",newline="",encoding="utf-8") as stream:
        w=csv.DictWriter(stream,fieldnames=fields);w.writeheader();w.writerows(items)


def valid_history():
    names=["matematica","ciencias","geografia","artes"]
    return [{"id_caso":f"c{i}","serie":f"{1+i//4}F","ano_letivo":2011+i//4,
             "disciplina":names[i%4], "N1":7,"N2":7.5,"N3":8,"N4":9}
            for i in range(36)]


def test_read_history_covers_areas_only_from_pre2020(tmp_path):
    path=tmp_path/"history.csv";write_history(path,valid_history())
    entries=read_history(path);p=profile(entries)
    assert len(entries)==36
    assert set(p)=={"MATEMATICA","NATUREZA","HUMANAS","LINGUAGENS"}
    assert p["MATEMATICA"]["cases"]==9


def test_reject_2020_reference_or_duplicate_case(tmp_path):
    entries=valid_history();entries[0]["ano_letivo"]=2020;entries[0]["serie"]="1M"
    path=tmp_path/"history.csv";write_history(path,entries)
    with pytest.raises(ValueError,match="boundary"):
        read_history(path)
    entries=valid_history();entries[1]["id_caso"]=entries[0]["id_caso"]
    write_history(path,entries)
    with pytest.raises(ValueError,match="duplicate"):
        read_history(path)


def test_reject_unmapped_alias_and_out_of_range_scores(tmp_path):
    entries=valid_history();entries[0]["disciplina"]="secret course"
    path=tmp_path/"history.csv";write_history(path,entries)
    with pytest.raises(ValueError,match="unknown historical subject"):
        read_history(path)
    entries=valid_history();entries[0]["N4"]=-1
    write_history(path,entries)
    with pytest.raises(ValueError,match="invalid historical grade"):
        read_history(path)