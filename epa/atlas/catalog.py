"""Validate explicit curriculum sources and local synthetic teaching plans."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ALLOWED_AREAS = {"MATEMATICA", "LINGUAGENS", "NATUREZA", "HUMANAS"}
def load_catalog(path: Path) -> dict:
    raw = path.read_bytes()
    catalog = json.loads(raw)
    if not isinstance(catalog, dict) or catalog.get("schema_version") != "epa.atlas.v1":
        raise ValueError("invalid catalog schema")
    if catalog.get("curriculum_type") != "SYNTHETIC_DEMO":
        raise ValueError("only synthetic demonstrator catalogs supported in MVP")
    source = catalog.get("source", {})
    if not isinstance(source, dict) or not source.get("reference_url") or not source.get("source_label"):
        raise ValueError("source reference required")
    grades = catalog.get("grades")
    if not isinstance(grades, list) or not grades:
        raise ValueError("grades required")
    seen = set()
    for grade in grades:
        level = grade.get("grade_level")
        if not isinstance(level, int) or not (6 <= level <= 12) or level in seen:
            raise ValueError("invalid or duplicate grade")
        seen.add(level)
        subjects = grade.get("subjects")
        if not isinstance(subjects, list) or not subjects:
            raise ValueError("subjects required")
        names = set()
        for subject in subjects:
            sid = subject.get("id")
            if not isinstance(sid, str) or not sid or sid in names or subject.get("area") not in ALLOWED_AREAS:
                raise ValueError("invalid or repeated subject")
            names.add(sid)
            if subject.get("bncc_skill_codes"):
                raise ValueError("skill links require an independently verified official import")
    return catalog

def catalog_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
