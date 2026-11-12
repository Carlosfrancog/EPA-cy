"""Bounded MAPA training from verified GENESIS Rust feature Parquet."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score, f1_score, recall_score, confusion_matrix, balanced_accuracy_score, log_loss
from epa.core_engine.mapa import FEATURES, CLASSES, models
from epa.core_engine.mapa_feature_export import SCHEMA as INPUT_SCHEMA

SCHEMA = "epa.mapa.native_training.v1"

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for piece in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(piece)
    return h.hexdigest()

def verify(directory):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("schema_version") != INPUT_SCHEMA or
        manifest.get("classification") != "SYNTHETIC" or
        manifest.get("feature_names") != list(FEATURES) or
        manifest.get("target_usage") != "LABEL_ONLY_NOT_FEATURE" or
        manifest.get("cutoffs") != {"N1":1,"N2":2,"N3":3} or
        set(manifest.get("artifacts", {})) != {"N1","N2","N3"}):
        raise ValueError("invalid feature manifest")
    for n in (1,2,3):
        name = f"N{n}"
        artifact = manifest["artifacts"][name]
        if artifact.get("path") != f"{name}.parquet":
            raise ValueError("unsafe artifact path")
        path = directory / artifact["path"]
        if digest(path) != artifact.get("sha256"):
            raise ValueError("feature Parquet digest mismatch")
    return manifest

def scores(y, pred, proba):
    if (proba.shape != (len(y), 3) or not np.all(np.isfinite(proba)) or
        np.any(proba < 0) or not np.allclose(proba.sum(axis=1),1,atol=1e-8)):
        raise ValueError("invalid predicted class probabilities")
    hot = (y[:,None] == np.asarray(CLASSES)[None,:]).astype(float)
    return {
        "accuracy": float(accuracy_score(y,pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y,pred)),
        "f1_macro": float(f1_score(y,pred,labels=CLASSES,average="macro",zero_division=0)),
        "recall_by_class": dict(zip(CLASSES,[float(v) for v in recall_score(y,pred,labels=CLASSES,average=None,zero_division=0)])),
        "confusion_matrix": confusion_matrix(y,pred,labels=CLASSES).tolist(),
        "log_loss": float(log_loss(y,proba,labels=CLASSES)),
        "brier_multiclass": float(np.mean(np.sum((proba-hot)**2,axis=1))),
    }

def run(directory, *, seed=20261029, max_students=500,
        algorithms=("majority","logistic_regression"), test_size=0.25):
    import duckdb
    directory = Path(directory)
    if not 8 <= max_students <= 5000 or not 0 < test_size < 1:
        raise ValueError("invalid student cap or split fraction")
    if not algorithms or set(algorithms) - {"majority","logistic_regression","random_forest","mlp"}:
        raise ValueError("invalid algorithm")
    manifest = verify(directory)
    with duckdb.connect(":memory:") as db:
        db.execute("SET memory_limit='512MB'")
        first = str(directory / "N1.parquet")
        students = [r[0] for r in db.execute(
            "SELECT DISTINCT student_id FROM read_parquet(?) ORDER BY student_id",[first]
        ).fetchall()]
        if len(students) < 8 or any(not (s.startswith("SYN") and s[3:].isdigit()) for s in students):
            raise ValueError("invalid student population")
        chosen = sorted(students,key=lambda s:(hashlib.sha256(f"{seed}|{s}".encode()).digest(),s))[:max_students]
        # GroupShuffleSplit is performed on UNIQUE student groups and reused for all cutoffs.
        groups = np.asarray(sorted(chosen))
        tr,te = next(GroupShuffleSplit(n_splits=1,test_size=test_size,random_state=seed).split(groups,groups=groups))
        train_ids, test_ids = set(groups[tr]), set(groups[te])
        blocks = []
        for cutoff in (1,2,3):
            cols = ["student_id",*FEATURES,"target_final_subject_outcome"]
            projection = ",".join('"' + c + '"' for c in cols)
            file = str(directory / f"N{cutoff}.parquet")
            count = db.execute("SELECT COUNT(*) FROM read_parquet(?)",[file]).fetchone()[0]
            if count != manifest["artifacts"][f"N{cutoff}"]["row_count"]:
                raise ValueError("feature count mismatch")
            placeholders = ",".join("?" for _ in chosen)
            rows = db.execute(
                f"SELECT {projection} FROM read_parquet(?) WHERE student_id IN ({placeholders}) "
                "AND cutoff_term=? AND data_classification='SYNTHETIC' "
                "AND target_usage='LABEL_ONLY_NOT_FEATURE' ORDER BY enrollment_id,subject_id",
                [file,*chosen,cutoff]
            ).fetchall()
            if not rows: raise ValueError("empty snapshots")
            student_ids = np.asarray([r[0] for r in rows])
            if set(student_ids) != set(chosen): raise ValueError("missing students in cutoff")
            x = np.asarray([[float(v) if v is not None else np.nan for v in r[1:-1]] for r in rows],dtype=float)
            y = np.asarray([r[-1] for r in rows])
            if set(y) - set(CLASSES): raise ValueError("invalid labels")
            train = np.isin(student_ids,list(train_ids))
            test = np.isin(student_ids,list(test_ids))
            if len(set(y[train])) < 2: raise ValueError("insufficient training classes")
            outcomes = []
            for name in algorithms:
                if name == "mlp":
                    from sklearn.neural_network import MLPClassifier
                    from sklearn.pipeline import make_pipeline
                    from sklearn.impute import SimpleImputer
                    from sklearn.preprocessing import StandardScaler
                    model = make_pipeline(SimpleImputer(strategy="constant",fill_value=0),StandardScaler(),
                                          MLPClassifier(hidden_layer_sizes=(32,16),max_iter=300,random_state=seed))
                else:
                    model = models(seed)[name]
                begin = time.perf_counter()
                model.fit(x[train],y[train])
                fit_seconds = time.perf_counter()-begin
                pred = model.predict(x[test])
                raw = model.predict_proba(x[test])
                aligned = np.zeros((len(pred),len(CLASSES)))
                for i,label in enumerate(CLASSES):
                    if label in model.classes_:
                        aligned[:,i] = raw[:,list(model.classes_).index(label)]
                outcomes.append({"model":name,"fit_seconds":fit_seconds,**scores(y[test],pred,aligned)})
            blocks.append({"cutoff_term":cutoff,"train_students":len(train_ids),
                           "test_students":len(test_ids),"train_observations":int(train.sum()),
                           "test_observations":int(test.sum()),
                           "test_class_counts":{c:int(np.sum(y[test]==c)) for c in CLASSES},
                           "results":outcomes})
    return {"schema_version":SCHEMA,"research_status":"SYNTHETIC_NOT_EMPIRICALLY_VALIDATED",
            "feature_manifest_sha256":digest(directory/"manifest.json"),
            "seed":seed,"selected_students":len(chosen),"student_cap":max_students,
            "sampling":"SHA256(seed|student_id)","split":"GroupShuffleSplit unique students reused across N1-N3",
            "feature_names":list(FEATURES),"classes":list(CLASSES),"protocols":blocks,
            "limitations":["scikit-learn fits in memory; not out-of-core",
             "student/subject records are correlated",
             "single holdout, synthetic labels; no real-school validity",
             "unadjusted probabilities; calibration to be studied with separate validation"]}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--features",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--max-students",type=int,default=500)
    ap.add_argument("--seed",type=int,default=20261029)
    ap.add_argument("--models",nargs="+",default=["majority","logistic_regression"],
                    choices=["majority","logistic_regression","random_forest","mlp"])
    args=ap.parse_args()
    if args.output.exists(): ap.error("immutable report already exists")
    report=run(args.features,seed=args.seed,max_students=args.max_students,algorithms=tuple(args.models))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as target:
        json.dump(report,target,indent=2,ensure_ascii=False)
        target.write("\n")
    print(json.dumps({"status":"PASS","cutoffs":3,"selected_students":report["selected_students"]}))

if __name__ == "__main__":
    main()
