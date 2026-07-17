#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Block Enterprise packaging until commercial and evidence gates close."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_FIELDS = (
    "Reviewed commit SHA",
    "GitHub Actions run URL",
    "Active OpenSSL version",
    "Enterprise metadata result",
    "AnoCrypto-C SDK integration result",
    "Pending parity result",
)
PENDING_VALUES = {"", "pending", "tbd", "todo"}


def evidence_value(text: str, field: str) -> str:
    match = re.search(rf"^\|\s*{re.escape(field)}\s*\|\s*(.*?)\s*\|$", text, flags=re.MULTILINE)
    return match.group(1).strip().strip("`") if match else ""


def release_blockers(root: Path) -> list[str]:
    root = root.resolve()
    edition = json.loads((root / ".edition/edition.json").read_text(encoding="utf-8"))
    enterprise_license = (root / "LICENSES/LicenseRef-AnoPKI-Enterprise.txt").read_text(encoding="utf-8")
    evidence = (root / "docs/enterprise/private-alpha-evidence.md").read_text(encoding="utf-8")
    blockers: list[str] = []

    packaging_paths = (
        root / "packaging/license-inventory.json",
        root / "packaging/package-policy.json",
        root / "scripts/generate-package-manifest.py",
        root / "scripts/validate-package-boundary.py",
    )
    missing_packaging = [str(path.relative_to(root)) for path in packaging_paths if not path.is_file()]
    if missing_packaging:
        blockers.append("packaging boundary is incomplete: " + ", ".join(missing_packaging))
        inventory: dict[str, object] = {}
        package_policy: dict[str, object] = {}
    else:
        inventory = json.loads(packaging_paths[0].read_text(encoding="utf-8"))
        package_policy = json.loads(packaging_paths[1].read_text(encoding="utf-8"))

    if "PLACEHOLDER" in enterprise_license.upper() or edition.get("commercial_license_status") != "complete":
        blockers.append("commercial license is incomplete")
    if inventory.get("commercial_license_status") != "complete":
        blockers.append("license inventory is incomplete")
    if inventory.get("customer_distribution_authorized") is not True:
        blockers.append("license inventory does not authorize customer distribution")
    classes = package_policy.get("package_classes")
    customer_policy = classes.get("customer-release", {}) if isinstance(classes, dict) else {}
    if package_policy.get("customer_distribution_authorized") is not True or not isinstance(
        customer_policy, dict
    ) or customer_policy.get("authorized") is not True:
        blockers.append("customer package policy is not authorized")
    if edition.get("commercial_release_authorized") is not True:
        blockers.append("commercial release authorization is absent")
    if edition.get("production_ready") is not True:
        blockers.append("production readiness is false")

    hosted = edition.get("hosted_ci")
    if not isinstance(hosted, dict) or hosted.get("remote_validation") != "passed":
        blockers.append("hosted qualification is not passed")
    if edition.get("enterprise_overlay_version") == "unreleased":
        blockers.append("Enterprise overlay version is unreleased")
    if edition.get("distribution_status") == "prohibited":
        blockers.append("customer and production distribution are prohibited")

    anocrypto_status = str(edition.get("anocrypto_status", "")).lower()
    if edition.get("crypto_backend_default") == "anocrypto" or anocrypto_status in {"active", "default", "production", "production_ready"}:
        active_evidence = root / "docs/enterprise/anocrypto-production-evidence.md"
        if not active_evidence.is_file():
            blockers.append("AnoCrypto is production-ready without evidence")

    if edition.get("kcmvp_status") == "validated":
        certification = root / "docs/enterprise/kcmvp-certification-evidence.md"
        if not certification.is_file():
            blockers.append("KCMVP is validated without evidence")

    for field in EVIDENCE_FIELDS:
        value = evidence_value(evidence, field)
        if value.lower() in PENDING_VALUES:
            blockers.append(f"private-alpha evidence pending: {field}")
    return blockers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT, type=Path)
    parser.add_argument("--expect-blocked", action="store_true")
    args = parser.parse_args()
    blockers = release_blockers(args.root)

    if args.expect_blocked:
        if not blockers:
            raise SystemExit("expected Enterprise release to be blocked")
        print("enterprise release blocked as expected:\n" + "\n".join(blockers))
        return
    if blockers:
        print("Enterprise release blocked:\n" + "\n".join(blockers), file=sys.stderr)
        raise SystemExit(1)
    print("enterprise release guard ok")


if __name__ == "__main__":
    main()
