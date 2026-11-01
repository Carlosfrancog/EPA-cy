# LUPA v0.1 — Explainability

LUPA now computes actual **held-out permutation importance** for each N1/N2/N3 protocol. The model is a Random Forest fitted on the same group-by-student split and seed as MAPA baseline; preprocessing and feature allowlists come from MAPA Core.

```bash
python -m epa.core_engine.lupa --dataset data/mapa-demo-v2 \
  --output data/lupa-report.json --seed 20261029 --repeats 2
```

The output records baseline F1 macro and the average drop in this metric after shuffling each feature in the test split, including standard deviation over permutations, class counts, student counts and the verified original dataset digest. Rails generates and verifies LUPA JSON at the end of each *new* MAPA job, persists SHA256 and renders all three protocols. Historical runs remain readable.

**Interpretation:** permutation importance is association / model sensitivity, **not causal impact** or evidence of educational interventions. Correlated predictors can conceal or redistribute importance; negative importance is valid. No per-student explanations, decision paths, 3D animation, or empirical validation is claimed in v0.1.
