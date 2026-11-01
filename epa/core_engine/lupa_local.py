"""LUPA v0.3: synthetic holdout error inspection, without student identifiers.

Local sensitivity: replacing one feature by its training median is diagnostic,
not a causal intervention or an actionable recommendation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import confusion_matrix, f1_score
from epa.core_engine.mapa import CLASSES, FEATURES, feature_vector, models
from epa.core_engine.student_timeline import CUTS, build_snapshots, read_verified_v2

SCHEMA = "epa.lupa.local_diagnostics.v1"


def inspect(rows, *, cutoff: int, seed: int, max_cases: int = 12):
    if cutoff not in CUTS.values() or not 1 <= max_cases <= 30:
        raise ValueError("invalid cutoff or sample limit")
    if not rows or any(r["cutoff_term"] != cutoff or r["data_classification"] != "SYNTHETIC" for r in rows):
        raise ValueError("invalid synthetic rows")
    x = np.asarray([feature_vector(r) for r in rows], dtype=float)
    y = np.asarray([r["target_final_subject_outcome"] for r in rows])
    groups = np.asarray([r["student_id"] for r in rows])
    if len(set(groups)) < 8 or not set(y) <= set(CLASSES):
        raise ValueError("invalid labels or student groups")
    train, test = next(GroupShuffleSplit(n_splits=1, test_size=.25,
                                         random_state=seed).split(x, y, groups))
    if set(groups[train]) & set(groups[test]) or len(set(y[train])) < 2:
        raise ValueError("invalid split")
    model = models(seed)["random_forest"]
    model.fit(x[train], y[train])
    predicted = model.predict(x[test])
    probabilities = model.predict_proba(x[test])
    labels = list(model.classes_)
    medians = np.nanmedian(x[train], axis=0)
    medians = np.nan_to_num(medians, nan=0.0)
    cases = []
    errors = [i for i in range(len(test)) if predicted[i] != y[test[i]]]
    for i in errors[:max_cases]:
        sample = x[test[i]].copy()
        original_class = str(predicted[i])
        original_probability = float(probabilities[i, labels.index(original_class)])
        changes = []
        for j, feature in enumerate(FEATURES):
            changed = sample.copy()
            changed[j] = medians[j]
            alternate = float(model.predict_proba(changed.reshape(1, -1))[0, labels.index(original_class)])
            changes.append({"feature": feature, "probability_delta": float(alternate - original_probability)})
        changes.sort(key=lambda v: (-abs(v["probability_delta"]), v["feature"]))
        cases.append({
            "case_number": len(cases) + 1,
            "actual": str(y[test[i]]), "predicted": original_class,
            "predicted_probability": original_probability,
            "top_sensitivities": changes[:3],
        })
    matrix = confusion_matrix(y[test], predicted, labels=CLASSES).tolist()
    return {
        "protocol": next(k for k, term in CUTS.items() if term == cutoff),
        "cutoff_term": cutoff, "algorithm": "random_forest",
        "test_observations": int(len(test)), "error_observations": len(errors),
        "confusion_matrix": matrix,
        "f1_macro": float(f1_score(y[test], predicted, labels=CLASSES, average="macro", zero_division=0)),
        "cases": cases, "sampled_error_cases": len(cases),
        "sample_policy": "first_holdout_errors_in_deterministic_split_order",
        "sensitivity_method": "replace_one_feature_with_training_median",
    }


def run(directory: Path, *, seed: int = 20261029, max_cases: int = 12):
    data = read_verified_v2(directory)
    return {
        "schema_version": SCHEMA, "dataset_classification": "SYNTHETIC",
        "source_manifest_sha256": hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest(),
        "seed": seed, "protocols": [
            inspect(build_snapshots(data, cutoff=cutoff), cutoff=cutoff, seed=seed,
                    max_cases=max_cases) for cutoff in CUTS.values()
        ],
        "caveat": "Diagnostics on synthetic holdout errors. No student IDs or row feature vectors. "
                  "Median replacement is a noncausal model probe, not an individual intervention.",
    }


def main():
    parser = argparse.ArgumentParser(description="LUPA synthetic holdout error diagnostics")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--max-cases", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("immutable output already exists")
    report = run(args.dataset, seed=args.seed, max_cases=args.max_cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
