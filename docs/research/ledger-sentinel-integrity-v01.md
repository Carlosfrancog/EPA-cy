# EPA LEDGER + SENTINEL — Integridade local v0.1

Rails `/integrity` now reads the 20 most recent completed MAPA runs and checks six persisted artifacts against their stored SHA-256 digest, schema, synthetic dataset classification, manifest digest, seed when available, and three N1/N2/N3 cutoffs. Historical missing artifacts are labelled `absent`, not `invalid`. Mismatched bytes or provenance are labelled `invalid`.

This is **read-only local consistency verification**, not an append-only authenticated ledger, trusted timestamp, external signature or proof of no data leakage. No automatic quarantine, artifact rewriting, model deployment or changes to historical records.
