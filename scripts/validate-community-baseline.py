#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Verify exact Community blobs and explicit Enterprise mixed boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_COMMIT = "ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc"
PREVIOUS_BASELINE_COMMIT = "acb71b8f4e9133d9c25dad1be3bca58209fba0d7"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

# Frozen Community stays read-only. These reviewed fixes pin both normalized
# upstream and Enterprise bytes; they do not permit arbitrary shared-file drift.
REVIEWED_ENTERPRISE_PATCHES = {
    "CONTRIBUTING.md": (
        "613b101abe9502a6367a48b41fbfa2b080216fdff1e0b7d064d62d0c1f2c8170",
        "bf9d189a57e57c3a29912c0fc66b720d3b2aa2e585879b567e7a2cf75eea2d7f",
    ),
    "docs/operations/backup-restore-runbook.md": (
        "773bd634194163a53bc8bfc2c05788088e1373756dd42c530a313290880025dc",
        "7dfe6372c82ed12c738677f190e051987df45681d9dabd91ec2e4b215b690c00",
    ),
    "scripts/acme-smoke/test-run-certbot-smoke.ps1": (
        "6129848d6afa29e238e580a9b67aef3c95e6cdc48b97ad274c027361c61336e0",
        "298968aaab3872b3953024cff355047439c483f393ac55087fdeaadd2a8c7885",
    ),
    "scripts/test_verify_audit_hash_chain.py": (
        "3e2acf4364dcb7713bcc310b8cf37d28aad2ce2386938d201c2a7f21eccf5169",
        "ccacc2cbd030214fe3f903e40c94da32504fc66376e2f7c1c4c8c1d836d619ff",
    ),
    "scripts/test_verify_audit_integrity_drill.py": (
        "752956a4658b6fc01657692b0a0997950da39aae2930e8bbdcd00eb7d584ff73",
        "c1d5d02ac155604add036a6e4391aa1d708ceca9667fee23ce62bf37a46fd4a3",
    ),
    "scripts/test_verify_audit_replay_drill.py": (
        "87d566f716d9b4387610f2d0787f8343730ebfef2635132bb0bd9e5fc80d12ea",
        "b75742e90f47fa6c22ee36dc7d95107856614e88bbdbc1c1487dd2d501d33307",
    ),
    "scripts/test_verify_authorization_boundary.py": (
        "43fcfc4d8ec3d1492053e2dc7e10242abd13263f13f1071d456d1e7893516b46",
        "ddc7f40568ba19bee65a38506a945dedc883b2df9fae208ce2693a694d175491",
    ),
    "scripts/test_verify_issuer_rollover_drill.py": (
        "cfb9605bcf54c043f544364b63f5bfc354d377f6bff09bab60112fa1d593b60c",
        "3bcf18cd429b304fb10337c3316fb29e6fbe8fac7cc2c7e2652a3494b4d72388",
    ),
    "scripts/test_verify_multi_node_reliability.py": (
        "527e4bff62ec6ab1ad7dd00b21fd487bc03b7650a63bcb6d5f86c7e6fab5baa4",
        "776bea119c9acc07c1d0860535515f7856475c913c5eed308ff5ca22973a59e2",
    ),
    "scripts/test_verify_postgres_recovery_drill.py": (
        "5c3b1dea16e349480f45276264e39b44e82658898d29b7c639ab00dd35276e47",
        "914b0b8960a5efca3159f231e4606827b1bcc3c04a6c025e88da162a9a42f352",
    ),
    "scripts/test_verify_status_outage_drill.py": (
        "f60e8f3f7c1233a4d5ff04fcb10d7e77a8505e5d85904c03984533b3726a06c6",
        "5b27bc09bc6d4629cda3dd97efaa4b864ce1d97094f73a49880e1e4e54322a3e",
    ),
    "scripts/verify-audit-hash-chain.py": (
        "262280cad9385bc691d6697b9cee258b7f656c1de65f3e48b422f43cd71cddc9",
        "61712f2a07fe6744b62fe928adb7f93bf8a336fb92c175d22f561c665e3a9448",
    ),
    "scripts/verify-audit-integrity-drill.py": (
        "359178da72aca0a0b972339b468ec10679cbcdd62593a908e58bbb7cbc2016d0",
        "37d7763491c658e94fad80824ae347ff3054eaaee0d9d2d2c11f615bb5f48a4c",
    ),
    "scripts/verify-audit-replay-drill.py": (
        "f3e13eca2081383bc1e0df387a9d5b5050aa657556fd4342985a71c9f94257e7",
        "85d65d09b8ebb19ec25b6053ebbb42261c640006718bb482779d692de336daa4",
    ),
    "scripts/verify-authorization-boundary.py": (
        "47ea9de9e3413dbd91bcb9031df208d45b9952ac16c7ed57304a05e7837d5c3d",
        "e0c6c9a2c7e31bb47c793086ac3ee83e42d1712caf6f0161a45219e1c2384d78",
    ),
    "scripts/verify-issuer-rollover-drill.py": (
        "a699bd417652117ea6f6fdca3dd180ac14d0b865261bb5b8c5445e38c34c07fe",
        "a37d2073cd54982ec6da5d4608970f0c99104293bb72c90d4ae65315102e4e2e",
    ),
    "scripts/verify-multi-node-reliability.py": (
        "97b901e6a69852cc9f4bbb2474766d59aba793356667d68ca539469672621b35",
        "814a3f80858b1df27c7731063845c99427e799b37e3aa0b774bf8237dcb03a6b",
    ),
    "scripts/verify-postgres-recovery-drill.py": (
        "99f504272091e1d539cd11ac2bf7faf7acd394980b58d873c79893eb7144cff8",
        "7ea09d3f87962f35725d8316e1b32e66b85674534449eab8bda3afebaa8d6f6e",
    ),
    "scripts/verify-status-outage-drill.py": (
        "73cd4d8db22469fe0e322dc71f7284ef7446777d9ed6440159637ca76e7ad9bf",
        "f5f49223c6dc5bc44e18cc96342ea051301ea2acea5e26ec42ac7b957104f46f",
    ),
    "service/cmd/anopki-service/main_test.go": (
        "cd06896dd896f5754379c0fb8d6e3b5f45204cfe6c3f4abe2467b13bcc3953df",
        "89b3962d0c519f3574fd2fedf5004d97ad3a612115df267cfa07a5dfd1f3185b",
    ),
    "service/go.mod": (
        "eb867a231ce77fdb953e9c135da82c7e0b669988e7d64d8993756ecd11ea9353",
        "c35e60073cd52286434d4cbe528d045b63834b625647c53789858297c1b19ad3",
    ),
    "service/go.sum": (
        "c5047eb2164657a02f1caf91143645a4d9c67c61ee7de61fb57f0ed90a80fdc1",
        "2418eaeb89ddd7118f59bf22b17ce20f9f35388231a9062d32cd26138ca02d81",
    ),
    "service/internal/store/migrate.go": (
        "780ef32d30d68d0c864be22bd953b620d34733e4c6cb69dca0ea88b7a47dbc6f",
        "5eda4a8f9ed6a395a2f7f0a886dac433ba3a20eb609745052d227429ec1f86f1",
    ),
    "service/internal/store/sqlstore_outbox.go": (
        "8fb7a27ff713430270f9e4e9427fd529c0c35dc89a9d50c638356c0aedfaad2b",
        "0906397c8a4f53958cbf9eee71d2758f48ba0296043d60baee6dfcc139aa6f7e",
    ),
}

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
        "anopki-enterprise-go-analysis-1.26.11",
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
        "python scripts/verify-authorization-boundary.py",
        "anopki-authorization-boundary-verification",
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
        "anopki-authorization-boundary-verification.tar.gz",
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
        "authorization boundary evidence",
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
        "verify-authorization-boundary.py",
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
        "generic authorization boundary",
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
        "anopki-authorization-boundary-verification.tar.gz",
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
        "verify-authorization-boundary.py",
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
        "test_missing_authorization_boundary_evidence_fails",
        "test_authorization_boundary_placeholder_commit_fails",
        "test_authorization_boundary_stale_baseline_fails",
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
        "require_authorization_boundary_evidence_archive",
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
        "test_missing_release_authorization_boundary_evidence_fails",
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
        "REQUIRED_AUTHORIZATION_BOUNDARY_RUNNER_TEXT",
        "REQUIRED_ISSUER_ROLLOVER_RUNNER_TEXT",
        "REQUIRED_MULTI_NODE_RUNNER_TEXT",
        "REQUIRED_POSTGRES_RECOVERY_RUNNER_TEXT",
    ),
    "scripts/test_validate_version_metadata.py": (
        "Enterprise edition metadata drift",
        "test_non_exact_or_stale_community_baseline_fails",
    ),
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
        "verify-authorization-boundary.py",
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
        "verify-authorization-boundary.py",
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
    if not COMMIT_RE.fullmatch(BASELINE_COMMIT) or not COMMIT_RE.fullmatch(PREVIOUS_BASELINE_COMMIT):
        raise SystemExit("Community baselines must be exact lowercase 40-character SHAs")
    if BASELINE_COMMIT == PREVIOUS_BASELINE_COMMIT:
        raise SystemExit("Community baseline must not reuse the stale previous baseline")
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
    unmatched_patches = sorted(set(REVIEWED_ENTERPRISE_PATCHES) - set(exact_paths))
    for rel in exact_paths:
        path = root / rel
        if not path.is_file():
            missing.append(rel)
            continue
        target = git(root, "show", f"{BASELINE_COMMIT}:{rel}")
        actual = normalized(path.read_bytes())
        target = normalized(target)
        if rel in REVIEWED_ENTERPRISE_PATCHES:
            expected_upstream, expected_enterprise = REVIEWED_ENTERPRISE_PATCHES[rel]
            matches = (
                hashlib.sha256(target).hexdigest() == expected_upstream
                and hashlib.sha256(actual).hexdigest() == expected_enterprise
            )
        else:
            matches = actual == target
        if not matches:
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
    if unmatched_patches:
        details.append("reviewed patches outside exact Community files:\n" + "\n".join(unmatched_patches))
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
        f"({len(exact_paths) - len(REVIEWED_ENTERPRISE_PATCHES)} exact shared files, "
        f"{len(REVIEWED_ENTERPRISE_PATCHES)} reviewed Enterprise patches, "
        f"{len(MIXED_REQUIRED_TEXT)} mixed files)"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT, type=Path)
    args = parser.parse_args()
    validate(args.root)


if __name__ == "__main__":
    main()
