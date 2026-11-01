"""MAPA Core v0.1 — grouped synthetic 3-class research benchmarks.

Trains distinct classifiers for each N1/N2/N3 prediction cutoff.
Results are NOT empirical evidence of model efficacy in real schools.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, recall_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from epa.core_engine.student_timeline import CUTS, read_verified_v2, build_snapshots

CLASSES = ("approved", "recovery", "failed")
FEATURES = (
    "current_mean_grade", "current_attendance_rate", "current_absences",
    "current_unexcused_absences", "current_sessions", "prior_mean_grade",
    "prior_attendance_rate", "prior_absences", "prior_unexcused_absences",
    "prior_term_count", "prior_years_observed",
)
SCHEMA = "epa.mapa.benchmark.v1"


def feature_vector(snapshot: dict) -> list[float]:
    """Allowlist ONLY permitted timestamped features; no target/IDs/future records."""
    current = snapshot["current"]
    prior = snapshot["prior_same_subject"]
    return [
        float(current["mean_grade"]), float(current["attendance_rate"]),
        float(current["absences_total"]), float(current["absences_unexcused"]),
        float(current["scheduled_sessions"]),
        float(prior["mean_grade"]) if prior else np.nan,
        float(prior["attendance_rate"]) if prior else np.nan,
        float(prior["absences_total"]) if prior else np.nan,
        float(prior["absences_unexcused"]) if prior else np.nan,
        float(prior["term_count"]) if prior else 0.0,
        float(snapshot["prior_years_observed"]),
    ]


def models(seed: int) -> dict:
    return {
        "majority": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": make_pipeline(
            SimpleImputer(strategy="constant", fill_value=0),
            StandardScaler(),
            LogisticRegression(max_iter=1500, random_state=seed),
        ),
        "random_forest": make_pipeline(
            SimpleImputer(strategy="constant", fill_value=0),
            RandomForestClassifier(n_estimators=200, random_state=seed, n_jobs=1),
        ),
    }


def evaluate(snapshots: list[dict], *, cutoff: int, seed: int = 20261029,
             test_size: float = 0.25) -> dict:
    if cutoff not in CUTS.values():
        raise ValueError("invalid MAPA cutoff")
    if not 0 < test_size < 1:
        raise ValueError("invalid test fraction")
    if not snapshots or any(s["cutoff_term"] != cutoff for s in snapshots):
        raise ValueError("snapshots have incompatible cutoff")
    if any(s["data_classification"] != "SYNTHETIC" for s in snapshots):
        raise ValueError("only synthetic data supported")
    groups = np.asarray([s["student_id"] for s in snapshots])
    if len(set(groups)) < 8:
        raise ValueError("at least eight students required")
    x = np.asarray([feature_vector(s) for s in snapshots], dtype=float)
    y = np.asarray([s["target_final_subject_outcome"] for s in snapshots])
    if not set(y) <= set(CLASSES):
        raise ValueError("invalid label")
    train, test = next(GroupShuffleSplit(n_splits=1, test_size=test_size,
                                         random_state=seed).split(x, y, groups))
    train_students = set(groups[train])
    test_students = set(groups[test])
    if train_students & test_students:
        raise AssertionError("student leakage")
    if len(set(y[train])) < 2:
        raise ValueError("training data have fewer than two observed classes")
    results = []
    for model_name, estimator in models(seed).items():
        estimator.fit(x[train], y[train])
        predicted = estimator.predict(x[test])
        results.append({
            "model": model_name,
            "accuracy": float(accuracy_score(y[test], predicted)),
            "balanced_accuracy": float(balanced_accuracy_score(y[test], predicted)),
            "f1_macro": float(f1_score(y[test], predicted, labels=CLASSES,
                                       average="macro", zero_division=0)),
            "recall_by_class": {cls: float(v) for cls, v in zip(
                CLASSES, recall_score(y[test], predicted, labels=CLASSES,
                                     average=None, zero_division=0))},
            "confusion_matrix": confusion_matrix(y[test], predicted, labels=CLASSES).tolist(),
        })
    return {
        "cutoff_term": cutoff,
        "protocol": next(name for name, term in CUTS.items() if term == cutoff),
        "seed": seed, "split": "GroupShuffleSplit_by_student",
        "feature_names": list(FEATURES), "classes": list(CLASSES),
        "train_students": len(train_students), "test_students": len(test_students),
        "train_observations": len(train), "test_observations": len(test),
        "train_class_counts": {cls: int((y[train] == cls).sum()) for cls in CLASSES},
        "test_class_counts": {cls: int((y[test] == cls).sum()) for cls in CLASSES},
        "results": results,
    }


def run(directory: Path, *, seed: int = 20261029) -> dict:
    """One verified dataset, one group split seed, three independent cutoff studies."""
    import hashlib
    data = read_verified_v2(directory)
    reports = [evaluate(build_snapshots(data, cutoff=term), cutoff=term, seed=seed)
               for term in CUTS.values()]
    return {
        "schema_version": SCHEMA,
        "dataset_classification": "SYNTHETIC",
        "research_status": "EXPERIMENTAL_NOT_EMPIRICALLY_VALIDATED",
        "task": "final_subject_grade_3class",
        "target_policy": "SYNTHETIC illustrative thresholds: approved >=6; recovery >=4; failed <4",
        "dataset_manifest_sha256": hashlib.sha256(
            (directory / "manifest.json").read_bytes()).hexdigest(),
        "baselines": reports,
        "caveat": "Synthetic generator outcomes are not empirical model effectiveness. "
                  "No dropout labels or inference. Macro F1 includes all three classes; "
                  "absent classes yield zero recall; see per-cutoff class counts.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="MAPA synthetic N1/N2/N3 benchmark")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mlflow-uri", type=str, default=None,
                        help="Optional MLflow tracking URI (for example sqlite:///data/mlflow.db)")
    parser.add_argument("--mlflow-experiment", type=str, default="EPA MAPA Synthetic")
    parser.add_argument("--mlflow-link-output", type=Path, default=None,
                        help="Optional immutable JSON link manifest for the parent Rails run")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output exists; benchmark reports are immutable")
    if args.mlflow_link_output and not args.mlflow_uri:
        parser.error("link output requires --mlflow-uri")
    if args.mlflow_link_output and args.mlflow_link_output.exists():
        parser.error("MLflow link output already exists")
    result = run(args.dataset, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.mlflow_uri:
        from epa.core_engine.mapa_tracking import log_benchmark
        ids = log_benchmark(result, tracking_uri=args.mlflow_uri,
                            experiment_name=args.mlflow_experiment,
                            report_path=args.output)
        if args.mlflow_link_output:
            import hashlib
            pairs = [(block["protocol"], model["model"])
                     for block in result["baselines"] for model in block["results"]]
            if len(ids) != len(pairs):
                raise RuntimeError("incomplete MLflow run links")
            links = {
                "schema_version": "epa.mapa.mlflow_links.v1",
                "report_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
                "runs": [{"protocol": protocol, "model": model, "run_id": run_id}
                         for (protocol, model), run_id in zip(pairs, ids)],
            }
            args.mlflow_link_output.parent.mkdir(parents=True, exist_ok=True)
            with args.mlflow_link_output.open("x", encoding="utf-8") as stream:
                json.dump(links, stream, ensure_ascii=False, indent=2)
                stream.write("\\n")


if __name__ == "__main__":
    main()
