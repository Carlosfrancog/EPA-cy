# Entrega A — Scientific Validation for MLP and optional XGBoost

Independent research report with **GroupKFold by student** and out-of-time
holdout on nonoverlapping synthetic entry cohorts. Uses the exact MAPA
feature allowlist, with train-only preprocessing.

```bash
python -m epa.core_engine.mapa_research_extended \
  --dataset data/cohorts-demo --output data/extended-cv.json --folds 3

pip install -e '.[research,boosting]'
python -m epa.core_engine.mapa_research_extended \
  --dataset data/cohorts-demo --output data/extended-cv-xgb.json --xgboost
```

When the three-class XGBoost training prerequisite fails the result is
explicitly skipped, rather than publishing fictitious scores. Intervals in
the temporal holdout are synthetic **cluster-bootstrap** intervals
conditional on the fitted model. They do not constitute true-school
generalization or a model selection mandate.

This independent report leaves the original nine MLflow baselines,
original Research v2 and Rails reporting contracts unchanged. Rails
integration and evidence gates are the next subincrement of Entrega A.
