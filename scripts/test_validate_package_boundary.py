#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Self-checks for Enterprise package boundary validation."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate-package-boundary.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_package_boundary", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def expect_failure(function, expected: str) -> None:
    try:
        function()
    except SystemExit as exc:
        assert expected in str(exc), str(exc)
    else:
        raise AssertionError("package boundary unexpectedly passed")


def main() -> None:
    validator = load_validator()
    generator = validator.load_generator()
    validator.validate(ROOT)
    inventory = validator.read_json(ROOT / "packaging/license-inventory.json")
    policy = validator.read_json(ROOT / "packaging/package-policy.json")
    edition = validator.read_json(ROOT / ".edition/edition.json")
    manifest = generator.build_manifest(ROOT, "enterprise-openssl", "internal-validation")
    validator.validate_manifest(ROOT, manifest, generator)

    fallback = copy.deepcopy(manifest)
    fallback["fallback_used"] = True
    expect_failure(lambda: validator.validate_manifest(ROOT, fallback, generator), "fallback")

    bad_hash = copy.deepcopy(manifest)
    bad_hash["files"][0]["sha256"] = "0" * 64
    expect_failure(lambda: validator.validate_manifest(ROOT, bad_hash, generator), "SHA-256 mismatch")

    bad_inventory_hash = copy.deepcopy(manifest)
    bad_inventory_hash["dependency_inventory_sha256"] = "0" * 64
    expect_failure(lambda: validator.validate_manifest(ROOT, bad_inventory_hash, generator), "dependency inventory SHA-256")

    bad_notices_hash = copy.deepcopy(manifest)
    bad_notices_hash["third_party_notices_sha256"] = "0" * 64
    expect_failure(lambda: validator.validate_manifest(ROOT, bad_notices_hash, generator), "third-party notices SHA-256")

    bad_size = copy.deepcopy(manifest)
    bad_size["files"][0]["size"] = -1
    expect_failure(lambda: validator.validate_manifest(ROOT, bad_size, generator), "size is invalid")

    bad_mode = copy.deepcopy(manifest)
    bad_mode["files"][0]["mode"] = "0777"
    expect_failure(lambda: validator.validate_manifest(ROOT, bad_mode, generator), "mode is invalid")

    unallowlisted = copy.deepcopy(manifest)
    item = copy.deepcopy(unallowlisted["files"][-1])
    item["path"] = "unallowlisted.txt"
    unallowlisted["files"].append(item)
    unallowlisted["files"].sort(key=lambda value: value["path"])
    expect_failure(lambda: validator.validate_manifest(ROOT, unallowlisted, generator), "unallowlisted")

    both = copy.deepcopy(manifest)
    item = copy.deepcopy(both["files"][-1])
    item["path"] = "src/backends/anocrypto_c/anocrypto_backend.cpp"
    both["files"].append(item)
    both["files"].sort(key=lambda value: value["path"])
    expect_failure(lambda: validator.validate_manifest(ROOT, both, generator), "both OpenSSL and AnoCrypto-C")

    copied = copy.deepcopy(manifest)
    item = copy.deepcopy(copied["files"][-1])
    item["path"] = "enterprise/anocrypto/include/anocrypto.h"
    copied["files"].append(item)
    copied["files"].sort(key=lambda value: value["path"])
    expect_failure(lambda: validator.validate_manifest(ROOT, copied, generator), "copied AnoCrypto-C")

    forbidden = copy.deepcopy(manifest)
    forbidden["files"][0]["path"] = "build/customer-credential.txt"
    forbidden["files"].sort(key=lambda value: value["path"])
    expect_failure(lambda: validator.validate_manifest(ROOT, forbidden, generator), "forbidden build/cache/secret")

    nested = copy.deepcopy(manifest)
    nested["files"][0]["path"] = "source.zip"
    nested["files"].sort(key=lambda value: value["path"])
    expect_failure(lambda: validator.validate_manifest(ROOT, nested, generator), "forbidden build/cache/secret")

    sdk_binary = copy.deepcopy(generator.build_manifest(ROOT, "enterprise-anocrypto-c", "internal-validation"))
    item = copy.deepcopy(sdk_binary["files"][-1])
    item["path"] = "sdk/anocrypto-c.dll"
    sdk_binary["files"].append(item)
    sdk_binary["files"].sort(key=lambda value: value["path"])
    expect_failure(lambda: validator.validate_manifest(ROOT, sdk_binary, generator), "without exact SDK evidence")

    customer = copy.deepcopy(manifest)
    customer["package_class"] = "customer-release"
    expect_failure(lambda: validator.validate_manifest(ROOT, customer, generator), "final commercial license")

    kcmvp = copy.deepcopy(manifest)
    kcmvp["kcmvp_status"] = "validated"
    expect_failure(lambda: validator.validate_manifest(ROOT, kcmvp, generator), "KCMVP")

    mislabeled = copy.deepcopy(inventory)
    next(item for item in mislabeled["components"] if item["name"] == "enterprise-commercial-overlay")[
        "license_expression"
    ] = "MPL-2.0"
    expect_failure(lambda: validator.validate_inventory(ROOT, mislabeled, policy, edition), "must not be labeled as MPL-2.0")

    missing_notice = copy.deepcopy(inventory)
    next(item for item in missing_notice["components"] if item["name"] == "synchronized-community-mpl-files")[
        "required_notices"
    ] = ["LICENSES/MPL-2.0.txt"]
    expect_failure(lambda: validator.validate_inventory(ROOT, missing_notice, policy, edition), "source/overlay notice")

    hosted_success = copy.deepcopy(edition)
    hosted_success["hosted_ci"]["remote_validation"] = "passed"
    expect_failure(lambda: validator.validate_hosted_state(hosted_success), "runner-assignment blocker")

    trusted_completed = copy.deepcopy(edition)
    trusted_completed["trusted_anocrypto_sdk_lane"]["status"] = "completed"
    expect_failure(lambda: validator.validate_hosted_state(trusted_completed), "not_run")

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "internal.zip"
        sources = generator.git_files(ROOT, [item["path"] for item in manifest["files"]])
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr("package-manifest.json", json.dumps(manifest))
            for item in manifest["files"]:
                package.writestr(item["path"], sources[item["path"]][0])
        validator.validate_archive(archive, manifest)
        with zipfile.ZipFile(archive, "a") as package:
            package.writestr("unexpected.txt", "unexpected")
        expect_failure(lambda: validator.validate_archive(archive, manifest), "archive/member mismatch")

    print("package boundary validator tests ok")


if __name__ == "__main__":
    main()
