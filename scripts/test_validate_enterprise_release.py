#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Self-checks for Enterprise release prevention."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate-enterprise-release.py"


def write_fixture(root: Path) -> None:
    (root / ".edition").mkdir(parents=True)
    (root / "LICENSES").mkdir()
    (root / "docs/enterprise").mkdir(parents=True)
    edition = {
        "enterprise_overlay_version": "0.1.0-private-alpha.1",
        "commercial_license_status": "approved",
        "distribution_status": "allowed",
        "crypto_backend_default": "openssl",
        "anocrypto_status": "skeleton_pending",
        "kcmvp_status": "not_validated",
    }
    (root / ".edition/edition.json").write_text(json.dumps(edition), encoding="utf-8")
    (root / "LICENSES/LicenseRef-AnoPKI-Enterprise.txt").write_text("Approved terms for validator test.\n", encoding="utf-8")
    rows = "\n".join(f"| {field} | `recorded` |" for field in (
        "Reviewed commit SHA",
        "GitHub Actions run URL",
        "Active OpenSSL version",
        "Enterprise metadata result",
        "AnoCrypto skeleton result",
        "Pending parity result",
    ))
    (root / "docs/enterprise/private-alpha-evidence.md").write_text(rows + "\n", encoding="utf-8")


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args], text=True, capture_output=True)


def main() -> None:
    current = run(ROOT, "--expect-blocked")
    assert current.returncode == 0, current.stderr or current.stdout
    assert "commercial license is placeholder" in current.stdout
    assert "private-alpha evidence pending" in current.stdout

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_fixture(root)
        ready = run(root)
        assert ready.returncode == 0, ready.stderr or ready.stdout

        edition_path = root / ".edition/edition.json"
        edition = json.loads(edition_path.read_text(encoding="utf-8"))
        edition["anocrypto_status"] = "production_ready"
        edition_path.write_text(json.dumps(edition), encoding="utf-8")
        anocrypto = run(root)
        assert anocrypto.returncode == 1
        assert "AnoCrypto is production-ready without evidence" in anocrypto.stderr

        edition["anocrypto_status"] = "skeleton_pending"
        edition["kcmvp_status"] = "validated"
        edition_path.write_text(json.dumps(edition), encoding="utf-8")
        kcmvp = run(root)
        assert kcmvp.returncode == 1
        assert "KCMVP is validated without evidence" in kcmvp.stderr

    print("enterprise release guard tests ok")


if __name__ == "__main__":
    main()
