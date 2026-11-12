"""Exploratory grouped MLP convergence experiment; no production model changes.

Uses one outer student-disjoint holdout and an inner grouped validation split
for choosing the iteration budget. The outer test is evaluated only after
selection; this is exploratory synthetic evidence, not external validation.
"""
from __future__ import annotations

import argparse
import json
import time
import warnings
from pathlib import Path

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.metrics import f1_score, accuracy_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset
from epa.core_engine.mapa import CLASSES, FEATURES, feature_vector
from epa.core_engine.student_timeline import build_snapshots

SCHEMA = "epa.research.mlp_convergence.v1"
ROOT = Path(__file__).resolve().parents[2]
BUDGETS = (300, 600, 1000)


def mlp(seed: int, max_iter: int):
    # Keep the fixed 11-column contract even if a cohort has no past history.
    return make_pipeline(
        SimpleImputer(strategy="constant", fill_value=0, keep_empty_features=True),
        StandardScaler(),
        MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=max_iter,
                      early_stopping=False, random_state=seed),
    )


def _groupsplit(x, y, groups, seed: int):
    train, test = next(GroupShuffleSplit(
        n_splits=1, test_size=0.25, random_state=seed,
    ).split(x, y, groups))
    if set(groups[train]) & set(groups[test]):
        raise AssertionError("student leakage")
    if len(set(y[train])) < 2:
        raise ValueError("training fold has fewer than two classes")
    return train, test


def _fit(model, x, y):
    start = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(x, y)
    fitted = model.named_steps["mlpclassifier"]
    return {
        "wall_seconds": time.perf_counter() - start,
        "n_iter": int(fitted.n_iter_),
        "loss": float(fitted.loss_),
        "convergence_warning": any(
            issubclass(w.category, ConvergenceWarning) for w in caught
        ),
        "warnings": [type(w.message).__name__ for w in caught],
        "features_out": int(model.named_steps["simpleimputer"].transform(x[:1]).shape[1]),
    }


def evaluate_cutoff(rows: list[dict], *, cutoff: int, seed: int, budgets=BUDGETS) -> dict:
    if not rows or any(row["cutoff_term"] != cutoff or row["data_classification"] != "SYNTHETIC"
                       for row in rows):
        raise ValueError("invalid synthetic snapshots")
    if not budgets or any(b < 1 for b in budgets) or len(set(budgets)) != len(budgets):
        raise ValueError("invalid iteration budgets")
    x = np.asarray([feature_vector(row) for row in rows], dtype=float)
    y = np.asarray([row["target_final_subject_outcome"] for row in rows])
    groups = np.asarray([row["student_id"] for row in rows])
    if x.shape[1] != len(FEATURES) or len(set(groups)) < 12 or not set(y) <= set(CLASSES):
        raise ValueError("invalid data")
    outer_train, outer_test = _groupsplit(x, y, groups, seed)
    inner_local_train, inner_local_val = _groupsplit(
        x[outer_train], y[outer_train], groups[outer_train], seed + 1)
    inner_train = outer_train[inner_local_train]
    inner_val = outer_train[inner_local_val]
    if set(groups[inner_train]) & set(groups[inner_val]) or set(groups[outer_train]) & set(groups[outer_test]):
        raise AssertionError("overlapping students")
    trials = []
    for budget in budgets:
        estimator = mlp(seed, budget)
        fit = _fit(estimator, x[inner_train], y[inner_train])
        predicted = estimator.predict(x[inner_val])
        trials.append({
            "max_iter": budget,
            "fit": fit,
            "validation_f1_macro": float(f1_score(
                y[inner_val], predicted, labels=CLASSES, average="macro", zero_division=0)),
        })
    # The outer test never participates in hyperparameter selection.
    chosen = sorted(trials, key=lambda r: (-r["validation_f1_macro"], r["max_iter"]))[0]
    final_model = mlp(seed, chosen["max_iter"])
    final_fit = _fit(final_model, x[outer_train], y[outer_train])
    predicted = final_model.predict(x[outer_test])
    return {
        "cutoff": cutoff, "seed": seed,
        "train_students": len(set(groups[inner_train])),
        "validation_students": len(set(groups[inner_val])),
        "outer_train_students": len(set(groups[outer_train])),
        "outer_test_students": len(set(groups[outer_test])),
        "split": "nested_grouped_holdout_by_student",
        "features": list(FEATURES),
        "trials": trials,
        "selected_max_iter": chosen["max_iter"],
        "final_fit": final_fit,
        "heldout_f1_macro": float(f1_score(
            y[outer_test], predicted, labels=CLASSES, average="macro", zero_division=0)),
        "heldout_accuracy": float(accuracy_score(y[outer_test], predicted)),
        "heldout_class_support": {
            c: int(np.sum(y[outer_test] == c)) for c in CLASSES
        },
    }


def run(*, catalog: Path, students: int, seed: int, cutoffs=(1, 2, 3)) -> dict:
    if students < 24 or students > 2000 or not cutoffs or any(c not in (1, 2, 3) for c in cutoffs):
        raise ValueError("students 24..2000 and cutoffs 1/2/3 required")
    data = build_dataset(load_catalog(catalog), students=students, seed=seed, start_year=2020)
    return {
        "schema_version": SCHEMA,
        "classification": "SYNTHETIC",
        "students": students,
        "seed": seed,
        "budgets": list(BUDGETS),
        "cutoffs": [evaluate_cutoff(build_snapshots(data, cutoff=c), cutoff=c, seed=seed)
                    for c in cutoffs],
        "limitations": [
            "One synthetic dataset and one nested split; exploratory, not external validation.",
            "Do not choose training budgets based on the outer heldout score.",
            "keep_empty_features=True is experimental and preserves the 11 feature columns.",
            "Wall-clock fit timings are diagnostic, not a hardware benchmark.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=ROOT / "examples/atlas.demo.json")
    parser.add_argument("--students", type=int, default=24)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--cutoffs", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(catalog=args.catalog, students=args.students,
                 seed=args.seed, cutoffs=tuple(args.cutoffs))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(f"PASS: exploratory MLP report saved to {args.output}")


if __name__ == "__main__":
    main()
