import hashlib
from pathlib import Path

from epa.sentinel.policy import Verdict, verify_manifest


def manifest(tmp_path: Path, content=b"mock-data"):
    artifact = tmp_path / "data.bin"
    artifact.write_bytes(content)
    return {
        "schema_version": "epa.manifest.v1",
        "classification": "SYNTHETIC",
        "artifact_path": "data.bin",
        "digest_algorithm": "sha256",
        "digest": hashlib.sha256(content).hexdigest(),
        "prediction_at": "2026-03-01T00:00:00Z",
        "dependencies": [
            {"feature": "n1", "available_at": "2026-02-10T00:00:00Z"},
            {"feature": "attendance_n1", "available_at": "2026-02-11T00:00:00Z"},
        ],
    }


def test_valid_declared_evidence_is_permitted(tmp_path):
    assert verify_manifest(manifest(tmp_path), tmp_path).verdict is Verdict.PERMIT


def test_tampered_artifact_denied(tmp_path):
    m = manifest(tmp_path)
    (tmp_path / "data.bin").write_bytes(b"tampered")
    assert verify_manifest(m, tmp_path).verdict is Verdict.DENY


def test_future_feature_denied(tmp_path):
    m = manifest(tmp_path)
    m["dependencies"].append({"feature": "n4", "available_at": "2026-12-01T00:00:00Z"})
    assert verify_manifest(m, tmp_path).verdict is Verdict.DENY


def test_missing_dependency_evidence_unknown(tmp_path):
    m = manifest(tmp_path)
    m["dependencies"] = []
    assert verify_manifest(m, tmp_path).verdict is Verdict.UNKNOWN


def test_path_escape_unknown(tmp_path):
    m = manifest(tmp_path)
    m["artifact_path"] = "../outside.bin"
    assert verify_manifest(m, tmp_path).verdict is Verdict.UNKNOWN


def test_real_personal_data_not_authorized_in_mvp(tmp_path):
    m = manifest(tmp_path)
    m["classification"] = "PERSONAL"
    assert verify_manifest(m, tmp_path).verdict is Verdict.DENY


def test_absent_timezone_is_unknown(tmp_path):
    m = manifest(tmp_path)
    m["prediction_at"] = "2026-03-01T00:00:00"
    assert verify_manifest(m, tmp_path).verdict is Verdict.UNKNOWN


def test_permit_is_not_publication_authorization(tmp_path):
    assert verify_manifest(manifest(tmp_path), tmp_path).publishable is False
