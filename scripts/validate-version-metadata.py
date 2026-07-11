#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Validate release version source-of-truth wiring."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def require_text(root: Path, path: Path, values: list[str]) -> str:
    if not path.is_file():
        fail(f"missing required file: {path.relative_to(root)}")
    text = path.read_text(encoding="utf-8")
    missing = [value for value in values if value not in text]
    if missing:
        fail(f"{path.relative_to(root)} missing:\n" + "\n".join(missing))
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    version = require_text(root, root / "VERSION", []).strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?", version):
        fail("VERSION must be MAJOR.MINOR.PATCH with an optional SemVer prerelease")

    require_text(
        root,
        root / "CMakeLists.txt",
        [
            'file(READ "${CMAKE_CURRENT_SOURCE_DIR}/VERSION" ANOPKI_VERSION)',
            'string(REGEX MATCH "^[0-9]+\\\\.[0-9]+\\\\.[0-9]+" ANOPKI_PROJECT_VERSION "${ANOPKI_VERSION}")',
            "project(anopki VERSION ${ANOPKI_PROJECT_VERSION} LANGUAGES C CXX)",
            "src/version_config.hpp.in",
        ],
    )
    require_text(
        root,
        root / "src/version.cpp",
        [
            "ANOPKI_VERSION_MAJOR",
            "ANOPKI_VERSION_STRING",
        ],
    )
    edition_path = root / ".edition/edition.json"
    edition = json.loads(require_text(root, edition_path, []))
    expected_edition = {
        "community_baseline_commit": "2be155780d4b024c76b0a901ec130e83fc221f2f",
        "base_version": version,
        "edition": "AnoPKI Enterprise",
        "enterprise_overlay_version": "unreleased",
        "enterprise_overlay_status": "private-alpha",
        "crypto_backend_default": "openssl",
        "crypto_backend_direction": "anocrypto",
        "anocrypto_status": "skeleton_pending",
        "commercial_license_status": "placeholder",
        "kcmvp_status": "not_validated",
        "provider_status": "not_implemented",
        "distribution_status": "prohibited",
    }
    drift = [f"{key}: expected {value!r}, got {edition.get(key)!r}" for key, value in expected_edition.items() if edition.get(key) != value]
    if drift:
        fail("Enterprise edition metadata drift:\n" + "\n".join(drift))

    require_text(
        root,
        root / "service/internal/enterprise/edition.go",
        [
            'EditionName = "AnoPKI Enterprise"',
            'OverlayVersion = "unreleased"',
            'OverlayStatus = "private-alpha"',
            'ActiveCryptoBackend = "openssl"',
            'ExperimentalCryptoBackend = "anocrypto"',
            'ExperimentalCryptoBackendStatus = "skeleton_pending"',
        ],
    )
    require_text(
        root,
        root / "src/enterprise/edition.cpp",
        [
            'return "AnoPKI Enterprise";',
            'return "unreleased";',
            'return "private-alpha";',
            'return "openssl";',
            'return "anocrypto";',
            'return "skeleton_pending";',
        ],
    )
    require_text(
        root,
        root / "service/cmd/anopki-service/main.go",
        [
            "serviceVersion   = defaultServiceVersion",
            '"version":    cfg.Version',
        ],
    )
    require_text(
        root,
        root / "scripts/validate-release-artifacts.py",
        ['VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()'],
    )
    require_text(
        root,
        root / ".github/workflows/release.yml",
        [
            'VERSION="$(cat VERSION)"',
            'test "${GITHUB_REF_NAME#v}" = "$VERSION"',
            "-X main.serviceVersion=${VERSION}",
            "anopki-service-v${VERSION}-linux-amd64.tar.gz",
            "anopki-core-v${VERSION}-linux-amd64.tar.gz",
        ],
    )
    require_text(
        root,
        root / "docs/enterprise/private-alpha-evidence.md",
        [
            "2be155780d4b024c76b0a901ec130e83fc221f2f",
            version,
            "Active backend | OpenSSL",
            "AnoCrypto | Opt-in skeleton; pending",
            "KCMVP | Not validated; no evidence",
            "Commercial license | Placeholder; distribution blocked",
            "HSM/KMS/PKCS#11 | Not implemented",
            "unsupported_pending",
            "Reviewed commit SHA | `PENDING`",
            "GitHub Actions run URL | `PENDING`",
            "Customer and production distribution prohibited",
        ],
    )
    print("version metadata ok")


if __name__ == "__main__":
    main()
