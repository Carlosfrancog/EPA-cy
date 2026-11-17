"""Experimental N4 longitudinal grade-distribution adapter.

Calibrates ALL FOUR SYNTHETIC grade terms, not just their label, using only
an authorized 2011-2019 reference history. 2020-2022 labels are never read
until the scoring phase. This is a one-student exploratory sensitivity study;
NOT a population calibrated GENESIS release.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import unicodedata

import numpy as np

from epa.core_engine.mapa_real_n4 import (
    PUBLIC_MODELS, features, generated_synthetic_rows, load_private_answer_key,
    load_private_inputs, predict_all, score_predictions,
)

SCHEMA = "epa.mapa.real_n4_longitudinal_calibration.v1"
HISTORY_FIELDS = {"id_caso", "serie", "ano_letivo", "disciplina", "N1", "N2", "N3", "N4"}
# Whitelisted transcription aliases. Fundamental 'ciencias' maps to the knowledge
# AREA NATUREZA, never directly to any secondary-school subject (BIO/FIS/QUI).
AREA_BY_SUBJECT = {
    "matematica": "MATEMATICA",
    "ciencias": "NATUREZA",
    "historia": "HUMANAS", "geografia": "HUMANAS",
    "artes": "LINGUAGENS", "ingles": "LINGUAGENS", "portugues": "LINGUAGENS",
    "educacao fisica": "LINGUAGENS",
    "eduacacao fisica": "LINGUAGENS", "eduacaco fisica": "LINGUAGENS",
}
AREAS = ("MATEMATICA", "NATUREZA", "HUMANAS", "LINGUAGENS")
AREA_SHRINK = 20.0
STRENGTH = 0.40
MAX_SHIFT = 1.5
MAX_SCALE = 1.45
MIN_SCALE = 0.70


def normalize_subject(label: str) -> str:
    from epa.core_engine.mapa_n4_subjects import normalize_subject as shared_normalizer
    return shared_normalizer(label)


def read_history(path: Path) -> list[dict]:
    result, seen = [], set()
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if set(reader.fieldnames or []) != HISTORY_FIELDS:
            raise ValueError("historical calibration CSV columns mismatch")
        for raw in reader:
            identifier = raw["id_caso"].strip()
            year = int(raw["ano_letivo"])
            serie = raw["serie"].strip().upper()
            if (not identifier or identifier in seen or not 2011 <= year <= 2019
                    or serie != f"{year - 2010}F"):
                raise ValueError("historical calibration boundary or duplicate violated")
            norm = normalize_subject(raw["disciplina"])
            if norm not in AREA_BY_SUBJECT:
                raise ValueError("unknown historical subject, explicit mapping required")
            grades = tuple(float(raw[f"N{i}"]) for i in range(1, 5))
            if not all(math.isfinite(x) and 0 <= x <= 10 for x in grades):
                raise ValueError("invalid historical grade")
            result.append({"area": AREA_BY_SUBJECT[norm], "year": year,
                           "grades": grades})
            seen.add(identifier)
    if len(result) < 30 or set(r["area"] for r in result) != set(AREAS):
        raise ValueError("insufficient reference history/area coverage")
    return result


def profile(rows: list[dict]) -> dict:
    """Fitted only on calibration rows. Subject-level identities never persist."""
    by_area = defaultdict(list)
    for row in rows:
        by_area[row["area"]].append(np.asarray(row["grades"], dtype=float))
    if set(by_area) != set(AREAS):
        raise ValueError("missing knowledge area")
    return {area: {"cases": len(seq),
                    "grade_mean": float(np.asarray(seq).mean()),
                    "grade_sd": float(np.asarray(seq).std()),
                    "mean_abs_step": float(np.abs(np.diff(np.asarray(seq), axis=1)).mean())}
            for area, seq in by_area.items()}


def adapt_training(train_rows: list[dict], train_n4: list[float], ref_profile: dict,
                   *, strength: float = STRENGTH) -> tuple[list[dict], list[float], dict]:
    """Transform N1/N2/N3/N4 together, maintaining within-series temporal ordering.

    The empirical grade mean and within-year variation are shrunken toward the
    original synthetic domain, with caps. The generator's multi-year student
    tendencies are NOT refitted: a single student's Fundamental history cannot
    identify their population-level High School dynamics.
    """
    if not (0 <= strength <= 0.5):
        raise ValueError("strength must be 0..0.5 (pre-registered)")
    if not train_rows or len(train_rows) != len(train_n4):
        raise ValueError("synthetic feature/target mismatch")
    if any("N4" in r or "MF" in r for r in train_rows):
        raise ValueError("future label leaked to predictors")
    by_area = defaultdict(list)
    for row, n4 in zip(train_rows, train_n4):
        if row["area"] not in AREAS or not math.isfinite(float(n4)) or not 0 <= float(n4) <= 10:
            raise ValueError("invalid synthetic row")
        by_area[row["area"]].append([row["N1"], row["N2"], row["N3"], float(n4)])
    if set(by_area) != set(AREAS) or set(ref_profile) != set(AREAS):
        raise ValueError("area coverage mismatch")
    parameters = {}
    for area, seqs in by_area.items():
        x = np.asarray(seqs, dtype=float)
        empirical = ref_profile[area]
        n = int(empirical["cases"])
        if n <= 0:
            raise ValueError("missing reference area")
        w = strength * n / (n + AREA_SHRINK)
        syn_mu = float(x.mean())
        shift = float(np.clip(w * (empirical["grade_mean"] - syn_mu), -MAX_SHIFT, MAX_SHIFT))
        # Scale within-year grade deviations using observed inter-term volatility.
        syn_step = float(np.abs(np.diff(x, axis=1)).mean())
        ratio = empirical["mean_abs_step"] / max(syn_step, 0.05)
        scale = float(np.clip(1 + w * (ratio - 1), MIN_SCALE, MAX_SCALE))
        parameters[area] = {"support": n, "weight": w,
                            "mean_shift": shift, "intra_year_scale": scale,
                            "synthetic_grade_mean": syn_mu,
                            "synthetic_mean_abs_step": syn_step}
    adapted_rows, adapted_n4 = [], []
    for row, n4 in zip(train_rows, train_n4):
        seq = np.array([row["N1"], row["N2"], row["N3"], n4], dtype=float)
        p = parameters[row["area"]]
        mean = seq.mean()
        transformed = np.clip(mean + p["mean_shift"] + p["intra_year_scale"] * (seq - mean), 0, 10)
        adapted_rows.append(features(n1=transformed[0], n2=transformed[1], n3=transformed[2],
                                     grade_level=row["grade_level"], subject_id=row["subject_id"],
                                     area=row["area"]))
        adapted_n4.append(float(transformed[3]))
    return adapted_rows, adapted_n4, {"kind": "EXPERIMENTAL_FOUR_TERM_MOMENT_ADAPTER",
                                      "generator_modified": False,
                                      "n_real_student_clusters": 1,
                                      "area_parameters": parameters,
                                      "fixed_strength": strength,
                                      "not_a_population_calibration": True}


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def run(catalog: Path, inputs: Path, history: Path, answer_key: Path | None = None,
        *, students: int = 250, seed: int = 20261029,
        algorithms: tuple[str, ...] = PUBLIC_MODELS) -> tuple[dict, list[dict]]:
    actual_rows = load_private_inputs(inputs)
    history_rows = read_history(history)
    src, targets, provenance = generated_synthetic_rows(catalog, students=students, seed=seed)
    adapted, adapted_targets, audit = adapt_training(src, targets, profile(history_rows))
    control, control_time = predict_all(src, targets, actual_rows, seed=seed, algorithms=algorithms)
    treatment, treatment_time = predict_all(adapted, adapted_targets, actual_rows, seed=seed, algorithms=algorithms)
    result = {"schema_version": SCHEMA, "status": "PREDICTIONS_ONLY_NO_LABELS_LOADED",
              "research_status": "EXPLORATORY_SINGLE_STUDENT_NOT_INDEPENDENT_VALIDATION",
              "n_cases": len(actual_rows), "independent_students": 1,
              "models": list(algorithms), "provenance": provenance, "calibration": audit,
              "history_sha256": file_digest(history), "catalog_sha256": file_digest(catalog),
              "reference_years": "2011-2019", "reference_records": len(history_rows),
              "caveat": "Only Fundamental history from one student. Both first three synthetic grades and synthetic N4 are transformed; full longitudinal generator v3 is not modified. Holdout is retrospective and already observed."}
    prediction_rows = [{"id_caso": row["id_caso"],
                        **{f"original__{m}": control[m][i] for m in algorithms},
                        **{f"adapted__{m}": treatment[m][i] for m in algorithms}}
                       for i, row in enumerate(actual_rows)]
    if answer_key is not None:
        # Guard: scoring labels are loaded AFTER both fits have finished.
        key = load_private_answer_key(answer_key, {r["id_caso"] for r in actual_rows})
        original = score_predictions(control, actual_rows, key, control_time)
        calibrated = score_predictions(treatment, actual_rows, key, treatment_time)
        by_orig = {r["model"]: r for r in original["model_metrics"]}
        by_cal = {r["model"]: r for r in calibrated["model_metrics"]}
        result["comparison"] = [{"model": name, "original": by_orig[name],
                                 "adapted": by_cal[name],
                                 "delta_mae": round(by_cal[name]["mae"] - by_orig[name]["mae"], 6)}
                                for name in algorithms]
        result["status"] = "EXPLORATORY_REAL_N4_SCORED_SINGLE_STUDENT"
    return result, prediction_rows


def main() -> None:
    p = argparse.ArgumentParser(description="Experimental grade-sequence GENESIS adapter for private N4 benchmark")
    p.add_argument("--catalog", type=Path, default=Path("examples/atlas.demo.json"))
    p.add_argument("--inputs", required=True, type=Path)
    p.add_argument("--calibration-history", required=True, type=Path)
    p.add_argument("--answer-key", type=Path, default=None)
    p.add_argument("--students", type=int, default=250)
    p.add_argument("--seed", type=int, default=20261029)
    p.add_argument("--models", nargs="+", choices=PUBLIC_MODELS, default=list(PUBLIC_MODELS))
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--predictions", type=Path, default=None)
    args = p.parse_args()
    for dest in (args.report, args.predictions):
        if dest is not None and (dest.exists() or dest.is_symlink()):
            p.error("output exists; refuses to overwrite immutable results")
    report, details = run(args.catalog, args.inputs, args.calibration_history, args.answer_key,
                          students=args.students, seed=args.seed, algorithms=tuple(args.models))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    if args.predictions:
        args.predictions.parent.mkdir(parents=True, exist_ok=True)
        with args.predictions.open("x", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id_caso", *[f"original__{m}" for m in args.models],
                                                 *[f"adapted__{m}" for m in args.models]])
            writer.writeheader()
            writer.writerows(details)
    print(json.dumps({"schema_version": SCHEMA, "status": report["status"],
                      "n_cases": report["n_cases"]}))


if __name__ == "__main__":
    main()