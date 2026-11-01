# MAPA Extended Rails

New MAPA runs generate separate MLP experimental reports. Enable optional XGBoost with `EPA_MAPA_XGBOOST=1` and install `.[research,boosting]`. Reports are validated by schema, manifest hash, seed and model list, persisted with SHA-256, and shown on `/mapa/:id` and `/mapa/evaluation`. Original MAPA baselines, MLflow nine-run contract and historical records are unchanged. The extended-model evidence gate remains `insufficient_evidence`; no real-world validation or automatic promotion.
