"""Conditional cluster-bootstrap intervals for synthetic held-out predictions.

Resamples entire student clusters (not individual subjects/years), keeping the
trained model and predictions fixed. This measures test-cohort sampling
uncertainty only, not training variability or transport to real schools.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import f1_score

from epa.core_engine.mapa import CLASSES


def cluster_bootstrap_f1(y_true, y_pred, student_ids, *, seed=0, repetitions=300):
    if not 100 <= repetitions <= 2000:
        raise ValueError("bootstrap repetitions outside allowed range")
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    groups = np.asarray(student_ids)
    if not (len(y_true) == len(y_pred) == len(groups)) or len(y_true) == 0:
        raise ValueError("invalid aligned arrays")
    if not set(y_true) <= set(CLASSES) or not set(y_pred) <= set(CLASSES):
        raise ValueError("invalid label")
    unique = np.unique(groups)
    if len(unique) < 8:
        return {"status": "insufficient_clusters", "student_clusters": int(len(unique))}
    per_cluster = [np.flatnonzero(groups == identifier) for identifier in unique]
    rng = np.random.default_rng(seed)
    scores = []
    for _ in range(repetitions):
        sampled = rng.integers(0, len(unique), size=len(unique))
        indices = np.concatenate([per_cluster[j] for j in sampled])
        scores.append(float(f1_score(y_true[indices], y_pred[indices],
                                     labels=CLASSES, average="macro", zero_division=0)))
    return {
        "status": "estimated", "method": "student_cluster_bootstrap_percentile",
        "conditional_on_fitted_model": True, "confidence_level": 0.95,
        "student_clusters": int(len(unique)), "repetitions": repetitions,
        "lower": float(np.quantile(scores, .025)),
        "upper": float(np.quantile(scores, .975)),
        "point_estimate": float(f1_score(y_true, y_pred, labels=CLASSES,
                                         average="macro", zero_division=0)),
        "caution": "Conditional synthetic holdout uncertainty, not model training or real-world generalization.",
    }
