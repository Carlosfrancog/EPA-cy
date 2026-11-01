# EPA Student Timeline — point-in-time feature snapshots v0

Scientific stage: **feature preparation / SYNTHETIC ONLY**, not a trained MAPA model.

## Data flow

`GENESIS v2 (Parquet + SHA-256 manifest)` → `Student Timeline` → `N1/N2/N3 research snapshots` → future MAPA training.

```bash
python -m epa.genesis.v2 --output data/demo-v2 --students 100
python -m epa.core_engine.student_timeline --dataset data/demo-v2 --cutoff 1 --output data/snapshots-early.json
python -m epa.core_engine.student_timeline --dataset data/demo-v2 --cutoff 2 --output data/snapshots-trajectory.json
python -m epa.core_engine.student_timeline --dataset data/demo-v2 --cutoff 3 --output data/snapshots-consolidated.json
pytest -q tests/test_student_timeline.py
```

`--output` refuses overwrites; choose a new path for a new experiment.

## Contract

Each snapshot refers to **one student/enrollment/year/subject**. The `current` feature group contains only observations from that year's terms **up to the selected cutoff**. `prior_same_subject` summarizes the same subject from previous years, including all their terms, without leaking the current year's future data. All attendance rates use their session denominators; justified/unjustified absences reconcile. `student_profile` retrieves a cutoff-filtered timeline for LUPA and related research.

The `target_final_subject_outcome` field is **label-only**, separate from features, with explicitly illustrative synthetic thresholds: approved ≥ 6; recovery ≥ 4 and < 6; failed < 4. This is not a verified school policy and is not an estimate of dropout.

All five required GENESIS v2 artifacts must have manifest-declared exact paths, hashes and row counts. `read_verified_v2` then checks dataset relationships/attendance invariants. Output records the source manifest SHA-256.

## Strict limitations

- The final-outcome label necessarily uses future term grades **only to define supervised ground truth**; it must never be read into X. Future years and current terms beyond cutoff are excluded from all feature aggregates.
- The snapshots are preparatory; **no classifier training, validation, MLflow, Rails UI or model selection is added in this PR**.
- Future work must ensure preprocessing is fitted on training folds only; split by student; add held-out temporal validation and class-sensitive metrics.
- Data come from the simplified synthetic simulator; no claim of predictive effectiveness on actual school populations.
- The v1 experimental Core/Rails pipeline remains separate and unchanged.
