"""Verified native GENESIS Rust -> immutable MAPA features (DuckDB/Parquet).

Features are computed point-in-time. Labels can use final-year terms but are
never exported among the eleven model features. Synthetic datasets only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from epa.genesis.parquet_deep_audit import audit, quoted_path

SCHEMA = "epa.mapa.feature_dataset.v1"
SOURCE_SCHEMA = "epa.genesis.dataset.rust_native.v1"
FEATURES = (
    "current_mean_grade", "current_attendance_rate", "current_absences",
    "current_unexcused_absences", "current_sessions", "prior_mean_grade",
    "prior_attendance_rate", "prior_absences", "prior_unexcused_absences",
    "prior_term_count", "prior_years_observed",
)


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _query(cutoff: int, period_path: Path) -> str:
    if cutoff not in (1, 2, 3):
        raise ValueError("cutoff must be 1, 2 or 3")
    return f"""
WITH annual AS (
 SELECT enrollment_id, student_id, class_id, academic_year, grade_level, subject_id,
   COUNT(*) AS total_terms,
   SUM(assessment_grade) AS total_grades,
   SUM(scheduled_sessions) AS all_sessions,
   SUM(present_sessions) AS all_present,
   SUM(absences_total) AS all_absences,
   SUM(absences_unexcused) AS all_unexcused,
   SUM(CASE WHEN term <= {cutoff} THEN assessment_grade ELSE 0 END) AS current_grades,
   SUM(CASE WHEN term <= {cutoff} THEN scheduled_sessions ELSE 0 END) AS current_sessions,
   SUM(CASE WHEN term <= {cutoff} THEN present_sessions ELSE 0 END) AS current_present,
   SUM(CASE WHEN term <= {cutoff} THEN absences_total ELSE 0 END) AS current_absences,
   SUM(CASE WHEN term <= {cutoff} THEN absences_unexcused ELSE 0 END) AS current_unexcused,
   SUM(CASE WHEN term <= {cutoff} THEN 1 ELSE 0 END) AS known_terms
 FROM read_parquet({quoted_path(period_path)})
 GROUP BY enrollment_id, student_id, class_id, academic_year, grade_level, subject_id
), history AS (
 SELECT *,
  SUM(total_terms) OVER prior AS prior_terms,
  SUM(total_grades) OVER prior AS prior_grades,
  SUM(all_sessions) OVER prior AS prior_sessions,
  SUM(all_present) OVER prior AS prior_present,
  SUM(all_absences) OVER prior AS prior_absences,
  SUM(all_unexcused) OVER prior AS prior_unexcused,
  COUNT(*) OVER prior AS prior_years
 FROM annual
 WINDOW prior AS (
  PARTITION BY student_id, subject_id ORDER BY academic_year
  ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
 )
)
SELECT student_id, enrollment_id, class_id, academic_year, grade_level, subject_id,
 {cutoff}::INTEGER AS cutoff_term, known_terms::INTEGER AS known_term_count,
 ROUND(current_grades / known_terms, 6) AS current_mean_grade,
 ROUND(current_present::DOUBLE / current_sessions, 6) AS current_attendance_rate,
 current_absences::INTEGER AS current_absences,
 current_unexcused::INTEGER AS current_unexcused_absences,
 current_sessions::INTEGER AS current_sessions,
 CASE WHEN prior_terms IS NULL THEN NULL ELSE ROUND(prior_grades / prior_terms, 6) END AS prior_mean_grade,
 CASE WHEN prior_terms IS NULL THEN NULL ELSE ROUND(prior_present::DOUBLE / prior_sessions, 6) END AS prior_attendance_rate,
 prior_absences::INTEGER AS prior_absences,
 prior_unexcused::INTEGER AS prior_unexcused_absences,
 COALESCE(prior_terms, 0)::INTEGER AS prior_term_count,
 prior_years::INTEGER AS prior_years_observed,
 CASE WHEN total_grades / total_terms >= 6 THEN 'approved'
      WHEN total_grades / total_terms >= 4 THEN 'recovery'
      ELSE 'failed' END AS target_final_subject_outcome,
 'LABEL_ONLY_NOT_FEATURE' AS target_usage,
 'SYNTHETIC' AS data_classification
