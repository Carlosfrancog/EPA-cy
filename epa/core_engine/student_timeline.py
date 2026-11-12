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
    """Build point-in-time academic snapshots with one pass over student history.

    Records are indexed by student/subject and enrollment/subject once.
    A chronological accumulator avoids repeatedly scanning previous years
    for every new subject/year snapshot. Its features contain strictly
    preceding years; the final outcome is stored only as a training label.
    """
    if cutoff not in (1, 2, 3):
        raise ValueError("cutoff must be 1, 2 or 3")

    grouped: dict[tuple[str, str], dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in data["period_records"]:
        grouped[(row["student_id"], row["subject_id"])][row["enrollment_id"]].append(row)

    output = []
    for (student_id, subject_id), enrollments in grouped.items():
        # History is accumulated in calendar order, independent of how
        # enrollment records happen to be ordered in the input.
        ordered = sorted(
            enrollments.items(), key=lambda item: item[1][0]["academic_year"]
        )
        prior_grade_sum = 0.0
        prior_terms = 0
        prior_sessions = prior_present = prior_absences = 0
        prior_excused = prior_unexcused = 0
        prior_years: set[int] = set()

        for enrollment_id, current in ordered:
            current.sort(key=lambda row: row["term"])
            reference = current[0]
            year = reference["academic_year"]
            available = [row for row in current if row["term"] <= cutoff]
            if len(available) != cutoff:
                raise ValueError("incomplete current cutoff")
            current_metrics = _aggregate(available)
            previous_metrics = None
            if prior_terms:
                previous_metrics = {
                    "term_count": prior_terms,
                    "mean_grade": round(prior_grade_sum / prior_terms, 6),
                    "scheduled_sessions": prior_sessions,
                    "present_sessions": prior_present,
                    "absences_total": prior_absences,
                    "absences_excused": prior_excused,
                    "absences_unexcused": prior_unexcused,
                    "attendance_rate": round(prior_present / prior_sessions, 6),
                }

            final_mean = sum(row["assessment_grade"] for row in current) / len(current)
            target = ("approved" if final_mean >= 6.0
                      else "recovery" if final_mean >= 4.0 else "failed")
            output.append({
                "student_id": student_id, "enrollment_id": enrollment_id,
                "class_id": reference["class_id"], "academic_year": year,
                "grade_level": reference["grade_level"], "subject_id": subject_id,
                "cutoff_term": cutoff, "known_term_count": len(available),
                "current": current_metrics,
                "prior_same_subject": previous_metrics,
                "prior_years_observed": len(prior_years),
                "target_final_subject_outcome": target,
                "target_usage": "LABEL_ONLY_NOT_FEATURE",
                "data_classification": "SYNTHETIC",
            })

            # Only after creating this year's snapshot do we advance the
            # historical accumulator. This is the point-in-time safety gate.
            prior_years.add(year)
            for record in current:
                prior_grade_sum += record["assessment_grade"]
                prior_terms += 1
                prior_sessions += record["scheduled_sessions"]
                prior_present += record["present_sessions"]
                prior_absences += record["absences_total"]
                prior_excused += record["absences_excused"]
                prior_unexcused += record["absences_unexcused"]

    # Retain historical API order for reproducible downstream model inputs.
    output.sort(key=lambda item: (item["enrollment_id"], item["subject_id"]))
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
