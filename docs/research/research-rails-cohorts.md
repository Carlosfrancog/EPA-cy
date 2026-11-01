# EPA Research Protocol — Rails + Independent Cohorts

This increment connects the already-approved MAPA Research Protocol v0.2
to local MAPA training jobs. A new job generates `research.json` after
the baseline JSON is verified, validates the report contract and source
SHA-256, then persists the report and digest with the operational run.
Old runs remain readable without research data.

The default local Rails dataset is GENESIS v2 longitudinal; therefore the
extra panel **correctly identifies temporal holdout as not identifiable**.
To exercise independent out-of-time research in an isolated CLI workflow:

```bash
python -m epa.genesis.cohorts --output data/cohorts-demo \
  --students-per-cohort 40 --cohort-years 3
python -m epa.core_engine.mapa_research --dataset data/cohorts-demo \
  --output data/cohort-research.json --folds 3
```

Independent cohorts are three different entering groups, all **same
grade and curriculum**, observed in different calendar years. This avoids
student overlap; it does not model longitudinal progression for any
individual student. The temporal split uses the latest cohort as test.
Both distributions and labels still derive from a synthetic generator;
results must NOT be represented as external educational validation.

Potential limitation: the research report can be larger than the default
baseline JSON; maximum permitted size is 900 KB. Job failures do not
publish an incomplete report to Rails. No MLflow logging for the research
cross-validation metrics yet. Full LUPA / model registry remain future work.
