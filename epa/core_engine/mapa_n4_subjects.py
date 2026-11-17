"""Vetted spelling aliases for the N4 high-school grade prediction protocol.

Only language/orthography is normalized; subjects are never inferred via fuzzy match.
Historical Fundamental 'ciencias' is not a High School subject ID.
"""
from __future__ import annotations
import re
import unicodedata


def normalize_subject(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("empty school subject")
    text = unicodedata.normalize("NFKD", value.strip().casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.split(r"[\s_-]+", text))


# Explicit, documented equivalences. No arbitrary corrections, e.g. Ciencias != Fisica.
ALIASES = {
    "artes": ("ART", "LINGUAGENS"),
    "arte": ("ART", "LINGUAGENS"),
    "biologia": ("BIO", "NATUREZA"),
    "educacao fisica": ("EDF", "LINGUAGENS"),
    "filosofia": ("FIL", "HUMANAS"),
    "fisica": ("FIS", "NATUREZA"),
    "geografia": ("GEO", "HUMANAS"),
    "historia": ("HIS", "HUMANAS"),
    "ingles": ("ING", "LINGUAGENS"),
    "matematica": ("MAT", "MATEMATICA"),
    "portugues": ("POR", "LINGUAGENS"),
    "quimica": ("QUI", "NATUREZA"),
    "sociologia": ("SOC", "HUMANAS"),
}