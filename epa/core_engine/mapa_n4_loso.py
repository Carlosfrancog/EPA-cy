"""Private two-student leave-one-student-out *calibration transfer* diagnostic.

Not an estimator leave-one-out validation: model weights are fitted to GENESIS
synthetic students, while the opposite real student's pre-2020 history supplies
only a distribution adapter. No real 2020-22 N4 label is used until scoring.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from epa.core_engine.mapa_real_n4 import (
    PUBLIC_MODELS, generated_synthetic_rows, load_private_inputs,
    load_private_answer_key, predict_all, score_predictions,
)
from epa.core_engine.mapa_n4_longitudinal import adapt_training, profile, read_history, file_digest

SCHEMA = "epa.mapa.n4.loso_calibration_transfer.v1"


def read_manifest(path: Path) -> list[dict]:
    """Two pseudonymous profiles, all private paths; exact keys and no raw data in output."""
    spec = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if set(spec) != {"students"} or not isinstance(spec["students"], list) or len(spec["students"]) != 2:
        raise ValueError("exactly two student profiles required")
    ids = set()
    profiles = []
    for entry in spec["students"]:
        if not isinstance(entry, dict) or set(entry) != {"student", "inputs", "calibration_history", "answer_key"}:
            raise ValueError("student manifest fields mismatch")
        name = entry["student"]
        if name not in ("ALN1", "ALN2") or name in ids:
            raise ValueError("unique pseudonymous ALN1 / ALN2 required")
        ids.add(name)
        values = {key: Path(entry[key]).expanduser().resolve() for key in ("inputs", "calibration_history", "answer_key")}
        if len({str(v) for v in values.values()}) != 3 or not all(v.is_file() for v in values.values()):
            raise ValueError("missing or duplicated private input paths")
        profiles.append({"student": name, **values})
    if ids != {"ALN1", "ALN2"}:
        raise ValueError("both ALN1 and ALN2 required")
    return profiles


def compare(profiles: list[dict], catalog: Path, *, students: int = 250, seed: int = 20261029,
            algorithms: tuple[str, ...] = PUBLIC_MODELS) -> tuple[dict, list[dict]]:
    if {p["student"] for p in profiles} != {"ALN1", "ALN2"} or len(profiles) != 2:
        raise ValueError("exactly two distinct students are required")
    if not algorithms or len(set(algorithms)) != len(algorithms) or set(algorithms) - set(PUBLIC_MODELS):
        raise ValueError("unknown or duplicate model")
    # Prepare all pre-N4 inputs and pre-2020 reference profiles before any scoring.
    prepared = {}
    for p in profiles:
        name = p["student"]
        cases = load_private_inputs(p["inputs"])
        history = read_history(p["calibration_history"])
        prepared[name] = {"cases": cases, "history": history,
                          "history_sha256": file_digest(p["calibration_history"]),
                          "answer_key": p["answer_key"]}
    synthetic, target, provenance = generated_synthetic_rows(catalog, students=students, seed=seed)
    comparisons = []
    private_predictions = []
    for held_out in ("ALN1", "ALN2"):
        reference = "ALN2" if held_out == "ALN1" else "ALN1"
        cases = prepared[held_out]["cases"]
        adapted, adapted_targets, audit = adapt_training(synthetic, target, profile(prepared[reference]["history"]))
        control, ctrl_time = predict_all(synthetic, target, cases, seed=seed, algorithms=algorithms)
        transfer, transfer_time = predict_all(adapted, adapted_targets, cases, seed=seed, algorithms=algorithms)
        # Only now open held-out labels. No labels from either 2020-22 test enter calibration.
        key = load_private_answer_key(prepared[held_out]["answer_key"], {r["id_caso"] for r in cases})
        a = score_predictions(control, cases, key, ctrl_time)["model_metrics"]
        b = score_predictions(transfer, cases, key, transfer_time)["model_metrics"]
        orig = {m["model"]: m for m in a}
        other = {m["model"]: m for m in b}
        comparisons.append({"held_out_student": held_out, "calibration_from": reference,
                            "n_cases": len(cases), "reference_records": len(prepared[reference]["history"]),
                            "reference_history_sha256": prepared[reference]["history_sha256"],
                            "calibration": audit,
                            "models": [{"model": m, "control": orig[m], "transferred": other[m],
                                        "delta_mae": round(other[m]["mae"] - orig[m]["mae"], 6)}
                                       for m in algorithms]})
        for i, r in enumerate(cases):
            private_predictions.append({"student": held_out, "id_caso": r["id_caso"],
               **{f"control__{m}": control[m][i] for m in algorithms},
               **{f"transferred__{m}": transfer[m][i] for m in algorithms}})
    # Equal-student weighting: 36 correlated cases are NOT 36 independent students.
    overall = []
    for m in algorithms:
        x = [next(y for y in c["models"] if y["model"] == m) for c in comparisons]
        overall.append({"model": m,
                        "mean_student_mae_control": round(sum(z["control"]["mae"] for z in x)/2, 6),
                        "mean_student_mae_transfer": round(sum(z["transferred"]["mae"] for z in x)/2, 6)})
    return {"schema_version": SCHEMA, "research_status": "EXPLORATORY_TWO_STUDENT_TRANSFER_NOT_POPULATION_VALIDATION",
            "independent_students": 2, "total_cases": 72, "generator": provenance,
            "catalog_sha256": file_digest(catalog), "protocol": "leave_one_student_out_calibration_transfer",
            "calibration_uses": "other_student_pre2020_only", "models": list(algorithms),
            "per_student": comparisons, "equal_student_mean": overall,
            "caveat": "Model trained on synthetic GENESIS, not on held-in student grades. Transfer tests generalization of calibration parameters only; results already inspected in preliminary experiments."}, private_predictions


def main():
    parser = argparse.ArgumentParser(description="Two-student private N4 LOSO calibration transfer")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=Path("examples/atlas.demo.json"))
    parser.add_argument("--students", type=int, default=250)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--models", nargs="+", choices=PUBLIC_MODELS, default=list(PUBLIC_MODELS))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--predictions", type=Path)
    args = parser.parse_args()
    for dest in (args.report, args.predictions):
        if dest is not None and (dest.exists() or dest.is_symlink()):
            parser.error("output already exists: immutable artifacts")
    result, predictions = compare(read_manifest(args.manifest), args.catalog,
                                  students=args.students, seed=args.seed, algorithms=tuple(args.models))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    if args.predictions:
        args.predictions.parent.mkdir(parents=True, exist_ok=True)
        with args.predictions.open("x", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["student", "id_caso", *[f"control__{m}" for m in args.models],
                                                     *[f"transferred__{m}" for m in args.models]])
            w.writeheader()
            w.writerows(predictions)
    print(json.dumps({"schema_version": SCHEMA, "students": 2, "cases": 72,
                      "protocol": result["protocol"]}))


if __name__ == "__main__":
    main()