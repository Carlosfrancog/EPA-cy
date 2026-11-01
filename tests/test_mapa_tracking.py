import hashlib
import json

import pytest

from epa.core_engine.mapa_tracking import log_benchmark


class FakeRun:
    def __init__(self, run_id):
        self.info = type("Info", (), {"run_id": run_id})()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeClient:
    def __init__(self):
        self.started = []
        self.params = []
        self.metrics = []
        self.tags = []

    def set_tracking_uri(self, value):
        self.uri = value

    def set_experiment(self, value):
        self.experiment = value

    def start_run(self, *, run_name):
        self.started.append(run_name)
        return FakeRun(str(len(self.started)))

    def set_tags(self, tags):
        self.tags.append(tags)

    def log_params(self, values):
        self.params.append(values)

    def log_metrics(self, values):
        self.metrics.append(values)


def test_tracks_nine_runs_and_keeps_identifiers_out(tmp_path):
    path = tmp_path / "report.json"
    path.write_text('{"synthetic":true}', encoding="utf8")
    blocks = []
    for term, protocol in [(1, "early"), (2, "trajectory"), (3, "consolidated")]:
        blocks.append({
            "protocol": protocol, "cutoff_term": term, "seed": 5,
            "split": "GroupShuffleSplit_by_student", "feature_names": ["attendance"],
            "train_students": 10, "test_students": 4,
            "test_class_counts": {"approved": 2, "recovery": 1, "failed": 1},
            "results": [
                {"model": algo, "accuracy": .5, "balanced_accuracy": .4, "f1_macro": .35,
                 "recall_by_class": {"approved": .5, "recovery": .4, "failed": .2}}
                for algo in ("majority", "logistic_regression", "random_forest")
            ],
        })
    report = {
        "schema_version": "epa.mapa.benchmark.v1",
        "dataset_classification": "SYNTHETIC",
        "dataset_manifest_sha256": "a" * 64, "baselines": blocks,
    }
    client = FakeClient()
    ids = log_benchmark(report, tracking_uri="sqlite:///mlflow.db",
                        experiment_name="EPA MAPA Synthetic",
                        report_path=path, client=client)
    assert len(ids) == 9
    assert len(client.metrics) == 9
    assert client.tags[0]["epa.report_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert client.params[-1]["algorithm"] == "random_forest"
    assert "student_id" not in json.dumps(client.params + client.tags + client.metrics)
    assert client.experiment == "EPA MAPA Synthetic"


def test_rejects_wrong_source(tmp_path):
    path = tmp_path / "report.json"
    path.write_text("{}")
    with pytest.raises(ValueError, match="synthetic"):
        log_benchmark({"schema_version": "epa.mapa.benchmark.v1",
                       "dataset_classification": "REAL", "baselines": [1, 2, 3]},
                      tracking_uri="sqlite:///x.db", experiment_name="x",
                      report_path=path, client=FakeClient())
