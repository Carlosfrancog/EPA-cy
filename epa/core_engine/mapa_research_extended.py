"""Extended grouped and temporal research protocol for synthetic classifiers.

Preserves the v2 three-model report and uses its same split semantics.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import LabelEncoder
from epa.core_engine.mapa import CLASSES, feature_vector
from epa.core_engine.mapa_extended import candidates
from epa.core_engine.mapa_research import _score, _mean_interval
from epa.core_engine.mapa_uncertainty import cluster_bootstrap_f1
from epa.core_engine.student_timeline import CUTS, build_snapshots, read_verified_v2

SCHEMA = "epa.mapa.research_extended.v1"


def fit_predict(name, model, train_x, train_y, test_x):
    if name == "xgboost":
        if len(set(train_y)) < len(CLASSES):
            return None
        encoder = LabelEncoder().fit(CLASSES)
        model.fit(train_x, encoder.transform(train_y))
        return encoder.inverse_transform(model.predict(test_x).astype(int))
    model.fit(train_x, train_y)
    return model.predict(test_x)


def evaluate(rows, *, cutoff, seed=20261029, folds=3, xgboost=False):
    if cutoff not in CUTS.values() or not 2 <= folds <= 10:
        raise ValueError("invalid cutoff or folds")
    if not rows or any(r["cutoff_term"] != cutoff or r["data_classification"] != "SYNTHETIC" for r in rows):
        raise ValueError("invalid synthetic rows")
    x = np.asarray([feature_vector(r) for r in rows], dtype=float)
    y = np.asarray([r["target_final_subject_outcome"] for r in rows])
    groups = np.asarray([r["student_id"] for r in rows])
    years = np.asarray([r["academic_year"] for r in rows])
    if not set(y) <= set(CLASSES) or len(set(groups)) < folds:
        raise ValueError("invalid labels or student groups")
    names = list(candidates(seed, include_xgboost=xgboost))
    observations = []
    for index, (train, test) in enumerate(GroupKFold(n_splits=folds).split(x, y, groups)):
        if set(groups[train]) & set(groups[test]) or len(set(y[train])) < 2:
            raise ValueError("invalid grouped fold")
        for name, model in candidates(seed + index, include_xgboost=xgboost).items():
            predicted = fit_predict(name, model, x[train], y[train], x[test])
            if predicted is None:
                observations.append({"fold": index + 1, "model": name, "status": "skipped",
                                     "reason": "missing_training_class"})
            else:
                observations.append({"fold": index + 1, "model": name, "status": "evaluated",
                                     "train_students": len(set(groups[train])),
                                     "test_students": len(set(groups[test])),
                                     **_score(y[test], predicted)})
    summaries = []
    for name in names:
        subset = [v for v in observations if v["model"] == name and v["status"] == "evaluated"]
        if not subset:
            summaries.append({"model": name, "status": "skipped", "missing_class_folds": folds})
        else:
            summaries.append({"model": name, "status": "evaluated",
                              "f1_macro_fold_distribution": _mean_interval([v["f1_macro"] for v in subset]),
                              "accuracy_fold_distribution": _mean_interval([v["accuracy"] for v in subset]),
                              "missing_class_folds": folds - len(subset) + sum(
                                  bool(v["missing_test_classes"]) for v in subset)})
    last = max(years)
    past = set(groups[years < last])
    future = set(groups[years == last])
    if past & future:
        temporal = {"status": "not_identifiable", "reason": "same_students_across_years"}
    elif not past or not future:
        temporal = {"status": "not_identifiable", "reason": "insufficient_temporal_cohorts"}
    else:
        train, test = np.flatnonzero(years < last), np.flatnonzero(years == last)
        if len(set(y[train])) < 2:
            temporal = {"status": "not_identifiable", "reason": "insufficient_train_classes"}
        else:
            temporal = {"status": "evaluated", "test_year": int(last), "models": []}
            for name, model in candidates(seed, include_xgboost=xgboost).items():
                predicted = fit_predict(name, model, x[train], y[train], x[test])
                if predicted is None:
                    temporal["models"].append({"model": name, "status": "skipped",
                                               "reason": "missing_training_class"})
                else:
                    temporal["models"].append({
                        "model": name, "status": "evaluated", **_score(y[test], predicted),
                        "f1_macro_cluster_interval": cluster_bootstrap_f1(
                            y[test], predicted, groups[test], seed=seed, repetitions=300),
                    })
    return {"cutoff_term": cutoff,
            "protocol": next(k for k, v in CUTS.items() if v == cutoff),
            "algorithms": names, "fold_strategy": "GroupKFold_by_student",
            "n_splits": folds, "folds": observations, "summaries": summaries,
            "temporal_holdout": temporal}


def run(directory: Path, *, seed=20261029, folds=3, xgboost=False):
    dataset = read_verified_v2(directory)
    return {
        "schema_version": SCHEMA, "dataset_classification": "SYNTHETIC",
        "research_status": "EXPERIMENTAL_NOT_EMPIRICALLY_VALIDATED",
        "source_manifest_sha256": hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest(),
        "seed": seed, "algorithms": ["mlp"] + (["xgboost"] if xgboost else []),
        "protocols": [evaluate(build_snapshots(dataset, cutoff=term), cutoff=term,
                               seed=seed, folds=folds, xgboost=xgboost) for term in CUTS.values()],
        "caveat": "Synthetic grouped CV and conditional temporal bootstrap are not external validation. "
                  "No model is approved for operational prediction.",
    }


def main():
    parser = argparse.ArgumentParser(description="MAPA extended research evaluation")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--folds", type=int, choices=range(2, 11), default=3)
    parser.add_argument("--xgboost", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("immutable report already exists")
    report = run(args.dataset, seed=args.seed, folds=args.folds, xgboost=args.xgboost)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
