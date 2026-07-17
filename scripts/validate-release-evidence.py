#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Validate release evidence decisions and CI hooks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DOC_TEXT = [
    "# Release Evidence",
    "## Tool Decisions",
    "## Release Artifacts",
    "## Compatibility Matrix",
    "## SQLite Recovery Evidence Runner",
    "## CRL And OCSP Outage Evidence Runner",
    "## Audit Repair And Dead-Letter Replay Evidence Runner",
    "## Supported-Go Evidence Runner",
    "## Required Evidence Per Release Candidate",
    "verify-go-release.py",
    "anopki-enterprise-go-verification.tar.gz",
    "syft",
    "cosign",
    "govulncheck",
    "go vet ./...",
    "go test -race ./...",
    "staticcheck",
    "gosec",
    "Clang/libFuzzer",
    "anopki-backend-info.json",
    "anopki-release-metadata.json",
    "package-manifest.json",
]

REQUIRED_COMPATIBILITY_ROWS = [
    "OS",
    "Go",
    "OpenSSL",
    "SQLite",
    "PostgreSQL",
    "lego",
    "certbot",
]

REQUIRED_COMPATIBILITY_ROW_TEXT = {
    "OS": ["GitHub Actions Ubuntu", "Windows local verification"],
    "Go": ["go version", "Go 1.25.11"],
    "OpenSSL": ["CMake configure"],
    "SQLite": ["Go test", "SQLite"],
    "PostgreSQL": ["PostgreSQL integration", "DSN major version"],
    "lego": ["ACME smoke"],
    "certbot": ["Linux or elevated Windows", "WSL certbot evidence"],
}

REQUIRED_COMPATIBILITY_TEMPLATE_TEXT = [
    "## Release Candidate Compatibility Evidence Template",
    "| Area | Command or source | Result | Evidence pointer |",
    "| OS | GitHub Actions Ubuntu job plus any Windows local verification |",
    "| Go | `go version` from CI and release host |",
    "| OpenSSL | CMake configure output or package version |",
    "| SQLite | Local or CI Go test result covering SQLite store |",
    "| PostgreSQL | PostgreSQL integration job and DSN major version |",
    "| lego | ACME smoke command/output when ACME behavior changed |",
    "| certbot | WSL/Linux/elevated Windows smoke command/output when ACME behavior changed |",
]

REQUIRED_CI_TEXT = [
    "python scripts/test_validate_version_metadata.py",
    "python scripts/validate-version-metadata.py",
    "python scripts/test_generate_enterprise_release_metadata.py",
    "python scripts/test_verify_go_release.py",
    "python scripts/test_verify_recovery_drill.py",
    "python scripts/verify-recovery-drill.py",
    "anopki-recovery-verification",
    "python scripts/test_verify_status_outage_drill.py",
    "python scripts/verify-status-outage-drill.py",
    "anopki-status-outage-verification",
    "python scripts/test_verify_audit_replay_drill.py",
    "python scripts/verify-audit-replay-drill.py",
    "anopki-audit-replay-verification",
    "python scripts/test_validate_release_artifacts.py",
    "python scripts/test_generate_package_manifest.py",
    "python scripts/test_validate_package_boundary.py",
    "python scripts/validate-package-boundary.py",
    "python scripts/test_validate_release_evidence.py",
    "python scripts/validate-release-evidence.py",
    'go: ["1.25.12", "1.26.5"]',
    'go-version: "1.26.5"',
    'go-version: "1.25.12"',
    "python ../scripts/verify-go-release.py",
    "--profile baseline",
    "--profile analysis",
    "anopki-enterprise-go-baseline-${{ matrix.go }}",
    "anopki-enterprise-go-analysis-1.26.5",
    '--commit "${GITHUB_SHA}"',
    "ANOPKI_ENABLE_FUZZING=ON",
    "anopki_core_csr_fuzz",
    "anopki_core_ocsp_fuzz",
    "anopki_core_crl_fuzz",
    "-max_total_time=20",
    "timeout 30s",
    "postgres-integration:",
    'PGPASSWORD=anopki psql -h localhost -U anopki -d anopki_test -Atc "SHOW server_version;"',
    "pkg-config --modversion openssl",
    "acme-harness:",
    "test-run-certbot-smoke.ps1",
    "no live lego or certbot compatibility claim",
]

