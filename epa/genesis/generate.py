"""Deterministic, partitioned synthetic grade and attendance generator.

No attempt is made to claim realistic demographic, pedagogic or causal validity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import random
from datetime import date
from pathlib import Path

from epa.atlas.catalog import catalog_sha256, load_catalog

def _seed(base: int, *parts: object) -> int:
    value = "|".join(map(str, (base, *parts))).encode()
    return int.from_bytes(hashlib.sha256(value).digest()[:8], "big")

def _score(value: float) -> float:
    return round(max(0.0, min(10.0, value)), 2)

def build_rows(catalog: dict, n_students: int, seed: int, start_year: int) -> list[dict]:
    if n_students < 1 or n_students > 50000:
        raise ValueError("MVP student count must be between 1 and 50000")
    if not isinstance(seed, int) or not 2000 <= start_year <= 2100:
        raise ValueError("invalid seed or start year")
    grades = sorted(catalog["grades"], key=lambda g: g["grade_level"])
    rows = []
    for student_num in range(1, n_students + 1):
        student_id = f"SYN{student_num:08d}"
        profile = random.Random(_seed(seed, student_id, "profile"))
        strengths = {area: profile.uniform(-1.8, 1.8) for area in ["MATEMATICA", "LINGUAGENS", "NATUREZA", "HUMANAS"]}
        trend = profile.uniform(-0.35, 0.35)
        for i, grade in enumerate(grades):
            year = start_year + i
            for sub in grade["subjects"]:
                r = random.Random(_seed(seed, student_id, year, sub["id"]))
                score = _score(6.3 + strengths[sub["area"]] + trend * i + r.gauss(0, 1.05))
                attendance = round(max(0.0, min(1.0, 0.89 + r.gauss(0, 0.085) - max(0, 5-score) * 0.015)), 4)
                rows.append({"student_id": student_id, "academic_year": year, "grade_level": grade["grade_level"],
                             "subject_id": sub["id"], "knowledge_area": sub["area"], "final_grade": score,
                             "attendance_rate": attendance, "data_classification": "SYNTHETIC"})
    return rows

def write_parquet(rows: list[dict], destination: Path, catalog_digest: str, seed: int) -> dict:
    import duckdb
    if destination.exists():
        raise FileExistsError("immutable dataset destination already exists")
    destination.mkdir(parents=True)
    output = destination / "academic_history.parquet"
    con = duckdb.connect(":memory:")
    try:
        con.execute("CREATE TABLE records (student_id VARCHAR, academic_year INTEGER, grade_level INTEGER, subject_id VARCHAR, knowledge_area VARCHAR, final_grade DOUBLE, attendance_rate DOUBLE, data_classification VARCHAR)")
        con.executemany("INSERT INTO records VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [tuple(r.values()) for r in rows])
        # Destination is controlled by caller, not interpolated from the dataset.
        con.execute("COPY records TO ? (FORMAT PARQUET)", [str(output)])
    finally:
        con.close()
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest = {"schema_version":"epa.genesis.dataset.v1","classification":"SYNTHETIC","generator_seed":seed,
                "catalog_sha256":catalog_digest,"row_count":len(rows),"artifact_path":"academic_history.parquet",
                "digest_algorithm":"sha256","digest":digest,"scope":"synthetic demonstration, not empirical validation"}
    (destination/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return manifest

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--catalog",type=Path,default=Path("examples/atlas.demo.json"))
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--students",type=int,default=25)
    p.add_argument("--seed",type=int,default=20261029)
    p.add_argument("--start-year",type=int,default=2020)
    a=p.parse_args()
    catalog=load_catalog(a.catalog)
    rows=build_rows(catalog,a.students,a.seed,a.start_year)
    print(json.dumps(write_parquet(rows,a.output,catalog_sha256(a.catalog),a.seed),ensure_ascii=False,indent=2))
if __name__ == "__main__":
    main()
