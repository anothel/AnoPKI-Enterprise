#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Self-tests for the PostgreSQL multi-node failover evidence runner."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_postgres_multi_node_failover",
    ROOT / "scripts" / "verify-enterprise-postgres-failover.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@contextmanager
def dsn(value: str):
    previous = os.environ.get(MODULE.DSN_ENV)
    if value:
        os.environ[MODULE.DSN_ENV] = value
    else:
        os.environ.pop(MODULE.DSN_ENV, None)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(MODULE.DSN_ENV, None)
        else:
            os.environ[MODULE.DSN_ENV] = previous


def fake_go(root: Path, *, version: str = "go1.26.11", fail: str = "", omit: str = "", skip: str = "", sensitive: str = "") -> list[str]:
    root.mkdir(parents=True, exist_ok=True)
    script = root / "fake-go.py"
    payload = {
        "version": version,
        "tests": list(MODULE.TESTS),
        "package": MODULE.PACKAGE,
        "fail": fail,
        "omit": omit,
        "skip": skip,
        "sensitive": sensitive,
    }
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        f"P={json.dumps(payload)!r}\n"
        "P=json.loads(P)\n"
        "if len(sys.argv)>1 and sys.argv[1]=='version':\n"
        " print('go version '+P['version']+' linux/amd64'); raise SystemExit(0)\n"
        "if P['sensitive']: print(P['sensitive'])\n"
        "code=0\n"
        "for name in P['tests']:\n"
        " if name==P['omit']: continue\n"
        " action='pass'\n"
        " if name==P['fail']: action='fail'; code=1\n"
        " if name==P['skip']: action='skip'\n"
        " print(json.dumps({'Action':action,'Package':P['package'],'Test':name}))\n"
        "raise SystemExit(code)\n",
        encoding="utf-8",
    )
    return [os.sys.executable, str(script)]


def main() -> None:
    test_dsn = "postgres://operator:secret@localhost:5432/anopki?sslmode=disable"

    with tempfile.TemporaryDirectory() as dirname, dsn(test_dsn):
        root = Path(dirname)
        evidence = MODULE.run_drill(ROOT, root / "out", fake_go(root / "go"), MODULE.resolve_commit(ROOT, ""))
        assert evidence["result"] == "passed"
        assert evidence["edition"] == "enterprise"
        assert evidence["community_baseline_commit"] == "ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc"
        assert "-race" in evidence["test_command"]
        assert len(evidence["tests"]) == len(MODULE.TESTS)
        assert all(check["status"] == "passed" for check in evidence["checks"])
        combined = "\n".join(path.read_text(encoding="utf-8") for path in (root / "out").iterdir())
        assert test_dsn not in combined
        assert "postgres://" not in combined.lower()

    with tempfile.TemporaryDirectory() as dirname, dsn(""):
        root = Path(dirname)
        evidence = MODULE.run_drill(ROOT, root / "out", fake_go(root / "go"), MODULE.resolve_commit(ROOT, ""))
        assert evidence["result"] == "failed"
        assert MODULE.DSN_ENV in evidence["blocker"]

    with tempfile.TemporaryDirectory() as dirname, dsn(test_dsn):
        root = Path(dirname)
        evidence = MODULE.run_drill(ROOT, root / "out", fake_go(root / "go", version="go1.23.2"), MODULE.resolve_commit(ROOT, ""))
        assert evidence["result"] == "failed"

    with tempfile.TemporaryDirectory() as dirname, dsn(test_dsn):
        root = Path(dirname)
        evidence = MODULE.run_drill(ROOT, root / "out", fake_go(root / "go", fail=MODULE.TESTS[0]), MODULE.resolve_commit(ROOT, ""))
        assert evidence["result"] == "failed"

    with tempfile.TemporaryDirectory() as dirname, dsn(test_dsn):
        root = Path(dirname)
        evidence = MODULE.run_drill(ROOT, root / "out", fake_go(root / "go", omit=MODULE.TESTS[1]), MODULE.resolve_commit(ROOT, ""))
        assert evidence["result"] == "failed"

    with tempfile.TemporaryDirectory() as dirname, dsn(test_dsn):
        root = Path(dirname)
        evidence = MODULE.run_drill(ROOT, root / "out", fake_go(root / "go", skip=MODULE.TESTS[2]), MODULE.resolve_commit(ROOT, ""))
        assert evidence["result"] == "failed"

    with tempfile.TemporaryDirectory() as dirname, dsn(test_dsn):
        root = Path(dirname)
        evidence = MODULE.run_drill(ROOT, root / "out", fake_go(root / "go", sensitive="-----BEGIN " + "PRIVATE KEY-----"), MODULE.resolve_commit(ROOT, ""))
        assert evidence["result"] == "failed"
        assert evidence["redaction"]["private_key_markers_found"] is True

    for secret_dsn, diagnostic, absent in (
        ("postgres://operator:s3cr%40t-Value@localhost/db", "s3cr@t-Value", "s3cr@t-Value"),
        ("host=localhost user=operator password='phrase secret' dbname=db", "phrase secret", "phrase secret"),
    ):
        with tempfile.TemporaryDirectory() as dirname, dsn(secret_dsn):
            root = Path(dirname)
            evidence = MODULE.run_drill(ROOT, root / "out", fake_go(root / "go", sensitive=diagnostic), MODULE.resolve_commit(ROOT, ""))
            combined = "\n".join(p.read_text(encoding="utf-8") for p in (root / "out").iterdir())
            assert absent not in combined, "decoded credentials leaked into evidence"
            assert secret_dsn not in combined

    with tempfile.TemporaryDirectory() as dirname, dsn(test_dsn):
        root = Path(dirname)
        evidence = MODULE.run_drill(ROOT, root / "out", fake_go(root / "go", version="go1.26.10"), MODULE.resolve_commit(ROOT, ""))
        assert evidence["result"] == "failed", "vulnerable compiler accepted"

    events = [
        {"Action": action, "Package": MODULE.PACKAGE, "Test": MODULE.TESTS[0]}
        for action in ("fail", "pass")
    ]
    assert MODULE.parse_test_events("\n".join(json.dumps(e) for e in events))[MODULE.TESTS[0]] != "pass"
    assert MODULE.parse_test_events("malformed output") == {}

    try:
        MODULE.resolve_commit(ROOT, "bad")
    except MODULE.DrillFailure:
        pass
    else:
        raise AssertionError("invalid commit passed")

    try:
        MODULE.resolve_commit(ROOT, "0" * 40)
    except MODULE.DrillFailure:
        pass
    else:
        raise AssertionError("mismatched checkout commit accepted")

    for key_type in ("RSA", "EC", "OPENSSH"):
        with tempfile.TemporaryDirectory() as dirname, dsn(test_dsn):
            root = Path(dirname)
            evidence = MODULE.run_drill(ROOT, root / "out", fake_go(root / "go", sensitive="-----BEGIN " + key_type + " PRIVATE KEY-----"), MODULE.resolve_commit(ROOT, ""))
            assert evidence["result"] == "failed", "private key output accepted"
            combined = "\n".join(p.read_text(encoding="utf-8") for p in (root / "out").iterdir())
            assert "-----BEGIN " not in combined

    print("Enterprise PostgreSQL failover runner self-tests passed: 17")


if __name__ == "__main__":
    main()
