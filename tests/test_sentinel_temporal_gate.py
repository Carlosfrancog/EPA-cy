import copy

from epa.atlas.catalog import load_catalog
from epa.core_engine.student_timeline import build_snapshots
from epa.genesis.v2 import build_dataset
from epa.sentinel.temporal_gate import Verdict, audit_cutoff

from pathlib import Path
CATALOG = Path(__file__).resolve().parents[1] / "examples" / "atlas.demo.json"
HASH = "a" * 64


def fixture_data():
    return build_dataset(load_catalog(CATALOG), students=8, seed=42, start_year=2020)


def test_clean_n1_n2_n3_are_permitted():
    data = fixture_data()
    for cutoff in (1, 2, 3):
        result = audit_cutoff(data, build_snapshots(data, cutoff=cutoff),
                              cutoff=cutoff, manifest_sha256=HASH)
        assert result.verdict is Verdict.PERMIT, result.reasons
        assert result.approved_manifest_sha256 == HASH


def test_n1_rejects_future_derived_grade():
    data = fixture_data()
    snaps = build_snapshots(data, cutoff=1)
    snaps[0]["current"]["mean_grade"] = 0.0  # not justified by N1 source
    verdict = audit_cutoff(data, snaps, cutoff=1, manifest_sha256=HASH)
    assert verdict.verdict is Verdict.DENY
    assert verdict.approved_manifest_sha256 is None
    assert verdict.manifest_sha256 == HASH  # immutable evidence is not modified


def test_n2_rejects_direct_target_as_feature():
    data = fixture_data()
    snaps = build_snapshots(data, cutoff=2)
    snaps[0]["current"]["final_outcome"] = "approved"
    assert audit_cutoff(data, snaps, cutoff=2, manifest_sha256=HASH).verdict is Verdict.DENY


def test_changing_future_grade_does_not_change_earlier_features():
    data = fixture_data()
    before = build_snapshots(data, cutoff=1)
    modified = copy.deepcopy(data)
    for row in modified["period_records"]:
        if row["academic_year"] == 2026 and row["term"] > 1:
            row["assessment_grade"] = 0.0
    after = build_snapshots(modified, cutoff=1)
    assert [(r["current"], r["prior_same_subject"]) for r in before] == [
        (r["current"], r["prior_same_subject"]) for r in after
    ]
