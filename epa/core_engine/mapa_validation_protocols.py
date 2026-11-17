"""EPIC #77: explicit synthetic grouped/temporal split planning (no fitting).

Protocol A: unseen student groups, no temporal claim.
Protocol B: future academic year, students may recur.
Protocol C: future academic year AND previously unseen students.

All labels in the training set must have become available before the *start*
of the held-out test year. This module does not load grades or train models.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter

import numpy as np
from sklearn.model_selection import GroupKFold

SCHEMA = "epa.mapa.validation_splits.v1"
PROTOCOLS = ("A_grouped", "B_out_of_time", "C_unseen_future")
REQUIRED = {"student_id", "academic_year", "label_available_year", "data_classification"}


def _validate(rows: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not rows:
        raise ValueError("empty synthetic records")
    students, years, available = [], [], []
    for row in rows:
        if not isinstance(row, dict) or not REQUIRED <= set(row):
            raise ValueError("missing explicit student/year/label availability fields")
        sid, year, label_year = row["student_id"], row["academic_year"], row["label_available_year"]
        if (row["data_classification"] != "SYNTHETIC" or
            not isinstance(sid, str) or not sid.startswith("SYN") or
            type(year) is not int or type(label_year) is not int or
            not 2000 <= year <= 2100 or not year <= label_year <= 2101):
            raise ValueError("invalid synthetic student or temporal metadata")
        students.append(sid)
        years.append(year)
        available.append(label_year)
    return np.asarray(students), np.asarray(years), np.asarray(available)


def _indices_digest(indices: list[int]) -> str:
    return hashlib.sha256(json.dumps(indices, separators=(",", ":")).encode()).hexdigest()


def _fold(ids: np.ndarray, years: np.ndarray, availability: np.ndarray,
          train: np.ndarray, test: np.ndarray, protocol: str, cutoff: int | None) -> dict:
    if not len(train) or not len(test) or set(train.tolist()) & set(test.tolist()):
        raise ValueError("empty or overlapping row partitions")
    shared = sorted(set(ids[train]) & set(ids[test]))
    if protocol != "B_out_of_time" and shared:
        raise ValueError("student-group leakage")
    if cutoff is not None:
        if np.any(years[train] >= cutoff) or np.any(availability[train] >= cutoff) or np.any(years[test] != cutoff):
            raise ValueError("future label, feature-year or test-year leakage")
    return {
        "train_indices": train.tolist(), "test_indices": test.tolist(),
        "train_indices_sha256": _indices_digest(train.tolist()),
        "test_indices_sha256": _indices_digest(test.tolist()),
        "train_students": len(set(ids[train])), "test_students": len(set(ids[test])),
        "overlapping_students": len(shared),
        "train_years": sorted(map(int, set(years[train]))),
        "test_years": sorted(map(int, set(years[test]))),
        "training_labels_available_before_test_year": cutoff is not None,
        "protocol": protocol,
    }


def plan_splits(rows: list[dict], *, protocol: str,
                test_year: int | None = None, folds: int = 3) -> dict:
    """Return deterministic split indices for synthetic datasets, or explicit skip.

    The caller must ensure the features themselves are point-in-time. No fitting,
    label inspection or hyperparameter selection occurs here. A fold's output
    contains only numeric indices and aggregate metadata, never real records.
    """
    if protocol not in PROTOCOLS:
        raise ValueError("unknown evaluation protocol")
    ids, years, available = _validate(rows)
    result = {"schema_version": SCHEMA, "protocol": protocol,
              "dataset_classification": "SYNTHETIC", "status": "evaluated",
              "limitation": "synthetic split planning; not external population validation",
              "folds": []}
    if protocol == "A_grouped":
        if not 2 <= folds <= 10 or len(set(ids)) < folds:
            raise ValueError("insufficient students or invalid grouped fold count")
        splitter = GroupKFold(n_splits=folds)
        for train, test in splitter.split(np.arange(len(ids)), groups=ids):
            result["folds"].append(_fold(ids, years, available, train, test, protocol, None))
        result["caveat"] = "group-isolated CV; mixes years, NOT out-of-time validation"
        return result
    if type(test_year) is not int or not 2001 <= test_year <= 2100:
        raise ValueError("temporal protocols require an explicit test_year")
    # An observation can only enter train after its outcome is known. Historical
    # observations with unavailable labels are excluded, NOT leaked into training.
    train = np.flatnonzero((years < test_year) & (available < test_year))
    test = np.flatnonzero(years == test_year)
    if protocol == "C_unseen_future":
        prior = set(ids[years < test_year])  # prior observation, even if its label cannot enter training
        test = np.asarray([i for i in test if ids[i] not in prior], dtype=int)
    if not len(train) or not len(test):
        result.update(status="not_identifiable", reason=(
            "insufficient_eligible_training_rows" if not len(train)
            else "no_unseen_future_students" if protocol == "C_unseen_future"
            else "no_future_year_rows"))
        return result
    result["folds"] = [_fold(ids, years, available, train, test, protocol, test_year)]
    result["test_year"] = test_year
    result["caveat"] = ("same students across years allowed; temporal shift only" if protocol == "B_out_of_time"
                        else "future cohorts disjoint from earlier labeled training cohorts")
    return result