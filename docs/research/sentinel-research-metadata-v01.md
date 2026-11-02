# SENTINEL — Scientific research metadata audit v0.1

The read-only `/integrity` panel now checks the declarations in the latest
20 completed MAPA research reports: matching schema, synthetic classification,
manifest SHA and seed; N1/N2/N3 order; declared grouped-fold strategy,
bounded split count, valid group sizes and class support, and temporal
validation status.

A `not_identifiable` future cohort is correctly reported as scientific
limitation **rather than integrity failure**. This is a structural metadata
audit, **not** a verification of actual student IDs, a proof of no leakage,
a population validation or a security attestation. The underlying Python
research engine must independently verify disjoint groups at runtime.

The existing LEDGER SHA audit remains independent and unchanged.
