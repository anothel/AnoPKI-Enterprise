#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch


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


def test_elf_artifacts(reader: Path, clean: Path, openssl: Path) -> None:
    VALIDATOR.inspect_artifact("clean ELF fixture", clean, reader)
    command = VALIDATOR.dependency_command(reader, openssl)
    dynamic = subprocess.check_output(command, text=True)
    assert any("(NEEDED)" in line and "libcrypto" in line for line in dynamic.splitlines()), dynamic
    expect_failure(lambda: VALIDATOR.inspect_artifact("OpenSSL ELF fixture", openssl, reader), "forbidden OpenSSL")
    expect_failure(lambda: VALIDATOR.inspect_artifact("unsupported reader", clean, Path("ld")), "unsupported dependency reader")
    with tempfile.TemporaryDirectory() as dirname:
        missing_reader = Path(dirname) / "readelf"
        expect_failure(
            lambda: VALIDATOR.inspect_artifact("missing reader", clean, missing_reader),
            "could not execute dependency reader",
        )
    for returncode, stdout, stderr, error in (
        (1, "", "unreadable input", "dependency inspection failed"),
        (0, "", "", "invalid ELF dependency reader output"),
        (0, "There is no dynamic section in this file.", "malformed ELF", "invalid ELF dependency reader output"),
    ):
        with patch.object(VALIDATOR.subprocess, "run", return_value=subprocess.CompletedProcess(
            command, returncode, stdout, stderr
        )):
            expect_failure(lambda: VALIDATOR.inspect_artifact("invalid scan", clean, reader), error)
    print("ELF controls passed: clean artifact accepted, real OpenSSL import and invalid readers rejected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--elf-reader", type=Path)
    parser.add_argument("--clean-artifact", type=Path)
    parser.add_argument("--openssl-artifact", type=Path)
    args = parser.parse_args()
    elf_inputs = (args.elf_reader, args.clean_artifact, args.openssl_artifact)
    if any(elf_inputs) and not all(elf_inputs):
        parser.error("ELF checks require a reader and both artifacts")
    test_clean_source_passes()
    test_openssl_and_generic_sha1_fail()
    test_binary_dependency_name_fails()
    if all(elf_inputs):
        test_elf_artifacts(*elf_inputs)
    print("AnoCrypto boundary validator tests passed")
