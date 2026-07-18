#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Self-checks for deterministic internal package construction."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build-internal-package.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_internal_package", SCRIPT)
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
        raise AssertionError("internal package build unexpectedly passed")


def main() -> None:
    builder = load_builder()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        outputs = [tmp / name / "internal.zip" for name in ("first", "second", "third")]
        builds = [builder.build_package(ROOT, output, require_clean=False) for output in outputs]
        archives = [output.read_bytes() for output in outputs]
        assert archives[0] == archives[1] == archives[2]
        assert builds[0] == builds[1] == builds[2]
        with zipfile.ZipFile(outputs[0]) as archive:
            assert archive.namelist() == sorted(archive.namelist(), key=lambda value: value.encode("utf-8"))
            assert not any(info.is_dir() for info in archive.infolist())
            assert all(info.compress_type == zipfile.ZIP_STORED and not info.extra for info in archive.infolist())
            entries = {
                info.filename: (archive.read(info), f"{stat.S_IMODE((info.external_attr >> 16) & 0xffff):04o}")
                for info in archive.infolist()
            }
            epoch = json.loads(archive.read(builder.MANIFEST_NAME))["source_date_epoch"]
        assert builder.zip_bytes(dict(reversed(list(entries.items()))), epoch) == archives[0]

        source = ROOT / "README.md"
        original = source.stat()
        try:
            os.utime(source, ns=(original.st_atime_ns, original.st_mtime_ns - 2_000_000_000))
            source.chmod(stat.S_IMODE(original.st_mode) | stat.S_IWUSR)
            changed = tmp / "metadata-changed" / "internal.zip"
            builder.build_package(ROOT, changed, require_clean=False)
            assert changed.read_bytes() == archives[0]
        finally:
            source.chmod(stat.S_IMODE(original.st_mode))
            os.utime(source, ns=(original.st_atime_ns, original.st_mtime_ns))

        expect_failure(
            lambda: builder.build_package(ROOT, tmp / "customer.zip", package_class="customer-release", require_clean=False),
            "not authorized",
        )
        expect_failure(
            lambda: builder.build_package(ROOT, tmp / "anocrypto.zip", profile="enterprise-anocrypto-c", require_clean=False),
            "only enterprise-openssl",
        )
        expect_failure(
            lambda: builder.build_package(ROOT, tmp / "internal.tar.gz", archive_format="tar.gz", require_clean=False),
            "only deterministic ZIP",
        )

    untracked = ROOT / "untracked-package-negative-test"
    untracked.write_text("must make clean preflight fail\n", encoding="utf-8")
    try:
        expect_failure(lambda: builder.require_clean_head(ROOT), "clean working tree")
    finally:
        untracked.unlink()
    print("internal package builder tests ok")


if __name__ == "__main__":
    main()
