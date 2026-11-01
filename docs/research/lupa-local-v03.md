# LUPA v0.3 — anonymized synthetic error inspection

New MAPA jobs calculate and persist diagnostics on the held-out student groups for each N1/N2/N3 protocol. Output reports the 3×3 confusion matrix, count of errors, and up to 12 anonymized incorrect cases per protocol. Each case contains only actual class, predicted class, predicted-class probability, and the top three feature probes.

The probes replace **one feature with its training-set median** and measure change in predicted-class probability. This is a noncausal sensitivity test, NOT SHAP, NOT a causal estimate, and NOT an intervention recommendation. Correlated features and unrealistic median substitutions limit interpretation.

No IDs, source rows, or raw scores per student are persisted. Historical MAPA runs remain available without this report. The synthetic generator does not validate effectiveness with actual students.
