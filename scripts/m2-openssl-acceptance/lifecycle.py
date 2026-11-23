# SPDX-License-Identifier: MPL-2.0
"""Exercise the real service with disposable keys and verify its signed output."""

import hashlib
import http.client
import json
import os
import re
import secrets
import signal
import socket
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

CA_NAME = "M2 disposable CA"
DNS = "m2-acceptance.example.test"
IP = "127.0.0.1"
DISTRIBUTION_POINT = f"http://{DNS}/issuer.crl"
CA_ARGS = ("-no-CApath", "-no-CAstore", "-CAfile", "ca.pem")
CA_EXTENSIONS = (
    "-addext", "basicConstraints=critical,CA:TRUE",
    "-addext", "keyUsage=critical,keyCertSign,cRLSign,digitalSignature",
)
CASES = (
    "service_backend", "api_key_scopes", "csr_and_approval", "issue_and_verify",
    "issue_retry", "ocsp_good", "revoke", "crl_der", "ocsp_revoked_unknown",
    "malformed_ocsp", "audit_and_outbox",
)


class CheckFailed(RuntimeError):
    """A failed assertion with a message safe for public evidence."""


def require(condition, message):
    if not condition:
        raise CheckFailed(message)


def timestamp(hours):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def owns_listener(pid, port):
    # /proc/net/tcp lists the network namespace. Match its listener inode to
    # this child's descriptors before sending any HTTP request or credential.
    proc = Path("/proc") / str(pid)
    endpoint = f"0100007F:{port:04X}"
    inodes = set()
    for line in (proc / "net" / "tcp").read_text().splitlines()[1:]:
        columns = line.split()
        if len(columns) > 9 and columns[1] == endpoint and columns[3] == "0A":
            inodes.add(f"socket:[{columns[9]}]")
    for fd in (proc / "fd").iterdir():
        try:
            if os.readlink(fd) in inodes:
                return True
        except FileNotFoundError:
            continue
    return False


@contextmanager
def running_service(work, service, core, operator, evidence):
    with socket.socket() as sock:
        sock.bind((IP, 0))
        port = sock.getsockname()[1]
    env = {
        "LC_ALL": "C", "HOME": str(work), "TMPDIR": str(work),
        "ANOPKI_ADDR": f"{IP}:{port}", "ANOPKI_DB_DRIVER": "sqlite",
        "ANOPKI_DB_DSN": "file:lifecycle.db?_txlock=immediate&_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)",
        "ANOPKI_CORE_BIN": str(core), "ANOPKI_AUTH_MODE": "api_key",
        "ANOPKI_BOOTSTRAP_API_KEY": operator, "ANOPKI_API_KEY_PEPPER": secrets.token_hex(32),
        "ANOPKI_BOOTSTRAP_API_KEY_ACTOR": "m2-operator", "ANOPKI_OUTBOX_ENABLED": "true",
        "ANOPKI_OUTBOX_INTERVAL": "1s", "ANOPKI_EXPIRATION_SCAN_ENABLED": "false",
        "ANOPKI_ACME_BOOTSTRAP_DEFAULTS": "false",
    }
    record = {"argv": ["<scratch>/anopki-service"], "cwd": "<scratch>",
              "env": {k: v.replace(str(work), "<scratch>")
                      for k, v in env.items() if k not in {
                          "ANOPKI_BOOTSTRAP_API_KEY", "ANOPKI_API_KEY_PEPPER",
                      }}}
    evidence["commands"].append(record)
    process = subprocess.Popen([service], cwd=work, env=env, start_new_session=True,
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)

    def request(method, route, code, token=None, payload=None, content_type="application/json"):
        require(process.poll() is None, "service exited before request")
        connection = http.client.HTTPConnection(IP, port, timeout=8)
        headers = {"Content-Type": content_type}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        body = payload if isinstance(payload, bytes) else (
            json.dumps(payload).encode() if payload is not None else None
        )
        try:
            connection.request(method, route, body=body, headers=headers)
            response = connection.getresponse()
            data = response.read(4 * 1024 * 1024 + 1)
        finally:
            connection.close()
        evidence.setdefault("http", []).append({"method": method, "path": route, "status": response.status})
        require(len(data) <= 4 * 1024 * 1024, "response exceeds evidence harness limit")
        require(response.status == code, f"{method} returned HTTP {response.status}, expected {code}")
        return response.getheader("Content-Type"), data

    try:
        deadline = time.monotonic() + 15
        while not owns_listener(process.pid, port):
            require(process.poll() is None, "service exited before binding its loopback socket")
            require(time.monotonic() < deadline, "service did not bind its loopback socket")
            time.sleep(0.1)
        request("GET", "/readyz", 200)
        yield request
    finally:
        # The executable is a direct child. Stop and reap it before deleting its database and issuer key.
        if process.poll() is None:
            process.terminate()
        try:
            record["exit"] = process.wait(timeout=20)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                evidence["service_cleanup"] = "PASS" if record["exit"] == 0 else "FAIL"
            else:
                evidence["service_cleanup"] = "FAIL"
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            record["exit"] = process.wait(timeout=5)
            evidence["service_cleanup"] = "FAIL"


