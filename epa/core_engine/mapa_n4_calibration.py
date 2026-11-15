"""Pre-2020 historical residual calibration overlay for unmodified GENESIS v3 N4.

Experimental, single-student external test (2020-2022); never use those N4s
in calibration, tuning or model fitting. The generator itself is not mutated.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from epa.core_engine.mapa_real_n4 import (
    PUBLIC_MODELS, canonical_subject, generated_synthetic_rows,
    load_private_inputs, load_private_answer_key, predict_all, score_predictions,
)

SCHEMA = "epa.mapa.real_n4_calibration.v1"
CALIBRATION_FIELDS = {"id_caso", "serie", "ano_letivo", "disciplina", "N1", "N2", "N3", "N4"}
ALLOWED_YEARS = frozenset(range(2011, 2020))
AREA_SHRINK = 20.0  # fixed a priori: small subject groups must not dominate
CALIBRATION_STRENGTH = 0.50  # fixed a priori: conservative overlay, never fit on 2020-22
MIN_CALIBRATION_ROWS = 30


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for piece in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(piece)
    return h.hexdigest()


def _number(value: str) -> float:
    x = float(value)
    if not (math.isfinite(x) and 0 <= x <= 10):
        raise ValueError("invalid historical assessment; expected 0..10")
    return x


def read_calibration_history(path: Path, forbidden_ids: set[str] | None = None) -> list[dict]:
    """Only historical 2011-2019 N4 labels permitted; reject future rows entirely."""
    records = []
    seen = set()
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or ()) != CALIBRATION_FIELDS:
            raise ValueError("calibration history must use exact historical columns")
        for row in reader:
            key = row["id_caso"].strip()
            year = int(row["ano_letivo"])
            serie = row["serie"].strip().upper()
            if not key or key in seen or key in (forbidden_ids or set()):
                raise ValueError("duplicate or held-out case in calibration")
            if year not in ALLOWED_YEARS or not serie.endswith("F") or not serie[:-1].isdigit() or int(serie[:-1]) != year - 2010:
                raise ValueError("calibration must use only pre-2020 Fundamental historical records")
            scores = [_number(row[f"N{i}"]) for i in range(1, 5)]
            try:
                _, area = canonical_subject(row["disciplina"])
            except ValueError:
                area = "OUTROS"  # older Fundamental subjects absent from current catalog
            records.append({"area": area, "mean_123": sum(scores[:3]) / 3,
                            "residual": scores[3] - sum(scores[:3]) / 3})
            seen.add(key)
    if len(records) < MIN_CALIBRATION_ROWS:
        raise ValueError("insufficient pre-2020 calibration records")
    return records


def calibrate_targets(train_rows: list[dict], train_n4: list[float], history: list[dict]) -> tuple[list[float], dict]:
    """Shrink residual means toward pooled history; preserve synthetic predictors.

    All targets remain synthetic-derived. Historical records influence only
    mean residual shift; no real student record is inserted in model fit().
    """
    if len(train_rows) != len(train_n4) or not train_rows:
        raise ValueError("synthetic training inputs / labels mismatch")
    if len(history) < MIN_CALIBRATION_ROWS:
        raise ValueError("insufficient calibration observations")
    from collections import defaultdict
    hist_areas = defaultdict(list)
    syn_areas = defaultdict(list)
    for item in history:
        hist_areas[item["area"]].append(float(item["residual"]))
    synthetic_residuals = []
    for item, n4 in zip(train_rows, train_n4):
        r = float(n4) - float(item["mean_123"])
        synthetic_residuals.append(r)
        syn_areas[item["area"]].append(r)
    hist_all = [x for group in hist_areas.values() for x in group]
    hmean = float(np.mean(hist_all))
    smean = float(np.mean(synthetic_residuals))
    offsets = {}
    for area in syn_areas:
        local = hist_areas.get(area, [])
        local_real = float(np.mean(local)) if local else hmean
        local_synthetic = float(np.mean(syn_areas[area]))
        weight = len(local) / (len(local) + AREA_SHRINK)
        # Pool both the observed and synthetic effects to prevent sparse area noise.
        target_residual_mean = (1 - weight) * hmean + weight * local_real
        current_residual_mean = (1 - weight) * smean + weight * local_synthetic
        offsets[area] = CALIBRATION_STRENGTH * (target_residual_mean - current_residual_mean)
    calibrated = [float(np.clip(float(y) + offsets[r["area"]], 0, 10))
                  for r, y in zip(train_rows, train_n4)]
    audit = {
        "calibration": "PRE2020_REAL_RESIDUAL_SHRINKAGE_OVERLAY",
        "generator_modified": False,
        "real_history_count": len(history),
        "allowed_history_years": "2011-2019",
        "historical_mean_n4_minus_mean123": round(hmean, 8),
        "synthetic_mean_n4_minus_mean123": round(smean, 8),
        "shrinkage_count": AREA_SHRINK,
        "overlay_strength": CALIBRATION_STRENGTH,
        "area_adjustment_counts": {k: len(hist_areas.get(k, [])) for k in sorted(offsets)},
        "target_range": [0, 10],
        "interpretation": "Exploratory domain adaptation from one student's earlier school stage; not population calibration",
    }
    return calibrated, audit


def run(catalog: Path, inputs: Path, historical_calibration: Path, answer_key: Path | None = None,
        *, students: int = 250, seed: int = 20261029,
        algorithms: tuple[str, ...] = PUBLIC_MODELS) -> tuple[dict, list[dict]]:
    real = load_private_inputs(inputs)
    history = read_calibration_history(historical_calibration, {r["id_caso"] for r in real})
    synthetic, original_targets, provenance = generated_synthetic_rows(catalog, students=students, seed=seed)
    calibrated_targets, calibration = calibrate_targets(synthetic, original_targets, history)
    # Independent fit() for each condition, identical synthetic predictors and model parameters.
    control, control_time = predict_all(synthetic, original_targets, real, seed=seed, algorithms=algorithms)
    treatment, treatment_time = predict_all(synthetic, calibrated_targets, real, seed=seed, algorithms=algorithms)
    report = {
        "schema_version": SCHEMA,
        "status": "PREDICTIONS_ONLY_NO_LABELS_LOADED",
        "research_status": "EXPLORATORY_RETROSPECTIVE_SINGLE_STUDENT_NOT_INDEPENDENT_VALIDATION",
        "input_count": len(real), "models": list(algorithms),
        "provenance": provenance,
        "calibration": calibration,
        "history_sha256": sha256(historical_calibration),
        "catalog_sha256": sha256(catalog),
        "score_is_prospective": False,
        "disclosure": "Only synthetic rows used for model fit; 2011-2019 real historical labels only adjust synthetic residuals; 2020-2022 N4 test labels never enter calibration or fit.",
    }
    case_preds = [
        {"id_caso": r["id_caso"], **{f"original__{m}": control[m][i] for m in algorithms},
         **{f"calibrated__{m}": treatment[m][i] for m in algorithms}}
        for i, r in enumerate(real)
    ]
    if answer_key is not None:
        key = load_private_answer_key(answer_key, {r["id_caso"] for r in real})
        a = score_predictions(control, real, key, control_time)
        b = score_predictions(treatment, real, key, treatment_time)
        a_by = {x["model"]: x for x in a["model_metrics"]}
        b_by = {x["model"]: x for x in b["model_metrics"]}
        report["comparison"] = [
            {"model": m, "original": a_by[m], "calibrated": b_by[m],
             "delta_mae_calibrated_minus_original": round(b_by[m]["mae"] - a_by[m]["mae"], 6)}
            for m in algorithms
        ]
        report["status"] = "REAL_RETROSPECTIVE_CALIBRATION_SCORED_SINGLE_STUDENT"
        report["independent_students"] = 1
    return report, case_preds


def main() -> None:
    p = argparse.ArgumentParser(description="Real N4 retrospective calibration over unchanged GENESIS")
    p.add_argument("--catalog", type=Path, default=Path("examples/atlas.demo.json"))
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--calibration-history", type=Path, required=True)
    p.add_argument("--answer-key", type=Path, default=None)
    p.add_argument("--students", type=int, default=250)
    p.add_argument("--seed", type=int, default=20261029)
    p.add_argument("--models", nargs="+", choices=PUBLIC_MODELS, default=list(PUBLIC_MODELS))
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--predictions", type=Path, default=None)
    args = p.parse_args()
    if args.report.exists() or args.report.is_symlink() or (args.predictions and (args.predictions.exists() or args.predictions.is_symlink())):
        p.error("immutable output path already exists")
    report, cases = run(args.catalog, args.inputs, args.calibration_history, args.answer_key,
                        students=args.students, seed=args.seed, algorithms=tuple(args.models))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    if args.predictions:
        args.predictions.parent.mkdir(parents=True, exist_ok=True)
        with args.predictions.open("x", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id_caso", *[f"original__{m}" for m in args.models],
                                                    *[f"calibrated__{m}" for m in args.models]])
            writer.writeheader()
            writer.writerows(cases)
    print(json.dumps({"schema_version": SCHEMA, "status": report["status"],
                      "input_count": report["input_count"], "models": report["models"]}))


if __name__ == "__main__":
    main()