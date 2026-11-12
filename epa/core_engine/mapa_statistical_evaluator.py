"""MAPA statistical evaluator: student-cluster bootstrap, paired deltas, reliability.

Use a single fixed synthetic population with repeated student-disjoint holdouts.
This does not measure external-population generalization or calibrate models.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import GroupShuffleSplit

from epa.core_engine.mapa import CLASSES, FEATURES, models
from epa.core_engine.mapa_native_training import verify, digest, scores

SCHEMA = "epa.mapa.statistical_evaluation.v1"
VALID_MODELS = ("majority", "logistic_regression", "random_forest", "mlp")


def _estimator(name: str, seed: int):
    if name != "mlp":
        return models(seed)[name]
    from sklearn.impute import SimpleImputer
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    return make_pipeline(
        SimpleImputer(strategy="constant", fill_value=0),
        StandardScaler(),
        MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=300, random_state=seed),
    )


def _select_students(conn, directory: Path, count: int, selection_seed: int):
    path = str(directory / "N1.parquet")
    ids = [row[0] for row in conn.execute(
        "SELECT DISTINCT student_id FROM read_parquet(?) ORDER BY student_id", [path]
    ).fetchall()]
    if len(ids) < 8 or any(not isinstance(i, str) or not i.startswith("SYN") or
                           not i[3:].isdigit() for i in ids):
        raise ValueError("invalid SYNTHETIC student ids")
    return sorted(ids, key=lambda s: (
        hashlib.sha256(f"{selection_seed}|{s}".encode()).digest(), s
    ))[:count]


def _load(conn, directory: Path, cutoff: int, students: list[str], count: int):
    """DuckDB scans Parquet but only selected feature rows become NumPy matrices."""
    path = str(directory / f"N{cutoff}.parquet")
    actual_count = conn.execute(
        "SELECT count(*) FROM read_parquet(?)", [path]
    ).fetchone()[0]
    if actual_count != count:
        raise ValueError("feature artifact count mismatch")
    fields = ["student_id", *FEATURES, "target_final_subject_outcome"]
    columns = ", ".join('"' + col + '"' for col in fields)
    params = ", ".join("?" for _ in students)
    rows = conn.execute(
        f"SELECT {columns} FROM read_parquet(?) WHERE student_id IN ({params}) "
        "AND cutoff_term = ? AND data_classification = 'SYNTHETIC' "
        "AND target_usage = 'LABEL_ONLY_NOT_FEATURE' ORDER BY enrollment_id, subject_id",
        [path, *students, cutoff],
    ).fetchall()
    if not rows or set(row[0] for row in rows) != set(students):
        raise ValueError("missing student records in cutoff")
    x = np.asarray([
        [np.nan if value is None else float(value) for value in row[1:-1]]
        for row in rows
    ], dtype=np.float64)
    y = np.asarray([row[-1] for row in rows])
    group = np.asarray([row[0] for row in rows])
    if set(y) - set(CLASSES):
        raise ValueError("unknown target class")
    return x, y, group


def _aligned_probabilities(estimator, x):
    raw = estimator.predict_proba(x)
    aligned = np.zeros((len(x), len(CLASSES)), dtype=float)
    for i, label in enumerate(CLASSES):
        if label in estimator.classes_:
            aligned[:, i] = raw[:, list(estimator.classes_).index(label)]
    if not np.isfinite(aligned).all() or not np.allclose(
        aligned.sum(axis=1), 1.0, atol=1e-8
    ):
        raise ValueError("invalid class probabilities")
    return aligned


def _f1_from_cm(cm: np.ndarray) -> float:
    """Macro-F1 in the fixed three-class order; missing support contributes 0."""
    tp = np.diag(cm)
    denominator = cm.sum(axis=0) + cm.sum(axis=1)
    return float(np.mean(np.divide(
        2 * tp, denominator, out=np.zeros(3, dtype=float), where=denominator != 0
    )))


def cluster_bootstrap(y: np.ndarray, predictions: dict[str, np.ndarray],
                      groups: np.ndarray, *, repetitions: int,
                      seed: int, confidence: float = 0.95) -> dict:
    """Resample students, not rows, with identical draws for every model."""
    if not 50 <= repetitions <= 10000 or not 0 < confidence < 1:
        raise ValueError("invalid bootstrap configuration")
    unique = sorted(set(groups))
    if len(unique) < 8 or not predictions:
        raise ValueError("insufficient independent clusters")
    rng = np.random.default_rng(seed)
    confusion_by_student = {}
    for name, pred in predictions.items():
        if len(pred) != len(y):
            raise ValueError("prediction length mismatch")
        confusion_by_student[name] = np.stack([
            confusion_matrix(y[groups == student], pred[groups == student],
                             labels=CLASSES)
            for student in unique
        ])
    distributions = {name: np.empty(repetitions) for name in predictions}
    for i in range(repetitions):
        chosen = rng.integers(0, len(unique), len(unique))
        for name, matrices in confusion_by_student.items():
            distributions[name][i] = _f1_from_cm(matrices[chosen].sum(axis=0))
    low, high = (1 - confidence) / 2, 1 - (1 - confidence) / 2
    intervals = {}
    for name, values in distributions.items():
        intervals[name] = {
            "lower": float(np.quantile(values, low)),
            "upper": float(np.quantile(values, high)),
        }
    pairs = {}
    keys = list(predictions)
    for i, first in enumerate(keys):
        for second in keys[i + 1:]:
            difference = distributions[first] - distributions[second]
            pairs[f"{first}__minus__{second}"] = {
                "lower": float(np.quantile(difference, low)),
                "upper": float(np.quantile(difference, high)),
                "probability_delta_positive_in_bootstrap": float(np.mean(difference > 0)),
            }
    return {
        "method": "percentile_student_cluster_bootstrap",
        "confidence_level": confidence,
        "repetitions": repetitions,
        "independent_clusters": len(unique),
        "macro_f1_intervals": intervals,
        "paired_macro_f1_differences": pairs,
        "interpretation": "conditional on trained models and selected synthetic test students; not a hypothesis-test p-value",
    }


def reliability(y: np.ndarray, proba: np.ndarray, bins: int = 10) -> dict:
    """Descriptive top-label and one-vs-rest reliability; no calibration fitting."""
    if bins < 2 or bins > 30:
        raise ValueError("bins must be 2..30")
    predicted_index = np.argmax(proba, axis=1)
    labels = np.asarray(CLASSES)
    confidence = proba.max(axis=1)
    correctness = (y == labels[predicted_index]).astype(float)

    def table(p, outcomes):
        parts = []
        for index in range(bins):
            lower, upper = index / bins, (index + 1) / bins
            mask = (p >= lower) & ((p < upper) if index < bins - 1 else (p <= upper))
            n = int(mask.sum())
            parts.append({
                "lower": lower, "upper": upper, "count": n,
                "mean_probability": float(p[mask].mean()) if n else None,
                "observed_frequency": float(outcomes[mask].mean()) if n else None,
            })
        ece = sum(
            part["count"] / len(p) *
            abs(part["mean_probability"] - part["observed_frequency"])
            for part in parts if part["count"]
        )
        return {"ece": float(ece), "bins": parts}
    return {
        "top_label": table(confidence, correctness),
        "one_vs_rest": {
            label: table(proba[:, col], (y == label).astype(float))
            for col, label in enumerate(CLASSES)
        },
        "caveat": "ECE depends on binning and can be biased; use with Brier/log loss and validation.",
    }


def run(directory: Path, *, max_students: int = 500,
        seeds: tuple[int, ...] = (20261029, 20261030, 20261031),
        selection_seed: int = 20261029,
        algorithms: tuple[str, ...] = ("logistic_regression", "mlp"),
        bootstrap_repetitions: int = 200) -> dict:
    import duckdb
    directory = Path(directory)
    if not 8 <= max_students <= 5000 or not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("invalid student cap or repeated/empty seeds")
    if any(not 0 <= seed <= 999999999 for seed in seeds):
        raise ValueError("invalid holdout seed")
    if (not algorithms or len(set(algorithms)) != len(algorithms) or
        set(algorithms) - set(VALID_MODELS)):
        raise ValueError("invalid models")
    if not 50 <= bootstrap_repetitions <= 10000:
        raise ValueError("invalid bootstrap repetitions")
    manifest = verify(directory)
    blocks = []
    with duckdb.connect(":memory:") as conn:
        conn.execute("SET threads=2")
        conn.execute("SET memory_limit='512MB'")
        students = _select_students(conn, directory, max_students, selection_seed)
        student_array = np.asarray(sorted(students))
        for cutoff in (1, 2, 3):
            x, y, group = _load(
                conn, directory, cutoff, students,
                manifest["artifacts"][f"N{cutoff}"]["row_count"]
            )
            for seed in seeds:
                train_idx, test_idx = next(GroupShuffleSplit(
                    n_splits=1, test_size=0.25, random_state=seed
                ).split(student_array, groups=student_array))
                train_ids = student_array[train_idx]
                test_ids = student_array[test_idx]
                train = np.isin(group, train_ids)
                test = np.isin(group, test_ids)
                if not train.any() or not test.any() or len(set(y[train])) < 2:
                    raise ValueError("invalid grouped holdout")
                metrics = []
                predictions = {}
                test_group = group[test]
                for name in algorithms:
                    model = _estimator(name, seed)
                    start = time.perf_counter()
                    model.fit(x[train], y[train])
                    fit_duration = time.perf_counter() - start
                    pred = model.predict(x[test])
                    prob = _aligned_probabilities(model, x[test])
                    predictions[name] = pred
                    metrics.append({
                        "model": name, "fit_seconds": fit_duration,
                        **scores(y[test], pred, prob),
                        "reliability": reliability(y[test], prob),
                    })
                bootstrap = cluster_bootstrap(
                    y[test], predictions, test_group,
                    repetitions=bootstrap_repetitions,
                    seed=seed + 8191 * cutoff,
                )
                # Explicitly include paired observed delta and interval in the same direction.
                for name, other in (
                    (first, second)
                    for i, first in enumerate(algorithms) for second in algorithms[i + 1:]
                ):
                    key = f"{name}__minus__{other}"
                    first = next(row for row in metrics if row["model"] == name)
                    second = next(row for row in metrics if row["model"] == other)
                    bootstrap["paired_macro_f1_differences"][key]["observed_delta"] = (
                        first["f1_macro"] - second["f1_macro"]
                    )
                blocks.append({
                    "cutoff_term": cutoff, "seed": seed,
                    "train_students": len(train_ids),
                    "test_students": len(test_ids),
                    "train_observations": int(train.sum()),
                    "test_observations": int(test.sum()),
                    "train_class_counts": {c: int(np.sum(y[train] == c)) for c in CLASSES},
                    "test_class_counts": {c: int(np.sum(y[test] == c)) for c in CLASSES},
                    "results": metrics,
                    "uncertainty": bootstrap,
                })
    return {
        "schema_version": SCHEMA,
        "research_status": "SYNTHETIC_NOT_EMPIRICALLY_VALIDATED",
        "feature_manifest_sha256": digest(directory / "manifest.json"),
        "student_selection_seed": selection_seed,
        "selected_students": len(students),
        "holdout_seeds": list(seeds),
        "models": list(algorithms),
        "feature_names": list(FEATURES), "classes": list(CLASSES),
        "protocols": blocks,
        "limitations": [
            "Repeated split seeds share one synthetic student population; not independent populations.",
            "Bootstrap resamples student clusters from held-out students, conditional on fitted model.",
            "Intervals do not capture between-population shift or retraining uncertainty.",
            "Reliability diagram/ECE is descriptive, not a recalibration procedure.",
            "Hyperparameters fixed; never select thresholds on final test folds.",
            "Synthetic academic outcomes cannot establish real-school prediction quality.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-students", type=int, default=500)
    parser.add_argument("--selection-seed", type=int, default=20261029)
    parser.add_argument("--seeds", type=int, nargs="+", default=[20261029, 20261030, 20261031])
    parser.add_argument("--models", choices=VALID_MODELS, nargs="+",
                        default=["logistic_regression", "mlp"])
    parser.add_argument("--bootstrap", type=int, default=200)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("immutable report already exists")
    report = run(args.features, max_students=args.max_students,
                 selection_seed=args.selection_seed, seeds=tuple(args.seeds),
                 algorithms=tuple(args.models), bootstrap_repetitions=args.bootstrap)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "cutoffs": 3, "holdouts": len(args.seeds),
                      "student_groups": report["selected_students"]}))


if __name__ == "__main__":
    main()