REQUIRED_GO_RUNNER_TEXT = [
    "MINIMUM_GO_VERSION = (1, 25, 11)",
    '"baseline"',
    '"analysis"',
    '"full"',
    'StepDefinition("go-test"',
    '(go_command, "test", "./...")',
    'StepDefinition("go-vet"',
    '(go_command, "vet", "./...")',
    'StepDefinition("go-race"',
    '(go_command, "test", "-race", "./...")',
    'STATICCHECK_VERSION = "2026.1"',
    'GOSEC_VERSION = "v2.25.0"',
    'GOVULNCHECK_VERSION = "v1.1.4"',
    "GOTOOLCHAIN",
    "go-verification.json",
    "go-verification.md",
    '"product": "AnoPKI Enterprise"',
    '"edition": "enterprise"',
    '"product_profile": "enterprise-openssl"',
    '"enterprise_commit"',
    '"community_baseline_commit"',
    '"commercial_release_authorized": False',
    '"anocrypto_sdk_status": "not_run"',
    '"pki_parity_status": "unsupported_pending"',
    '"kcmvp_status": "not_validated"',
]

REQUIRED_RECOVERY_RUNNER_TEXT = [
    "MIGRATION = Path",
    "schema_migrations",
    "certificate_issuance_attempts",
    "crl_publications",
    "webhook_deliveries",
    "private-key-exclusion",
    "recovery-verification.json",
    "recovery-verification.md",
    "resolve_commit",
    "SENSITIVE_FIXTURES",
]

REQUIRED_STATUS_OUTAGE_RUNNER_TEXT = [
    "MINIMUM_GO_VERSION = (1, 25, 11)",
    "community_status_outage_drill",
    "TestPublishCRLOutageRecoversWithoutPhantomPublication",
    "TestRespondOCSPOutageRecoversWithoutSuccessAudit",
    "TestPublishCRLOutageReturnsBadGatewayAndRecovers",
    "TestRespondOCSPOutageReturnsBadGatewayAndRecovers",
    "status-outage-verification.json",
    "status-outage-verification.md",
    "status-outage-test.log",
    "resolve_commit",
    "sensitive-evidence-exclusion",
]

REQUIRED_AUDIT_REPLAY_RUNNER_TEXT = [
    "MINIMUM_GO_VERSION = (1, 25, 11)",
    "community_audit_replay_drill",
    "TestRepairMissingIssuanceAuditEventsPreservesCurrentEvidenceAndIsIdempotent",
    "TestReplayDeadLetterOutboxMessagesPreservesHistoryAndCompletesAfterRecovery",
    "audit-replay-verification.json",
    "audit-replay-verification.md",
    "audit-replay-test.log",
    "dead-letter-attempt-history-preserved",
    "sensitive-evidence-exclusion",
]

REQUIRED_RELEASE_TEXT = [
    "workflow_dispatch:",
    "tags:",
    "contents: read",
    "contents: write",
    "id-token: write",
    'go-version: "1.25.12"',
    "python scripts/verify-go-release.py",
    "--profile full",
    "anopki-enterprise-go-verification.tar.gz",
    "python scripts/verify-recovery-drill.py",
    "anopki-recovery-verification.tar.gz",
    "python scripts/verify-status-outage-drill.py",
    "anopki-status-outage-verification.tar.gz",
    "python scripts/verify-audit-replay-drill.py",
    "anopki-audit-replay-verification.tar.gz",
    '--commit "${GITHUB_SHA}"',
    'VERSION="$(cat VERSION)"',
    "go build -ldflags",
    "cmake --build build-release --config Release",
    "anopki-service-v${VERSION}-linux-amd64.tar.gz",
    "anopki-core-v${VERSION}-linux-amd64.tar.gz",
    "./dist/anopki-core backend info > dist/anopki-backend-info.json",
    "python scripts/generate-enterprise-release-metadata.py",
    "python scripts/generate-package-manifest.py",
    "Validate package boundary",
    "Validate generated package manifest",
    "Require an authorized customer package manifest",
    "python scripts/validate-package-boundary.py",
    'echo "PACKAGE_CLASS=customer-release"',
    'echo "PACKAGE_CLASS=internal-validation"',
    '--package-class "$PACKAGE_CLASS"',
    "package-manifest.json",
    "--manifest dist/package-manifest.json",
    "anopki-release-metadata.json",
    "sha256sum dist/*.tar.gz dist/anopki-backend-info.json dist/anopki-release-metadata.json dist/package-manifest.json",
    "python scripts/validate-release-artifacts.py dist",
    "syft scan dir:dist",
    "cosign sign-blob",
    "actions/upload-artifact",
    "actions/download-artifact",
    "SIGNING-STATUS.txt",
    "Signing skipped: manual dry-run",
    "publish-tagged-release:",
    "if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')",
    "environment: release",
    "Require a signed annotated tag",
    "GH_TOKEN: ${{ github.token }}",
    "gh release create",
    "gh release upload",
]

