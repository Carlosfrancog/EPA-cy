# MAPA MLflow → Rails run linkage v0.2

When `EPA_MLFLOW_TRACKING_URI` is configured, Python creates a sidecar
`data/mapa-runs/<id>/mlflow-links.json` **after** all nine MLflow runs complete.
The sidecar has schema `epa.mapa.mlflow_links.v1`, the immutable JSON report
SHA-256, and ordered triplets of protocol, algorithm and MLflow run ID.

Rails validates the expected nine pairs, unique hexadecimal IDs and report
digest, then stores the sidecar JSON in `mapa_runs.mlflow_links_json`.
The MAPA report screen displays the nine IDs. We deliberately do not link
the UI to a potentially untrusted tracking URI, and we do not store student rows.

Without MLflow configuration the JSON linkage remains NULL and the panel says
that tracking is disabled. Old reports are not backfilled.

Notes: no cross-system transaction; partial MLflow failures leave the Rails job
failed and may leave runs in MLflow. Deduplication/reconciliation and model
registry are separate future tasks. No proof of efficacy on real students.