def verify_certificate(ssl, serial, csr_public_key):
    ssl("verify", *CA_ARGS, "-purpose", "sslserver", "-verify_hostname", DNS,
        "-verify_ip", IP, "leaf.pem")
    require(ssl("x509", "-in", "leaf.pem", "-pubkey", "-noout")[0] == csr_public_key,
            "issued certificate public key differs from CSR")
    extensions = ssl("x509", "-in", "leaf.pem", "-noout",
                     "-ext", "subjectAltName,keyUsage,extendedKeyUsage,basicConstraints,authorityKeyIdentifier")[0]
    require(all(value in extensions for value in (
        "Digital Signature", "TLS Web Server Authentication", "CA:FALSE", "Authority Key Identifier",
    )), "issued certificate profile extensions mismatch")
    san = re.search(r"Subject Alternative Name:[^\n]*\n\s*([^\n]+)", extensions)
    require(san and set(san[1].strip().split(", ")) == {f"DNS:{DNS}", f"IP Address:{IP}"},
            "issued certificate SAN set mismatch")
    serial_hex = ssl("x509", "-in", "leaf.pem", "-noout", "-serial")[0].strip().removeprefix("serial=")
    require(int(serial_hex, 16) == serial, "certificate serial mismatch")
    issuer = ssl("x509", "-in", "leaf.pem", "-noout", "-issuer", "-nameopt", "RFC2253")[0].strip()
    require(issuer == f"issuer=CN={CA_NAME}", "certificate issuer mismatch")


def verify_crl(work, ssl, publication, serial):
    ssl("crl", "-in", "crl.pem", "-outform", "DER", "-out", "crl.der")
    stdout, stderr = ssl("crl", "-in", "crl.der", "-inform", "DER", "-verify",
                         *CA_ARGS, "-noout", "-text", "-crlnumber")
    require("verify OK" in stderr, "CRL signature verification failed")
    number = re.search(r"^crlNumber=(0x[0-9A-Fa-f]+)$", stdout, re.M)
    require(number and int(number[1], 16) == publication["crl_number"] == 1, "CRL number mismatch")
    serials = [int(value, 16) for value in re.findall(r"Serial Number: ([0-9A-Fa-f]+)", stdout)]
    require(serials == [serial] and "Key Compromise" in stdout, "CRL revocation entry mismatch")
    issuer = ssl("crl", "-in", "crl.der", "-inform", "DER", "-issuer", "-nameopt", "RFC2253", "-noout")[0]
    require(issuer.strip() == f"issuer=CN={CA_NAME}", "CRL issuer name mismatch")
    dates = re.search(r"Last Update: ([^\n]+)\n\s*Next Update: ([^\n]+)", stdout)
    now = datetime.now(timezone.utc)
    require(dates and parsedate_to_datetime(dates[1]) <= now < parsedate_to_datetime(dates[2]),
            "CRL validity window mismatch")
    _, verify_error = ssl("verify", *CA_ARGS, "-CRLfile", "crl.pem", "-crl_check",
                          "leaf.pem", expected=2)
    require("error 23 at 0 depth lookup: certificate revoked" in verify_error,
            "verification did not reject revoked leaf at depth zero")
    return hashlib.sha256((work / "crl.der").read_bytes()).hexdigest()


