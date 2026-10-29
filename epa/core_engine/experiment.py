"""Leakage-aware, student-grouped longitudinal baseline (synthetic only).

Target is the *next academic year's* average subject grade >= 6, NOT dropout.
This experimental target must not be confused with M1/M2/M3 TGI-I cutoffs.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

AREAS = ("MATEMATICA", "LINGUAGENS", "NATUREZA", "HUMANAS")
FEATURES = ["current_mean", "current_attendance", "history_mean", "history_slope", "years_observed"] + [f"area_{a.lower()}" for a in AREAS]
SCHEMA = "epa.genesis.dataset.v1"


def validate_artifact(path: Path) -> dict:
    manifest_path = path.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA or manifest.get("classification") != "SYNTHETIC":
        raise ValueError("only documented synthetic Genesis dataset supported")
    if manifest.get("artifact_path") != path.name or manifest.get("digest_algorithm") != "sha256":
        raise ValueError("invalid artifact contract")
    expected = manifest.get("digest")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("missing dataset digest")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    if h.hexdigest() != expected:
        raise ValueError("dataset artifact digest mismatch")
    return manifest


def snapshots(path: Path) -> list[dict]:
    """Make year-t features only, and year-(t+1) target separately."""
    validate_artifact(path)
    conn = duckdb.connect(":memory:")
    try:
        rows = conn.execute("""
            SELECT student_id, academic_year, knowledge_area, final_grade, attendance_rate
            FROM read_parquet(?) ORDER BY student_id, academic_year, knowledge_area
        """, [str(path)]).fetchall()
    finally:
        conn.close()
    per_student: dict[str, dict[int, list[tuple[str,float,float]]]] = {}
    for student, year, area, score, attendance in rows:
        if area not in AREAS or score is None or attendance is None:
            raise ValueError("invalid or missing synthetic observation")
        if not 0 <= score <= 10 or not 0 <= attendance <= 1:
            raise ValueError("value outside expected domain")
        per_student.setdefault(student, {}).setdefault(year, []).append((area,score,attendance))
    output = []
    for student, years in sorted(per_student.items()):
        ordered = sorted(years)
        history = []
        for index, year in enumerate(ordered[:-1]):
            # Only consecutive-year comparisons are supported.
            if ordered[index+1] != year + 1:
                continue
            data = years[year]
            current_mean = float(np.mean([r[1] for r in data]))
            history.append(current_mean)
            area_scores = {a: [r[1] for r in data if r[0] == a] for a in AREAS}
            row = {"student_id": student, "academic_year": year,
                   "current_mean": current_mean,
                   "current_attendance": float(np.mean([r[2] for r in data])),
                   "history_mean": float(np.mean(history)),
                   "history_slope": float(history[-1]-history[0]) / max(1,len(history)-1),
                   "years_observed": len(history)}
            row.update({f"area_{a.lower()}": float(np.mean(values)) if values else np.nan for a,values in area_scores.items()})
            future = years[year+1]
            row["target_next_year_pass"] = int(np.mean([r[1] for r in future]) >= 6.0)
            output.append(row)
        # Continue history even across missing observation years, but never create
        # a label from a non-consecutive year.
    return output


def evaluate(rows: list[dict], *, seed: int = 20261029, test_size: float = .25) -> dict:
    if len(rows) < 8:
        raise ValueError("too few longitudinal observations")
    x = np.asarray([[r[f] for f in FEATURES] for r in rows],dtype=float)
    y = np.asarray([r["target_next_year_pass"] for r in rows],dtype=int)
    groups = np.asarray([r["student_id"] for r in rows])
    if len(set(groups)) < 4:
        raise ValueError("at least 4 distinct students required")
    train, test = next(GroupShuffleSplit(n_splits=1,test_size=test_size,random_state=seed).split(x,y,groups))
    if set(groups[train]) & set(groups[test]):
        raise AssertionError("student isolation violated")
    if len(set(y[train])) < 2:
        raise ValueError("training split contains only one class: increase students or change seed")
    candidates = {
        "majority": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": make_pipeline(SimpleImputer(strategy="constant",fill_value=0),StandardScaler(),LogisticRegression(max_iter=1000,random_state=seed)),
        "random_forest": make_pipeline(SimpleImputer(strategy="constant",fill_value=0),RandomForestClassifier(n_estimators=100,random_state=seed,n_jobs=1)),
    }
    results = []
    for name, model in candidates.items():
        model.fit(x[train],y[train])
        pred = model.predict(x[test])
        results.append({
            "model":name, "accuracy":float(accuracy_score(y[test],pred)),
            "balanced_accuracy":float(balanced_accuracy_score(y[test],pred)),
            "f1_macro":float(f1_score(y[test],pred,labels=[0,1],average="macro",zero_division=0)),
            "recall_by_class":{str(i):float(v) for i,v in zip([0,1],recall_score(y[test],pred,labels=[0,1],average=None,zero_division=0))},
            "confusion_matrix":confusion_matrix(y[test],pred,labels=[0,1]).tolist()
        })
    return {
        "schema_version":"epa.core_engine.report.v1",
        "dataset_kind":"SYNTHETIC",
        "research_status":"EXPERIMENTAL_NOT_VALIDATED",
        "task":"binary_next_year_mean_grade_at_least_6",
        "split":"group_shuffle_by_student",
        "seed":seed,"features":FEATURES,
        "train_students":int(len(set(groups[train]))),"test_students":int(len(set(groups[test]))),
        "train_observations":len(train),"test_observations":len(test),
        "train_class_counts":{str(i):int((y[train]==i).sum()) for i in [0,1]},
        "test_class_counts":{str(i):int((y[test]==i).sum()) for i in [0,1]},
        "results":results,
        "caveat":"Synthetic outcomes arise from simulator rules; estimates are not evidence of real-world educational performance."
    }


def run(path: Path, seed: int = 20261029) -> dict:
    manifest = validate_artifact(path)
    report = evaluate(snapshots(path),seed=seed)
    report["input_sha256"]=manifest["digest"]
    return report
