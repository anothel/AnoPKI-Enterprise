#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-enterprise-boundary.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_enterprise_boundary", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_file(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_clean_enterprise_root(root: Path) -> None:
    write_file(root, "ENTERPRISE-LICENSE-NOTICE.md", "LicenseRef-AnoPKI-Enterprise\n")
    write_file(
        root,
        "CMakeLists.txt",
        "# SPDX-License-Identifier: MPL-2.0\nANOPKI_ENTERPRISE_EDITION\nANOPKI_ENABLE_ANOCRYPTO_BACKEND\nanocrypto_c99\n",
    )
    write_file(root, "README.md", "# AnoPKI\nOpenSSL remains current.\n")
    write_file(root, "docs/reference/crypto-backend-strategy.md", "AnoCrypto implementation pending. OpenSSL remains current.\n")
    write_file(root, "docs/enterprise/anocrypto-integration-plan.md", "AnoCrypto skeleton; not KCMVP validated.\n")
    write_file(root, "docs/enterprise/kcmvp-preparation.md", "KCMVP target planning only.\n")
    write_file(root, "enterprise/anocrypto/include/anocrypto/anocrypto.h", "/* SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise */\n")
    write_file(root, "enterprise/anocrypto/src/anocrypto.c", "/* SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise */\n")
    write_file(root, "src/core/crypto/anocrypto_backend.cpp", "// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise\n")
    write_file(root, "include/anopki/enterprise/edition.hpp", "// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise\n")
    write_file(root, "service/internal/enterprise/edition.go", "// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise\n")
    write_file(root, "src/core/issue.cpp", "// SPDX-License-Identifier: MPL-2.0\n")


def assert_fails(root: Path, expected: str) -> None:
    validator = load_validator()
    try:
        validator.validate(root)
    except SystemExit as exc:
        assert expected in str(exc)
    else:
        raise AssertionError("validator unexpectedly passed")


def test_clean_enterprise_root_passes() -> None:
    validator = load_validator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_clean_enterprise_root(root)
        validator.validate(root)


def test_requires_enterprise_license_notice() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_clean_enterprise_root(root)
        (root / "ENTERPRISE-LICENSE-NOTICE.md").unlink()
        assert_fails(root, "missing required overlay files")


def test_finds_enterprise_docs_outside_private_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_clean_enterprise_root(root)
        write_file(root, "docs/enterprise-plan.md", "LicenseRef-AnoPKI-Enterprise\n")
        assert_fails(root, "Enterprise docs outside private paths")


def test_finds_enterprise_code_outside_private_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_clean_enterprise_root(root)
        write_file(root, "src/core/private_overlay.cpp", "// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise\n")
        assert_fails(root, "Enterprise-only code outside private paths")


def test_finds_missing_mpl_notice_on_community_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_clean_enterprise_root(root)
        write_file(root, "src/core/issue.cpp", "int main() { return 0; }\n")
        assert_fails(root, "Community MPL-2.0 files missing SPDX header")


def test_finds_premature_anocrypto_claims() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_clean_enterprise_root(root)
        write_file(root, "docs/reference/bad.md", "AnoCrypto is the default production backend.\n")
        assert_fails(root, "unsupported AnoCrypto production claims")


def test_finds_kcmvp_certification_claims() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_clean_enterprise_root(root)
        write_file(root, "docs/enterprise/bad.md", "AnoCrypto is KCMVP certified.\n")
        assert_fails(root, "unsupported KCMVP certification claims")


def test_finds_private_key_material() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_clean_enterprise_root(root)
        write_file(root, "enterprise/key.pem", "-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----\n")
        assert_fails(root, "private key material or obvious secrets")


def test_finds_generated_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_clean_enterprise_root(root)
        write_file(root, "build/generated.txt", "generated\n")
        assert_fails(root, "generated build/cache files")


def main() -> None:
    test_clean_enterprise_root_passes()
    test_requires_enterprise_license_notice()
    test_finds_enterprise_docs_outside_private_paths()
    test_finds_enterprise_code_outside_private_paths()
    test_finds_missing_mpl_notice_on_community_file()
    test_finds_premature_anocrypto_claims()
    test_finds_kcmvp_certification_claims()
    test_finds_private_key_material()
    test_finds_generated_files()
    print("enterprise boundary validator tests ok")


if __name__ == "__main__":
    main()
