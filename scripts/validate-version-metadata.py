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
            "project(anopki VERSION ${ANOPKI_PROJECT_VERSION} LANGUAGES CXX)",
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
        "community_baseline_commit": "ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc",
        "base_version": version,
        "edition": "AnoPKI Enterprise",
        "enterprise_overlay_version": "unreleased",
        "enterprise_overlay_status": "private-alpha",
        "crypto_backend_default": "openssl",
        "crypto_backend_direction": "anocrypto-c",
        "experimental_crypto_backend": "anocrypto-c",
        "anocrypto_status": "external_sdk_not_configured",
        "anocrypto_sdk_package": "AnoCryptoC::AnoCryptoC",
        "anocrypto_sdk_version": None,
        "anocrypto_sdk_build_fingerprint": None,
        "anocrypto_capability_status": "sdk_capabilities_unverified",
        "pki_parity_status": "unsupported_pending",
        "validated_mode": False,
        "kcmvp_evidence": "none",
        "commercial_license_status": "incomplete",
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
            'ExperimentalCryptoBackend = "anocrypto-c"',
            'ExperimentalCryptoBackendStatus = "external_sdk_not_configured"',
            'AnoCryptoSDKPackage = "AnoCryptoC::AnoCryptoC"',
            'AnoCryptoCapabilityStatus = "sdk_capabilities_unverified"',
            'PKIParityStatus = "unsupported_pending"',
            "ValidatedMode = false",
        ],
    )
    require_text(
        root,
        root / "src/enterprise/edition.cpp",
        [
            'return "AnoPKI Enterprise";',
            'return "unreleased";',
            'return "private-alpha";',
            'return ANOPKI_ANOCRYPTO_PROFILE ? "anocrypto-c" : "openssl";',
            'return "anocrypto-c";',
            'return ANOPKI_ANOCRYPTO_PROFILE ? "configured" : "external_sdk_not_configured";',
            'return "AnoCryptoC::AnoCryptoC";',
            'return ANOPKI_ANOCRYPTO_PROFILE ? "pki_operations_complete" : "sdk_capabilities_unverified";',
            'return ANOPKI_ANOCRYPTO_PROFILE ? "local_parity_verified" : "unsupported_pending";',
            "return false;",
        ],
    )
    require_text(
        root,
        root / "service/cmd/anopki-service/main.go",
        [
            "serviceVersion   = defaultServiceVersion",
            '"version":             cfg.Version',
            '"backend":             cfg.Backend',
            '"key_provider_policy": cfg.KeyProviderPolicy',
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
            "ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc",
            version,
            "Active backend | OpenSSL",
            "AnoCrypto-C integration | External SDK adapter boundary; SDK not configured",
            "AnoCrypto-C module self-test | Owned by the external SDK; not executed by this baseline",
            "AnoCrypto-C capability set | Unverified until a pinned external SDK is supplied",
            "PKI parity | Required operations remain `unsupported_pending`",
            "Validated mode | `false`",
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
