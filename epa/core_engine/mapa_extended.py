"""Optional MAPA extended classifiers; baseline report contracts remain frozen.

MLP is available through sklearn; XGBoost is opt-in and requires the extra.
These candidates are evaluated on exactly the baseline GroupShuffleSplit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from epa.core_engine.mapa import CLASSES, FEATURES, feature_vector
from epa.core_engine.student_timeline import CUTS, build_snapshots, read_verified_v2

SCHEMA = "epa.mapa.extended_models.v1"


def candidates(seed: int, *, include_xgboost: bool = False):
    result = {
        "mlp": make_pipeline(
            SimpleImputer(strategy="constant", fill_value=0),
            StandardScaler(),
            MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=300,
                          early_stopping=False, random_state=seed),
        ),
    }
    if include_xgboost:
        try:
            from xgboost import XGBClassifier
        except ImportError as exc:
            raise RuntimeError("Install optional XGBoost: pip install -e '.[boosting]'") from exc
        result["xgboost"] = make_pipeline(
            SimpleImputer(strategy="constant", fill_value=0),
            XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.05,
                          objective="multi:softprob", eval_metric="mlogloss",
                          n_jobs=1, random_state=seed),
        )
    return result


def evaluate(rows, *, cutoff: int, seed: int, include_xgboost: bool = False):
    if cutoff not in CUTS.values() or not rows:
        raise ValueError("invalid cutoff")
    if any(r["cutoff_term"] != cutoff or r["data_classification"] != "SYNTHETIC" for r in rows):
        raise ValueError("incompatible snapshots")
    x = np.asarray([feature_vector(r) for r in rows], dtype=float)
    y = np.asarray([r["target_final_subject_outcome"] for r in rows])
    groups = np.asarray([r["student_id"] for r in rows])
    if len(set(groups)) < 8 or not set(y) <= set(CLASSES):
        raise ValueError("invalid student groups or labels")
    train, test = next(GroupShuffleSplit(n_splits=1, test_size=.25,
                                         random_state=seed).split(x, y, groups))
    if set(groups[train]) & set(groups[test]) or len(set(y[train])) < 2:
        raise ValueError("invalid grouped split")
    results = []
    for name, model in candidates(seed, include_xgboost=include_xgboost).items():
        if name == "xgboost":
            encoder = LabelEncoder().fit(CLASSES)
            if len(set(y[train])) < len(CLASSES):
                results.append({"model": name, "status": "skipped",
                                "reason": "xgboost_requires_all_three_training_classes"})
                continue
            model.fit(x[train], encoder.transform(y[train]))
            predicted = encoder.inverse_transform(model.predict(x[test]).astype(int))
        else:
            model.fit(x[train], y[train])
            predicted = model.predict(x[test])
        results.append({
            "model": name, "status": "evaluated",
            "accuracy": float(accuracy_score(y[test], predicted)),
            "balanced_accuracy": float(balanced_accuracy_score(y[test], predicted)),
            "f1_macro": float(f1_score(y[test], predicted, labels=CLASSES,
                                       average="macro", zero_division=0)),
            "recall_by_class": {label: float(score) for label, score in zip(
                CLASSES, recall_score(y[test], predicted, labels=CLASSES,
                                      average=None, zero_division=0))},
            "confusion_matrix": confusion_matrix(y[test], predicted, labels=CLASSES).tolist(),
        })
    return {
        "protocol": next(key for key, term in CUTS.items() if term == cutoff),
        "cutoff_term": cutoff, "seed": seed,
        "split": "GroupShuffleSplit_by_student",
        "feature_names": list(FEATURES),
        "train_students": len(set(groups[train])),
        "test_students": len(set(groups[test])),
        "test_class_counts": {label: int(np.sum(y[test] == label)) for label in CLASSES},
        "results": results,
    }


def run(directory: Path, *, seed: int = 20261029, include_xgboost: bool = False):
    data = read_verified_v2(directory)
    return {
        "schema_version": SCHEMA, "dataset_classification": "SYNTHETIC",
        "research_status": "EXPERIMENTAL_NOT_EMPIRICALLY_VALIDATED",
        "source_manifest_sha256": hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest(),
        "algorithms": ["mlp"] + (["xgboost"] if include_xgboost else []),
        "protocols": [
            evaluate(build_snapshots(data, cutoff=term), cutoff=term, seed=seed,
                     include_xgboost=include_xgboost)
            for term in CUTS.values()
        ],
        "caveat": "Research-only models on synthetic data. Same grouped holdout as baseline; "
                  "not a separate validation or statistical superiority test.",
    }


def main():
    parser = argparse.ArgumentParser(description="Optional MAPA model comparison")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--xgboost", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("immutable report already exists")
    result = run(args.dataset, seed=args.seed, include_xgboost=args.xgboost)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
