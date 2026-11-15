#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Qualify Enterprise application-node PostgreSQL lease recovery.

Adapted from frozen Community 49142ff50f5b37ba142d18cf61b60d8b287bdb49.
This does not qualify database-primary failover or live cryptographic signing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / ".tmp" / "postgres-multi-node-failover-evidence"
MINIMUM_GO_VERSION = (1, 26, 11)
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
PACKAGE = "github.com/anothel/anopki/service/internal/lifecycle"
LOG_NAME = "postgres-multi-node-failover-test.log"
DSN_ENV = "ANOPKI_POSTGRES_FAILOVER_DSN"

TESTS = (
    "TestPostgresMultiNodeIssuanceFailoverIntegration",
    "TestPostgresMultiNodeCRLFailoverIntegration",
    "TestPostgresMultiNodeOutboxTrafficShiftIntegration",
)

EXPECTED_CHECKS = (
    "independent-postgres-node-connections",
    "issuance-active-lease-not-stolen",
    "issuance-expired-lease-takeover",
    "issuance-stale-writer-cas-rejected",
    "issuance-finalization-idempotent-without-resign",
    "crl-active-lease-not-stolen",
    "crl-expired-lease-takeover",
    "crl-stale-completion-cas-rejected",
    "crl-numbering-contiguous-after-failover",
    "outbox-active-lease-not-stolen",
    "outbox-expired-lease-traffic-shift",
    "outbox-stale-completion-cas-rejected",
    "outbox-single-handler-and-attempt-in-crash-before-handler-scenario",
    "sensitive-evidence-exclusion",
)

FORBIDDEN_TEXT = (
    "postgres://",
    "postgresql://",
    "password=",
    "pgpassword",
    "file:local-dev-only",
    '"key_ref"',
    '"private_key"',
    '"credential"',
    "-----begin private key-----",
    "-----begin encrypted private key-----",
    "-----begin rsa private key-----",
    "-----begin ec private key-----",
    "-----begin openssh private key-----",
)


