"""Privacy and time boundaries for N4 calibration; no real records in repo."""
import csv
import json
from pathlib import Path

import pytest

from epa.core_engine.mapa_n4_calibration import (
    read_calibration_history, calibrate_targets, run, sha256,
)


def write_history(tmp_path, *, n=36, future=False, leak=False):
    p = tmp_path / "private-history.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id_caso", "serie", "ano_letivo", "disciplina", "N1", "N2", "N3", "N4"])
        w.writeheader()
        for i in range(n):
            year = (2020 if future and i == n - 1 else 2011 + i % 9)
            grade = 1 if year == 2020 else year - 2010
            w.writerow({"id_caso": "held-out-case" if leak and i == 0 else f"private-{i}",
                        "serie": f"{grade}{'M' if year == 2020 else 'F'}",
                        "ano_letivo": year, "disciplina": "Matemática",
                        "N1": 4, "N2": 5, "N3": 6, "N4": 7})
    return p


def test_strict_time_boundary(tmp_path):
    p = write_history(tmp_path, future=True)
    with pytest.raises(ValueError, match="pre-2020"):
        read_calibration_history(p)


def test_reject_held_out_identifiers(tmp_path):
    p = write_history(tmp_path, leak=True)
    with pytest.raises(ValueError, match="held-out"):
        read_calibration_history(p, {"held-out-case"})


def test_reject_leaky_columns(tmp_path):
    p = write_history(tmp_path)
    s = p.read_text(encoding="utf-8").replace("N4\n", "N4,MF\n", 1)
    p.write_text(s, encoding="utf-8")
    with pytest.raises(ValueError, match="exact historical columns"):
        read_calibration_history(p)


def test_calibration_identity_of_features_and_bounds(tmp_path):
    history = read_calibration_history(write_history(tmp_path))
    x = [{"mean_123": 5., "area": "MATEMATICA"}, {"mean_123": 8., "area": "MATEMATICA"}]
    y = [4., 10.]
    before = [dict(r) for r in x]
    out, audit = calibrate_targets(x, y, history)
    assert x == before and y == [4., 10.]
    assert len(out) == 2 and all(0 <= z <= 10 for z in out)
    assert audit["generator_modified"] is False
    assert audit["allowed_history_years"] == "2011-2019"


def test_insufficient_history(tmp_path):
    with pytest.raises(ValueError, match="insufficient"):
        read_calibration_history(write_history(tmp_path, n=12))


def test_deterministic_overlay(tmp_path):
    history = read_calibration_history(write_history(tmp_path))
    xs = [{"mean_123": 5., "area": "MATEMATICA"} for _ in range(40)]
    ys = [6.] * 40
    a = calibrate_targets(xs, ys, history)
    assert a == calibrate_targets(xs, ys, history)


def test_integration_unmodified_genesis(tmp_path):
    # Purely fabricated test cases; no real records / answer key in CI.
    history = write_history(tmp_path)
    inputs = tmp_path / "private-inputs.csv"
    with inputs.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=["id_caso","serie","ano_letivo","disciplina","N1","N2","N3"])
        w.writeheader()
        for s,year in (("1M",2020),("2M",2021),("3M",2022)):
            for i, subject in enumerate(["Matemática","Português","Física","Química","Biologia","História","Geografia","Filosofia","Sociologia","Artes","Inglês","Educação Física"]):
                w.writerow({"id_caso":f"{s}-{i}","serie":s,"ano_letivo":year,"disciplina":subject,"N1":4,"N2":5,"N3":6})
    catalog = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"
    if not catalog.exists():
        pytest.skip("official demo catalog unavailable in isolated test fixture")
    result, cases = run(catalog, inputs, history, students=16, seed=9,
                        algorithms=("baseline_n3","baseline_mean","linear"))
    assert result["status"] == "PREDICTIONS_ONLY_NO_LABELS_LOADED"
    assert result["input_count"] == len(cases) == 36
    assert result["calibration"]["real_history_count"] == 36
    assert all(row["original__baseline_n3"] == row["calibrated__baseline_n3"] for row in cases)
    assert all(row["original__baseline_mean"] == row["calibrated__baseline_mean"] for row in cases)
    assert "comparison" not in result