def check_ocsp(work, ssl, request, serial, status):
    serial_hex = f"0x{serial:X}"
    ssl("ocsp", "-issuer", "ca.pem", "-serial", serial_hex, "-nonce", "-reqout", "request.der")
    content_type, response = request("POST", "/ocsp", 200, payload=(work / "request.der").read_bytes(),
                                     content_type="application/ocsp-request")
    require(content_type == "application/ocsp-response", "unexpected OCSP content type")
    (work / "response.der").write_bytes(response)
    # Verify the response signature and nonce against the exact request. The second
    # invocation uses the same issuer and serial to check OpenSSL's CertID lookup.
    args = ("ocsp", "-respin", "response.der", *CA_ARGS)
    _, stderr = ssl(*args, "-reqin", "request.der")
    require("Response verify OK" in stderr and "Nonce" not in stderr, "OCSP signature or nonce mismatch")
    stdout, stderr = ssl(*args, "-issuer", "ca.pem", "-serial", serial_hex, "-no_nonce",
                         "-status_age", "3600", "-validity_period", "60")
    require(f"{serial_hex}: {status}" in stdout.splitlines() and "WARNING" not in stdout + stderr,
            "OCSP CertID, status or time mismatch")
    dates = re.search(r"This Update: ([^\n]+)\n\s*Next Update: ([^\n]+)", stdout)
    now = datetime.now(timezone.utc)
    require(dates and parsedate_to_datetime(dates[1]) <= now < parsedate_to_datetime(dates[2]),
            "OCSP response validity window mismatch")
    if status == "revoked":
        require("Reason: keyCompromise" in stdout and "Revocation Time:" in stdout,
                "OCSP revocation detail mismatch")
    return hashlib.sha256(response).hexdigest()


