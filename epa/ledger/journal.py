"""Deterministic hash-linked audit journal.

Security boundary: this is a tamper-evidence *prototype*, not a trusted immutable
ledger. An attacker able to rewrite the entire file can recompute the chain.
Use signed, externally anchored checkpoints and restricted storage in later phases.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

SCHEMA = "epa.ledger.event.v1"
ZERO_HASH = "0" * 64


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _event_hash(event: dict[str, Any]) -> str:
    return digest_bytes(canonical_json({k: v for k, v in event.items() if k != "event_hash"}))


def read_verified(path: Path) -> list[dict[str, Any]]:
    """Fail closed on malformed, truncated or inconsistent chain entries.

    This cannot detect deletion of a valid trailing suffix without an external
    trusted checkpoint. Do not treat success as authenticity.
    """
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open("rb") as stream:
        for number, raw in enumerate(stream, 1):
            if not raw.endswith(b"\n"):
                raise ValueError(f"truncated event at line {number}")
            event = json.loads(raw)
            if not isinstance(event, dict):
                raise ValueError(f"event {number}: expected object")
            if event.get("schema_version") != SCHEMA or event.get("sequence") != number:
                raise ValueError(f"event {number}: schema or sequence mismatch")
            prior = ZERO_HASH if number == 1 else events[-1]["event_hash"]
            if event.get("previous_hash") != prior:
                raise ValueError(f"event {number}: broken previous hash")
            if event.get("event_hash") != _event_hash(event):
                raise ValueError(f"event {number}: digest mismatch")
            events.append(event)
    return events


def append_event(path: Path, *, event_type: str, subject_digest: str, payload: dict[str, Any], recorded_at: str) -> dict[str, Any]:
    """Append a local event after verifying existing history.

    Single-process prototype only: caller must guarantee an exclusive writer.
    Network filesystem and concurrent writers are unsupported.
    """
    if not event_type or not isinstance(payload, dict):
        raise ValueError("invalid event")
    if len(subject_digest) != 64 or any(c not in "0123456789abcdef" for c in subject_digest):
        raise ValueError("subject_digest must be lowercase SHA-256 hex")
    from datetime import datetime
    date = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    if date.tzinfo is None:
        raise ValueError("recorded_at requires timezone")
    if path.is_symlink():
        raise ValueError("journal path must not be symlink")
    if path.exists():
        if not path.is_file():
            raise ValueError("journal path must be a file")
        events = read_verified(path)
    else:
        events = []
        path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "schema_version": SCHEMA,
        "sequence": len(events) + 1,
        "event_type": event_type,
        "subject_digest": subject_digest,
        "recorded_at": recorded_at,
        "payload": payload,
        "previous_hash": events[-1]["event_hash"] if events else ZERO_HASH,
    }
    entry["event_hash"] = _event_hash(entry)
    line = canonical_json(entry) + b"\n"
    # O_APPEND and fsync are durability aids, not an immutable storage guarantee.
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "ab", closefd=True) as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        raise
    return entry


def verify_subject(path: Path, expected_digest: str) -> bool:
    """Verify a local file matches an independently supplied digest."""
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest() == expected_digest
