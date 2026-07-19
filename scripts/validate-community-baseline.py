#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Verify exact Community blobs and explicit Enterprise mixed boundaries."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_COMMIT = "96297b14d2f681b75861032d9871a41d6e689c78"
PREVIOUS_BASELINE_COMMIT = "ae3ddee72dd05f274b9bbae1b514cdc4c4de03f5"

COMMUNITY_ONLY_FILES = {
    "docs-pack/README.md",
    "docs-pack/anopki-community-docpack.zip",
    "docs/edition/community-edition.md",
    "scripts/generate-release-metadata.py",
    "scripts/test_generate_release_metadata.py",
}

ENTERPRISE_OWNED_TARGET_FILES = {
    ".edition/edition.json",
    "docs/edition/edition-boundary.md",
    "EDITION.md",
    "LICENSE",
}

MIXED_REQUIRED_TEXT = {
    ".github/workflows/ci.yml": (
        "python scripts/test_validate_key_provider_boundary.py",
        "python scripts/validate-key-provider-boundary.py",
        "python scripts/test_generate_enterprise_release_metadata.py",
        "python scripts/test_verify_go_release.py",
        "anopki-enterprise-go-baseline-${{ matrix.go }}",
        "anopki-enterprise-go-analysis-1.26.5",
        "ANOPKI_PRODUCT_PROFILE=enterprise-openssl",
        "ANOPKI_PRODUCT_PROFILE=enterprise-anocrypto-c",
        "validate-enterprise-release.py --expect-blocked",
        "python scripts/verify-recovery-drill.py",
        "anopki-recovery-verification",
        "python scripts/verify-status-outage-drill.py",
        "anopki-status-outage-verification",
        "python scripts/verify-audit-replay-drill.py",
        "anopki-audit-replay-verification",
        "python scripts/verify-audit-integrity-drill.py",
        "anopki-audit-integrity-verification",
        "python scripts/verify-issuer-rollover-drill.py",
        "anopki-issuer-rollover-verification",
        "python scripts/verify-multi-node-reliability.py",
        "anopki-multi-node-verification",
        "python scripts/verify-postgres-recovery-drill.py",
        "anopki-postgres-recovery-verification",
    ),
    ".github/workflows/release.yml": (
        "validate-enterprise-release.py",
        "ANOPKI_PRODUCT_PROFILE=enterprise-openssl",
        "generate-enterprise-release-metadata.py",
        "verify-go-release.py",
        "anopki-enterprise-go-verification.tar.gz",
        "anopki-backend-info.json",
        "anopki-release-metadata.json",
        "anopki-recovery-verification.tar.gz",
        "anopki-status-outage-verification.tar.gz",
        "anopki-audit-replay-verification.tar.gz",
        "anopki-audit-integrity-verification.tar.gz",
        "anopki-issuer-rollover-verification.tar.gz",
        "anopki-multi-node-verification.tar.gz",
        "anopki-postgres-recovery-verification.tar.gz",
    ),
    "CHANGELOG.md": (
        "FileKeyProvider",
        "ECDSA P-256",
        "no fallback",
        "audit-repair",
        "CRL/OCSP outage",
        "SQLite backup/restore",
        "policy-decision",
        "Enterprise Go release verification runner",
        "tamper-evident `sha256-v1` audit chain",
        "PostgreSQL backup/restore verification",
    ),
    "CMakeLists.txt": (
        'set(ANOPKI_PRODUCT_PROFILE "enterprise-openssl"',
        "enterprise-anocrypto-c",
        "find_package(AnoCryptoC 0.1.0 EXACT CONFIG REQUIRED)",
        "AnoCryptoC::AnoCryptoC",
        "src/backends/openssl/key_providers/file_key_provider.cpp",
        "src/backends/openssl/key_providers/provider_resolver.cpp",
        "src/backends/openssl/openssl_backend_config.hpp.in",
        "anopki_file_key_provider_test",
        "anopki_software_token_key_provider_test",
        "anopki.key_provider_boundary",
    ),
    "README.md": (
        "enterprise-openssl",
        "enterprise-anocrypto-c",
        "test_generate_enterprise_release_metadata.py",
        "test_verify_go_release.py",
        "enterprise-verify-local",
        "automatic fallback is disabled",
        "verify-recovery-drill.py",
        "verify-status-outage-drill.py",
        "verify-audit-replay-drill.py",
        "verify-audit-integrity-drill.py",
        "verify-issuer-rollover-drill.py",
        "verify-multi-node-reliability.py",
        "verify-postgres-recovery-drill.py",
    ),
    "docs/INDEX.md": ("Enterprise/OpenSSL", "Enterprise/AnoCrypto-C", "Implemented hash-chain"),
    "docs/ROADMAP.md": (
        "real local PKCS#11/HSM target",
        "AnoCrypto-C",
        "verify-go-release.py --profile full",
        "Keep SQLite/PostgreSQL backup/restore, CRL/OCSP outage-and-recovery",
    ),
    "docs/adr/0006-crypto-backend-direction-anocrypto.md": (
        "Community owns the backend-neutral core contract and OpenSSL adapter",
        "Enterprise reuses Community",
        "must not silently call OpenSSL",
    ),
    "docs/adr/0007-key-provider-signing-boundary.md": (
        "reused by Enterprise/OpenSSL",
        "provider.evidence_failed",
        "production non-exportability claim",
    ),
    "docs/reference/core-boundary-integration.md": ("certificate, CRL, and OCSP",),
    "docs/reference/core-cli-contract.md": (
        "BackendInfo",
        "ANOPKI_CORE_SIGNING_EVIDENCE_FILE",
        "fallback_used",
    ),
    "docs/reference/crypto-backend-strategy.md": (
        "Enterprise/OpenSSL records",
        "anocrypto_used=false",
        "kcmvp_status=not_validated",
    ),
    "docs/reference/project-scope.md": ("current Enterprise implementation scope",),
    "docs/reference/release-evidence.md": (
        "generate-enterprise-release-metadata.py",
        "anopki-enterprise-go-verification.tar.gz",
        "enterprise_commit",
        "community_baseline_commit",
        "anocrypto_used=false",
        "RSA and ECDSA",
        "non-interactive encrypted-PEM rejection",
        "A real non-exportable provider remains unimplemented",
        "anopki-recovery-verification.tar.gz",
        "anopki-status-outage-verification.tar.gz",
        "anopki-audit-replay-verification.tar.gz",
        "anopki-audit-integrity-verification.tar.gz",
        "anopki-issuer-rollover-verification.tar.gz",
        "anopki-multi-node-verification.tar.gz",
        "anopki-postgres-recovery-verification.tar.gz",
    ),
    "docs/reference/target-architecture.md": (
        "reuses it without a fork",
        "GET /version",
        "real production non-exportable provider remains unimplemented",
    ),
    "docs/runbooks/release-process.md": (
        "anopki-backend-info.json",
        "anopki-enterprise-go-verification.tar.gz",
        "verify-go-release.py --profile full",
        "anopki-release-metadata.json",
        "kcmvp_status=not_applicable",
        "verify-recovery-drill.py",
        "verify-status-outage-drill.py",
        "verify-audit-replay-drill.py",
        "verify-audit-integrity-drill.py",
        "verify-issuer-rollover-drill.py",
        "verify-multi-node-reliability.py",
        "verify-postgres-recovery-drill.py",
    ),
    "docs/security/threat-model.md": (
        "Enterprise production non-exportable provider remains pending",
        "Monotonic `sha256-v1` chain",
    ),
    "scripts/test_validate_docs.py": (
        "test_generated_build_tree_headers_are_ignored",
        "test_completed_key_provider_work_in_roadmap_fails",
    ),
    "scripts/validate-docs.py": (
        "is_generated_or_ignored_path",
        "ROADMAP still lists completed shared KeyProvider/backend work",
    ),
    "scripts/test_validate_release_artifacts.py": (
        "enterprise-openssl",
        "anopki-enterprise-go-verification.tar.gz",
        "commercial_release_authorized",
        'value["anocrypto_used"] = True',
        "test_missing_recovery_evidence_fails",
        "test_missing_status_outage_evidence_fails",
        "test_missing_audit_replay_evidence_fails",
        "test_missing_audit_integrity_evidence_fails",
        "test_missing_issuer_rollover_evidence_fails",
        "test_missing_multi_node_evidence_fails",
        "test_missing_postgres_recovery_evidence_fails",
    ),
    "scripts/validate-release-artifacts.py": (
        "Enterprise/OpenSSL",
        "anopki-enterprise-go-verification.tar.gz",
        "community_baseline_commit",
        "anocrypto_used=false",
        "anopki-release-metadata.json",
        "require_recovery_evidence_archive",
        "require_status_outage_evidence_archive",
        "require_audit_replay_evidence_archive",
        "require_audit_integrity_evidence_archive",
        "require_issuer_rollover_evidence_archive",
        "require_multi_node_evidence_archive",
        "require_postgres_recovery_evidence_archive",
    ),
    "scripts/test_validate_release_evidence.py": (
        "release evidence validator tests ok",
        "test_missing_release_go_evidence_fails",
        "test_missing_release_recovery_evidence_fails",
        "test_missing_release_status_outage_evidence_fails",
        "test_missing_release_audit_replay_evidence_fails",
        "test_missing_release_audit_integrity_evidence_fails",
        "test_missing_release_issuer_rollover_evidence_fails",
        "test_missing_release_multi_node_evidence_fails",
        "test_missing_release_postgres_recovery_evidence_fails",
    ),
    "scripts/validate-release-evidence.py": (
        "test_generate_enterprise_release_metadata.py",
        "generate-enterprise-release-metadata.py",
        "REQUIRED_GO_RUNNER_TEXT",
        "anopki-enterprise-go-verification.tar.gz",
        "REQUIRED_RECOVERY_RUNNER_TEXT",
        "REQUIRED_STATUS_OUTAGE_RUNNER_TEXT",
        "REQUIRED_AUDIT_REPLAY_RUNNER_TEXT",
        "REQUIRED_AUDIT_INTEGRITY_RUNNER_TEXT",
        "REQUIRED_ISSUER_ROLLOVER_RUNNER_TEXT",
        "REQUIRED_MULTI_NODE_RUNNER_TEXT",
        "REQUIRED_POSTGRES_RECOVERY_RUNNER_TEXT",
    ),
    "scripts/test_validate_version_metadata.py": ("Enterprise edition metadata drift",),
    "scripts/validate-version-metadata.py": (BASELINE_COMMIT, "Enterprise edition metadata drift"),
    "scripts/test_verify_go_release.py": (
        "AnoPKI Enterprise",
        "community_baseline_commit",
        "commercial_release_authorized",
        "fake-go.cmd",
        "DisableDelayedExpansion",
        '"%~dp0fake-go.py" %*',
    ),
    "scripts/verify-go-release.py": (
        "AnoPKI Enterprise Go Verification Evidence",
        '"enterprise_commit"',
        '"community_baseline_commit"',
        '"commercial_release_authorized": False',
        '"anocrypto_sdk_status": "not_run"',
        '"pki_parity_status": "unsupported_pending"',
        '"kcmvp_status": "not_validated"',
    ),
    "scripts/test_verify_local.py": (
        "test_generate_enterprise_release_metadata.py",
        "test_verify_go_release.py",
        "enterprise-verify-local",
        "verify-recovery-drill.py",
        "verify-status-outage-drill.py",
        "verify-audit-replay-drill.py",
        "verify-audit-integrity-drill.py",
        "verify-issuer-rollover-drill.py",
        "verify-multi-node-reliability.py",
        "test_verify_postgres_recovery_drill.py",
    ),
    "scripts/verify-local.ps1": (
        "test_generate_enterprise_release_metadata.py",
        "test_verify_go_release.py",
        "enterprise-verify-local",
        "verify-recovery-drill.py",
        "verify-status-outage-drill.py",
        "verify-audit-replay-drill.py",
        "verify-audit-integrity-drill.py",
        "verify-issuer-rollover-drill.py",
        "verify-multi-node-reliability.py",
        "test_verify_postgres_recovery_drill.py",
    ),
}