def exercise(work, core, service, evidence, run, verify_backend):
    def ssl(*args, expected=0):
        return run("openssl", *args, cwd=work, expected=expected)

    def started(case):
        evidence["cases"][case] = "FAIL"

    def passed(case):
        evidence["cases"][case] = "PASS"

    ssl("req", "-new", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1",
        "-noenc", "-days", "4", "-subj", f"/CN={CA_NAME}", *CA_EXTENSIONS,
        "-keyout", "ca.key", "-out", "ca.pem")
    ssl("req", "-new", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1",
        "-noenc", "-subj", f"/CN={DNS}", "-addext", f"subjectAltName=DNS:{DNS},IP:{IP}",
        "-keyout", "leaf.key", "-out", "leaf.csr")
    signature_check = "".join(ssl("req", "-in", "leaf.csr", "-verify", "-noout"))
    require("self-signature verify OK" in signature_check, "CSR self-signature verification failed")
    csr_public_key = ssl("req", "-in", "leaf.csr", "-pubkey", "-noout")[0]

    operator = secrets.token_hex(32)
    started("service_backend")
    with running_service(work, service, core, operator, evidence) as request:
        def api(method, route, code, token=operator, payload=None):
            result = json.loads(request(method, route, code, token, payload)[1])
            if isinstance(result, dict) and "id" in result:
                require(re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", result["id"]),
                        "resource ID is not a canonical UUID")
            return result

        version = api("GET", "/version", 200, None)
        require(version["commit"] == evidence["commit"], "service commit mismatch")
        require(verify_backend(version["backend"]) == evidence["backend"], "service and CLI backend metadata differ")
        passed("service_backend")

        started("api_key_scopes")
        read_key = api("POST", "/api-keys", 201, payload={
            "name": "m2-read", "actor": "m2-reader", "scopes": ["read"],
        })
        write_key = api("POST", "/api-keys", 201, payload={
            "name": "m2-write", "actor": "m2-writer", "scopes": ["write"],
        })
        reader, writer = read_key["token"], write_key["token"]
        api("GET", "/certificates", 401, None)
        api("GET", "/certificates", 401, secrets.token_hex(32))
        api("GET", "/certificates", 200, reader)
        api("POST", "/certificates", 403, reader, {"enrollment_id": "unavailable"})
        api("GET", "/audit-events", 403, writer)
        passed("api_key_scopes")

        started("csr_and_approval")
        issuer = api("POST", "/issuers", 201, payload={
            "name": "m2-ca", "kind": "root_ca", "certificate_pem": (work / "ca.pem").read_text(),
            "key_ref": str(work / "ca.key"), "crl_distribution_points": [DISTRIBUTION_POINT],
        })
        identity = api("POST", "/identities", 201, writer, {
            "type": "machine", "name": DNS, "allowed_dns_names": [DNS], "allowed_ip_addresses": [IP],
        })
        profile = api("POST", "/certificate-profiles", 201, payload={
            "name": "m2-server", "issuer_id": issuer["id"], "validity_period_seconds": 86400,
            "allowed_dns_patterns": [DNS], "allowed_ip_ranges": [f"{IP}/32"],
            "key_usage": {"critical": True, "values": ["digital_signature"]},
            "extended_key_usage": {"values": ["server_auth"]},
            "basic_constraints": {"critical": True, "ca": False},
            "subject_key_identifier": True, "authority_key_identifier": True,
        })
        enrollment_payload = {
            "identity_id": identity["id"], "issuer_id": issuer["id"], "profile_id": profile["id"],
            "csr_pem": (work / "leaf.csr").read_text(), "requested_subject": f"CN={DNS}",
            "requested_dns_names": [DNS], "requested_ip_addresses": [IP],
            "requested_not_after": timestamp(12),
        }
        api("POST", "/enrollments", 422, writer, enrollment_payload | {"csr_pem": "invalid CSR"})
        api("POST", "/enrollments", 400, writer,
            enrollment_payload | {"requested_dns_names": ["wrong.example.test"]})
        enrollment = api("POST", "/enrollments", 201, writer, enrollment_payload)
        enrollment_route = f"/enrollments/{enrollment['id']}"
        approval = f"{enrollment_route}/approve"
        issue_payload = {"enrollment_id": enrollment["id"]}
        require(enrollment["status"] == "pending", "enrollment was not pending")
        api("POST", "/certificates", 409, writer, issue_payload)
        api("POST", approval, 403, reader)
        require(api("GET", "/certificates", 200, reader) == [], "negative requests created a certificate")
        require(len(api("GET", "/enrollments", 200, reader)) == 1, "invalid requests created enrollments")
        approved = api("POST", approval, 200)
        require(approved["status"] == "approved" and approved["approved_by"] == "m2-operator",
                "approval state or actor mismatch")
        api("POST", approval, 409)
        passed("csr_and_approval")

        started("issue_and_verify")
        certificate = api("POST", "/certificates", 201, writer, issue_payload)
        certificate_route = f"/certificates/{certificate['id']}"
        require(certificate["status"] == "valid" and certificate["issuer_id"] == issuer["id"]
                and certificate["profile_id"] == profile["id"] and certificate["enrollment_id"] == enrollment["id"],
                "issued certificate state or references mismatch")
        require(api("GET", enrollment_route, 200, reader)["status"] == "issued",
                "enrollment did not become issued")
        (work / "leaf.pem").write_text(certificate["certificate_pem"])
        serial = int(certificate["serial_number"], 10)
        verify_certificate(ssl, serial, csr_public_key)
        dates = dict(line.split("=", 1) for line in
                     ssl("x509", "-in", "leaf.pem", "-noout", "-startdate", "-enddate")[0].splitlines())
        not_before = parsedate_to_datetime(dates["notBefore"])
        not_after = parsedate_to_datetime(dates["notAfter"])
        require(not_before == datetime.fromisoformat(certificate["not_before"])
                and not_after == datetime.fromisoformat(certificate["not_after"])
                == datetime.fromisoformat(enrollment_payload["requested_not_after"]),
                "certificate validity differs from issued API metadata or enrollment")
        ssl("x509", "-in", "leaf.pem", "-outform", "DER", "-out", "leaf.der")
        ssl("x509", "-in", "ca.pem", "-outform", "DER", "-out", "ca.der")
        evidence["signed_artifacts"] = {
            "serial_decimal": str(serial), "issuer": f"CN={CA_NAME}", "issuer_id": issuer["id"],
            "profile_id": profile["id"], "ca_der_sha256": hashlib.sha256((work / "ca.der").read_bytes()).hexdigest(),
            "leaf_der_sha256": hashlib.sha256((work / "leaf.der").read_bytes()).hexdigest(),
        }
        passed("issue_and_verify")

        started("issue_retry")
        # Replay after finalization with the disposable signing key unavailable.
        ca_key, hidden_key = work / "ca.key", work / "ca.key.offline"
        ca_key.rename(hidden_key)
        try:
            replay = api("POST", "/certificates", 201, writer, issue_payload)
        finally:
            hidden_key.rename(ca_key)
        require(all(replay[k] == certificate[k] for k in ("id", "serial_number", "certificate_pem")),
                "issuance replay changed the signed result")
        require(len(api("GET", "/certificates", 200, reader)) == 1, "duplicate certificate after retry")
        passed("issue_retry")

        started("ocsp_good")
        artifacts = evidence["signed_artifacts"]
        artifacts["ocsp_good_der_sha256"] = check_ocsp(work, ssl, request, serial, "good")
        passed("ocsp_good")

        started("revoke")
        revoke = f"{certificate_route}/revoke"
        reason = {"reason": "key_compromise"}
        api("POST", revoke, 403, reader, reason)
        require(api("GET", certificate_route, 200, reader)["status"] == "valid", "read key revoked leaf")
        require(api("POST", revoke, 200, writer, reason)["status"] == "revoked", "revocation did not persist")
        require(api("GET", certificate_route, 200, reader)["status"] == "revoked", "revoked state not visible")
        passed("revoke")

        started("crl_der")
        publication = api("POST", "/crls", 201, writer, {
            "issuer_id": issuer["id"], "distribution_point": DISTRIBUTION_POINT, "next_update": timestamp(24),
        })
        content_type, published = request("GET", f"/issuers/{issuer['id']}/crl", 200)
        require(content_type == "application/x-pem-file" and published == publication["crl_pem"].encode()
                and publication["issuer_id"] == issuer["id"]
                and publication["distribution_point"] == DISTRIBUTION_POINT, "latest CRL does not match publication")
        (work / "crl.pem").write_bytes(published)
        artifacts["crl_der_sha256"] = verify_crl(work, ssl, publication, serial)
        artifacts["crl_number"] = publication["crl_number"]
        passed("crl_der")

        started("ocsp_revoked_unknown")
        artifacts["ocsp_revoked_der_sha256"] = check_ocsp(work, ssl, request, serial, "revoked")
        unknown = 1 if serial != 1 else 2
        artifacts["ocsp_unknown_der_sha256"] = check_ocsp(work, ssl, request, unknown, "unknown")
        artifacts["ocsp_unknown_serial_decimal"] = str(unknown)
        passed("ocsp_revoked_unknown")

        started("malformed_ocsp")
        request("POST", "/ocsp", 415, payload=b"not DER")
        request("POST", "/ocsp", 400, payload=b"not DER", content_type="application/ocsp-request")
        passed("malformed_ocsp")

        started("audit_and_outbox")
        events = api("GET", "/audit-events", 200)
        serialized = json.dumps(events)
        require(not any(value in serialized for value in (
            operator, reader, writer, "PRIVATE KEY-----", str(work / "ca.key"),
        )), "audit contains test credentials or issuer key path")
        for action, resource, actor in (
            ("enrollment.created", enrollment["id"], "m2-writer"),
            ("enrollment.approved", enrollment["id"], "m2-operator"),
            ("certificate.issued", certificate["id"], "m2-writer"),
            ("certificate.revoked", certificate["id"], "m2-writer"),
            ("crl.published", publication["id"], "m2-writer"),
        ):
            matching = [event for event in events if event["action"] == action and event["resource_id"] == resource]
            require(len(matching) == 1 and matching[0]["actor"] == actor, "audit actor or event count mismatch")
            require(json.loads(matching[0]["metadata_json"])["auth_method"] == "api_key",
                    "audit authentication method mismatch")
        require(sum(event["action"] == "ocsp.requested" for event in events) == 3, "OCSP success audit count mismatch")
        require(api("GET", "/audit-events/integrity", 200)["valid"] is True, "audit chain failed integrity check")
        deadline = time.monotonic() + 15
        while True:
            messages = api("GET", "/outbox/messages?type=certificate.revoked", 200)
            revoked = [m for m in messages if json.loads(m["payload_json"])["certificate_id"] == certificate["id"]]
            require(len(revoked) == 1, "revocation outbox row count mismatch")
            if revoked[0]["status"] == "completed":
                break
            require(time.monotonic() < deadline, "revocation outbox did not complete")
            time.sleep(0.2)
        passed("audit_and_outbox")

    require(evidence["service_cleanup"] == "PASS", "service did not exit cleanly")
