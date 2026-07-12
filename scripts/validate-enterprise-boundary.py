#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Validate that Enterprise remains a private overlay on Community."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "LICENSE",
    "LICENSES/MPL-2.0.txt",
    "LICENSES/LicenseRef-AnoPKI-Enterprise.txt",
    "ENTERPRISE-LICENSE-NOTICE.md",
    "include/anopki/enterprise/anocrypto_backend.hpp",
    "src/backends/anocrypto_c/anocrypto_backend.cpp",
    "enterprise/tests/anocrypto_sdk_integration_test.cpp",
    ".github/workflows/anocrypto-sdk-integration.yml",
    "scripts/validate-anocrypto-sdk-evidence.py",
    "scripts/compose-anocrypto-sdk-evidence.py",
    "scripts/test_validate_anocrypto_sdk_evidence.py",
    "sdk-manifests/anocrypto-c/README.md",
    "sdk-manifests/anocrypto-c/example-evidence.json",
    "include/anopki/enterprise/edition.hpp",
    "service/internal/enterprise/edition.go",
    "docs/enterprise/anocrypto-integration-plan.md",
    "docs/enterprise/kcmvp-preparation.md",
    "docs/enterprise/private-alpha-evidence.md",
    "enterprise/tests/edition_metadata_test.cpp",
    "src/backends/openssl/openssl_backend.hpp",
    "src/backends/openssl/openssl_backend.cpp",
    "src/backends/openssl/csr.cpp",
    "src/backends/openssl/issue.cpp",
    "src/backends/openssl/crl.cpp",
    "src/backends/openssl/ocsp.cpp",
    "include/anopki/crypto/runtime.hpp",
]

PRIVATE_DOC_PREFIXES = ("docs/enterprise/",)
PRIVATE_CODE_PREFIXES = (
    "enterprise/",
    "src/backends/anocrypto_c/",
    "include/anopki/enterprise/",
    "service/internal/enterprise/",
    "src/enterprise/",
)
PRIVATE_ROOT_FILES = {"ENTERPRISE-LICENSE-NOTICE.md", "EDITION.md"}
SOURCE_EXTENSIONS = {".c", ".cpp", ".go", ".h", ".hpp", ".ps1", ".py"}
CLAIM_EXTENSIONS = {".json", ".md", ".txt"}
GENERATED_DIRS = {"build", "build-enterprise", "build-fuzz", "build-release", ".tmp", ".gocache", ".tmp-gocache"}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "docs-pack", "node_modules", "vendor"}
SELF_TEST_FILES = {
    "validate-enterprise-boundary.py",
    "test_validate_enterprise_boundary.py",
}

ANOCRYPTO_CLAIM_WORDS = ("implemented", "implementation", "active", "current", "default", "production", "ready")
KCMVP_CLAIM_WORDS = ("certified", "validated")
ALLOW_QUALIFIERS = (
    "planned",
    "intended",
    "pending",
    "future",
    "target",
    "preparation",
    "skeleton",
    "not implemented",
    "not a cryptographic implementation",
    "not kcmvp",
    "not a kcmvp",
    "not validated",
    "not_validated",
    "not a production default",
    "not claim",
    "do not claim",
    "must not claim",
    "not mark",
    "until",
    "before switching",
    "after parity",
    "evidence exist",
    "evidence are complete",
    "implementation pending",
    "readiness",
    "direction",
    "fallback",
    "not-production-complete",
    "production release blocked",
    "production-releasable only after",
    "production expansion",
    "under development",
    "external sdk",
    "capability unavailable",
    "earlier planning",
    "openSSL remains the active".lower(),
    "block the",
    "can be production-releasable",
    "금지",
    "검증 완료",
    "if any",
    "only for the listed",
    "has been removed",
    "have been removed",
    "requires no anocrypto-c sdk",
    "proceed separately",
    "when the first",
    "when anocrypto implementation begins",
    "implementation and backend adapter",
    "implementation, sso/rbac",
    "does not make",
    "adoption",
    "private keys",
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\baws_secret_access_key\s*=\s*['\"]?[A-Za-z0-9/+=]{20,}"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{12,}['\"]"),
)

