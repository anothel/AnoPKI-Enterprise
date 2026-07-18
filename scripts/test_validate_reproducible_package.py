#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Negative checks for deterministic internal package validation."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import warnings
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
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
        raise AssertionError("reproducible package validator unexpectedly passed")


def rewrite(source: Path, target: Path, mutate) -> None:
    with zipfile.ZipFile(source) as archive:
        entries = [(copy.copy(info), archive.read(info)) for info in archive.infolist()]
    mutate(entries)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
            for info, data in entries:
                archive.writestr(info, data)


def mutate_manifest(entries, change) -> None:
    for index, (info, data) in enumerate(entries):
        if info.filename == "package-manifest.json":
            manifest = json.loads(data)
            change(manifest)
            entries[index] = (info, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))
            return
    raise AssertionError("missing package manifest")


def main() -> None:
    builder = load("build_internal_package", ROOT / "scripts/build-internal-package.py")
    validator = load("validate_reproducible_package", ROOT / "scripts/validate-reproducible-package.py")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        package = tmp / "internal.zip"
        builder.build_package(ROOT, package, require_clean=False)
        validator.validate_package(package, ROOT)

        unordered = tmp / "unordered.zip"
        rewrite(package, unordered, lambda entries: entries.reverse())
        expect_failure(lambda: validator.validate_package(unordered, ROOT, False), "canonical byte order")

        timestamp = tmp / "timestamp.zip"
        rewrite(package, timestamp, lambda entries: setattr(entries[0][0], "date_time", (2020, 1, 1, 0, 0, 0)))
        expect_failure(lambda: validator.validate_package(timestamp, ROOT, False), "timestamp")

        permission = tmp / "permission.zip"
        rewrite(package, permission, lambda entries: setattr(entries[0][0], "external_attr", 0o777 << 16))
        expect_failure(lambda: validator.validate_package(permission, ROOT, False), "mode mismatch")

        duplicate = tmp / "duplicate.zip"
        rewrite(package, duplicate, lambda entries: entries.append(copy.deepcopy(entries[-1])))
        expect_failure(lambda: validator.validate_package(duplicate, ROOT, False), "duplicate ZIP entry")

        nested = tmp / "nested.zip"
        def add_nested(entries):
            info = copy.copy(entries[-1][0])
            info.filename = "zzz-source.zip"
            entries.append((info, b"nested"))
        rewrite(package, nested, add_nested)
        expect_failure(lambda: validator.validate_package(nested, ROOT, False), "nested archive")

        mismatch = tmp / "mismatch.zip"
        rewrite(package, mismatch, lambda entries: entries.__setitem__(0, (entries[0][0], entries[0][1] + b"changed")))
        expect_failure(lambda: validator.validate_package(mismatch, ROOT, False), "content mismatch")

        dependency = tmp / "dependency.zip"
        def change_dependency(entries):
            for index, (info, data) in enumerate(entries):
                if info.filename == "packaging/dependency-license-inventory.json":
                    entries[index] = (info, data + b"changed")
                    return
            raise AssertionError("missing dependency inventory")
        rewrite(package, dependency, change_dependency)
        expect_failure(lambda: validator.validate_package(dependency, ROOT, False), "content mismatch")

        extra = tmp / "extra.zip"
        def add_extra(entries):
            info = copy.copy(entries[-1][0])
            info.filename = "zzz-unexpected.txt"
            entries.append((info, b"unexpected"))
        rewrite(package, extra, add_extra)
        expect_failure(lambda: validator.validate_package(extra, ROOT, False), "file list")

        fallback = tmp / "fallback.zip"
        rewrite(package, fallback, lambda entries: mutate_manifest(entries, lambda value: value.__setitem__("fallback_used", True)))
        expect_failure(lambda: validator.validate_package(fallback, ROOT, False), "fallback")

        customer = tmp / "customer.zip"
        rewrite(package, customer, lambda entries: mutate_manifest(entries, lambda value: value.__setitem__("package_class", "customer-release")))
        expect_failure(lambda: validator.validate_package(customer, ROOT, False), "not internal-validation")

        stale = tmp / "stale.zip"
        rewrite(package, stale, lambda entries: mutate_manifest(entries, lambda value: value.__setitem__("source_date_epoch", 1)))
        expect_failure(lambda: validator.validate_package(stale, ROOT, False), "SOURCE_DATE_EPOCH")

        with package.open("ab") as stream:
            stream.write(b"replaced")
        expect_failure(lambda: validator.validate_package(package, ROOT), "sidecar mismatch")
    print("reproducible package validator tests ok")


if __name__ == "__main__":
    main()