EXPECTED_HOSTED_CI = {
    "enterprise_commit": "22f5ebde6bfe2e3b40f874bb52dd5957152e4f22",
    "community_baseline_commit": "71f0e898c32a7d6e00d0725eeab6ca150ccaa0af",
    "workflow_name": "CI",
    "run_id": "29579430288",
    "run_url": "https://github.com/anothel/AnoPKI-Enterprise/actions/runs/29579430288",
    "event": "push",
    "head_sha": "22f5ebde6bfe2e3b40f874bb52dd5957152e4f22",
    "started_at": "2026-07-17T12:12:35Z",
    "completed_at": "2026-07-17T12:12:41Z",
    "job_count": 17,
    "runner_assigned": False,
    "steps_executed": 0,
    "artifacts_created": 0,
    "job_logs_created": 0,
    "release_artifact_evidence": False,
    "classification": "REMOTE_DEFERRED/BLOCKED_EXTERNAL",
    "blocker": "github_actions_billing_or_spending_limit_runner_allocation_blocked",
    "local_validation": "passed",
    "remote_validation": "not_run",
}

EXPECTED_TRUSTED_SDK = {
    "workflow_present": True,
    "execution": "not_run",
    "status": "REMOTE_UNVERIFIED",
    "required_secret": "ANOCRYPTO_C_READ_TOKEN",
    "exact_sdk_commit_required": True,
    "capacity_blocked": True,
    "parity": "unsupported_pending",
    "production_ready": False,
    "kcmvp_status": "not_validated",
}


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def require_text(path: Path, required: list[str]) -> str:
    if not path.is_file():
        fail(f"missing required file: {path}")
    text = path.read_text(encoding="utf-8")
    missing = [value for value in required if value not in text]
    if missing:
        fail(f"{path} missing:\n" + "\n".join(missing))
    forbidden = [value for value in ("TBD", "TODO") if value in text]
    if forbidden:
        fail(f"{path} contains placeholder text: {', '.join(forbidden)}")
    return text


def markdown_section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start == -1:
        return ""
    rest = text[start + len(heading):]
    next_heading = rest.find("\n## ")
    if next_heading != -1:
        rest = rest[:next_heading]
    return rest


def check_compatibility_matrix(text: str) -> None:
    text = markdown_section(text, "## Compatibility Matrix")
    missing = [
        area
        for area in REQUIRED_COMPATIBILITY_ROWS
        if f"| {area} |" not in text
    ]
    if missing:
        fail("release evidence compatibility matrix missing:\n" + "\n".join(missing))
    drift = []
    for area, snippets in REQUIRED_COMPATIBILITY_ROW_TEXT.items():
        match = re.search(rf"^\|\s*{re.escape(area)}\s*\|(?P<body>.*)\|$", text, flags=re.MULTILINE)
        if not match:
            continue
        row = match.group("body")
        missing_snippets = [snippet for snippet in snippets if snippet not in row]
        if missing_snippets:
            drift.append(f"{area}: " + ", ".join(missing_snippets))
    if drift:
        fail("release evidence compatibility matrix row detail drift:\n" + "\n".join(drift))


def check_compatibility_evidence_template(text: str) -> None:
    missing = [value for value in REQUIRED_COMPATIBILITY_TEMPLATE_TEXT if value not in text]
    if missing:
        fail("release evidence compatibility template missing:\n" + "\n".join(missing))


def check_local_verification_evidence(root: Path, text: str) -> None:
    script = require_text(root / "scripts/verify-local.ps1", [])
    commands = re.findall(r'Display\s*=\s*"([^"]+)"', script)
    evidence_section = markdown_section(text, "## Required Evidence Per Release Candidate")
    normalized_text = evidence_section.replace("\\", "/")
    missing = [command for command in commands if command.replace("\\", "/") not in normalized_text]
    if missing:
        fail("release evidence missing local verification commands:\n" + "\n".join(missing))