ROOT_LICENSE_MARKERS = (
    "AnoPKI Enterprise Mixed-License Notice",
    "LICENSES/MPL-2.0.txt",
    "LICENSES/LicenseRef-AnoPKI-Enterprise.txt",
)
MPL_LICENSE_MARKERS = (
    "Mozilla Public License Version 2.0",
    "https://mozilla.org/MPL/2.0/",
)
ENTERPRISE_LICENSE_MARKERS = (
    "LicenseRef-AnoPKI-Enterprise",
    "internal evaluation and development only",
    "no customer distribution",
    "no production distribution",
    "not release-ready",
    "must be replaced by an approved commercial agreement before release",
)


def fail(message: str) -> None:
    raise SystemExit(message)


def relpath(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def has_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def should_skip(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    return path.suffix == ".txtt" or path.name in SELF_TEST_FILES or any(part in SKIP_DIRS for part in rel.parts)


def text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file() and not should_skip(path, root):
            yield path


def source_files(root: Path) -> Iterable[Path]:
    for path in text_files(root):
        if path.name == "CMakeLists.txt" or path.suffix in SOURCE_EXTENSIONS:
            yield path


def has_allow_qualifier(line: str) -> bool:
    lowered = line.lower()
    if (
        "sha-256" in lowered
        and any(scope in lowered for scope in ("primitive", "self-test", "known-answer"))
        and not any(word in lowered for word in ("backend", "production", "ready", "validated", "kcmvp"))
    ):
        return True
    if '"anocrypto_self_test": "implemented"' in lowered:
        return True
    return any(qualifier in lowered for qualifier in ALLOW_QUALIFIERS)


def has_active_anocrypto_evidence(root: Path) -> bool:
    evidence = root / "docs/enterprise/private-release-evidence.md"
    tests = root / "enterprise/anocrypto/tests"
    if not evidence.is_file() or not tests.exists():
        return False
    text = evidence.read_text(encoding="utf-8", errors="ignore").lower()
    return "active anocrypto backend evidence: complete" in text


def has_kcmvp_certification_evidence(root: Path) -> bool:
    evidence = root / "docs/enterprise/kcmvp-certification-evidence.md"
    if not evidence.is_file():
        return False
    text = evidence.read_text(encoding="utf-8", errors="ignore").lower()
    return "certificate" in text and "kcmvp" in text


def check_required_files(root: Path) -> None:
    missing = [path for path in REQUIRED if not (root / path).is_file()]
    if missing:
        fail("Enterprise tree missing required overlay files:\n" + "\n".join(missing))


def check_license_layout(root: Path) -> None:
    root_license = (root / "LICENSE").read_text(encoding="utf-8")
    if "GNU AFFERO GENERAL PUBLIC LICENSE" in root_license.upper():
        fail("Enterprise root LICENSE must not contain AGPL terms")
    missing = [marker for marker in ROOT_LICENSE_MARKERS if marker not in root_license]
    if missing:
        fail("Enterprise root LICENSE missing mixed-license markers:\n" + "\n".join(missing))

    mpl_license = (root / "LICENSES/MPL-2.0.txt").read_text(encoding="utf-8")
    missing = [marker for marker in MPL_LICENSE_MARKERS if marker not in mpl_license]
    if missing:
        fail("MPL-2.0 license text missing required markers:\n" + "\n".join(missing))

    enterprise_license = (root / "LICENSES/LicenseRef-AnoPKI-Enterprise.txt").read_text(encoding="utf-8")
    lowered = " ".join(enterprise_license.lower().split())
    missing = [marker for marker in ENTERPRISE_LICENSE_MARKERS if marker.lower() not in lowered]
    if missing:
        fail("Enterprise license placeholder missing required restrictions:\n" + "\n".join(missing))

    notice = (root / "ENTERPRISE-LICENSE-NOTICE.md").read_text(encoding="utf-8")
    missing = [marker for marker in ROOT_LICENSE_MARKERS[1:] if marker not in notice]
    if missing:
        fail("Enterprise license notice missing license paths:\n" + "\n".join(missing))


def check_cmake_markers(root: Path) -> None:
    cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
    required = [
        'set(ANOPKI_PRODUCT_PROFILE "enterprise-openssl"',
        "enterprise-anocrypto-c",
        "ANOCRYPTO_SDK_ROOT",
        "find_package(AnoCryptoC 0.1.0 EXACT CONFIG REQUIRED)",
        "AnoCryptoC::AnoCryptoC",
        "anopki_enterprise_anocrypto_adapter",
        "anocrypto_sdk_integration",
        "anocrypto_no_fallback",
        "anopki-enterprise-openssl",
        "anopki-enterprise-anocrypto-c",
    ]
    missing = [token for token in required if token not in cmake]
    if missing:
        fail("Enterprise CMake missing external AnoCrypto-C integration markers:\n" + "\n".join(missing))

    if 'ANOPKI_PRODUCT_PROFILE STREQUAL "enterprise-anocrypto-c"' not in cmake:
        fail("Enterprise CMake missing explicit enterprise-anocrypto-c profile")
    adapter_source = (root / "src/backends/anocrypto_c/anocrypto_backend.cpp").read_text(encoding="utf-8")
    if "openssl/" in adapter_source.lower() or "OpenSSL::Crypto" in adapter_source:
        fail("Enterprise AnoCrypto-C adapter must not reference OpenSSL")
    forbidden = ["anocrypto_c99", "ANOCRYPTO_ENABLE_TEST_HOOKS", "enterprise/anocrypto/src"]
    hits = [token for token in forbidden if token in cmake]
    if hits:
        fail("Enterprise CMake still builds an embedded AnoCrypto implementation:\n" + "\n".join(hits))


def check_openssl_adapter_separation(root: Path) -> None:
    cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
    if "add_library(anopki_openssl_adapter" not in cmake:
        fail("Enterprise must reuse the separated Community OpenSSL adapter target")
    if "target_link_libraries(anopki_openssl_adapter" not in cmake:
        fail("Enterprise OpenSSL adapter target is missing its dependency declaration")

    for target in ("anopki_core", "anopki-core"):
        pattern = re.compile(
            rf"target_link_libraries\(\s*{re.escape(target)}(?=\s|\))(?P<body>.*?)\)",
            re.DOTALL,
        )
        for match in pattern.finditer(cmake):
            if "OpenSSL::Crypto" in match.group("body"):
                fail(f"{target} must not link OpenSSL::Crypto directly")

    hits: list[str] = []
    core_root = root / "src/core"
    for path in core_root.rglob("*") if core_root.exists() else ():
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(content.splitlines(), start=1):
            if "#include <openssl/" in line or "#include \"openssl/" in line:
                hits.append(f"{relpath(path, root)}:{number}: {line.strip()}")
    if hits:
        fail("Backend-neutral Enterprise Core contains direct OpenSSL includes:\n" + "\n".join(hits))

    cli = root / "src/cli/main.cpp"
    if cli.is_file() and "#include <openssl/" in cli.read_text(encoding="utf-8"):
        fail("Enterprise CLI must obtain dependency diagnostics through the selected adapter")


def check_embedded_anocrypto_absent(root: Path) -> None:
    forbidden_paths = [
        root / "enterprise/anocrypto/src",
        root / "enterprise/anocrypto/include",
        root / "src/core/crypto/anocrypto_backend.cpp",
        root / "src/core/crypto/anocrypto_backend.hpp",
    ]
    hits = [str(path.relative_to(root)) for path in forbidden_paths if path.exists()]
    if hits:
        fail("embedded AnoCrypto implementation/header paths are prohibited:\n" + "\n".join(hits))
    implementation_tokens = ("sha256_transform", "anocrypto_hash(", "ANOCRYPTO_ENABLE_TEST_HOOKS")
    source = root / "src/backends/anocrypto_c/anocrypto_backend.cpp"
    text = source.read_text(encoding="utf-8")
    hits = [token for token in implementation_tokens if token in text]
    if hits:
        fail("AnoCrypto-C adapter contains embedded cryptographic implementation markers:\n" + "\n".join(hits))

def check_ci_markers(root: Path) -> None:
    ci = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    if "ctest --test-dir build-enterprise -R anocrypto" in ci:
        fail("Enterprise CI must not use broad AnoCrypto regex selection")
    required = [
        "ANOPKI_PRODUCT_PROFILE=enterprise-openssl",
        "ANOPKI_PRODUCT_PROFILE=enterprise-anocrypto-c",
        "CMAKE_DISABLE_FIND_PACKAGE_AnoCryptoC=TRUE",
        "expected AnoCrypto-C SDK configuration failure",
        "anocrypto_parity_pending",
        "test_validate_anocrypto_sdk_evidence.py",
    ]
    missing = [text for text in required if text not in ci]
    if missing:
        fail("Enterprise CI missing external AnoCrypto-C boundary checks:\n" + "\n".join(missing))

def check_trusted_sdk_workflow(root: Path) -> None:
    workflow = (root / ".github/workflows/anocrypto-sdk-integration.yml").read_text(encoding="utf-8")
    required = [
        "workflow_dispatch",
        "anocrypto_commit",
        "ANOCRYPTO_C_READ_TOKEN",
        "repository: anothel/AnoCrypto-C",
        "persist-credentials: false",
        "ANOPKI_PRODUCT_PROFILE=enterprise-anocrypto-c",
        "ANOCRYPTO_SDK_ROOT",
        "validate-anocrypto-sdk-evidence.py",
        "Prove no OpenSSL dependency",
        "PKI operation parity: unsupported/pending",
        "REQUESTED_ANOCRYPTO_COMMIT: ${{ inputs.anocrypto_commit }}",
        "--enterprise-commit",
        "--workflow-run-id",
        "--workflow-run-attempt",
        "anocrypto_no_fallback",
        "share/licenses/AnoCrypto-C",
        "--use-compress-program='gzip -n'",
    ]
    missing = [token for token in required if token not in workflow]
    if missing:
        fail("trusted AnoCrypto-C workflow missing security/evidence markers:\n" + "\n".join(missing))
    if "pull_request" in workflow.split("jobs:", 1)[0]:
        fail("trusted AnoCrypto-C SDK workflow must not run on pull_request")
    unsafe_shell_interpolation = (
        "commit='${{ inputs.anocrypto_commit }}'",
        "test \"$actual\" = '${{ inputs.anocrypto_commit }}'",
    )
    if any(token in workflow for token in unsafe_shell_interpolation):
        fail("trusted AnoCrypto-C workflow must pass dispatch input through env before shell use")


def check_generated_files(root: Path) -> None:
    hits = []
    for directory in GENERATED_DIRS:
        path = root / directory
        if path.exists() and any(child.is_file() for child in path.rglob("*")):
            hits.append(directory)
    if hits:
        fail("Enterprise tree contains generated build/cache files:\n" + "\n".join(sorted(hits)))


def check_private_paths(root: Path) -> None:
    doc_hits = []
    code_hits = []
    for path in text_files(root):
        rel = relpath(path, root)
        try:
            head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:5])
        except UnicodeDecodeError:
            continue
        is_enterprise = "LicenseRef-AnoPKI-Enterprise" in head
        if not is_enterprise:
            continue
        if rel.startswith("docs/") and not has_prefix(rel, PRIVATE_DOC_PREFIXES):
            doc_hits.append(rel)
        if (path.name == "CMakeLists.txt" or path.suffix in SOURCE_EXTENSIONS) and not (
            rel in PRIVATE_ROOT_FILES or has_prefix(rel, PRIVATE_CODE_PREFIXES)
        ):
            code_hits.append(rel)
    if doc_hits:
        fail("Enterprise docs outside private paths:\n" + "\n".join(sorted(doc_hits)))
    if code_hits:
        fail("Enterprise-only code outside private paths:\n" + "\n".join(sorted(code_hits)))


