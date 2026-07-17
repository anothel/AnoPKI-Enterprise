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
        "community_baseline_commit": "ae3ddee72dd05f274b9bbae1b514cdc4c4de03f5",
        "enterprise_overlay_version": "0.1.0-private-alpha.1",
        "commercial_license_status": "complete",
        "distribution_status": "allowed",
        "commercial_release_authorized": True,
        "production_ready": True,
        "crypto_backend_default": "openssl",
        "anocrypto_status": "external_sdk_not_configured",
        "kcmvp_status": "not_validated",
        "hosted_ci": {"remote_validation": "passed", "runner_assigned": True, "steps_executed": 17},
    }
    (root / ".edition/edition.json").write_text(json.dumps(edition), encoding="utf-8")
    (root / "LICENSES/LicenseRef-AnoPKI-Enterprise.txt").write_text("Approved terms for validator test.\n", encoding="utf-8")
    (root / "packaging").mkdir()
    (root / "scripts").mkdir()
    inventory = {
        "commercial_license_status": "complete",
        "customer_distribution_authorized": True,
    }
    policy = {
        "customer_distribution_authorized": True,
        "package_classes": {"customer-release": {"authorized": True}},
    }
    (root / "packaging/license-inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
    (root / "packaging/dependency-license-inventory.json").write_text("{}\n", encoding="utf-8")
    (root / "packaging/package-policy.json").write_text(json.dumps(policy), encoding="utf-8")
    (root / "THIRD_PARTY_NOTICES.md").write_text("fixture\n", encoding="utf-8")
    (root / "THIRD_PARTY_NOTICES.json").write_text("{}\n", encoding="utf-8")
    (root / "scripts/generate-package-manifest.py").write_text("# fixture\n", encoding="utf-8")
    (root / "scripts/generate-third-party-notices.py").write_text("# fixture\n", encoding="utf-8")
    (root / "scripts/validate-package-boundary.py").write_text("# fixture\n", encoding="utf-8")
    (root / "scripts/validate-third-party-notices.py").write_text("# fixture\n", encoding="utf-8")
    rows = "\n".join(f"| {field} | `recorded` |" for field in (
        "Reviewed commit SHA",
        "GitHub Actions run URL",
        "Active OpenSSL version",
        "Enterprise metadata result",
        "AnoCrypto-C SDK integration result",
        "Pending parity result",
    ))
    (root / "docs/enterprise/private-alpha-evidence.md").write_text(rows + "\n", encoding="utf-8")


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args], text=True, capture_output=True)


def main() -> None:
    current = run(ROOT, "--expect-blocked")
    assert current.returncode == 0, current.stderr or current.stdout
    assert "commercial license is incomplete" in current.stdout
    assert "license inventory is incomplete" in current.stdout
    assert "hosted qualification is not passed" in current.stdout
    assert "private-alpha evidence pending" in current.stdout

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_fixture(root)
        ready = run(root)
        assert ready.returncode == 0, ready.stderr or ready.stdout

        inventory_path = root / "packaging/license-inventory.json"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        inventory["commercial_license_status"] = "incomplete"
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
        incomplete = run(root)
        assert incomplete.returncode == 1
        assert "license inventory is incomplete" in incomplete.stderr
        inventory["commercial_license_status"] = "complete"
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

        edition_path = root / ".edition/edition.json"
        edition = json.loads(edition_path.read_text(encoding="utf-8"))
        edition["anocrypto_status"] = "production_ready"
        edition_path.write_text(json.dumps(edition), encoding="utf-8")
        anocrypto = run(root)
        assert anocrypto.returncode == 1
        assert "AnoCrypto is production-ready without evidence" in anocrypto.stderr

        edition["anocrypto_status"] = "external_sdk_not_configured"
        edition["kcmvp_status"] = "validated"
        edition_path.write_text(json.dumps(edition), encoding="utf-8")
        kcmvp = run(root)
        assert kcmvp.returncode == 1
        assert "KCMVP is validated without evidence" in kcmvp.stderr

    print("enterprise release guard tests ok")


if __name__ == "__main__":
    main()
