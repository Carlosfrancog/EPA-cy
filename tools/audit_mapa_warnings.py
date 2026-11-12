"""Diagnostic-only audit of synthetic MAPA missing features and MLP convergence.

No model reports or production predictions are changed. This tool builds a
small synthetic in-memory dataset, profiles snapshot creation and MLP fitting,
and emits aggregate-only JSON (no student-level observations).

Example:
  python tools/audit_mapa_warnings.py --students 24 --seed 13 --cutoffs 1 2 3
"""
from __future__ import annotations

import argparse
import json
import platform
import time
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.model_selection import GroupShuffleSplit

from epa.atlas.catalog import load_catalog
from epa.genesis.v2 import build_dataset
from epa.core_engine.mapa import FEATURES, CLASSES, feature_vector
from epa.core_engine.mapa_extended import candidates
from epa.core_engine.student_timeline import build_snapshots

SCHEMA = "epa.research.mapa_warning_audit.v1"
ROOT = Path(__file__).resolve().parents[1]


def audit_features(rows: list[dict]) -> dict:
    """Count finite/missing values, never include student-level observations."""
    if not rows:
        raise ValueError("empty snapshots")
    x = np.asarray([feature_vector(row) for row in rows], dtype=float)
    if x.shape[1] != len(FEATURES):
        raise AssertionError("feature contract changed")
    n = len(rows)
    missing = np.isnan(x)
    finite = np.isfinite(x)
    if not np.all(missing | finite):
        raise ValueError("infinite feature value")
    return {
        "observations": n,
        "features": [
            {"name": name, "missing_count": int(missing[:, col].sum()),
             "missing_fraction": float(missing[:, col].mean()),
             "observed_count": int(finite[:, col].sum())}
            for col, name in enumerate(FEATURES)
        ],
    }


def audit_cutoff(rows: list[dict], *, cutoff: int, seed: int) -> dict:
    if not rows or any(row["cutoff_term"] != cutoff for row in rows):
        raise ValueError("cutoff mismatch")
    result = audit_features(rows)
    x = np.asarray([feature_vector(row) for row in rows], dtype=float)
    y = np.asarray([row["target_final_subject_outcome"] for row in rows])
    groups = np.asarray([row["student_id"] for row in rows])
    if len(set(groups)) < 8 or not set(y) <= set(CLASSES):
        raise ValueError("invalid groups or target")
    train, test = next(GroupShuffleSplit(n_splits=1, test_size=.25, random_state=seed).split(x, y, groups))
    if set(groups[train]) & set(groups[test]):
        raise AssertionError("student overlap")
    result["train_students"] = len(set(groups[train]))
    result["test_students"] = len(set(groups[test]))
    result["train_labels"] = dict(sorted(Counter(y[train].tolist()).items()))
    result["test_labels"] = dict(sorted(Counter(y[test].tolist()).items()))
    result["all_missing_train_features"] = [
        name for index, name in enumerate(FEATURES) if np.isnan(x[train, index]).all()
    ]
    model = candidates(seed)["mlp"]
    start = time.perf_counter()
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        model.fit(x[train], y[train])
    elapsed = time.perf_counter() - start
    mlp = model.named_steps["mlpclassifier"]
    transformer = model.named_steps["simpleimputer"]
    result["mlp"] = {
        "fit_wall_seconds": elapsed,
        "max_iter_config": int(mlp.max_iter),
        "n_iter": int(mlp.n_iter_),
        "converged_before_iteration_cap": bool(mlp.n_iter_ < mlp.max_iter),
        "final_loss": float(mlp.loss_),
        "train_score": float(model.score(x[train], y[train])),
        "test_score": float(model.score(x[test], y[test])),
        "imputer_features_in": int(transformer.n_features_in_),
        "imputer_features_out": int(transformer.transform(x[train[:1]]).shape[1]),
        "warnings": [
            {"category": type(item.message).__name__, "message": str(item.message)}
            for item in captured
        ],
        "convergence_warning_count": sum(
            issubclass(item.category, ConvergenceWarning) for item in captured
        ),
    }
    return result


def run(*, students: int, seed: int, cutoffs: tuple[int, ...], catalog: Path) -> dict:
    if not (8 <= students <= 2000) or not cutoffs or any(c not in (1, 2, 3) for c in cutoffs):
        raise ValueError("students 8..2000 and cutoffs within 1/2/3 required")
    begin = time.perf_counter()
    dataset = build_dataset(load_catalog(catalog), students=students, seed=seed, start_year=2020)
    generation = time.perf_counter() - begin
    cutoffs_report = []
    for cutoff in cutoffs:
        begin = time.perf_counter()
        rows = build_snapshots(dataset, cutoff=cutoff)
        snapshot_seconds = time.perf_counter() - begin
        result = audit_cutoff(rows, cutoff=cutoff, seed=seed)
        result["cutoff_term"] = cutoff
        result["snapshot_wall_seconds"] = snapshot_seconds
        cutoffs_report.append(result)
    return {
        "schema_version": SCHEMA,
        "classification": "SYNTHETIC",
        "students": students,
        "seed": seed,
        "catalog": catalog.name,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "generation_wall_seconds": generation,
        "cutoffs": cutoffs_report,
        "limitations": [
            "Measured times are single-run wall-clock diagnostics, not a benchmark.",
            "The grouped split shares students across subjects but not train/test.",
            "NaN indicates absent prior same-subject history and is not automatically an error.",
            "Convergence warnings are captured and reported, not suppressed or corrected.",
            "The synthetic cohort does not establish external predictive validity.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=ROOT / "examples/atlas.demo.json")
    parser.add_argument("--students", type=int, default=24)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--cutoffs", nargs="+", type=int, default=[1, 2, 3])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    report = run(students=args.students, seed=args.seed,
                 cutoffs=tuple(args.cutoffs), catalog=args.catalog)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
        print(f"PASS: audit saved to {args.output}")


if __name__ == "__main__":
    main()
