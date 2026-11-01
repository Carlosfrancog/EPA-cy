# MAPA Research — cluster-bootstrap intervals

For strict out-of-time evaluations on independent synthetic entry cohorts,
the model now attaches a **95% percentile bootstrap interval for macro F1** to
each fitted classifier. The resampling unit is the **student**, with all
observations from that student resampled as a block. Uses 300 fixed-seed
resamples; reports the number of unique clusters, interval endpoints and
point estimate. A minimum of 8 test student clusters is required.

This interval describes uncertainty caused by sampling a synthetic **held-out
cohort conditional on one fitted model**. It does not account for retraining
variance or domain shift and does not constitute real-school validation. No
interval is reported if longitudinal students overlap both temporal partitions.
The existing GroupKFold fold distribution remains distinct from confidence
intervals and is still labelled accordingly.

To exercise:

```bash
python -m epa.genesis.cohorts --output data/cohorts-demo --students-per-cohort 40
python -m epa.core_engine.mapa_research --dataset data/cohorts-demo \
  --output data/ci-demo.json --folds 3
```

The Rails report renders intervals **only if** temporal validation is
`evaluated`. Default longitudinal demo correctly remains `not_identifiable`.
