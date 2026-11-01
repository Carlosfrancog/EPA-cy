"""MAPA Research Protocol v0.2: strictly separated synthetic research assessment.

Grouped cross-validation uses GroupKFold by student. Temporal evaluation trains
on previous-year student cohorts and tests later-year cohorts with DISJOINT IDs;
the GENESIS v2 demonstration uses the same students across all years, so that
strict temporal cohort validation is not identifiable and is transparently skipped.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, recall_score, confusion_matrix
from sklearn.model_selection import GroupKFold

from epa.core_engine.mapa import CLASSES, models, feature_vector
from epa.core_engine.mapa_uncertainty import cluster_bootstrap_f1
from epa.core_engine.student_timeline import CUTS, read_verified_v2, build_snapshots

SCHEMA = "epa.mapa.research_protocol.v2"


def _score(y_true, y_pred):
    support = {name: int(np.sum(y_true == name)) for name in CLASSES}
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1_score(y_true, y_pred, labels=CLASSES,
                                   average="macro", zero_division=0)),
        "recall_by_class": dict(zip(CLASSES, map(float, recall_score(
            y_true, y_pred, labels=CLASSES, average=None, zero_division=0)))),
        "class_support": support,
        "missing_test_classes": [k for k, n in support.items() if n == 0],
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=CLASSES).tolist(),
    }


def _mean_interval(values):
    """Distribution of folds, not a statistical population confidence interval."""
    a = np.asarray(values, dtype=float)
    return {"mean": float(np.mean(a)), "std": float(np.std(a, ddof=1)) if len(a) > 1 else 0.0,
            "min": float(np.min(a)), "max": float(np.max(a)),
            "n_folds": len(a)}


def evaluate_protocol(rows, *, cutoff, seed=20261029, n_splits=3):
    if cutoff not in CUTS.values():
        raise ValueError("invalid cutoff")
    if n_splits < 2 or n_splits > 10:
        raise ValueError("n_splits must be between 2 and 10")
    if not rows or any(s["cutoff_term"] != cutoff or s["data_classification"] != "SYNTHETIC" for s in rows):
        raise ValueError("invalid synthetic snapshots")
    groups = np.array([s["student_id"] for s in rows])
    if len(set(groups)) < n_splits:
        raise ValueError("insufficient students for grouped folds")
    x = np.asarray([feature_vector(s) for s in rows], dtype=float)
    y = np.asarray([s["target_final_subject_outcome"] for s in rows])
    if not set(y) <= set(CLASSES):
        raise ValueError("invalid target")
    years = np.asarray([s["academic_year"] for s in rows])
    folds = []
    for i, (train, test) in enumerate(GroupKFold(n_splits=n_splits).split(x, y, groups)):
        if set(groups[train]) & set(groups[test]):
            raise AssertionError("student groups overlap")
        if len(set(y[train])) < 2:
            raise ValueError("training fold has less than two observed classes")
        candidates = models(seed + i)
        for name, candidate in candidates.items():
            candidate.fit(x[train], y[train])
            folds.append({"fold": i + 1, "model": name, "train_students": len(set(groups[train])),
                          "test_students": len(set(groups[test])), "test_observations": len(test),
                          **_score(y[test], candidate.predict(x[test]))})
    summaries = []
    for model_name in ("majority", "logistic_regression", "random_forest"):
        matching = [f for f in folds if f["model"] == model_name]
        summaries.append({"model": model_name,
                          "f1_macro_fold_distribution": _mean_interval([f["f1_macro"] for f in matching]),
                          "accuracy_fold_distribution": _mean_interval([f["accuracy"] for f in matching]),
                          "missing_class_folds": sum(bool(f["missing_test_classes"]) for f in matching)})
    # Strict temporal external-cohort holdout requires unseen students in later years.
    # GENESIS v2 currently reuses the same student IDs in all years and therefore
    # does NOT meet the independent future cohort prerequisite.
    unique_years = sorted(set(years.tolist()))
    last_year = unique_years[-1]
    prior_students = set(groups[years < last_year])
    later_students = set(groups[years == last_year])
    if prior_students & later_students:
        temporal = {"status": "not_identifiable", "reason": "same_students_across_years",
                    "target_year": int(last_year), "overlapping_students": len(prior_students & later_students),
                    "message": "Sem coorte independente posterior. Não reportar generalização temporal."}
    elif not prior_students or not later_students:
        temporal = {"status": "not_identifiable", "reason": "insufficient_temporal_cohorts"}
    else:
        train = np.flatnonzero(years < last_year)
        test = np.flatnonzero(years == last_year)
        if len(set(y[train])) < 2:
            temporal = {"status": "not_identifiable", "reason": "insufficient_train_classes"}
        else:
            temporal = {"status": "evaluated", "target_year": int(last_year),
                        "train_students": len(set(groups[train])), "test_students": len(set(groups[test])),
                        "models": []}
            for name, candidate in models(seed).items():
                candidate.fit(x[train], y[train])
                predictions = candidate.predict(x[test])
                temporal["models"].append({
                    "model": name, **_score(y[test], predictions),
                    "f1_macro_cluster_interval": cluster_bootstrap_f1(
                        y[test], predictions, groups[test], seed=seed, repetitions=300),
                })
    return {
        "protocol": next(k for k, v in CUTS.items() if v == cutoff), "cutoff_term": cutoff,
        "fold_strategy": "GroupKFold_by_student", "n_splits": n_splits,
        "class_counts": dict(Counter(y.tolist())),
        "folds": folds, "summaries": summaries, "temporal_holdout": temporal,
        "interval_interpretation": "fold distribution, NOT population confidence interval",
    }


def run(directory: Path, *, seed=20261029, n_splits=3):
    data = read_verified_v2(directory)
    return {
        "schema_version": SCHEMA,
        "dataset_classification": "SYNTHETIC",
        "research_status": "EXPERIMENTAL_NOT_EMPIRICALLY_VALIDATED",
        "source_manifest_sha256": hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest(),
        "seed": seed, "protocols": [
            evaluate_protocol(build_snapshots(data, cutoff=cutoff), cutoff=cutoff,
                              seed=seed, n_splits=n_splits)
            for cutoff in CUTS.values()
        ],
        "limitations": [
            "Simulated student histories are not independent empirical evidence.",
            "Fold dispersion is not a statistical confidence interval.",
            "Overlapping students block independent temporal-cohort estimation.",
            "Cluster-bootstrap intervals are conditional on a fitted model and synthetic test-cohort sample.",
            "Class rarity can make per-class recall unstable; inspect each fold.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="MAPA independent grouped research assessment")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--folds", type=int, choices=range(2, 11), default=3)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("immutable output exists")
    report = run(args.dataset, seed=args.seed, n_splits=args.folds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
