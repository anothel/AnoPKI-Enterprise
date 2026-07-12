#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate-anocrypto-sdk-evidence.py"
SOURCE_COMMIT = "0123456789abcdef0123456789abcdef01234567"
ENTERPRISE_COMMIT = "89abcdef0123456789abcdef0123456789abcdef"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_anocrypto_sdk_evidence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def valid(artifact: Path) -> dict:
    repository = "anothel/AnoPKI-Enterprise"
    run_id = "123456789"
    return {
        "schema_version": 1,
        "status": "trusted_ci_complete",
        "repository": "anothel/AnoCrypto-C",
        "source_commit": SOURCE_COMMIT,
        "enterprise_repository": repository,
        "enterprise_commit": ENTERPRISE_COMMIT,
        "workflow_ref": f"{repository}/.github/workflows/anocrypto-sdk-integration.yml@refs/heads/main",
        "workflow_run_id": run_id,
        "workflow_run_attempt": 1,
        "package_version": "0.1.0",
        "artifact_name": artifact.name,
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "platform": "linux",
        "architecture": "x86_64",
        "compiler": "GCC 14",
        "cmake_version": "3.30",
        "build_type": "Release",
        "shared_library": True,
        "cmake_target": "AnoCryptoC::AnoCryptoC",
        "ci_run_url": f"https://github.com/{repository}/actions/runs/{run_id}",
        "license_included": True,
        "deterministic_archive": True,
        "sdk_tests_passed": True,
        "enterprise_integration_tests_passed": True,
        "no_openssl_dependency": True,
        "no_fallback_verified": True,
        "runtime": {
            "backend_id": "anocrypto-c",
            "dependency": "AnoCrypto-C",
            "runtime_version": "0.1.0-p1-23",
            "build_identity_abi": 1,
            "build_fingerprint": "fingerprint",
            "readiness": "ready",
            "capabilities": [],
        },
        "product_profile": "enterprise-anocrypto-c",
        "fallback_used": False,
        "pki_parity_status": "unsupported_pending",
        "kcmvp_status": "not_validated",
    }


def assert_fails(module, data, expected, artifact=None):
    try:
        module.validate(data, artifact)
    except SystemExit as exc:
        assert expected in str(exc), str(exc)
    else:
        raise AssertionError("validator unexpectedly passed")


def main() -> int:
    module = load_validator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        artifact = root / f"anocrypto-c-sdk-{SOURCE_COMMIT}-linux-x86_64.tar.gz"
        artifact.write_bytes(b"sdk")
        data = valid(artifact)
        module.validate(data, artifact)

        bad = dict(data)
        bad["source_commit"] = "0" * 40
        assert_fails(module, bad, "non-placeholder")

        bad = dict(data)
        bad["enterprise_commit"] = "short"
        assert_fails(module, bad, "40-character")

        bad = dict(data)
        bad["ci_run_url"] = "https://example.invalid/run/1"
        assert_fails(module, bad, "ci_run_url")

        bad = dict(data)
        bad["license_included"] = False
        assert_fails(module, bad, "license_included")

        bad = dict(data)
        bad["no_fallback_verified"] = False
        assert_fails(module, bad, "no_fallback_verified")

        bad = dict(data)
        bad["fallback_used"] = True
        assert_fails(module, bad, "fallback_used")

        bad = dict(data)
        bad["kcmvp_status"] = "validated"
        assert_fails(module, bad, "not_validated")

        bad = json.loads(json.dumps(data))
        bad["runtime"]["capabilities"] = ["certificate_issue"]
        assert_fails(module, bad, "must remain empty")

        artifact.write_bytes(b"changed")
        assert_fails(module, data, "SHA-256", artifact)

    print("AnoCrypto-C SDK evidence validator tests ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
