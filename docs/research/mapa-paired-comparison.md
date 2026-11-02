# Entrega A — Descriptive paired comparisons

The MAPA run detail displays per-fold paired macro-F1 differences against
Majority for up to five algorithms. Baseline and extended reports must match
the synthetic manifest digest and seed. Comparisons require matching
GroupKFold strategy, fold number, student counts and true class support.

The table reports mean/min/max paired differences and wins/ties/losses.
No per-fold test-student identifiers are exposed.

**Important:** GroupKFold partitions can contain repeated observations
from the same student; differences between folds are not independent samples.
These descriptive comparisons are *not* hypothesis tests, confidence intervals
or evidence of superiority. Historical runs without both protocols remain
accessible without a comparison. No automated model champion selection.
