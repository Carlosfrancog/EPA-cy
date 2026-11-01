"""Optional MLflow tracking adapter for a completed MAPA synthetic report.

No data rows, identifiers or sensitive student features are logged.
MLflow failure never alters the immutable local report; process exits nonzero.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


def log_benchmark(report: dict, *, tracking_uri: str, experiment_name: str,
                  report_path: Path, client=None) -> list[str]:
    if report.get("schema_version") != "epa.mapa.benchmark.v1":
        raise ValueError("unexpected MAPA report schema")
    if report.get("dataset_classification") != "SYNTHETIC":
        raise ValueError("only synthetic MAPA runs can be tracked")
    if len(report.get("baselines", [])) != 3:
        raise ValueError("three MAPA protocols expected")
    if client is None:
        try:
            import mlflow
        except ImportError as exc:
            raise RuntimeError("Install the optional MLflow dependency: pip install -e '.[tracking]'") from exc
        client = mlflow

    client.set_tracking_uri(tracking_uri)
    client.set_experiment(experiment_name)
    report_digest = hashlib.sha256(report_path.read_bytes()).hexdigest()
    run_ids = []
    for block in report["baselines"]:
        for result in block["results"]:
            # One immutable snapshot of the MODEL RESULTS per cutoff/algorithm.
            with client.start_run(run_name=f"mapa-{block['protocol']}-{result['model']}") as active:
                client.set_tags({
                    "epa.product": "MAPA", "epa.dataset_kind": "SYNTHETIC",
                    "epa.research_status": "EXPERIMENTAL_NOT_EMPIRICALLY_VALIDATED",
                    "epa.schema_version": report["schema_version"],
                    "epa.dataset_manifest_sha256": report["dataset_manifest_sha256"],
                    "epa.report_sha256": report_digest,
                })
                client.log_params({
                    "protocol": block["protocol"], "cutoff_term": block["cutoff_term"],
                    "algorithm": result["model"], "seed": block["seed"],
                    "split": block["split"], "feature_count": len(block["feature_names"]),
                    "train_students": block["train_students"],
                    "test_students": block["test_students"],
                })
                client.log_metrics({
                    "accuracy": result["accuracy"],
                    "balanced_accuracy": result["balanced_accuracy"],
                    "f1_macro": result["f1_macro"],
                    **{f"recall_{key}": value for key, value in result["recall_by_class"].items()},
                    **{f"test_count_{key}": value for key, value in block["test_class_counts"].items()},
                })
                run_ids.append(active.info.run_id)
    return run_ids
