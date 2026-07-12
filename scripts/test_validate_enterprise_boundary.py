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
    write_file(root, "LICENSE", "AnoPKI Enterprise Mixed-License Notice\nLICENSES/MPL-2.0.txt\nLICENSES/LicenseRef-AnoPKI-Enterprise.txt\n")
    write_file(root, "LICENSES/MPL-2.0.txt", "Mozilla Public License Version 2.0\nhttps://mozilla.org/MPL/2.0/\n")
    write_file(
        root,
        "LICENSES/LicenseRef-AnoPKI-Enterprise.txt",
        "LicenseRef-AnoPKI-Enterprise\nInternal evaluation and development only.\n"
        "No customer distribution.\nNo production distribution.\nNot release-ready.\n"
        "Must be replaced by an approved commercial agreement before release.\n",
    )
    write_file(root, "ENTERPRISE-LICENSE-NOTICE.md", "LICENSES/MPL-2.0.txt\nLICENSES/LicenseRef-AnoPKI-Enterprise.txt\n")
    write_file(
        root,
        "CMakeLists.txt",
        "# SPDX-License-Identifier: MPL-2.0\n"
        'set(ANOPKI_PRODUCT_PROFILE "enterprise-openssl"\nenterprise-anocrypto-c\nANOPKI_ENTERPRISE_EDITION\nANOCRYPTO_SDK_ROOT\n'
        "find_package(AnoCryptoC 0.1.0 EXACT CONFIG REQUIRED)\n"
        "AnoCryptoC::AnoCryptoC\nanopki_enterprise_anocrypto_adapter\nanocrypto_sdk_integration\nanocrypto_no_fallback\nanopki-enterprise-openssl\nanopki-enterprise-anocrypto-c\nANOPKI_PRODUCT_PROFILE STREQUAL \"enterprise-anocrypto-c\"\n"
        "add_library(anopki_core)\nadd_library(anopki_openssl_adapter)\n"
        "target_link_libraries(anopki_openssl_adapter PRIVATE OpenSSL::Crypto)\n"
        "add_executable(anopki-core)\n"
        "target_link_libraries(anopki-core PRIVATE anopki_core anopki_openssl_adapter)\n",
    )
    write_file(
        root,
        ".github/workflows/ci.yml",
        "ANOPKI_PRODUCT_PROFILE=enterprise-openssl\nANOPKI_PRODUCT_PROFILE=enterprise-anocrypto-c\n"
        "CMAKE_DISABLE_FIND_PACKAGE_AnoCryptoC=TRUE\n"
        "expected AnoCrypto-C SDK configuration failure\n"
        "anocrypto_parity_pending\n",
    )
    write_file(root, "README.md", "# AnoPKI Enterprise\nOpenSSL remains the active profile.\n")
    write_file(root, "docs/reference/crypto-backend-strategy.md", "AnoCrypto-C external SDK direction. OpenSSL remains current.\n")
    write_file(root, "docs/enterprise/anocrypto-integration-plan.md", "External AnoCrypto-C SDK adapter. KCMVP not validated.\n")
    write_file(root, "docs/enterprise/kcmvp-preparation.md", "KCMVP target planning only.\n")
    write_file(root, "docs/enterprise/private-alpha-evidence.md", "Private alpha evidence pending.\n")
    write_file(root, "include/anopki/enterprise/anocrypto_backend.hpp", "// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise\n")
    write_file(root, "src/backends/anocrypto_c/anocrypto_backend.cpp", "// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise\n")
    write_file(root, "enterprise/tests/anocrypto_sdk_integration_test.cpp", "// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise\n")
    write_file(root, "enterprise/tests/edition_metadata_test.cpp", "// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise\n")
    write_file(root, "include/anopki/enterprise/edition.hpp", "// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise\n")
    write_file(root, "service/internal/enterprise/edition.go", "// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise\n")
    write_file(root, "src/core/issue.cpp", "// SPDX-License-Identifier: MPL-2.0\n")
    write_file(root, "include/anopki/crypto/runtime.hpp", "// SPDX-License-Identifier: MPL-2.0\n")
    for rel in (
        "src/backends/openssl/openssl_backend.hpp",
        "src/backends/openssl/openssl_backend.cpp",
        "src/backends/openssl/csr.cpp",
        "src/backends/openssl/issue.cpp",
        "src/backends/openssl/crl.cpp",
        "src/backends/openssl/ocsp.cpp",
    ):
        write_file(root, rel, "// SPDX-License-Identifier: MPL-2.0\n")


def assert_fails(root: Path, expected: str) -> None:
    validator = load_validator()
    try:
        validator.validate(root)
    except SystemExit as exc:
        assert expected in str(exc), str(exc)
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
        root = Path(tmp); write_clean_enterprise_root(root)
        (root / "ENTERPRISE-LICENSE-NOTICE.md").unlink()
        assert_fails(root, "missing required overlay files")


def test_rejects_agpl_root_license() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        write_file(root, "LICENSE", "GNU AFFERO GENERAL PUBLIC LICENSE\n")
        assert_fails(root, "must not contain AGPL terms")


def test_rejects_missing_mpl_text() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        write_file(root, "LICENSES/MPL-2.0.txt", "incomplete\n")
        assert_fails(root, "MPL-2.0 license text missing required markers")


