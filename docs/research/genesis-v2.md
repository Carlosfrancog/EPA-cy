# EPA GENESIS v2 — synthetic student longitudinal history

Status: **first working increment; SYNTHETIC ONLY**. Related to issue #10.

## Generate

Install research dependencies, then:

```bash
python -m epa.genesis.v2 --catalog examples/atlas.demo.json \
  --output data/demo-v2 --students 100 --seed 20261029 --start-year 2020
pytest -q tests/test_genesis_v2.py
```

**Never overwrite a dataset output folder.** A different seed or scenario requires a new directory.

## Entity contract

- `students.parquet`: immutable synthetic student IDs.
- `classes.parquet`: yearly school/class/grade identities.
- `enrollments.parquet`: one student membership in a class per year.
- `subject_offerings.parquet`: curriculum subjects available in a given class.
- `period_records.parquet`: one record per enrollment, subject and term (1–4); term grade, scheduled/present sessions, excused/unexcused absences and derived attendance rate.
- `manifest.json`: v2 schema, catalog digest, per-file SHA-256, seed and row counts.

The same student ID is maintained over seven synthetic grade levels; subject IDs are inherited from ATLAS. Every offered subject in every enrollment has four assessment and attendance records. Validations reconcile sessions and absences and reject missing term records.

## Current constraints

- Explicit catalog is a **synthetic demonstration**, not verified official BNCC mapping.
- Demo progression is deterministic: every student advances one grade per year; no repetition, transfers, dropouts or skipped years. These are **future scenarios**, not fabricated as implemented.
- Two or more schools and classes are simulated, with class assignment changing by year.
- Attendance is aggregated by subject/term; **no individual dated absence events** yet. Consecutive missed days cannot be inferred.
- Demographic/pedagogical validity is not claimed; generator produces simplified synthetic signals and is unsuitable for empirical model performance claims.
- v1 remains the Rails Core Engine input. **Do not feed v2 Parquet to the v1 experimental CLI.**
- v2 MVP builds rows in RAM and is limited to 2,000 students; scalable partitioned writers will be introduced after contract tests.
- No training or MAPA classifier is added by this increment. Next: time-cutoff snapshots, 3-class outcome definition and leakage test suite.

## Acceptance

Run `pytest -q`. Validate stable student trajectories, full subject coverage, N1–N4, attendance consistency, digest and immutable output refusal. See `tests/test_genesis_v2.py`.
