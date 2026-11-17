"""EPIC #77 synthetic-only nested grouped MAPA robustness study.

Outer student-disjoint holdout is never used for hyperparameter selection.
Inner GroupKFold exclusively on outer-training students selects fixed candidate grids.
Shuffled-label sanity test permutes OUTER TRAIN labels only, without touching test.
No real-student files are accepted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from epa.core_engine.mapa import CLASSES, FEATURES, feature_vector
from epa.core_engine.student_timeline import CUTS, build_snapshots, read_verified_v2

SCHEMA = "epa.mapa.robustness.v1"
SEEDS = (20261029, 20261030, 20261031)
GRIDS = {
    "logistic_regression": ({"C": .1}, {"C": 1.0}, {"C": 10.0}),
    "random_forest": ({"min_samples_leaf": 1}, {"min_samples_leaf": 4}, {"min_samples_leaf": 8}),
}


def _model(name: str, seed: int, params: dict | None = None):
    params = params or {}
    if name == "majority":
        return DummyClassifier(strategy="most_frequent")
    if name == "logistic_regression":
        return make_pipeline(SimpleImputer(strategy="constant", fill_value=0), StandardScaler(),
                             LogisticRegression(C=params.get("C", 1.0), max_iter=1500,
                                                random_state=seed))
    if name == "random_forest":
        return make_pipeline(SimpleImputer(strategy="constant", fill_value=0),
                             RandomForestClassifier(n_estimators=100, max_depth=12,
                                 min_samples_leaf=params.get("min_samples_leaf", 1),
                                 random_state=seed, n_jobs=1))
    raise ValueError("unknown classifier")


def _metric(actual, predicted):
    return {"accuracy": float(accuracy_score(actual, predicted)),
            "f1_macro": float(f1_score(actual, predicted, average="macro",
                                       labels=CLASSES, zero_division=0))}


def _digest(indices):
    return hashlib.sha256(json.dumps(list(map(int, indices)), separators=(",", ":")).encode()).hexdigest()


def evaluate(snapshots: list[dict], *, cutoff: int, seeds=SEEDS,
             inner_folds: int = 3, test_size: float = .25) -> dict:
    if cutoff not in CUTS.values() or not snapshots or any(r.get("cutoff_term") != cutoff or
            r.get("data_classification") != "SYNTHETIC" for r in snapshots):
        raise ValueError("only matching synthetic cutoff snapshots accepted")
    if not 2 <= inner_folds <= 5 or not .1 <= test_size <= .4:
        raise ValueError("invalid research budget / group fraction")
    if not seeds or len(seeds) > 5 or len(set(seeds)) != len(seeds) or any(type(s) is not int for s in seeds):
        raise ValueError("seed budget must contain distinct integers (1..5)")
    groups = np.asarray([r["student_id"] for r in snapshots]); years = np.asarray([r["academic_year"] for r in snapshots])
    if len(set(groups)) < max(8, inner_folds + 2) or any(not isinstance(v, str) or not v.startswith("SYN") for v in groups):
        raise ValueError("insufficient synthetic student clusters")
    x = np.asarray([feature_vector(r) for r in snapshots], dtype=float)
    y = np.asarray([r["target_final_subject_outcome"] for r in snapshots])
    if set(y) - set(CLASSES) or len(set(y)) < 2:
        raise ValueError("invalid synthetic target classes")
    outputs = []
    for seed in seeds:
        train, test = next(GroupShuffleSplit(n_splits=1, test_size=test_size,
                                    random_state=seed).split(x, y, groups))
        if set(groups[train]) & set(groups[test]):
            raise AssertionError("outer student identity leakage")
        if len(set(groups[train])) < inner_folds or len(set(y[train])) < 2:
            raise ValueError("outer training groups/classes insufficient")
        outcome = {"seed": seed, "split_strategy": "outer_GroupShuffleSplit_inner_GroupKFold",
                   "outer_train_students": len(set(groups[train])), "outer_test_students": len(set(groups[test])),
                   "train_indices_sha256": _digest(train), "test_indices_sha256": _digest(test),
                   "train_years": sorted(map(int, set(years[train]))),
                   "test_years": sorted(map(int, set(years[test]))), "models": []}
        for model_name in ("majority", "logistic_regression", "random_forest"):
            trials = []
            params_set = ({},) if model_name == "majority" else GRIDS[model_name]
            for params in params_set:
                scores = []
                for itrain, ivalid in GroupKFold(n_splits=inner_folds).split(
                        x[train], y[train], groups[train]):
                    if set(groups[train][itrain]) & set(groups[train][ivalid]):
                        raise AssertionError("inner identity leakage")
                    if len(set(y[train][itrain])) < 2:
                        raise ValueError("inner fold has insufficient training classes")
                    model = _model(model_name, seed, params)
                    model.fit(x[train][itrain], y[train][itrain])
                    scores.append(_metric(y[train][ivalid], model.predict(x[train][ivalid]))["f1_macro"])
                trials.append({"params": params, "inner_f1_macro_mean": float(np.mean(scores)),
                               "inner_f1_macro_std": float(np.std(scores, ddof=1)),
                               "inner_fold_scores": scores})
            # Deterministic tie break by predeclared candidate order; NO test metrics consulted.
            best_idx = max(range(len(trials)), key=lambda i: (trials[i]["inner_f1_macro_mean"], -i))
            chosen = trials[best_idx]["params"]
            fitted = _model(model_name, seed, chosen).fit(x[train], y[train])
            train_score = _metric(y[train], fitted.predict(x[train]))
            test_score = _metric(y[test], fitted.predict(x[test]))
            # Negative control: training labels independently permuted, untouched test.
            rng = np.random.default_rng(seed + 404)
            permuted = y[train][rng.permutation(len(train))]
            shuffled = _model(model_name, seed, chosen).fit(x[train], permuted)
            shuffled_score = _metric(y[test], shuffled.predict(x[test]))
            outcome["models"].append({"model": model_name, "chosen_params": chosen,
                "inner_selection": trials, "train": train_score, "heldout": test_score,
                "train_minus_test_f1_macro": train_score["f1_macro"] - test_score["f1_macro"],
                "shuffled_train_labels_test": shuffled_score,
                "shuffled_label_control": "permutation_of_outer_train_only",
                "outer_test_used_for_selection": False})
        outputs.append(outcome)
    summary = []
    for name in ("majority", "logistic_regression", "random_forest"):
        rows = [next(m for m in o["models"] if m["model"] == name) for o in outputs]
        f1 = [r["heldout"]["f1_macro"] for r in rows]
        null = [r["shuffled_train_labels_test"]["f1_macro"] for r in rows]
        summary.append({"model": name, "n_seeds": len(seeds),
                        "heldout_f1_macro_mean": float(np.mean(f1)),
                        "heldout_f1_macro_sd": float(np.std(f1, ddof=1)) if len(f1) > 1 else None,
                        "shuffled_f1_macro_mean": float(np.mean(null)),
                        "train_test_gap_mean": float(np.mean([r["train_minus_test_f1_macro"] for r in rows]))})
    return {"schema_version": SCHEMA, "dataset_classification": "SYNTHETIC",
            "research_status": "SYNTHETIC_ROBUSTNESS_NOT_EXTERNAL_VALIDATION",
            "target": "same_year_final_subject_outcome_3class", "cutoff_term": cutoff,
            "seeds": list(seeds), "feature_names": list(FEATURES),
            "outer_split": "student_grouped_random_holdout_not_temporal",
            "inner_split": "group_kfold_on_outer_train_only", "inner_folds": inner_folds,
            "candidate_grids": {k: list(v) for k, v in GRIDS.items()},
            "repetitions": outputs, "summary": summary,
            "limitations": ["Synthetic data only; not evidence of school population accuracy.",
                 "Repeated seeds/folds are dependent; SD is dispersion not population CI.",
                 "Permutation diagnostic is not a statistical leakage proof.",
                 "Outer heldouts overlap across seeds; no nested uncertainty claim.",
                 "No temporal generalization claim; see EPIC77 protocol B."]}


def run(dataset: Path, *, seeds=SEEDS, inner_folds=3) -> dict:
    dataset = Path(dataset)
    data = read_verified_v2(dataset)
    results = [evaluate(build_snapshots(data, cutoff=c), cutoff=c,
                        seeds=seeds, inner_folds=inner_folds) for c in CUTS.values()]
    return {"schema_version": SCHEMA, "dataset_manifest_sha256": hashlib.sha256(
                (dataset / "manifest.json").read_bytes()).hexdigest(),
            "dataset_classification": "SYNTHETIC", "seeds": list(seeds),
            "results": results}


def main():
    p = argparse.ArgumentParser(description="EPIC77 nested grouped synthetic robustness")
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    p.add_argument("--inner-folds", type=int, default=3)
    p.add_argument("--report", required=True, type=Path)
    args = p.parse_args()
    if args.report.exists() or args.report.is_symlink():
        p.error("immutable experiment output already exists")
    result = run(args.dataset, seeds=tuple(args.seeds), inner_folds=args.inner_folds)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False); f.write("\n")
    print(json.dumps({"schema_version": SCHEMA,
                      "cutoffs": [r["cutoff_term"] for r in result["results"]],
                      "seeds": result["seeds"]}))


if __name__ == "__main__":
    main()