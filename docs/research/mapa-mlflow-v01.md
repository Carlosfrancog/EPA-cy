# EPA MAPA — MLflow tracking v0.1

The scientific baseline **still generates a verified local report first**. MLflow is optional: without `--mlflow-uri` the Python CLI and Rails operation remain unchanged.

## Enable

```bash
python -m pip install -e ".[dev,research,tracking]"
python -m epa.genesis.v2 --output data/demo-mlflow --students 100
python -m epa.core_engine.mapa --dataset data/demo-mlflow \
  --output data/mapa-report.json --mlflow-uri sqlite:///data/epa-mlflow.db
mlflow ui --backend-store-uri sqlite:///data/epa-mlflow.db --port 5000
```

Rails local-only configuration: set `EPA_MLFLOW_TRACKING_URI=sqlite:///data/epa-mlflow.db` before launching the local server/worker. This is a relative path interpreted by the Python process running with the Rails project as working directory. The database file is operational metadata and must not be committed to Git.

For each benchmark: three protocols (N1/N2/N3) × three algorithms = **nine MLflow tracking runs**. The tracker records accuracy, balanced accuracy, F1 macro, recall per class, test class counts, seed, dataset manifest digest, report digest, split type, algorithm and student counts. It **does not upload student records** or the training dataset.

Tracking is performed **after** the local JSON report has been written. MLflow failure produces a nonzero CLI exit and the Rails job fails with a controlled failure code; the local report is retained for diagnosis. Retries can create duplicate MLflow runs if the process fails partway through, so deduplication and durable cross-system transaction semantics remain future work. The version does not yet persist MLflow run IDs in Rails or register deployable models.

**Caution:** all metrics are from simplified synthetic data. MLflow does not certify model quality. Class imbalance and temporal validation still need scientific investigation.