def test_finds_enterprise_docs_outside_private_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        write_file(root, "docs/enterprise-plan.md", "LicenseRef-AnoPKI-Enterprise\n")
        assert_fails(root, "Enterprise docs outside private paths")


def test_finds_enterprise_code_outside_private_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        write_file(root, "src/core/private_overlay.cpp", "// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise\n")
        assert_fails(root, "Enterprise-only code outside private paths")


def test_rejects_mpl_spdx_on_enterprise_adapter() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        write_file(root, "src/backends/anocrypto_c/anocrypto_backend.cpp", "// SPDX-License-Identifier: MPL-2.0\n")
        assert_fails(root, "Enterprise-only source files missing proprietary SPDX header")


def test_rejects_embedded_anocrypto_source() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        write_file(root, "enterprise/anocrypto/src/anocrypto.c", "/* SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise */\n")
        assert_fails(root, "embedded AnoCrypto implementation/header paths are prohibited")


def test_rejects_copied_anocrypto_header() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        write_file(root, "enterprise/anocrypto/include/anocrypto/anocrypto.h", "/* copied */\n")
        assert_fails(root, "embedded AnoCrypto implementation/header paths are prohibited")


def test_rejects_embedded_algorithm_marker_in_adapter() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        write_file(root, "src/backends/anocrypto_c/anocrypto_backend.cpp", "// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise\nvoid sha256_transform();\n")
        assert_fails(root, "adapter contains embedded cryptographic implementation markers")


def test_requires_external_sdk_cmake_contract() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        cmake = root / "CMakeLists.txt"
        cmake.write_text(cmake.read_text(encoding="utf-8").replace("AnoCryptoC::AnoCryptoC", ""), encoding="utf-8")
        assert_fails(root, "missing external AnoCrypto-C integration markers")


def test_rejects_legacy_embedded_cmake_target() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        cmake = root / "CMakeLists.txt"
        cmake.write_text(cmake.read_text(encoding="utf-8") + "anocrypto_c99\n", encoding="utf-8")
        assert_fails(root, "still builds an embedded AnoCrypto implementation")


def test_requires_distribution_blocking_placeholder() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        write_file(root, "LICENSES/LicenseRef-AnoPKI-Enterprise.txt", "LicenseRef-AnoPKI-Enterprise\n")
        assert_fails(root, "Enterprise license placeholder missing required restrictions")


def test_finds_premature_anocrypto_claims() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        write_file(root, "docs/reference/bad.md", "AnoCrypto-C is the default production backend.\n")
        assert_fails(root, "unsupported AnoCrypto production claims")


def test_finds_kcmvp_certification_claims() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        write_file(root, "docs/enterprise/bad.md", "AnoCrypto-C is KCMVP certified.\n")
        assert_fails(root, "unsupported KCMVP certification claims")


def test_finds_private_key_material() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        write_file(root, "enterprise/key.pem", "-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----\n")  # secret-scan: allow
        assert_fails(root, "private key material or obvious secrets")


def test_finds_generated_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        write_file(root, "build/generated.txt", "generated\n")
        assert_fails(root, "generated build/cache files")


def test_rejects_broad_anocrypto_ci_selection() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        ci = root / ".github/workflows/ci.yml"
        ci.write_text(ci.read_text(encoding="utf-8") + "ctest --test-dir build-enterprise -R anocrypto\n", encoding="utf-8")
        assert_fails(root, "must not use broad AnoCrypto regex selection")



def test_rejects_direct_openssl_include_in_shared_core() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        write_file(root, "src/core/issue.cpp", "// SPDX-License-Identifier: MPL-2.0\n#include <openssl/x509.h>\n")
        assert_fails(root, "direct OpenSSL includes")


def test_rejects_direct_openssl_link_from_enterprise_core() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); write_clean_enterprise_root(root)
        cmake = root / "CMakeLists.txt"
        cmake.write_text(
            cmake.read_text(encoding="utf-8")
            + "target_link_libraries(anopki_core PRIVATE OpenSSL::Crypto)\n",
            encoding="utf-8",
        )
        assert_fails(root, "anopki_core must not link OpenSSL::Crypto directly")

def main() -> None:
    test_clean_enterprise_root_passes()
    test_requires_enterprise_license_notice()
    test_rejects_agpl_root_license()
    test_rejects_missing_mpl_text()
    test_finds_enterprise_docs_outside_private_paths()
    test_finds_enterprise_code_outside_private_paths()
    test_rejects_mpl_spdx_on_enterprise_adapter()
    test_rejects_embedded_anocrypto_source()
    test_rejects_copied_anocrypto_header()
    test_rejects_embedded_algorithm_marker_in_adapter()
    test_requires_external_sdk_cmake_contract()
    test_rejects_legacy_embedded_cmake_target()
    test_requires_distribution_blocking_placeholder()
    test_finds_premature_anocrypto_claims()
    test_finds_kcmvp_certification_claims()
    test_finds_private_key_material()
    test_finds_generated_files()
    test_rejects_broad_anocrypto_ci_selection()
    test_rejects_direct_openssl_include_in_shared_core()
    test_rejects_direct_openssl_link_from_enterprise_core()
    print("enterprise boundary validator tests ok")


if __name__ == "__main__":
    main()
