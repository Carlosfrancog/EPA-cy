"""Local conversion of own trusted academic PKLs into a PRIVATE pre-2020 CSV.

WARNING: pickle can execute code; run ONLY on files you produced and trust.
Never commit the CSV or zip to a public repo.
"""
from __future__ import annotations

import argparse
import csv
import io
import pickle
import zipfile
from pathlib import Path


FIELDS = ["id_caso", "serie", "ano_letivo", "disciplina", "N1", "N2", "N3", "N4"]


def export(source_zip: Path, destination: Path) -> int:
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("private output must not be overwritten")
    output = []
    with zipfile.ZipFile(source_zip) as archive:
        for name in sorted(archive.namelist()):
            if not name.lower().endswith(".pkl"):
                continue
            # Only trusted user-produced PKL. Limit file size to prevent accidental huge loads.
            if archive.getinfo(name).file_size > 128 * 1024:
                raise ValueError("unexpectedly large PKL")
            record = pickle.loads(archive.read(name))
            serie = str(record["ano"]).upper()
            if not serie.endswith("F") or not serie[:-1].isdigit():
                continue
            year = 2010 + int(serie[:-1])
            if year not in range(2011, 2020):
                continue
            b = record["bimestres"]
            output.append({"id_caso": Path(name).stem, "serie": serie, "ano_letivo": year,
                           "disciplina": str(record["materia"]),
                           "N1": b["1B"], "N2": b["2B"], "N3": b["3B"], "N4": b["4B"]})
    if len(output) < 30 or len({r["id_caso"] for r in output}) != len(output):
        raise ValueError("insufficient or duplicate historical records")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output)
    return len(output)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--pkl-zip", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    print(f"Private pre-2020 records exported: {export(a.pkl_zip, a.output)}")