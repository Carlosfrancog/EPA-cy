"""LUPA v0.1: permutation importance on held-out synthetic student groups.

Permuting a feature on the test set estimates score sensitivity, not causal
effect. Uses the SAME deterministic split as MAPA's baseline benchmark.
No student-level rows or predictions are emitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.inspection import permutation_importance
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import f1_score

from epa.core_engine.mapa import CLASSES, FEATURES, feature_vector, models
from epa.core_engine.student_timeline import CUTS, read_verified_v2, build_snapshots

SCHEMA = "epa.lupa.explainability.v1"


def explain_snapshots(rows: list[dict], *, cutoff: int, seed: int, repeats: int = 2) -> dict:
    if cutoff not in CUTS.values() or not 1 <= repeats <= 5:
        raise ValueError("invalid protocol or repeat count")
    if not rows or any(row["cutoff_term"] != cutoff or row["data_classification"] != "SYNTHETIC" for row in rows):
        raise ValueError("invalid snapshots")
    x = np.asarray([feature_vector(s) for s in rows], dtype=float)
    y = np.asarray([s["target_final_subject_outcome"] for s in rows])
    groups = np.asarray([s["student_id"] for s in rows])
    if len(set(groups)) < 8 or not set(y) <= set(CLASSES):
        raise ValueError("insufficient or invalid training data")
    train, test = next(GroupShuffleSplit(n_splits=1, test_size=0.25,
                                         random_state=seed).split(x, y, groups))
    if set(groups[train]) & set(groups[test]):
        raise AssertionError("student leakage")
    if len(set(y[train])) < 2:
        raise ValueError("insufficient train classes")

    estimator = models(seed)["random_forest"]
    estimator.fit(x[train], y[train])
    # Explicit estimator scorer avoids scikit-learn's implicit binary pos_label=1
    # handling with string-valued classes in some versions. The metric remains
    # macro-F1 over the same fixed three classes, including zero-support labels.
    def macro_f1(model, features, truth):
        return float(f1_score(truth, model.predict(features),
                              average="macro", labels=CLASSES, zero_division=0))

    baseline = macro_f1(estimator, x[test], y[test])
    permutation = permutation_importance(
        estimator, x[test], y[test], scoring=macro_f1, n_repeats=repeats,
        random_state=seed, n_jobs=1,
    )
    features = [
        {"name": name, "mean_f1_drop": float(permutation.importances_mean[i]),
         "std_f1_drop": float(permutation.importances_std[i])}
        for i, name in enumerate(FEATURES)
    ]
    features.sort(key=lambda f: (-f["mean_f1_drop"], f["name"]))
    return {
        "protocol": next(k for k, v in CUTS.items() if v == cutoff),
        "cutoff_term": cutoff,
        "algorithm": "random_forest",
        "split": "GroupShuffleSplit_by_student",
        "baseline_f1_macro": baseline,
        "train_students": len(set(groups[train])),
        "test_students": len(set(groups[test])),
        "test_observations": len(test),
        "class_support": {c: int(np.sum(y[test] == c)) for c in CLASSES},
        "repeats": repeats,
        "importance_method": "heldout_permutation_macro_f1",
        "features": features,
    }


def run(directory: Path, *, seed: int = 20261029, repeats: int = 2) -> dict:
    data = read_verified_v2(directory)
    return {
        "schema_version": SCHEMA,
        "dataset_classification": "SYNTHETIC",
        "research_status": "EXPERIMENTAL_NOT_EMPIRICALLY_VALIDATED",
        "source_manifest_sha256": hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest(),
        "seed": seed,
        "explanations": [
            explain_snapshots(build_snapshots(data, cutoff=cutoff),
                              cutoff=cutoff, seed=seed, repeats=repeats)
            for cutoff in CUTS.values()
        ],
        "caveat": "Permutation importance measures held-out model sensitivity, NOT causal influence. "
                  "Correlated grades and attendance may mask or redistribute importance. "
                  "Synthetic data do not establish empirical educational validity.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="LUPA held-out permutation importance")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--repeats", type=int, choices=range(1, 6), default=2)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("immutable output already exists")
    result = run(args.dataset, seed=args.seed, repeats=args.repeats)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
