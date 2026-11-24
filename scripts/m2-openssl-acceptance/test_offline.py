# SPDX-License-Identifier: MPL-2.0
"""Offline tests for profile rejection and the independent OCSP verifier."""

import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True

from accept import BACKEND, CAPABILITIES, verify_backend
from lifecycle import (
    CA_EXTENSIONS, CA_NAME, DNS, IP, CheckFailed, check_ocsp, verify_certificate, verify_crl,
)


class OfflineTests(unittest.TestCase):
    def test_rejects_fallback_and_other_profiles(self):
        info = {
            **BACKEND, "fallback_enabled": False, "backend_capabilities": sorted(CAPABILITIES),
            "backend_version": "OpenSSL 3.5.7", "backend_build_fingerprint": "sha256:" + "a" * 64,
        }
        self.assertEqual(verify_backend(info), info)
        for changes in (
            {"fallback_enabled": True},
            {"product_profile": "community-openssl"},
            {"product_profile": "enterprise-anocrypto-c"},
            {"backend_id": "anocrypto-c"},
            {"backend_capabilities": []},
        ):
            with self.subTest(changes=changes), self.assertRaises(CheckFailed):
                verify_backend(info | changes)

    @staticmethod
    def openssl(work, *args, expected=0):
        result = subprocess.run(["openssl", *args], cwd=work, capture_output=True, text=True,
                                env={"PATH": os.environ["PATH"], "LC_ALL": "C"}, timeout=10)
        if result.returncode != expected:
            raise CheckFailed("unexpected fixture OpenSSL exit status")
        return result.stdout, result.stderr

    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory(prefix="m2-offline-"))
        self.work = Path(directory)
        self.ssl("req", "-new", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1",
                 "-noenc", "-days", "4", "-subj", f"/CN={CA_NAME}", *CA_EXTENSIONS,
                 "-keyout", "ca.key", "-out", "ca.pem")

    def ssl(self, *args, expected=0):
        return self.openssl(self.work, *args, expected=expected)

    def test_certificate_and_crl(self):
        ssl, work = self.ssl, self.work
        ssl("req", "-new", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-noenc",
            "-subj", f"/CN={DNS}", "-keyout", "leaf.key", "-out", "leaf.csr")
        (work / "extensions").write_text(
            f"subjectAltName=DNS:{DNS},IP:{IP}\nkeyUsage=digitalSignature\n"
            "extendedKeyUsage=serverAuth\nbasicConstraints=CA:FALSE\nauthorityKeyIdentifier=keyid\n"
        )
        ssl("x509", "-req", "-in", "leaf.csr", "-CA", "ca.pem", "-CAkey", "ca.key", "-set_serial",
            "0x13", "-extfile", "extensions", "-days", "1", "-out", "leaf.pem")
        signature_check = "".join(ssl("req", "-in", "leaf.csr", "-verify", "-noout"))
        self.assertIn("self-signature verify OK", signature_check)
        public_key = ssl("req", "-in", "leaf.csr", "-pubkey", "-noout")[0]
        verify_certificate(ssl, 19, public_key)

        (work / "ca.cnf").write_text(
            "[ca]\ndefault_ca=fixture\n[fixture]\ndatabase=index\ncrlnumber=number\n"
            "certificate=ca.pem\nprivate_key=ca.key\ndefault_md=sha256\ndefault_crl_days=1\n"
        )
        (work / "index").touch()
        (work / "number").write_text("01\n")
        ssl("ca", "-config", "ca.cnf", "-revoke", "leaf.pem", "-crl_reason", "keyCompromise", "-batch")
        ssl("ca", "-config", "ca.cnf", "-gencrl", "-out", "crl.pem")
        self.assertRegex(verify_crl(work, ssl, {"crl_number": 1}, 19), r"^[0-9a-f]{64}$")
        with self.assertRaises(CheckFailed):
            verify_crl(work, ssl, {"crl_number": 1}, 20)

    def test_signed_ocsp_nonce_status_and_serial(self):
        ssl, work = self.ssl, self.work
        now = datetime.now(timezone.utc)
        expiry = (now + timedelta(days=1)).strftime("%y%m%d%H%M%SZ")
        revocation = now.strftime("%y%m%d%H%M%SZ") + ",keyCompromise"
        (work / "index").write_text(
            f"V\t{expiry}\t\t01\tunknown\t/CN=good\n"
            f"R\t{expiry}\t{revocation}\t02\tunknown\t/CN=revoked\n"
        )

        def respond(payload):
            (work / "in.der").write_bytes(payload)
            ssl("ocsp", "-index", "index", "-rsigner", "ca.pem", "-rkey", "ca.key",
                "-CA", "ca.pem", "-reqin", "in.der", "-respout", "out.der", "-nmin", "60")
            return "application/ocsp-response", (work / "out.der").read_bytes()

        def request(_method, _route, _status, *, payload, content_type):
            self.assertEqual(content_type, "application/ocsp-request")
            return respond(payload)

        for serial, status in ((1, "good"), (2, "revoked"), (3, "unknown")):
            with self.subTest(status=status):
                self.assertRegex(check_ocsp(work, ssl, request, serial, status), r"^[0-9a-f]{64}$")

        with self.assertRaises(CheckFailed):
            check_ocsp(work, ssl, request, 2, "good")

        ssl("ocsp", "-issuer", "ca.pem", "-serial", "0x02", "-nonce", "-reqout", "other.der")

        def wrong_request(_method, _route, _status, **_kwargs):
            return respond((work / "other.der").read_bytes())

        with self.assertRaises(CheckFailed):
            check_ocsp(work, ssl, wrong_request, 1, "good")


if __name__ == "__main__":
    unittest.main()
