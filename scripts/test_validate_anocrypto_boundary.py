#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate-anocrypto-boundary.py")
SPEC = importlib.util.spec_from_file_location("validate_anocrypto_boundary", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def fixture(root: Path) -> Path:
    source = root / "src/backends/anocrypto_c/pki.cpp"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("\n".join(VALIDATOR.REQUIRED_TOKENS), encoding="utf-8")
    return source


def expect_failure(action, fragment: str) -> None:
    try:
        action()
    except RuntimeError as error:
        assert fragment in str(error), str(error)
        return
    raise AssertionError(f"expected failure containing {fragment!r}")


def test_clean_source_passes() -> None:
    with tempfile.TemporaryDirectory() as dirname:
        root = Path(dirname)
        fixture(root)
        VALIDATOR.validate_sources(root)


def test_openssl_and_generic_sha1_fail() -> None:
    with tempfile.TemporaryDirectory() as dirname:
        root = Path(dirname)
        source = fixture(root)
        source.write_text(source.read_text(encoding="utf-8") + '\n#include <openssl/evp.h>\n', encoding="utf-8")
        expect_failure(lambda: VALIDATOR.validate_sources(root), "OpenSSL include")
        source = fixture(root)
        source.write_text(source.read_text(encoding="utf-8") + "\nano_crypto_hash_sha1();\n", encoding="utf-8")
        expect_failure(lambda: VALIDATOR.validate_sources(root), "generic SHA-1")


def test_binary_dependency_name_fails() -> None:
    expect_failure(
        lambda: VALIDATOR.reject_forbidden("KERNEL32.dll libcrypto-3-x64.dll", "fixture"),
        "libcrypto",
    )
    expect_failure(
        lambda: VALIDATOR.reject_forbidden("KERNEL32.dll EVP_DigestSignInit", "fixture"),
        "OpenSSL symbol",
    )


if __name__ == "__main__":
    test_clean_source_passes()
    test_openssl_and_generic_sha1_fail()
    test_binary_dependency_name_fails()
    print("AnoCrypto boundary validator tests passed")