def check_mpl_headers(root: Path) -> None:
    missing = []
    for path in source_files(root):
        rel = relpath(path, root)
        if has_prefix(rel, PRIVATE_CODE_PREFIXES):
            continue
        head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:5])
        if "SPDX-License-Identifier: MPL-2.0" not in head:
            missing.append(rel)
    if missing:
        fail("Community MPL-2.0 files missing SPDX header:\n" + "\n".join(sorted(missing)))


def check_enterprise_headers(root: Path) -> None:
    missing = []
    for path in source_files(root):
        rel = relpath(path, root)
        if not has_prefix(rel, PRIVATE_CODE_PREFIXES):
            continue
        head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:5])
        if "SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise" not in head:
            missing.append(rel)
    if missing:
        fail("Enterprise-only source files missing proprietary SPDX header:\n" + "\n".join(sorted(missing)))


def check_claims(root: Path) -> None:
    anocrypto_hits = []
    kcmvp_hits = []
    active_anocrypto_ok = has_active_anocrypto_evidence(root)
    kcmvp_ok = has_kcmvp_certification_evidence(root)
    for path in text_files(root):
        if path.name not in {"README.md", "EDITION.md"} and path.suffix not in CLAIM_EXTENSIONS:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        rel = relpath(path, root)
        for number, line in enumerate(lines, start=1):
            lowered = line.lower()
            if (
                "anocrypto" in lowered
                and any(word in lowered for word in ANOCRYPTO_CLAIM_WORDS)
                and not active_anocrypto_ok
                and not has_allow_qualifier(line)
            ):
                anocrypto_hits.append(f"{rel}:{number}: {line.strip()}")
            if (
                "kcmvp" in lowered
                and any(word in lowered for word in KCMVP_CLAIM_WORDS)
                and not kcmvp_ok
                and not has_allow_qualifier(line)
            ):
                kcmvp_hits.append(f"{rel}:{number}: {line.strip()}")
    if anocrypto_hits:
        fail("Enterprise overlay contains unsupported AnoCrypto production claims:\n" + "\n".join(sorted(anocrypto_hits)))
    if kcmvp_hits:
        fail("Enterprise overlay contains unsupported KCMVP certification claims:\n" + "\n".join(sorted(kcmvp_hits)))


