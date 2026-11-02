# LUPA Observatory 3D v0.1

Interactive HTML canvas perspective projection of **33 measured values** from one verified LUPA Random Forest report: 11 allowlisted predictors across N1, N2 and N3.

Coordinates are X=feature index, Y=signed macro-F1 permutation drop (preserves negative values), Z=prediction cutoff. Rotation, pan-like pointer movement, zoom and reset affect the camera only. A complete accessible numeric table and the existing 2D view remain available. No browser-side ML inference, WebGL package, external requests or fabricated embeddings.

The 3D axes are orthogonal visualization choices, **not** statistical distances or causal links. The three protocols use distinct training cutoffs; do not interpret inter-protocol displacement as student trajectory or causal effect. Displays only if all 3 verified protocols belong to the same experiment, manifest SHA and seed. Existing historical runs without complete LUPA output retain the 2D interface.
