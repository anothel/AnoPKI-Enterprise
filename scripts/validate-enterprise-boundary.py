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
    "enterprise/anocrypto/include/anocrypto/anocrypto.h",
    "enterprise/anocrypto/src/anocrypto.c",
    "src/core/crypto/anocrypto_backend.cpp",
    "include/anopki/enterprise/edition.hpp",
    "service/internal/enterprise/edition.go",
    "docs/enterprise/anocrypto-integration-plan.md",
    "docs/enterprise/kcmvp-preparation.md",
]

PRIVATE_DOC_PREFIXES = ("docs/enterprise/",)
PRIVATE_CODE_PREFIXES = (
    "enterprise/",
    "include/anopki/enterprise/",
    "service/internal/enterprise/",
    "src/enterprise/",
    "src/core/crypto/anocrypto_backend",
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
    for token in ["ANOPKI_ENTERPRISE_EDITION", "ANOPKI_ENABLE_ANOCRYPTO_BACKEND", "anocrypto_c99"]:
        if token not in cmake:
            fail(f"Enterprise CMake missing {token}")


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
    check_generated_files(root)
    check_private_paths(root)
    check_mpl_headers(root)
    check_enterprise_headers(root)
    check_claims(root)
    check_secrets(root)

    docs = (root / "docs/enterprise/anocrypto-integration-plan.md").read_text(encoding="utf-8")
    if "not KCMVP validated" not in docs or "skeleton" not in docs:
        fail("Enterprise AnoCrypto docs must clearly mark current implementation as skeleton/not validated")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT, type=Path)
    args = parser.parse_args()
    validate(args.root)
    print("enterprise boundary ok")


if __name__ == "__main__":
    main()