def check_secrets(root: Path) -> None:
    hits = []
    for path in text_files(root):
        if path.name.startswith("test_"):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(content.splitlines(), start=1):
            if "secret-scan: allow" in line:
                continue
            if any(pattern.search(line) for pattern in SECRET_PATTERNS):
                hits.append(f"{relpath(path, root)}:{number}")
    if hits:
        fail("Enterprise tree contains private key material or obvious secrets:\n" + "\n".join(sorted(hits)))


def validate(root: Path = ROOT) -> None:
    root = root.resolve()
    check_required_files(root)
    check_license_layout(root)
    check_cmake_markers(root)
    check_openssl_adapter_separation(root)
    check_embedded_anocrypto_absent(root)
    check_ci_markers(root)
    check_trusted_sdk_workflow(root)
    check_generated_files(root)
    check_private_paths(root)
    check_mpl_headers(root)
    check_enterprise_headers(root)
    check_claims(root)
    check_secrets(root)

    docs = (root / "docs/enterprise/anocrypto-integration-plan.md").read_text(encoding="utf-8")
    lowered = docs.lower()
    if ("not kcmvp validated" not in lowered and "kcmvp not validated" not in lowered) or "external" not in lowered or "sdk" not in lowered:
        fail("Enterprise AnoCrypto-C docs must describe the external SDK boundary and lack of KCMVP validation")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT, type=Path)
    args = parser.parse_args()
    validate(args.root)
    print("enterprise boundary ok")


if __name__ == "__main__":
    main()
