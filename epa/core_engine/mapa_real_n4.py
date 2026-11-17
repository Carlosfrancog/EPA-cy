"""MAPA N4: retrospective single-student grade regression, trained on uncalibrated GENESIS.

Sensitive CSVs are local-only. This module never serializes real input rows,
student identifiers, subjects or targets into GitHub-tracked outputs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from time import perf_counter

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SCHEMA = "epa.mapa.real_n4_retrospective.v1"
TARGET = "N4"
# Public catalog subject IDs; alias mapping is metadata only (never student data).
SUBJECT_ALIASES = {
    "artes": ("ART", "LINGUAGENS"),
    "biologia": ("BIO", "NATUREZA"),
    "educação física": ("EDF", "LINGUAGENS"),
    "filosofia": ("FIL", "HUMANAS"),
    "física": ("FIS", "NATUREZA"),
    "geografia": ("GEO", "HUMANAS"),
    "história": ("HIS", "HUMANAS"),
    "inglês": ("ING", "LINGUAGENS"),
    "matemática": ("MAT", "MATEMATICA"),
    "português": ("POR", "LINGUAGENS"),
    "química": ("QUI", "NATUREZA"),
    "sociologia": ("SOC", "HUMANAS"),
}
NUMERIC = ("N1", "N2", "N3", "mean_123", "delta_31", "range_123", "grade_level")
CATEGORICAL = ("subject_id", "area")
FEATURES = NUMERIC + CATEGORICAL
PUBLIC_MODELS = ("baseline_n3", "baseline_mean", "dummy_mean", "linear", "ridge", "random_forest", "extra_trees", "gradient_boosting", "hist_gradient_boosting", "mlp")


def canonical_subject(value: str) -> tuple[str, str]:
    from epa.core_engine.mapa_n4_subjects import normalize_subject, ALIASES
    normalized = normalize_subject(value)
    if normalized not in ALIASES:
        raise ValueError("Unrecognized school subject; update vetted alias mapping")
    return ALIASES[normalized]


def features(*, n1: float, n2: float, n3: float, grade_level: int, subject_id: str, area: str) -> dict:
    values = (float(n1), float(n2), float(n3))
    if not all(math.isfinite(x) and 0 <= x <= 10 for x in values):
        raise ValueError("Grades N1..N3 must be finite within [0,10]")
    if grade_level not in (10, 11, 12):
        raise ValueError("Only 1M..3M are supported")
    return {"N1": values[0], "N2": values[1], "N3": values[2],
            "mean_123": sum(values) / 3, "delta_31": values[2] - values[0],
            "range_123": max(values) - min(values), "grade_level": grade_level,
            "subject_id": subject_id, "area": area}


def load_private_inputs(path: Path) -> list[dict]:
    """Strict allowlist: reject accidental targets, aggregate labels or identities."""
    rows = []
    expected = {"id_caso", "serie", "ano_letivo", "disciplina", "N1", "N2", "N3"}
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or []) != expected:
            raise ValueError("Input CSV must contain ONLY the approved pre-N4 fields")
        for row in reader:
            key, serie = row["id_caso"].strip(), row["serie"].strip().upper()
            if not key or serie not in ("1M", "2M", "3M"):
                raise ValueError("Invalid case identifier or series")
            grade_level = {"1M": 10, "2M": 11, "3M": 12}[serie]
            year = int(row["ano_letivo"])
            if year != 2010 + grade_level:  # 1M=2020, 2M=2021, 3M=2022
                raise ValueError("Unexpected series/year combination")
            sid, area = canonical_subject(row["disciplina"])
            f = features(n1=float(row["N1"]), n2=float(row["N2"]), n3=float(row["N3"]),
                         grade_level=grade_level, subject_id=sid, area=area)
            rows.append({"id_caso": key, **f})
    if len(rows) != 36 or len({r["id_caso"] for r in rows}) != 36:
        raise ValueError("Exactly 36 unique real cases are required")
    return rows


def load_private_answer_key(path: Path, expected_ids: set[str]) -> dict[str, float]:
    """A separate, read-only evaluation boundary; never available to fit()."""
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "id_caso" not in reader.fieldnames or "N4_real" not in reader.fieldnames:
            raise ValueError("Answer key requires id_caso and N4_real")
        records = list(reader)
    values = {r["id_caso"].strip(): float(r["N4_real"]) for r in records}
    if len(values) != len(records) or set(values) != expected_ids:
        raise ValueError("Answer-key identifiers mismatch")
    if not all(math.isfinite(v) and 0 <= v <= 10 for v in values.values()):
        raise ValueError("Invalid N4 in answer key")
    return values


def generated_synthetic_rows(catalog_path: Path, *, students: int, seed: int) -> tuple[list[dict], list[float], dict]:
    """Use the ORIGINAL repo GENESIS v3 student_rows algorithm, without calibration.

    The catalog's 1M/2M/3M grade levels are 10/11/12; only generated N4 is
    training target, and no real N4 is read by this function.
    """
    from epa.atlas.catalog import catalog_sha256, load_catalog
    from epa.genesis.v3 import student_rows
    if not 16 <= students <= 20000:
        raise ValueError("students must be between 16 and 20000")
    catalog = load_catalog(catalog_path)
    real_catalog = {g["grade_level"]: g for g in catalog["grades"] if g["grade_level"] in (10, 11, 12)}
    if set(real_catalog) != {10, 11, 12}:
        raise ValueError("GENESIS catalog needs grade levels 10,11,12")
    # student_rows uses catalog grade index for trend; therefore keep original
    # full catalog, and filter only the output to Ensino Médio afterwards.
    xs, ys = [], []
    for number in range(1, students + 1):
        series = defaultdict(dict)
        for name, record in student_rows(catalog, number, seed=seed, start_year=2016,
                                         classes_per_grade=3, school_count=2):
            if name == "period_records" and record["grade_level"] in (10, 11, 12):
                series[(record["grade_level"], record["subject_id"], record["knowledge_area"])][record["term"]] = float(record["assessment_grade"])
        for (grade_level, sid, area), grades in series.items():
            if set(grades) != {1, 2, 3, 4}:
                raise ValueError("GENESIS generated incomplete school year")
            xs.append(features(n1=grades[1], n2=grades[2], n3=grades[3],
                               grade_level=grade_level, subject_id=sid, area=area))
            ys.append(grades[4])
    if not xs:
        raise ValueError("GENESIS yielded no valid middle-school records")
    return xs, ys, {"generator": "epa.genesis.v3.student_rows", "generator_seed": seed,
                    "students": students, "synthetic_records": len(xs),
                    "catalog_sha256": catalog_sha256(catalog_path),
                    "generator_calibration": "NONE_ORIGINAL", "generator_classification": "SYNTHETIC"}


def estimator(name: str, *, seed: int):
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    transform = ColumnTransformer([
        ("num", numeric, list(NUMERIC)),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), list(CATEGORICAL)),
    ])
    estimators = {
        "dummy_mean": DummyRegressor(strategy="mean"),
        "linear": LinearRegression(),
        "ridge": Ridge(alpha=10.0),
        "random_forest": RandomForestRegressor(n_estimators=250, min_samples_leaf=3, random_state=seed, n_jobs=1),
        "extra_trees": ExtraTreesRegressor(n_estimators=250, min_samples_leaf=3, random_state=seed, n_jobs=1),
        "gradient_boosting": GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, random_state=seed),
        "hist_gradient_boosting": HistGradientBoostingRegressor(max_iter=200, random_state=seed),
        "mlp": MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=450, early_stopping=True,
                            n_iter_no_change=25, random_state=seed),
    }
    if name not in estimators:
        raise ValueError("Unsupported regression model")
    return Pipeline([("preprocess", transform), ("regressor", estimators[name])])


def to_matrix(rows: list[dict]) -> list[list]:
    # ColumnTransformer works with a DataFrame or a 2-d numpy matrix; use
    # matrix with integer column indices configured in a fresh transformer.
    return [[r[key] for key in FEATURES] for r in rows]


def build_pipeline(name: str, seed: int):
    from sklearn.compose import ColumnTransformer
    # Column positions instead of names to avoid a pandas dependency.
    numeric = Pipeline([("fill", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    cat = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    preprocess = ColumnTransformer([("num", numeric, list(range(len(NUMERIC)))),
                                    ("cat", cat, list(range(len(NUMERIC), len(FEATURES))))])
    model = estimator(name, seed=seed).named_steps["regressor"]
    return Pipeline([("preprocess", preprocess), ("regressor", model)])


def predict_all(train_rows: list[dict], train_targets: list[float], real_rows: list[dict], *,
                seed: int, algorithms: tuple[str, ...] = PUBLIC_MODELS) -> tuple[dict[str, list[float]], dict]:
    if set(algorithms) - set(PUBLIC_MODELS) or not algorithms:
        raise ValueError("Unknown model specified")
    if not train_rows or len(train_rows) != len(train_targets):
        raise ValueError("Inconsistent training matrix")
    if any(TARGET in row or "MF" in row for row in train_rows + real_rows):
        raise ValueError("N4/MF target leaked into features")
    train_x, real_x = to_matrix(train_rows), to_matrix(real_rows)
    if len(train_x[0]) != len(FEATURES) or len(real_x[0]) != len(FEATURES):
        raise ValueError("Feature mismatch")
    predictions, times = {}, {}
    for name in algorithms:
        tic = perf_counter()
        if name == "baseline_n3":
            pred = np.array([row["N3"] for row in real_rows], dtype=float)
        elif name == "baseline_mean":
            pred = np.array([row["mean_123"] for row in real_rows], dtype=float)
        else:
            pipe = build_pipeline(name, seed)
            pipe.fit(train_x, np.asarray(train_targets, dtype=float))
            pred = np.asarray(pipe.predict(real_x), dtype=float)
        predictions[name] = np.clip(pred, 0, 10).tolist()
        times[name] = round(perf_counter() - tic, 4)
    return predictions, times


def score_predictions(predictions: dict[str, list[float]], real_rows: list[dict],
                      answer_key: dict[str, float], times: dict[str, float]) -> dict:
    actual = np.asarray([answer_key[r["id_caso"]] for r in real_rows], dtype=float)
    summaries = []
    for name, values in predictions.items():
        expected = np.asarray(values)
        if expected.shape != actual.shape or not np.isfinite(expected).all():
            raise ValueError("Invalid prediction array")
        error = np.abs(actual - expected)
        summaries.append({"model": name, "mae": round(float(mean_absolute_error(actual, expected)), 6),
                          "rmse": round(float(np.sqrt(mean_squared_error(actual, expected))), 6),
                          "median_absolute_error": round(float(np.median(error)), 6),
                          "within_0_5": round(float(np.mean(error <= 0.5)), 6),
                          "within_1_0": round(float(np.mean(error <= 1.0)), 6),
                          "fit_predict_seconds": times[name]})
    return {"model_metrics": summaries, "n_cases": len(actual),
            "independent_students": 1, "evaluation_type": "retrospective_known_outcomes_single_student",
            "non_generalization_caveat": "36 grade outcomes belong to ONE student; no student-population generalization"}


def run(catalog_path: Path, inputs_path: Path, answer_key_path: Path | None = None, *,
        students: int = 250, seed: int = 20261029, algorithms: tuple[str, ...] = PUBLIC_MODELS) -> tuple[dict, list[dict]]:
    rows = load_private_inputs(inputs_path)
    xs, ys, provenance = generated_synthetic_rows(catalog_path, students=students, seed=seed)
    catalog_subjects = {r["subject_id"] for r in xs}
    predictions, times = predict_all(xs, ys, rows, seed=seed, algorithms=algorithms)
    safe_report = {"schema_version": SCHEMA, "status": "PREDICTIONS_ONLY_NO_LABELS_LOADED",
                   "provenance": provenance, "input_count": len(rows), "models": list(algorithms),
                   "subject_out_of_catalog_count": sum(r["subject_id"] not in catalog_subjects for r in rows),
                   "disclosure": "Synthetic training; real retrospective test; no generator calibration. No personal records in public report."}
    # Preserve predictions in memory until optional LOCAL, private output. No
    # student data is printed to stdout; do not expose the case-level object in public CI.
    case_predictions = [{"id_caso": row["id_caso"], **{model: pred[i] for model, pred in predictions.items()}}
                        for i, row in enumerate(rows)]
    if answer_key_path is not None:
        key = load_private_answer_key(answer_key_path, {r["id_caso"] for r in rows})
        metrics = score_predictions(predictions, rows, key, times)
        safe_report.update(metrics)
        safe_report["status"] = "REAL_RETROSPECTIVE_SCORED_SINGLE_STUDENT"
    return safe_report, case_predictions


def main() -> None:
    parser = argparse.ArgumentParser(description="Privacy-safe GENESIS original -> real N4 benchmark")
    parser.add_argument("--catalog", type=Path, default=Path("examples/atlas.demo.json"))
    parser.add_argument("--inputs", type=Path, required=True, help="LOCAL PRIVATE CSV without N4")
    parser.add_argument("--answer-key", type=Path, default=None, help="LOCAL PRIVATE CSV with N4")
    parser.add_argument("--students", type=int, default=250)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--models", nargs="+", choices=PUBLIC_MODELS, default=list(PUBLIC_MODELS))
    parser.add_argument("--report", type=Path, required=True, help="LOCAL PRIVATE report JSON")
    parser.add_argument("--predictions", type=Path, default=None, help="LOCAL PRIVATE per-case predictions")
    args = parser.parse_args()
    if args.report.exists() or args.report.is_symlink() or (args.predictions and (args.predictions.exists() or args.predictions.is_symlink())):
        parser.error("Reports are immutable: output file already exists")
    report, predictions = run(args.catalog, args.inputs, args.answer_key, students=args.students,
                              seed=args.seed, algorithms=tuple(args.models))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    if args.predictions:
        args.predictions.parent.mkdir(parents=True, exist_ok=True)
        with args.predictions.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["id_caso", *args.models])
            writer.writeheader()
            writer.writerows(predictions)
    print(json.dumps({"schema_version": SCHEMA, "status": report["status"],
                      "n_cases": report["input_count"], "models": report["models"]}))


if __name__ == "__main__":
    main()