FROM history ORDER BY enrollment_id, subject_id
"""


def export(directory: Path, destination: Path, *, memory_limit: str = "512MB",
           threads: int = 2) -> dict:
    """Audit source, reject incomplete timelines, persist N1/N2/N3 and hashes."""
    import duckdb

    directory, destination = Path(directory), Path(destination)
    if not re.fullmatch(r"[1-9][0-9]*(?:KB|MB|GB)", memory_limit, re.I):
        raise ValueError("invalid memory_limit")
    if not 1 <= threads <= 32:
        raise ValueError("threads must be 1..32")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("immutable output already exists")

    manifest_path = directory / "manifest.json"
    source = json.loads(manifest_path.read_text(encoding="utf-8"))
    if source.get("schema_version") != SOURCE_SCHEMA or source.get("classification") != "SYNTHETIC":
        raise ValueError("expected SYNTHETIC GENESIS Rust native dataset")
    # Validates manifest hashes/counts and 17 SQL referential/domain invariants.
    checked = audit(directory, memory_limit=memory_limit, threads=threads)
    if checked["status"] != "PASS":
        raise ValueError("GENESIS SQL integrity checks failed")
    source_records = source["artifacts"]["period_records"]["row_count"]
    if not source_records:
        raise ValueError("empty source period_records")

    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(dir=destination.parent, prefix=f".{destination.name}.tmp-"))
    try:
        conn = duckdb.connect(":memory:")
        try:
            conn.execute(f"SET threads={threads}")
            conn.execute(f"SET memory_limit='{memory_limit}'")
            scratch = stage / "scratch"
            scratch.mkdir()
            conn.execute(f"SET temp_directory={quoted_path(scratch)}")
            p = directory / "period_records.parquet"
            conn.execute(f"CREATE VIEW periods AS SELECT * FROM read_parquet({quoted_path(p)})")
            missing = conn.execute("""
                SELECT COUNT(*) FROM (
                  SELECT enrollment_id, subject_id
                  FROM periods GROUP BY 1,2
                  HAVING COUNT(*) != 4 OR COUNT(DISTINCT term) != 4
                )
            """).fetchone()[0]
            if missing:
                raise ValueError(f"incomplete subject/year terms: {missing}")
            artifacts = {}
            for cutoff in (1, 2, 3):
                name = f"N{cutoff}.parquet"
                path = stage / name
                conn.execute(f"COPY ({_query(cutoff, p)}) TO {quoted_path(path)} (FORMAT PARQUET)")
                count = conn.execute(
                    f"SELECT COUNT(*) FROM read_parquet({quoted_path(path)})"
                ).fetchone()[0]
                if count * 4 != source_records:
                    raise ValueError(f"N{cutoff}: unexpected snapshot count {count}")
                artifacts[f"N{cutoff}"] = {
                    "path": name, "row_count": count, "sha256": _digest(path)
                }
        finally:
            conn.close()
        shutil.rmtree(stage / "scratch", ignore_errors=True)
        report = {
            "schema_version": SCHEMA,
            "classification": "SYNTHETIC",
            "source_schema": SOURCE_SCHEMA,
            "source_manifest_sha256": _digest(manifest_path),
            "catalog_sha256": source.get("catalog_sha256"),
            "generator_seed": source.get("generator_seed"),
            "feature_names": list(FEATURES),
            "cutoffs": {"N1": 1, "N2": 2, "N3": 3},
            "target": "final_subject_grade_3class",
            "target_policy": "approved >=6; recovery >=4; failed <4 (synthetic)",
            "target_usage": "LABEL_ONLY_NOT_FEATURE",
            "artifacts": artifacts,
            "research_status": "SYNTHETIC_NOT_EMPIRICALLY_VALIDATED",
        }
        (stage / "manifest.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if destination.exists() or destination.is_symlink():
            raise FileExistsError("destination concurrently created")
        os.rename(stage, destination)
        return report
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--memory-limit", default="512MB")
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    report = export(args.dataset, args.output, memory_limit=args.memory_limit, threads=args.threads)
    print(json.dumps({"status": "PASS", "rows": {
        key: artifact["row_count"] for key, artifact in report["artifacts"].items()
    }}, indent=2))


if __name__ == "__main__":
    main()
