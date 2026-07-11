#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Self-checks for pending parity JUnit validation."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate-pending-parity-junit.py"
NAME = "anopki.crypto_backend_parity.anocrypto_pending"


def run(xml: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "result.xml"
        path.write_text(xml, encoding="utf-8")
        return subprocess.run([sys.executable, str(SCRIPT), str(path)], text=True, capture_output=True)


def main() -> None:
    skipped = run(f'<testsuite><testcase name="{NAME}"><skipped/></testcase></testsuite>')
    assert skipped.returncode == 0, skipped.stderr or skipped.stdout
    passed = run(f'<testsuite><testcase name="{NAME}"/></testsuite>')
    assert passed.returncode == 1
    assert "unexpectedly reported normal success" in passed.stderr
    print("pending parity JUnit validator tests ok")


if __name__ == "__main__":
    main()
