"""GENESIS independent entry cohorts for *synthetic* out-of-time validation.

Each cohort enrolls new students in the same ATLAS grade (grade 6) in a
different academic year. All identifiers are scoped to the year. No student
is reused across cohorts, unlike the longitudinal demonstration dataset.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from epa.atlas.catalog import load_catalog, catalog_sha256
from epa.genesis.v2 import build_dataset, validate_dataset, write_dataset


def build_cohorts(catalog, *, students_per_cohort: int, seed: int,
                  start_year: int, cohort_years: int = 3):
    if not 8 <= students_per_cohort <= 300:
        raise ValueError("students_per_cohort must be between 8 and 300")
    if not 2 <= cohort_years <= 5 or start_year + cohort_years - 1 > 2100:
        raise ValueError("invalid years")
    entities = ("students", "classes", "enrollments", "subject_offerings", "period_records")
    combined = {key: [] for key in entities}
    for i in range(cohort_years):
        year = start_year + i
        source = build_dataset(catalog, students=students_per_cohort, seed=seed + i,
                               start_year=year)
        # The first ATLAS grade is repeated in each entry cohort. Selecting by
        # academic year ensures a real cohort boundary and consistent grade.
        selected = [e for e in source["enrollments"] if e["academic_year"] == year]
        enrollment_ids = {e["enrollment_id"] for e in selected}
        class_ids = {e["class_id"] for e in selected}
        rename = {e["student_id"]: f"COHORT{year}-{e['student_id']}" for e in selected}
        combined["students"].extend(
            {**row, "student_id": rename[row["student_id"]]}
            for row in source["students"] if row["student_id"] in rename)
        combined["classes"].extend(c for c in source["classes"] if c["class_id"] in class_ids)
        combined["subject_offerings"].extend(o for o in source["subject_offerings"]
                                             if o["class_id"] in class_ids)
        combined["enrollments"].extend(
            {**e, "student_id": rename[e["student_id"]],
             "enrollment_id": f"{year}-{e['enrollment_id']}"}
            for e in selected)
        combined["period_records"].extend(
            {**r, "student_id": rename[r["student_id"]],
             "enrollment_id": f"{year}-{r['enrollment_id']}"}
            for r in source["period_records"] if r["enrollment_id"] in enrollment_ids)
    validate_dataset(combined)
    return combined


def main():
    parser = argparse.ArgumentParser(description="Generate disjoint synthetic entry cohorts")
    parser.add_argument("--catalog", type=Path, default=Path("examples/atlas.demo.json"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--students-per-cohort", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--start-year", type=int, default=2020)
    parser.add_argument("--cohort-years", type=int, default=3)
    args = parser.parse_args()
    catalog = load_catalog(args.catalog)
    dataset = build_cohorts(catalog, students_per_cohort=args.students_per_cohort,
                            seed=args.seed, start_year=args.start_year, cohort_years=args.cohort_years)
    print(json.dumps(write_dataset(dataset, args.output, seed=args.seed,
                                   catalog_digest=catalog_sha256(args.catalog)),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