class DrillFailure(RuntimeError):
    """Raised when PostgreSQL failover evidence cannot be created safely."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_go_version(text: str) -> tuple[int, int, int]:
    match = re.search(r"\bgo(\d+)\.(\d+)(?:\.(\d+))?\b", text)
    if not match:
        raise DrillFailure("unable to parse Go version")
    return tuple(int(part or 0) for part in match.groups())  # type: ignore[return-value]


def resolve_commit(root: Path, explicit: str) -> str:
    if explicit:
        value = explicit.lower()
        if not COMMIT_RE.fullmatch(value):
            raise DrillFailure("commit must be an exact lowercase 40-character SHA")
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    value = result.stdout.strip().lower()
    if result.returncode == 0 and COMMIT_RE.fullmatch(value):
        if explicit and explicit != value:
            raise DrillFailure("supplied commit does not match checkout HEAD")
        return value
    return "unavailable"


def credential_values(dsn: str) -> set[str]:
    """Collect libpq and pgx password representations for safe diagnostics."""
    values = set()
    try:
        if dsn.lower().startswith(("postgres://", "postgresql://")):
            parsed = urlsplit(dsn)
            if parsed.password:
                values.add(unquote(parsed.password))
            values.update(value for key, value in parse_qsl(parsed.query) if key == "password" and value)
        else:
            # libpq permits whitespace around '=', single quoted values and
            # backslash escaping in both quoted and unquoted values. shlex has
            # different quote rules and must not be used for this grammar.
            position = 0
            while position < len(dsn):
                while position < len(dsn) and dsn[position].isspace():
                    position += 1
                if position == len(dsn):
                    break
                start = position
                while position < len(dsn) and not dsn[position].isspace() and dsn[position] != "=":
                    position += 1
                key = dsn[start:position]
                while position < len(dsn) and dsn[position].isspace():
                    position += 1
                if not key or position == len(dsn) or dsn[position] != "=":
                    raise ValueError("invalid connection assignment")
                position += 1
                while position < len(dsn) and dsn[position].isspace():
                    position += 1
                quoted = position < len(dsn) and dsn[position] == "'"
                if quoted:
                    position += 1
                value = []
                raw_value = []
                closed = not quoted
                while position < len(dsn):
                    char = dsn[position]
                    if char == "\\":
                        position += 1
                        if position == len(dsn):
                            raise ValueError("incomplete connection escape")
                        raw_value.extend((char, dsn[position]))
                        value.append(dsn[position])
                        position += 1
                    elif quoted and char == "'":
                        position += 1
                        closed = True
                        break
                    elif not quoted and char.isspace():
                        break
                    else:
                        raw_value.append(char)
                        value.append(char)
                        position += 1
                if not closed or (quoted and position < len(dsn) and not dsn[position].isspace()):
                    raise ValueError("invalid quoted connection value")
                if key == "password" and value:
                    values.add("".join(value))
                    # pgx v5 preserves non-quote/backslash escapes (including
                    # escaped spaces), unlike libpq. Cover both interpretations.
                    values.add("".join(raw_value).replace("\\\\", "\\").replace("\\'", "'"))
    except ValueError:
        # The Go helper emits only a stable configuration error for malformed
        # inputs. Previously parsed passwords still require redaction.
        pass
    if os.environ.get("PGPASSWORD"):
        values.add(os.environ["PGPASSWORD"])
    return values


def redact(text: str, output_dir: Path, dsn: str) -> str:
    replacements = {
        str(ROOT): "<repo>",
        str(ROOT.resolve()): "<repo>",
        str(Path.home()): "<home>",
        str(output_dir): "<evidence-dir>",
        str(output_dir.resolve()): "<evidence-dir>",
    }
    if dsn:
        replacements[dsn] = "<postgres-dsn>"
    for value in credential_values(dsn):
        # Also protect partial/malformed lines that cannot be JSON-decoded.
        for representation in (value, quote(value, safe=""), json.dumps(value)[1:-1], json.dumps(value, ensure_ascii=False)[1:-1]):
            replacements[representation] = "<redacted>"
    ordered = sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True)

    def plain(value: str) -> str:
        for original, replacement in ordered:
            value = value.replace(original, replacement)
        return value

    def structured(value: Any) -> Any:
        if isinstance(value, str):
            return plain(value)
        if isinstance(value, dict):
            return {plain(key): structured(item) for key, item in value.items()}
        if isinstance(value, list):
            return [structured(item) for item in value]
        return value

    lines = []
    for line in text.splitlines(keepends=True):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            lines.append(plain(line))
        else:
            # Decode Go JSON/HTML/Unicode escapes before searching secrets;
            # redact every string field, then serialize the sanitized event.
            lines.append(json.dumps(structured(event), ensure_ascii=False) + ("\n" if line.endswith("\n") else ""))
    return "".join(lines)


def decoded_diagnostics(text: str) -> str:
    """Inspect JSON field values before escaping can conceal sensitive markers."""
    fragments = [text]
    streams: dict[tuple[str, str], list[str]] = {}

    def visit(value: Any, depth: int) -> None:
        if depth > 8:
            raise DrillFailure("diagnostic nesting exceeds safe inspection limit")
        if isinstance(value, dict):
            for key, item in value.items():
                fragments.append(json.dumps(key))
                visit(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                visit(item, depth + 1)
        elif isinstance(value, str):
            fragments.append(value)
            try:
                nested = json.loads(value)
            except json.JSONDecodeError:
                return
            visit(nested, depth + 1)

    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        visit(event, 0)
        if isinstance(event, dict) and isinstance(event.get("Output"), str):
            stream = (str(event.get("Package", "")), str(event.get("Test", "")))
            streams.setdefault(stream, []).append(event["Output"])
    # test2json may split a long diagnostic mid-secret. Inspect the logical
    # stream as well as individual events before allowing any log to persist.
    for chunks in streams.values():
        visit("".join(chunks), 0)
    return "\n".join(fragments)


def sensitivity(texts: tuple[str, ...], dsn: str) -> dict[str, bool]:
    lowered = "\n".join(decoded_diagnostics(text) for text in texts).lower()
    return {
        "postgres_dsn_found": bool(dsn and dsn.lower() in lowered) or "postgres://" in lowered or "postgresql://" in lowered,
        "database_credentials_found": any(value in lowered for value in ("password=", "pgpassword", '"credential"')) or any(value.lower() in lowered for value in credential_values(dsn)),
        "raw_key_references_found": "file:local-dev-only" in lowered or '"key_ref"' in lowered,
        "private_key_markers_found": '"private_key"' in lowered or any(value in lowered for value in FORBIDDEN_TEXT if value.startswith("-----begin")),
    }


def parse_test_events(output: str) -> dict[str, str]:
    observed: dict[str, str] = {}
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        action = event.get("Action")
        package = event.get("Package")
        test = event.get("Test")
        if action in {"pass", "fail", "skip"} and package == PACKAGE and isinstance(test, str):
            previous = observed.get(test)
            observed[test] = action if previous in (None, action) else "conflicting-results"
    return observed


def test_regex() -> str:
    return "^(" + "|".join(re.escape(name) for name in TESTS) + ")$"


def go_command(go_executable: str | list[str], *arguments: str) -> list[str]:
    prefix = [go_executable] if isinstance(go_executable, str) else go_executable
    return [*prefix, *arguments]


def command(go_executable: str | list[str]) -> list[str]:
    return go_command(go_executable, "test", "-race", "-json", "-count=1", "-run", test_regex(), "./internal/lifecycle")


def evidence_template(commit: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "evidence_type": "enterprise_postgres_application_node_failover_drill",
        "product": "AnoPKI",
        "edition": "enterprise",
        "scope": "application-node-leases-on-postgresql-16",
        "cryptographic_backend_executed": False,
        "community_baseline_commit": "ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc",
        "adapted_from_commit": "49142ff50f5b37ba142d18cf61b60d8b287bdb49",
        "commit": commit,
        "enterprise_commit": commit,
        "minimum_go_version": "1.26.11",
        "postgres_required": True,
        "started_at": utc_now(),
        "completed_at": utc_now(),
        "result": "failed",
        "go_version": "unavailable",
        "test_command": [],
        "tests": [],
        "checks": [],
        "redaction": {
            "postgres_dsn_found": False,
            "database_credentials_found": False,
            "raw_key_references_found": False,
            "private_key_markers_found": False,
        },
        "blocker": "",
    }


def write_evidence(output_dir: Path, evidence: dict[str, Any]) -> None:
    evidence["completed_at"] = utc_now()
    serialized = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    lowered = serialized.lower()
    for forbidden in FORBIDDEN_TEXT:
        if forbidden in lowered:
            raise DrillFailure("forbidden sensitive content in PostgreSQL multi-node failover evidence")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "postgres-multi-node-failover-verification.json").write_text(serialized, encoding="utf-8")
    lines = [
        "# AnoPKI Enterprise PostgreSQL Application-Node Failover Evidence",
        "",
        f"- Result: `{evidence['result']}`",
        f"- Commit: `{evidence['commit']}`",
        f"- Go: `{evidence['go_version']}`",
        "- PostgreSQL: `required`",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- `{check['name']}`: `{check['status']}`" for check in evidence["checks"])
    if evidence["blocker"]:
        lines.extend(["", "## Blocker", "", f"`{evidence['blocker']}`"])
    markdown = "\n".join(lines) + "\n"
    for forbidden in FORBIDDEN_TEXT:
        if forbidden in markdown.lower():
            raise DrillFailure("forbidden sensitive content in PostgreSQL multi-node failover Markdown")
    (output_dir / "postgres-multi-node-failover-verification.md").write_text(markdown, encoding="utf-8")


def run_drill(root: Path, output_dir: Path, go_executable: str | list[str], commit: str) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    # Replace a previous successful run before any fallible preflight work.
    # A failed/rejected invocation must never leave old success evidence behind.
    evidence = evidence_template("unavailable")
    evidence["blocker"] = "drill has not completed"
    evidence["checks"] = [{"name": name, "status": "failed"} for name in EXPECTED_CHECKS]
    (output_dir / LOG_NAME).write_text("drill did not execute\n", encoding="utf-8")
    write_evidence(output_dir, evidence)
    try:
        evidence["commit"] = resolve_commit(root, commit)
        evidence["enterprise_commit"] = evidence["commit"]
        status = subprocess.run(["git", "-C", str(root), "status", "--porcelain"], text=True, capture_output=True, check=False, timeout=10)
        evidence["worktree_dirty"] = status.returncode != 0 or bool(status.stdout.strip())
        evidence["source_sha256"] = {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in (
                "service/internal/lifecycle/enterprise_postgres_failover_test.go",
                "scripts/verify-enterprise-postgres-failover.py",
            )
        }
        dsn = os.environ.get(DSN_ENV, "").strip()
        environment = os.environ.copy()
        environment["GOTOOLCHAIN"] = "local"
        environment.setdefault("GOCACHE", str(root / ".tmp" / "go-cache" / "postgres-multi-node-failover-build"))
        environment.setdefault("GOMODCACHE", str(root / ".tmp" / "go-cache" / "postgres-multi-node-failover-mod"))
        Path(environment["GOCACHE"]).mkdir(parents=True, exist_ok=True)
        Path(environment["GOMODCACHE"]).mkdir(parents=True, exist_ok=True)

        if not dsn:
            raise DrillFailure(f"{DSN_ENV} is required")
        if evidence["commit"] == "unavailable":
            raise DrillFailure("exact Enterprise commit is required")

        version_result = subprocess.run(
            go_command(go_executable, "version"),
            cwd=root / "service",
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        version = parse_go_version(version_result.stdout)
        evidence["go_version"] = ".".join(str(part) for part in version)
        if version_result.returncode != 0:
            raise DrillFailure("Go executable failed")
        if parse_go_version(version_result.stdout) < MINIMUM_GO_VERSION:
            raise DrillFailure("Go 1.26.11 or newer is required")

        args = command(go_executable)
        evidence["test_command"] = [redact(item, output_dir, dsn) for item in args]
        result = subprocess.run(
            args,
            cwd=root / "service",
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=600,
            check=False,
        )
        raw_log = result.stdout
        redacted_log = redact(raw_log, output_dir, dsn)
        observed = parse_test_events(raw_log)
        evidence["tests"] = [
            {"package": PACKAGE, "name": name, "status": observed.get(name, "missing")}
            for name in TESTS
        ]
        evidence["redaction"] = sensitivity((redacted_log,), dsn)
        passed = (
            result.returncode == 0
            and all(test["status"] == "pass" for test in evidence["tests"])
            and not any(evidence["redaction"].values())
        )
        evidence["checks"] = [
            {"name": name, "status": "passed" if passed else "failed"}
            for name in EXPECTED_CHECKS
        ]
        evidence["result"] = "passed" if passed else "failed"
        evidence["blocker"] = "" if passed else "one or more PostgreSQL multi-node failover tests, checks, or redaction rules failed"
        stored_log = redacted_log
        if any(evidence["redaction"].values()) or any(forbidden in decoded_diagnostics(redacted_log).lower() for forbidden in FORBIDDEN_TEXT):
            stored_log = "sensitive command output detected and omitted\n"
            evidence["result"] = "failed"
            evidence["blocker"] = "sensitive command output detected"
            for check in evidence["checks"]:
                check["status"] = "failed"
        (output_dir / LOG_NAME).write_text(stored_log, encoding="utf-8")
    except (OSError, subprocess.SubprocessError, DrillFailure) as exc:
        evidence["result"] = "failed"
        evidence["blocker"] = str(exc) if isinstance(exc, DrillFailure) else "command failed or timed out (details omitted)"
        evidence["checks"] = [{"name": name, "status": "failed"} for name in EXPECTED_CHECKS]
        (output_dir / LOG_NAME).write_text("drill did not complete; command output omitted\n", encoding="utf-8")

    write_evidence(output_dir, evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--go", default="go")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--commit", default="")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.list:
        cmd = command(args.go)
        print(subprocess.list2cmdline(cmd) if os.name == "nt" else shlex.join(cmd))
        return 0
    evidence = run_drill(ROOT, args.out_dir.resolve(), args.go, args.commit)
    if evidence["result"] == "passed":
        print(f"PostgreSQL multi-node failover drill passed: {len(EXPECTED_CHECKS)} checks")
        return 0
    print(f"PostgreSQL multi-node failover drill failed: {evidence['blocker']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
