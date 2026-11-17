"""EPIC #77: opt-in synthetic MAPA N1/N2/N3 evaluation using split protocols A/B/C.

Distinct from original MAPA reports; no real-student records or hyperparameter search.
Target is the final outcome of the SAME academic year, known only AFTER N4.
To avoid assuming a precise publication date, label_available_year=year+1 and
planner requires this value STRICTLY BEFORE the first day of test_year.
This conservatively excludes the previous year's outcomes from temporal fitting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, f1_score

from epa.core_engine.mapa import CLASSES, feature_vector, models
from epa.core_engine.mapa_validation_protocols import plan_splits
from epa.core_engine.student_timeline import CUTS, build_snapshots, read_verified_v2

SCHEMA = "epa.mapa.protocol_runner.v1"
MODEL_NAMES = ("majority", "logistic_regression", "random_forest")
AVAILABILITY = "end_of_same_year_outcome_conservatively_usable_start_of_year_plus_2"


def _rows_for_planning(snapshots: list[dict]) -> list[dict]:
    out = []
    for s in snapshots:
        year = s.get("academic_year")
        if type(year) is not int:
            raise ValueError("snapshot academic_year must be integer")
        out.append({"student_id": s["student_id"], "academic_year": year,
                    "label_available_year": year + 1,
                    "data_classification": s["data_classification"]})
    return out


def evaluate(snapshots: list[dict], *, cutoff: int, protocol: str, seed: int = 20261029,
             folds: int = 3, test_year: int | None = None) -> dict:
    if cutoff not in CUTS.values() or not snapshots or any(s.get("cutoff_term") != cutoff for s in snapshots):
        raise ValueError("snapshot cutoff mismatch")
    if any(s.get("data_classification") != "SYNTHETIC" for s in snapshots):
        raise ValueError("only synthetic snapshots allowed")
    labels = np.asarray([s["target_final_subject_outcome"] for s in snapshots])
    if set(labels) - set(CLASSES):
        raise ValueError("invalid MAPA outcome labels")
    split = plan_splits(_rows_for_planning(snapshots), protocol=protocol,
                        test_year=test_year, folds=folds)
    result = {"schema_version": SCHEMA, "protocol": protocol,
              "cutoff_term": cutoff, "target": "same_academic_year_final_subject_outcome_3class",
              "availability_contract": AVAILABILITY,
              "status": split["status"], "split_schema": split["schema_version"],
              "dataset_classification": "SYNTHETIC", "seed": seed,
              "research_status": "SYNTHETIC_NOT_EXTERNAL_VALIDATION",
              "split_reason": split.get("reason"), "folds": [], "models": [],
              "caveat": "This is a new independent protocol; it does not revise frozen MAPA reports. "
                        "Group folds are not independent populations; temporal labels use a conservative annual timestamp."}
    if split["status"] != "evaluated":
        return result
    x = np.asarray([feature_vector(s) for s in snapshots], dtype=float)
    for index, fold in enumerate(split["folds"]):
        train = np.asarray(fold["train_indices"], dtype=int)
        test = np.asarray(fold["test_indices"], dtype=int)
        if len(set(labels[train])) < 2:
            result["folds"].append({"fold": index + 1, "status": "skipped",
                                    "reason": "insufficient_training_classes",
                                    "train_indices_sha256": fold["train_indices_sha256"],
                                    "test_indices_sha256": fold["test_indices_sha256"]})
            continue
        scores = []
        for name, classifier in models(seed + index).items():
            classifier.fit(x[train], labels[train])
            pred = classifier.predict(x[test])
            scores.append({"model": name,
                           "f1_macro": float(f1_score(labels[test], pred, labels=CLASSES,
                                                      average="macro", zero_division=0)),
                           "accuracy": float(accuracy_score(labels[test], pred)),
                           "train_class_counts": {cls: int(np.sum(labels[train] == cls)) for cls in CLASSES},
                           "test_class_counts": {cls: int(np.sum(labels[test] == cls)) for cls in CLASSES}})
        result["folds"].append({"fold": index + 1, "status": "evaluated",
                                "train_students": fold["train_students"],
                                "test_students": fold["test_students"],
                                "overlapping_students": fold["overlapping_students"],
                                "train_years": fold["train_years"], "test_years": fold["test_years"],
                                "train_indices_sha256": fold["train_indices_sha256"],
                                "test_indices_sha256": fold["test_indices_sha256"],
                                "model_scores": scores})
    used = [fold for fold in result["folds"] if fold["status"] == "evaluated"]
    if not used:
        result["status"] = "not_identifiable"
        result["split_reason"] = "insufficient_training_classes"
        return result
    for name in MODEL_NAMES:
        values = [next(m for m in f["model_scores"] if m["model"] == name) for f in used]
        result["models"].append({"model": name,
                                 "folds_evaluated": len(values),
                                 "accuracy_mean": float(np.mean([v["accuracy"] for v in values])),
                                 "accuracy_std": float(np.std([v["accuracy"] for v in values], ddof=1)) if len(values)>1 else None,
                                 "f1_macro_mean": float(np.mean([v["f1_macro"] for v in values])),
                                 "f1_macro_std": float(np.std([v["f1_macro"] for v in values], ddof=1)) if len(values)>1 else None})
    return result


def run(dataset: Path, *, protocol: str, seed: int = 20261029,
        folds: int = 3, test_year: int | None = None) -> dict:
    dataset = Path(dataset)
    data = read_verified_v2(dataset)
    return {"schema_version": SCHEMA, "dataset_manifest_sha256": hashlib.sha256(
                (dataset / "manifest.json").read_bytes()).hexdigest(),
            "dataset_classification": "SYNTHETIC", "protocol": protocol, "seed": seed,
            "test_year": test_year, "folds_requested": folds,
            "results": [evaluate(build_snapshots(data, cutoff=cut), cutoff=cut,
                                 protocol=protocol, seed=seed, folds=folds,
                                 test_year=test_year) for cut in CUTS.values()]}


def main() -> None:
    p = argparse.ArgumentParser(description="EPIC77 synthetic-only MAPA split evaluator")
    p.add_argument("--dataset", required=True, type=Path)
    p.add_argument("--protocol", required=True,
                   choices=("A_grouped", "B_out_of_time", "C_unseen_future"))
    p.add_argument("--test-year", type=int, default=None)
    p.add_argument("--folds", type=int, default=3)
    p.add_argument("--seed", type=int, default=20261029)
    p.add_argument("--report", required=True, type=Path)
    args = p.parse_args()
    if args.report.exists() or args.report.is_symlink():
        p.error("report exists: immutable output cannot be overwritten")
    report = run(args.dataset, protocol=args.protocol, test_year=args.test_year,
                 folds=args.folds, seed=args.seed)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"schema_version": SCHEMA, "protocol": args.protocol,
                      "cutoffs": [r["status"] for r in report["results"]]}))


if __name__ == "__main__":
    main()