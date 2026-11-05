"""Fail-closed N1/N2/N3 feature-lineage gate for the current in-memory MAPA contract.

Prototype for MAPA v2 research snapshots; not yet wired to train jobs.
A scalable v3 gate must reproduce these checks with SQL/Parquet projections.
SHA-256 is evidence of content identity, NOT a validity status bit.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

METRIC_FIELDS = frozenset({
    "term_count", "mean_grade", "scheduled_sessions", "present_sessions",
    "absences_total", "absences_excused", "absences_unexcused", "attendance_rate",
})
SNAPSHOT_FIELDS = frozenset({
    "student_id", "enrollment_id", "class_id", "academic_year", "grade_level",
    "subject_id", "cutoff_term", "known_term_count", "current", "prior_same_subject",
    "prior_years_observed", "target_final_subject_outcome", "target_usage", "data_classification",
})


class Verdict(str, Enum):
    PERMIT = "PERMIT"
    DENY = "DENY"


@dataclass(frozen=True)
class Audit:
    verdict: Verdict
    manifest_sha256: str
    reasons: tuple[str, ...]
    checked_snapshots: int

    @property
    def approved_manifest_sha256(self) -> str | None:
        # Reject authorization without corrupting or modifying immutable evidence.
        return self.manifest_sha256 if self.verdict is Verdict.PERMIT else None


def _metrics(rows: list[dict]) -> dict[str, Any]:
    sessions = sum(row["scheduled_sessions"] for row in rows)
    present = sum(row["present_sessions"] for row in rows)
    if not rows or sessions <= 0:
        raise ValueError("incomplete or invalid history")
    return {
        "term_count": len(rows),
        "mean_grade": round(sum(row["assessment_grade"] for row in rows) / len(rows), 6),
        "scheduled_sessions": sessions,
        "present_sessions": present,
        "absences_total": sum(row["absences_total"] for row in rows),
        "absences_excused": sum(row["absences_excused"] for row in rows),
        "absences_unexcused": sum(row["absences_unexcused"] for row in rows),
        "attendance_rate": round(present / sessions, 6),
    }


def audit_cutoff(data: dict[str, list[dict]], snapshots: list[dict], *,
                 cutoff: int, manifest_sha256: str, max_reasons: int = 8) -> Audit:
    """Independently recompute allowed features using records known at cutoff.

    This prevents future-derived aggregates in N1/N2 and validates lineage.
    It does not prohibit *legitimate* statistical correlation between past
    grades and future outcomes, and does not prove model-training isolation.
    """
    reasons: list[str] = []
    def fail(message: str) -> None:
        if len(reasons) < max_reasons:
            reasons.append(message)

    if cutoff not in (1, 2, 3) or len(manifest_sha256) != 64 or any(
        c not in "0123456789abcdef" for c in manifest_sha256
    ):
        return Audit(Verdict.DENY, manifest_sha256, ("invalid cutoff or digest",), 0)
    if not isinstance(data, dict) or not isinstance(snapshots, list):
        return Audit(Verdict.DENY, manifest_sha256, ("missing source data/snapshots",), 0)
    try:
        records = data["period_records"]
        # The research grain is enrollment/year x subject; prior histories are
        # restricted to strictly older academic years in the same subject.
        by_key: dict[tuple[str, str], list[dict]] = {}
        by_student_subject: dict[tuple[str, str], list[dict]] = {}
        for row in records:
            if row.get("data_classification") != "SYNTHETIC":
                fail("non-synthetic source record")
            by_key.setdefault((row["enrollment_id"], row["subject_id"]), []).append(row)
            by_student_subject.setdefault((row["student_id"], row["subject_id"]), []).append(row)
        seen: set[tuple[str, str]] = set()
        for item in snapshots:
            if not isinstance(item, dict) or set(item) != SNAPSHOT_FIELDS:
                fail("unsupported snapshot fields; possible target/feature mixing")
                continue
            if item["cutoff_term"] != cutoff or item["target_usage"] != "LABEL_ONLY_NOT_FEATURE" or item["data_classification"] != "SYNTHETIC":
                fail("snapshot cutoff, target isolation, or classification mismatch")
                continue
            if not isinstance(item["current"], dict) or set(item["current"]) != METRIC_FIELDS:
                fail("unexpected current features")
                continue
            prior = item["prior_same_subject"]
            if prior is not None and (not isinstance(prior, dict) or set(prior) != METRIC_FIELDS):
                fail("unexpected prior features")
                continue
            key = (item["enrollment_id"], item["subject_id"])
            if key in seen:
                fail("duplicate snapshot")
                continue
            seen.add(key)
            full = by_key.get(key, [])
            if not full:
                fail("unknown enrollment/subject")
                continue
            first = full[0]
            if any(r["academic_year"] != item["academic_year"] or
                   r["student_id"] != item["student_id"] or
                   r["class_id"] != item["class_id"] or
                   r["grade_level"] != item["grade_level"] for r in full):
                fail("snapshot identity and source identity disagree")
                continue
            known = [r for r in full if 1 <= r["term"] <= cutoff]
            if len(known) != cutoff or item["known_term_count"] != cutoff:
                fail("incomplete/invalid cutoff periods")
                continue
            expected_current = _metrics(known)
            historic = [r for r in by_student_subject[(item["student_id"], item["subject_id"])]
                        if r["academic_year"] < item["academic_year"]]
            expected_prior = _metrics(historic) if historic else None
            years = len({r["academic_year"] for r in historic})
            if item["current"] != expected_current:
                fail(f"future/incorrect current features: {key}")
            if item["prior_same_subject"] != expected_prior or item["prior_years_observed"] != years:
                fail(f"future/incorrect prior features: {key}")
        if seen != set(by_key):
            fail("missing or extraneous snapshots")
    except (KeyError, ValueError, TypeError, ZeroDivisionError) as exc:
        fail(f"unable to verify lineage: {type(exc).__name__}")
    return Audit(Verdict.DENY if reasons else Verdict.PERMIT, manifest_sha256,
                 tuple(reasons), len(snapshots))
