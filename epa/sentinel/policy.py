"""Minimal fail-closed research manifest checks.

This module tests *declared* dependencies; it does not prove full feature lineage.
Untrusted manifests require authenticated provenance before being used for approval.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class Verdict(str, Enum):
    PERMIT = "PERMIT"
    DENY = "DENY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    reasons: tuple[str, ...]

    @property
    def publishable(self) -> bool:
        # No publication gate has been implemented. This is intentionally false.
        return False


def _instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must contain a timezone")
    return parsed.astimezone(timezone.utc)


def _safe_file(root: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("artifact path must be a non-traversing relative path")
    base = root.resolve(strict=True)
    target = (base / relative).resolve(strict=True)
    if not target.is_relative_to(base) or not target.is_file():
        raise ValueError("artifact path resolves outside root or is not a file")
    return target


def _digest_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def verify_manifest(manifest: dict[str, Any], root: Path) -> Decision:
    reasons: list[str] = []
    try:
        if manifest.get("schema_version") != "epa.manifest.v1":
            return Decision(Verdict.UNKNOWN, ("Unsupported or absent schema_version",))
        if manifest.get("classification") not in {"SYNTHETIC", "PUBLIC"}:
            return Decision(Verdict.DENY, ("Only synthetic/public files supported by MVP",))
        if manifest.get("digest_algorithm") != "sha256":
            return Decision(Verdict.UNKNOWN, ("Expected SHA-256 algorithm",))
        expected = manifest.get("digest")
        if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            return Decision(Verdict.UNKNOWN, ("Missing or invalid digest",))
        file = _safe_file(root, manifest["artifact_path"])
        actual = _digest_file(file)
        if actual != expected:
            reasons.append("Artifact digest mismatch")
        cutoff = _instant(manifest["prediction_at"])
        dependencies = manifest["dependencies"]
        if not isinstance(dependencies, list) or not dependencies:
            return Decision(Verdict.UNKNOWN, ("No declared feature dependencies",))
        for dep in dependencies:
            if not isinstance(dep, dict) or not dep.get("feature") or not dep.get("available_at"):
                return Decision(Verdict.UNKNOWN, ("Feature dependency metadata incomplete",))
            available = _instant(dep["available_at"])
            if available > cutoff:
                reasons.append(f"Future information used: {dep['feature']}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return Decision(Verdict.UNKNOWN, (f"Verification evidence incomplete: {type(exc).__name__}",))
    if reasons:
        return Decision(Verdict.DENY, tuple(reasons))
    return Decision(Verdict.PERMIT, ("Declared file digest and temporal dependencies verified",))


def load_and_verify(manifest_path: Path, root: Path) -> Decision:
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return Decision(Verdict.UNKNOWN, ("Manifest is not an object",))
        return verify_manifest(data, root)
    except (OSError, ValueError, UnicodeError) as exc:
        return Decision(Verdict.UNKNOWN, (f"Could not read manifest: {type(exc).__name__}",))