ENTERPRISE_REQUIRED_FILES = {
    ".github/workflows/anocrypto-sdk-integration.yml",
    "docs/enterprise/private-alpha-evidence.md",
    "enterprise/tests/anocrypto_sdk_integration_test.cpp",
    "include/anopki/enterprise/anocrypto_backend.hpp",
    "scripts/generate-enterprise-release-metadata.py",
    "scripts/test_generate_enterprise_release_metadata.py",
    "scripts/test_verify_go_release.py",
    "scripts/verify-go-release.py",
    "service/internal/enterprise/edition.go",
    "src/backends/anocrypto_c/anocrypto_backend.cpp",
}


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True)
    if result.returncode != 0:
        message = result.stderr.decode(errors="replace").strip()
        raise SystemExit(message or f"git {' '.join(args)} failed")
    return result.stdout


def normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def tree_paths(root: Path, commit: str) -> set[str]:
    return set(git(root, "ls-tree", "-r", "--name-only", commit).decode().splitlines())


def exact_shared(path: str) -> bool:
    return path not in COMMUNITY_ONLY_FILES and path not in ENTERPRISE_OWNED_TARGET_FILES and path not in MIXED_REQUIRED_TEXT


def validate(root: Path) -> None:
    root = root.resolve()
    edition = json.loads((root / ".edition/edition.json").read_text(encoding="utf-8"))
    if edition.get("community_baseline_commit") != BASELINE_COMMIT:
        raise SystemExit("Enterprise edition metadata does not match synchronized Community baseline")

    git(root, "cat-file", "-e", f"{BASELINE_COMMIT}^{{commit}}")
    git(root, "cat-file", "-e", f"{PREVIOUS_BASELINE_COMMIT}^{{commit}}")
    target_paths = tree_paths(root, BASELINE_COMMIT)
    previous_paths = tree_paths(root, PREVIOUS_BASELINE_COMMIT)

    missing: list[str] = []
    changed: list[str] = []
    exact_paths = sorted(path for path in target_paths if exact_shared(path))
    for rel in exact_paths:
        path = root / rel
        if not path.is_file():
            missing.append(rel)
            continue
        target = git(root, "show", f"{BASELINE_COMMIT}:{rel}")
        if normalized(path.read_bytes()) != normalized(target):
            changed.append(rel)

    stale = sorted(
        rel
        for rel in previous_paths - target_paths
        if exact_shared(rel) and (root / rel).exists()
    )

    mixed_missing: list[str] = []
    mixed_drift: list[str] = []
    for rel, required in MIXED_REQUIRED_TEXT.items():
        path = root / rel
        if not path.is_file():
            mixed_missing.append(rel)
            continue
        text = path.read_text(encoding="utf-8")
        absent = [token for token in required if token not in text]
        if absent:
            mixed_drift.append(f"{rel}: " + ", ".join(absent))

    leaked_community_only = sorted(rel for rel in COMMUNITY_ONLY_FILES if (root / rel).exists())
    missing_enterprise = sorted(rel for rel in ENTERPRISE_REQUIRED_FILES if not (root / rel).is_file())

    details: list[str] = []
    if missing:
        details.append("missing exact Community files:\n" + "\n".join(missing))
    if changed:
        details.append("drifted exact Community files:\n" + "\n".join(changed))
    if stale:
        details.append("stale files deleted by Community target:\n" + "\n".join(stale))
    if mixed_missing:
        details.append("missing mixed-ownership files:\n" + "\n".join(mixed_missing))
    if mixed_drift:
        details.append("mixed-ownership structure drift:\n" + "\n".join(mixed_drift))
    if leaked_community_only:
        details.append("Community-only files present in Enterprise:\n" + "\n".join(leaked_community_only))
    if missing_enterprise:
        details.append("missing Enterprise-owned files:\n" + "\n".join(missing_enterprise))
    if details:
        raise SystemExit("\n".join(details))

    print(
        f"community baseline ok: {BASELINE_COMMIT} "
        f"({len(exact_paths)} exact shared files, {len(MIXED_REQUIRED_TEXT)} mixed files)"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT, type=Path)
    args = parser.parse_args()
    validate(args.root)


if __name__ == "__main__":
    main()
