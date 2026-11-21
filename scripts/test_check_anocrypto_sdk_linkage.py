#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Exercise the linkage checker with ELF artifacts and scanner failure controls."""

import argparse
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("check-anocrypto-sdk-linkage.py")
SPEC = importlib.util.spec_from_file_location("check_anocrypto_sdk_linkage", SCRIPT)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)

DEPENDENCIES = """
    linux-vdso.so.1 (0x1)
    libanocrypto_c.so.0 => /sdk/libanocrypto_c.so.0 (0x2)
    libc.so.6 => /usr/lib/libc.so.6 (0x3)
    /usr/lib/ld-linux-x86-64.so.2 (0x4)
"""


class LinkageChecks(unittest.TestCase):
    def test_accepts_exact_sdk_names_and_weak_import(self):
        CHECK.check_dependencies(DEPENDENCIES)
        CHECK.check_symbols("ano_crypto_ocsp_certid_sha1_digest@ANOCRYPTO_C_7 U\n__gmon_start__ w")

    def test_rejects_forbidden_imports(self):
        for symbol in ("OPENSSL_init_crypto", "EVP_MD_fetch@OPENSSL_3.0.0",
                       "X509_verify@@OPENSSL_3.0.0", "OCSP_REQUEST_new", "SSL_connect"):
            with self.subTest(symbol=symbol), self.assertRaisesRegex(ValueError, "OpenSSL import"):
                CHECK.check_symbols(f"ano_crypto_ocsp_certid_sha1_digest@ANOCRYPTO_C_7 U\n{symbol} U")

    def test_rejects_forbidden_dependencies(self):
        for row in ("libcrypto.so.3 => /usr/lib/libcrypto.so.3 (0x5)",
                    "libssl.so.3 => /usr/lib/libssl.so.3 (0x5)",
                    "other.so => /usr/lib/libcrypto.so.3 (0x5)"):
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, "OpenSSL dependency"):
                CHECK.check_dependencies(DEPENDENCIES + row)

    def test_rejects_unresolved_or_malformed_deps_and_missing_sdk(self):
        for output, reason in (
            (DEPENDENCIES + "libbad.so => not found", "unresolved runtime dependency"),
            (DEPENDENCIES + "ldd said success", "malformed ldd output"),
            (DEPENDENCIES + "libbad.so => bogus (0x5)", "malformed ldd dependency path"),
            ("linux-vdso.so.1 (0x1)", "did not resolve"),
            ("", "did not resolve"),
        ):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, reason):
                CHECK.check_dependencies(output)

    def test_rejects_empty_malformed_or_partial_symbol_scan(self):
        for output, reason in (
            (" ", "no undefined symbol records"),
            ("unknown output", "malformed nm output"),
            ("foo U\nbar T", "malformed nm output"),
            ("foo U garbage", "malformed nm output"),
        ):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, reason):
                CHECK.check_symbols(output)

    def test_rejects_missing_reader_and_timeout(self):
        for tool in ("ldd", "nm"):
            for error in (FileNotFoundError("missing"), subprocess.TimeoutExpired(tool, 30)):
                with self.subTest(tool=tool, error=error), patch.object(CHECK.subprocess, "run", side_effect=error):
                    with self.assertRaisesRegex(ValueError, f"{tool} inspection failed"):
                        CHECK.inspect(tool, "/fixture")

    def test_rejects_failed_or_empty_reader_even_when_partial_output_looks_valid(self):
        for tool, output in (("ldd", DEPENDENCIES), ("nm", "foo U")):
            for status, stdout, stderr in ((1, output, ""), (0, "", ""), (0, output, "warning")):
                result = subprocess.CompletedProcess([tool], status, stdout, stderr)
                with self.subTest(tool=tool, result=result), patch.object(CHECK.subprocess, "run", return_value=result):
                    with self.assertRaisesRegex(ValueError, f"{tool} inspection failed"):
                        CHECK.inspect(tool, "/fixture")

    def test_missing_artifact_fails(self):
        result = subprocess.run([sys.executable, str(SCRIPT), str(SCRIPT.with_suffix(".missing"))],
                                capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing Enterprise CLI", result.stderr)


def real_artifacts(clean, forbidden):
    # Existing parity fixture genuinely imports OpenSSL for the test oracle.
    subprocess.run([sys.executable, str(SCRIPT), clean], check=True)
    result = subprocess.run([sys.executable, str(SCRIPT), forbidden],
                            capture_output=True, text=True, check=False)
    if result.returncode == 0 or "forbidden OpenSSL dependency" not in result.stderr:
        raise RuntimeError(f"real OpenSSL dependency fixture was not rejected: {result.stderr}")
    undefined = CHECK.inspect("nm", "-u", "--format=posix", forbidden)
    try:
        CHECK.check_symbols(undefined)
    except ValueError as error:
        if "forbidden OpenSSL import" not in str(error):
            raise
    else:
        raise RuntimeError("real OpenSSL import fixture was not rejected")
    print("ELF controls passed: clean production CLI accepted, real OpenSSL dependency and imports rejected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean-artifact")
    parser.add_argument("--openssl-artifact")
    args = parser.parse_args()
    if (args.clean_artifact is None) != (args.openssl_artifact is None):
        parser.error("provide both ELF artifacts")
    tests = unittest.main(argv=[sys.argv[0]], exit=False)
    if not tests.result.wasSuccessful():
        raise SystemExit(1)
    if args.clean_artifact:
        real_artifacts(args.clean_artifact, args.openssl_artifact)
