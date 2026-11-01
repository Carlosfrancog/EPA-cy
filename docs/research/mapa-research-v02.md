# MAPA Research Protocol v0.2

Execução reproduzível:

```bash
python -m epa.genesis.v2 --output data/research-demo --students 80
python -m epa.core_engine.mapa_research --dataset data/research-demo \
  --output data/research-report.json --folds 3
pytest -q tests/test_mapa_research.py
```

## Method
- 3 grouped folds (configurable 2–10) over unique **students**. Same student's subject/year observations never appear on both sides within a fold.
- Pipelines fit imputation and scaling on training fold only.
- Models: majority, logistic regression and RF; per-class counts, recall, confusion matrix, F1 macro and accuracy per fold.
- Fold score ranges, SD and mean are descriptive **fold dispersion**, not 95% confidence intervals. Honest population CIs require an appropriate sampling design and independent outcomes.
- Strict later-year independent-cohort test checks whether the later year has students not present in earlier training years. The current GENESIS v2 repeats the SAME student across years; temporal validation is marked `not_identifiable`, NOT given misleading scores.
- This increment is CLI-first: a separate research report does not modify legacy v1 or `MAPA` runtime report contracts. UI/MLflow extension follows after protocol acceptance.

Do not claim real-world generalization from simulated records. Generation of multiple independent cohorts is a prerequisite for true out-of-time testing.
