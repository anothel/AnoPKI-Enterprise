#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Self-checks for deterministic package manifest generation."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate-package-manifest.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_package_manifest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, check=False)


def main() -> None:
    generator = load_generator()
    first = generator.build_manifest(ROOT, "enterprise-openssl", "internal-validation")
    second = generator.build_manifest(ROOT, "enterprise-openssl", "internal-validation")
    assert first == second
    assert first["package_class"] == "internal-validation"
    assert first["selected_adapter"] == "openssl"
    assert first["customer_distribution_authorized"] is False
    assert first["fallback_enabled"] is False and first["fallback_used"] is False
    assert first["production_ready"] is False and first["kcmvp_status"] == "not_validated"
    assert first["archive_format"] == "zip"
    assert first["source_date_epoch"] == int(subprocess.check_output(["git", "show", "-s", "--format=%ct", "HEAD"], cwd=ROOT))
    assert len(first["dependency_inventory_sha256"]) == 64
    assert len(first["third_party_notices_sha256"]) == 64
    assert first["files"] == sorted(first["files"], key=lambda item: item["path"].encode("utf-8"))
    paths = {item["path"] for item in first["files"]}
    assert {
        "THIRD_PARTY_NOTICES.md",
        "THIRD_PARTY_NOTICES.json",
        "packaging/dependency-license-inventory.json",
        "packaging/license-inventory.json",
        "packaging/package-policy.json",
        "LICENSES/third-party/openssl/copyright",
    }.issubset(paths)
    sources = generator.git_files(ROOT, sorted(paths, key=lambda value: value.encode("utf-8")))
    for item in first["files"]:
        data, mode = sources[item["path"]]
        assert item["sha256"] == hashlib.sha256(data).hexdigest()
        assert item["size"] == len(data) and item["mode"] == mode
        assert not Path(item["path"]).is_absolute()

    anocrypto = generator.build_manifest(ROOT, "enterprise-anocrypto-c", "internal-validation")
    assert anocrypto["selected_adapter"] == "anocrypto-c"
    assert anocrypto["kcmvp_status"] == "not_validated"
    paths = {item["path"] for item in anocrypto["files"]}
    assert "src/backends/anocrypto_c/anocrypto_backend.cpp" in paths
    assert not any(path.startswith(("enterprise/anocrypto/src/", "enterprise/anocrypto/include/")) for path in paths)

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "package-manifest.json"
        result = run(
            "--profile", "enterprise-openssl",
            "--package-class", "internal-validation",
            "--out", str(out),
        )
        assert result.returncode == 0, result.stderr or result.stdout
        value = json.loads(out.read_text(encoding="utf-8"))
        assert value == first

    for profile in ("enterprise-openssl", "enterprise-anocrypto-c"):
        blocked = run(
            "--profile", profile,
            "--package-class", "customer-release",
            "--out", str(ROOT / ".tmp/package-manifest-should-not-exist.json"),
        )
        assert blocked.returncode != 0
        assert "customer release blocked" in (blocked.stderr + blocked.stdout)
        if profile == "enterprise-anocrypto-c":
            assert "AnoCrypto-C SDK license is unresolved" in (blocked.stderr + blocked.stdout)

    with tempfile.TemporaryDirectory() as tmp:
        allowlist = Path(tmp) / "manifest.txt"
        allowlist.write_text("src/*.cpp\n", encoding="utf-8")
        try:
            generator.parse_allowlist(allowlist)
        except SystemExit as exc:
            assert "must be exact" in str(exc)
        else:
            raise AssertionError("glob allow-list unexpectedly passed")

        allowlist.write_text("README.md\nreadme.md\n", encoding="utf-8")
        try:
            generator.parse_allowlist(allowlist)
        except SystemExit as exc:
            assert "case-insensitive" in str(exc)
        else:
            raise AssertionError("case-colliding allow-list unexpectedly passed")

    previous_epoch = os.environ.get("SOURCE_DATE_EPOCH")
    os.environ["SOURCE_DATE_EPOCH"] = "1"
    try:
        try:
            generator.build_manifest(ROOT, "enterprise-openssl", "internal-validation")
        except SystemExit as exc:
            assert "SOURCE_DATE_EPOCH" in str(exc)
        else:
            raise AssertionError("mismatched SOURCE_DATE_EPOCH unexpectedly passed")
    finally:
        if previous_epoch is None:
            del os.environ["SOURCE_DATE_EPOCH"]
        else:
            os.environ["SOURCE_DATE_EPOCH"] = previous_epoch

    serialized = json.dumps(first, sort_keys=True)
    assert str(ROOT) not in serialized
    assert "ANOCRYPTO_C_READ_TOKEN" not in serialized
    print("package manifest generator tests ok")


if __name__ == "__main__":
    main()
