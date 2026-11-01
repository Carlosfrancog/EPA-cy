# MAPA Extended Models v0.1

Separate experimental benchmark for MLP and optional XGBoost; **does not**
change the frozen baseline contract, its three models, nine MLflow runs,
LUPA Random Forest model, or Rails historical records.

```bash
python -m epa.core_engine.mapa_extended --dataset data/mapa-demo-v2 \
  --output data/mapa-extended.json --seed 20261029

pip install -e '.[research,boosting]'
python -m epa.core_engine.mapa_extended --dataset data/mapa-demo-v2 \
  --output data/mapa-extended-xgb.json --xgboost
```

- The same student-group holdout and allowlisted timestamped features as MAPA baseline.
- MLP uses training-only imputation and scaling, two hidden layers (32,16).
- XGBoost uses training-only imputation, fixed tree and learning-rate settings, encoded labels; if any class is missing from training, the XGBoost result is explicitly skipped.
- All metrics refer to the synthetic three-class outcome with fixed macro F1 label order, per-class recall and confusion matrices.
- These are **candidate baselines, not tuned or empirically validated models**. Running them on the same test data is not independent confirmation; subsequent work should evaluate grouped CV, independent temporal cohorts, MLflow registration and selection under a predefined protocol.
