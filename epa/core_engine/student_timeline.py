"""EPA Student Timeline: point-in-time snapshots of GENESIS v2 SYNTHETIC data.

Prediction features are built ONLY from prior school years and terms <= cutoff.
Future term labels are kept in a distinct 'target' field for offline research.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from epa.genesis.v2 import SCHEMA, validate_dataset

SNAPSHOT_SCHEMA = "epa.core_engine.student_snapshot.v1"
ARTIFACTS = ("students", "classes", "enrollments", "subject_offerings", "period_records")
CUTS = {"early": 1, "trajectory": 2, "consolidated": 3}


def read_verified_v2(directory: Path) -> dict[str, list[dict]]:
    """Reject missing, unexpected and modified v2 artifacts before reading Parquet."""
    import duckdb

    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA or manifest.get("classification") != "SYNTHETIC":
        raise ValueError("unsupported dataset schema or classification")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(ARTIFACTS):
        raise ValueError("incomplete v2 artifact manifest")
    data = {}
    db = duckdb.connect(":memory:")
    try:
        for name in ARTIFACTS:
            spec = artifacts[name]
            # Never allow manifest paths to escape the intended directory.
            if spec.get("path") != name + ".parquet":
                raise ValueError("unexpected artifact path")
            path = directory / spec["path"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if spec.get("sha256") != digest:
                raise ValueError("artifact digest mismatch")
            cursor = db.execute("SELECT * FROM read_parquet(?)", [str(path)])
            cols = [desc[0] for desc in cursor.description]
            data[name] = [dict(zip(cols, values)) for values in cursor.fetchall()]
            if spec.get("row_count") != len(data[name]):
                raise ValueError("artifact count mismatch")
    finally:
        db.close()
    validate_dataset(data)
    return data


def _aggregate(records: list[dict]) -> dict:
    sessions = sum(r["scheduled_sessions"] for r in records)
    present = sum(r["present_sessions"] for r in records)
    absences = sum(r["absences_total"] for r in records)
    excused = sum(r["absences_excused"] for r in records)
    unexcused = sum(r["absences_unexcused"] for r in records)
    if not sessions:
        raise ValueError("zero session count")
    return {
        "term_count": len(records),
        "mean_grade": round(sum(r["assessment_grade"] for r in records) / len(records), 6),
        "scheduled_sessions": sessions, "present_sessions": present,
        "absences_total": absences, "absences_excused": excused,
        "absences_unexcused": unexcused,
        "attendance_rate": round(present / sessions, 6),
    }


def build_snapshots(data: dict[str, list[dict]], *, cutoff: int) -> list[dict]:
    """Create one snapshot per enrollment/subject for a known term cutoff (1,2,3).

    History is restricted to the SAME subject in earlier academic years.
    Current-year observations include terms 1..cutoff only.
    No current year term 4 is included in a feature.
    """
    if cutoff not in (1, 2, 3):
        raise ValueError("cutoff must be 1, 2 or 3")
    by_student_subject: dict[tuple[str, str], list[dict]] = defaultdict(list)
    by_enrollment_subject: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in data["period_records"]:
        by_student_subject[(row["student_id"], row["subject_id"])].append(row)
        by_enrollment_subject[(row["enrollment_id"], row["subject_id"])].append(row)

    output = []
    for (enrollment_id, subject_id), current in sorted(by_enrollment_subject.items()):
        current.sort(key=lambda r: r["term"])
        reference = current[0]
        student_id = reference["student_id"]
        year = reference["academic_year"]
        eligible = [r for r in by_student_subject[(student_id, subject_id)]
                    if r["academic_year"] < year]
        available = [r for r in current if r["term"] <= cutoff]
        if len(available) != cutoff:
            raise ValueError("incomplete current cutoff")
        current_metrics = _aggregate(available)
        previous_metrics = _aggregate(eligible) if eligible else None

        # The label is strictly separate; training code must never place it in X.
        # Thresholds are SYNTHETIC illustrative policy, not school/BNCC policy.
        final_mean = sum(r["assessment_grade"] for r in current) / len(current)
        target = ("approved" if final_mean >= 6.0
                  else "recovery" if final_mean >= 4.0 else "failed")
        output.append({
            "student_id": student_id, "enrollment_id": enrollment_id,
            "class_id": reference["class_id"], "academic_year": year,
            "grade_level": reference["grade_level"], "subject_id": subject_id,
            "cutoff_term": cutoff, "known_term_count": len(available),
            "current": current_metrics,
            "prior_same_subject": previous_metrics,
            "prior_years_observed": len({r["academic_year"] for r in eligible}),
            "target_final_subject_outcome": target,
            "target_usage": "LABEL_ONLY_NOT_FEATURE",
            "data_classification": "SYNTHETIC",
        })
    return output


def student_profile(data: dict[str, list[dict]], student_id: str, *,
                    cutoff_year: int, cutoff_term: int) -> dict:
    """Retrieve full subject-wise timeline known at an explicit point in time."""
    if not 1 <= cutoff_term <= 4:
        raise ValueError("invalid cutoff term")
    if student_id not in {s["student_id"] for s in data["students"]}:
        raise ValueError("unknown student")
    history = sorted(
        (dict(r) for r in data["period_records"]
         if r["student_id"] == student_id
         and (r["academic_year"] < cutoff_year
              or (r["academic_year"] == cutoff_year and r["term"] <= cutoff_term))),
        key=lambda r: (r["academic_year"], r["subject_id"], r["term"])
    )
    return {
        "schema_version": SNAPSHOT_SCHEMA, "student_id": student_id,
        "cutoff_year": cutoff_year, "cutoff_term": cutoff_term,
        "data_classification": "SYNTHETIC", "records": history,
        "overall": _aggregate(history) if history else None,
    }


def run(directory: Path, *, cutoff: int) -> dict:
    data = read_verified_v2(directory)
    snapshots = build_snapshots(data, cutoff=cutoff)
    digest = hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest()
    return {
        "schema_version": SNAPSHOT_SCHEMA,
        "source_schema": SCHEMA, "source_manifest_sha256": digest,
        "data_classification": "SYNTHETIC",
        "prediction_cutoff_term": cutoff,
        "task": "synthetic_final_subject_outcome_3class",
        "target_policy": "ILLUSTRATIVE: approved >= 6, recovery >= 4, failed < 4",
        "feature_contract": "current terms <= cutoff; same-subject history from previous years only",
        "research_status": "FEATURE_PREPARATION_NOT_EMPIRICALLY_VALIDATED",
        "snapshots": snapshots,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build point-in-time GENESIS v2 research snapshots")
    parser.add_argument("--dataset", type=Path, required=True, help="GENESIS v2 directory")
    parser.add_argument("--cutoff", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists")
    report = run(args.dataset, cutoff=args.cutoff)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