def check_hosted_execution_evidence(root: Path) -> None:
    edition = json.loads((root / ".edition/edition.json").read_text(encoding="utf-8"))
    hosted = edition.get("hosted_ci")
    trusted = edition.get("trusted_anocrypto_sdk_lane")
    if not isinstance(hosted, dict) or not isinstance(trusted, dict):
        fail("missing structured hosted CI or trusted SDK evidence")

    if hosted.get("runner_assigned") is False and hosted.get("remote_validation") in {"passed", "success"}:
        fail("runner_assigned=false cannot record remote tests passed")
    if hosted.get("steps_executed") == 0 and hosted.get("classification") in {"CI_SUCCESS", "PASSED", "SUCCESS"}:
        fail("zero hosted CI steps cannot record CI success")
    if hosted.get("artifacts_created") == 0 and hosted.get("release_artifact_evidence") is not False:
        fail("zero hosted artifacts cannot claim release artifact evidence")
    if trusted.get("execution") == "not_run" and trusted.get("status") in {"completed", "COMPLETED", "passed", "success"}:
        fail("trusted SDK not_run cannot record completed SDK evidence")
    if trusted.get("kcmvp_status") == "validated" or edition.get("kcmvp_status") == "validated":
        fail("KCMVP validated claim requires certification evidence")
    if hosted.get("blocker") in {"code_failure", "test_failure"}:
        fail("billing blocker cannot be classified as a code failure")

    hosted_drift = [
        f"{key}: expected {value!r}, got {hosted.get(key)!r}"
        for key, value in EXPECTED_HOSTED_CI.items()
        if hosted.get(key) != value
    ]
    trusted_drift = [
        f"{key}: expected {value!r}, got {trusted.get(key)!r}"
        for key, value in EXPECTED_TRUSTED_SDK.items()
        if trusted.get(key) != value
    ]
    state_drift = [
        key
        for key in ("commercial_release_authorized", "production_ready", "fallback_enabled", "fallback_used")
        if edition.get(key) is not False
    ]
    if hosted_drift or trusted_drift or state_drift:
        fail(
            "hosted execution evidence drift:\n"
            + "\n".join(hosted_drift + trusted_drift + [f"{key}: expected false" for key in state_drift])
        )

    try:
        started = datetime.fromisoformat(hosted["started_at"].replace("Z", "+00:00"))
        completed = datetime.fromisoformat(hosted["completed_at"].replace("Z", "+00:00"))
    except (TypeError, ValueError):
        fail("hosted CI timestamps must be RFC3339")
    if completed < started:
        fail("hosted CI completed_at precedes started_at")

    evidence_doc = require_text(root / "docs/enterprise/private-alpha-evidence.md", [])
    required_doc_markers = list(EXPECTED_HOSTED_CI) + list(EXPECTED_TRUSTED_SDK)
    required_doc_markers += [str(value).lower() for value in EXPECTED_HOSTED_CI.values()]
    required_doc_markers += [str(value).lower() for value in EXPECTED_TRUSTED_SDK.values()]
    missing = [value for value in required_doc_markers if value not in evidence_doc.lower()]
    if missing:
        fail("private hosted evidence missing:\n" + "\n".join(sorted(set(missing))))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    doc = require_text(root / "docs/reference/release-evidence.md", REQUIRED_DOC_TEXT)
    check_compatibility_matrix(doc)
    check_compatibility_evidence_template(doc)
    check_local_verification_evidence(root, doc)
    check_hosted_execution_evidence(root)
    require_text(root / "scripts/verify-go-release.py", REQUIRED_GO_RUNNER_TEXT)
    require_text(root / "scripts/verify-recovery-drill.py", REQUIRED_RECOVERY_RUNNER_TEXT)
    require_text(root / "scripts/verify-status-outage-drill.py", REQUIRED_STATUS_OUTAGE_RUNNER_TEXT)
    require_text(root / "scripts/verify-audit-replay-drill.py", REQUIRED_AUDIT_REPLAY_RUNNER_TEXT)
    require_text(root / ".github/workflows/ci.yml", REQUIRED_CI_TEXT)
    require_text(root / ".github/workflows/release.yml", REQUIRED_RELEASE_TEXT)
    print("release evidence ok")


if __name__ == "__main__":
    main()
