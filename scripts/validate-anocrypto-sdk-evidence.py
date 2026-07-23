#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Validate trusted AnoCrypto-C SDK integration evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
POSITIVE_INTEGER = re.compile(r"^[1-9][0-9]*$")
REQUIRED_TOP = {
    "schema_version", "status", "repository", "source_commit",
    "enterprise_repository", "enterprise_commit", "workflow_ref",
    "workflow_run_id", "workflow_run_attempt", "package_version",
    "artifact_name", "artifact_sha256", "platform", "architecture", "compiler",
    "cmake_version", "build_type", "shared_library", "cmake_target", "ci_run_url",
    "license_included", "deterministic_archive",
    "sdk_tests_passed", "enterprise_integration_tests_passed",
    "no_openssl_dependency", "no_fallback_verified", "runtime", "product_profile",
    "fallback_used", "pki_parity_status", "kcmvp_status",
}
REQUIRED_RUNTIME = {
    "backend_id", "dependency", "runtime_version", "build_identity_abi",
    "build_fingerprint", "readiness", "capabilities",
}
OPERATION_CAPABILITIES = {
    "csr_inspect", "certificate_issue", "crl_generate", "crl_inspect",
    "ocsp_request_inspect", "ocsp_issuer_inspect", "ocsp_response_generate",
    "ocsp_responder_validate",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid evidence JSON: {exc}")
    if not isinstance(value, dict):
        fail("evidence root must be an object")
    return value


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require_commit(value: object, field: str, allow_example: bool) -> str:
    if not isinstance(value, str) or not HEX40.fullmatch(value):
        fail(f"{field} must be a 40-character lowercase SHA")
    if len(set(value)) == 1 and not allow_example:
        fail(f"{field} must be non-placeholder")
    return value


def validate(data: dict, artifact: Path | None = None, allow_example: bool = False) -> None:
    missing = sorted(REQUIRED_TOP - data.keys())
    if missing:
        fail("missing evidence fields: " + ", ".join(missing))
    if data["schema_version"] != 1:
        fail("unsupported evidence schema_version")
    if data["status"] == "example_only" and not allow_example:
        fail("example evidence is not trusted evidence")
    if data["status"] not in ({"trusted_ci_complete", "example_only"} if allow_example else {"trusted_ci_complete"}):
        fail("invalid evidence status")
    if data["repository"] != "anothel/AnoCrypto-C":
        fail("unexpected AnoCrypto-C repository")

    source_commit = require_commit(data["source_commit"], "source_commit", allow_example)
    require_commit(data["enterprise_commit"], "enterprise_commit", allow_example)
    enterprise_repository = data["enterprise_repository"]
    if not isinstance(enterprise_repository, str) or not REPOSITORY.fullmatch(enterprise_repository):
        fail("enterprise_repository must be owner/name")
    if not isinstance(data["workflow_ref"], str) or not data["workflow_ref"].strip():
        fail("workflow_ref must be non-empty")
    run_id = data["workflow_run_id"]
    if not isinstance(run_id, str) or not POSITIVE_INTEGER.fullmatch(run_id):
        fail("workflow_run_id must be a positive integer string")
    if not isinstance(data["workflow_run_attempt"], int) or data["workflow_run_attempt"] < 1:
        fail("workflow_run_attempt must be a positive integer")

    if data["package_version"] != "0.1.0":
        fail("unsupported AnoCrypto-C package version")
    digest = data["artifact_sha256"]
    if not isinstance(digest, str) or not HEX64.fullmatch(digest) or (len(set(digest)) == 1 and not allow_example):
        fail("artifact_sha256 must be a non-placeholder lowercase SHA-256")
    artifact_name = data["artifact_name"]
    if not isinstance(artifact_name, str) or not artifact_name.strip():
        fail("artifact_name must be non-empty")
    if source_commit not in artifact_name and not allow_example:
        fail("artifact_name must include the pinned AnoCrypto-C source commit")
    for field in ("platform", "architecture", "compiler", "cmake_version"):
        if not isinstance(data[field], str) or not data[field].strip():
            fail(f"{field} must be non-empty")
    expected_url = f"https://github.com/{enterprise_repository}/actions/runs/{run_id}"
    if data["ci_run_url"] != expected_url and not allow_example:
        fail("ci_run_url must match enterprise_repository and workflow_run_id")
    if not isinstance(data["ci_run_url"], str) or not data["ci_run_url"].strip():
        fail("ci_run_url must be non-empty")
    if data["build_type"] != "Release":
        fail("trusted SDK evidence must use a Release build")
    if data["shared_library"] is not True:
        fail("trusted SDK evidence currently requires a shared-library SDK")
    if data["cmake_target"] != "AnoCryptoC::AnoCryptoC":
        fail("unexpected CMake imported target")
    for field in (
        "license_included", "deterministic_archive",
    "sdk_tests_passed", "enterprise_integration_tests_passed",
        "no_openssl_dependency", "no_fallback_verified",
    ):
        if data[field] is not True:
            fail(f"{field} must be true")
    if data["product_profile"] != "enterprise-anocrypto-c":
        fail("unexpected product profile")
    if data["fallback_used"] is not False:
        fail("fallback_used must be false")
    if data["pki_parity_status"] != "operation_parity_verified":
        fail("PKI parity must record operation_parity_verified")
    if data["kcmvp_status"] != "not_validated":
        fail("KCMVP status must remain not_validated without exact evidence")

    runtime = data["runtime"]
    if not isinstance(runtime, dict):
        fail("runtime must be an object")
    missing = sorted(REQUIRED_RUNTIME - runtime.keys())
    if missing:
        fail("missing runtime fields: " + ", ".join(missing))
    if runtime["backend_id"] != "anocrypto-c" or runtime["dependency"] != "AnoCrypto-C":
        fail("unexpected runtime backend identity")
    if runtime["build_identity_abi"] != 1:
        fail("unsupported AnoCrypto-C build identity ABI")
    if runtime["readiness"] != "ready":
        fail("AnoCrypto-C module was not ready")
    if not isinstance(runtime["runtime_version"], str) or not runtime["runtime_version"]:
        fail("runtime version missing")
    if not isinstance(runtime["build_fingerprint"], str) or not runtime["build_fingerprint"]:
        fail("build fingerprint missing")
    if not isinstance(runtime["capabilities"], list):
        fail("runtime capabilities must be an array")
    if len(runtime["capabilities"]) != len(OPERATION_CAPABILITIES) or set(runtime["capabilities"]) != OPERATION_CAPABILITIES:
        fail("runtime capabilities must contain the exact verified operation set")

    if artifact is not None:
        if not artifact.is_file():
            fail(f"SDK artifact not found: {artifact}")
        if artifact.name != artifact_name:
            fail("artifact name does not match evidence")
        if sha256(artifact) != digest:
            fail("artifact SHA-256 does not match evidence")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--allow-example", action="store_true")
    args = parser.parse_args()
    validate(load(args.evidence), args.artifact, args.allow_example)
    print("AnoCrypto-C SDK evidence ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
