import hashlib
import json

import pytest

from epa.ledger.journal import append_event, canonical_json, read_verified, verify_subject


def _digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _add(path, t="RUN_CREATED"):
    return append_event(path, event_type=t, subject_digest=_digest("artifact"),
                        payload={"kind": "synthetic"}, recorded_at="2026-10-29T09:00:00Z")


def test_append_and_verify_chain(tmp_path):
    p = tmp_path / "audit.jsonl"
    first = _add(p)
    second = _add(p, "RUN_FINISHED")
    entries = read_verified(p)
    assert len(entries) == 2
    assert entries[0]["event_hash"] == first["event_hash"]
    assert entries[1]["previous_hash"] == first["event_hash"]
    assert second["sequence"] == 2


def test_payload_tampering_detected(tmp_path):
    p = tmp_path / "audit.jsonl"
    _add(p)
    p.write_bytes(p.read_bytes().replace(b"synthetic", b"modified!"))
    with pytest.raises(ValueError, match="digest mismatch"):
        read_verified(p)


def test_truncated_last_line_detected(tmp_path):
    p = tmp_path / "audit.jsonl"
    _add(p)
    p.write_bytes(p.read_bytes()[:-1])
    with pytest.raises(ValueError, match="truncated"):
        read_verified(p)


def test_deleted_first_line_detected_if_suffix_remains(tmp_path):
    p = tmp_path / "audit.jsonl"
    _add(p)
    _add(p)
    p.write_bytes(p.read_bytes().splitlines(keepends=True)[1])
    with pytest.raises(ValueError):
        read_verified(p)


def test_invalid_subject_digest_rejected(tmp_path):
    with pytest.raises(ValueError):
        append_event(tmp_path / "audit.jsonl", event_type="X", subject_digest="bad", payload={}, recorded_at="2026-10-29T09:00:00Z")


def test_untrusted_timestamp_rejected(tmp_path):
    with pytest.raises(ValueError, match="timezone"):
        append_event(tmp_path / "audit.jsonl", event_type="X", subject_digest=_digest("x"), payload={}, recorded_at="2026-10-29T09:00:00")


def test_subject_digest_check(tmp_path):
    p = tmp_path / "artifact"
    p.write_text("original")
    assert verify_subject(p, _digest("original"))
    p.write_text("changed")
    assert not verify_subject(p, _digest("original"))


def test_canonical_serialization_independent_of_key_order():
    assert canonical_json({"b": 2, "a": 1}) == canonical_json({"a": 1, "b": 2})


def test_missing_journal_is_empty_not_evidence(tmp_path):
    assert read_verified(tmp_path / "missing.jsonl") == []
