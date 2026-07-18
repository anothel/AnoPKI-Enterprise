#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Validate a deterministic AnoPKI Enterprise internal ZIP and its sidecars."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import stat
import sys
import zipfile
import zlib
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
BUILD_FIELDS = {
    "archive_filename",
    "archive_sha256",
    "archive_size",
    "enterprise_commit",
    "community_baseline_commit",
    "package_manifest_sha256",
    "archive_format",
    "reproducible",
}
NESTED_ARCHIVE_SUFFIXES = (".zip", ".tar", ".tar.gz", ".tgz")
BINARY_SUFFIXES = (".a", ".bin", ".dll", ".dylib", ".exe", ".lib", ".o", ".obj", ".so")


def fail(message: str) -> None:
    raise SystemExit(message)


def read_json(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid {label}: {exc}")
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        fail(f"cannot load {path.name}")
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_package(path: Path, root: Path = ROOT, validate_sidecars: bool = True) -> dict[str, object]:
    builder = load_module("build_internal_package", ROOT / "scripts/build-internal-package.py")
    boundary = load_module("validate_package_boundary", ROOT / "scripts/validate-package-boundary.py")
    root = root.resolve()
    if path.suffix.lower() != ".zip":
        fail("only deterministic ZIP packages are supported")
    boundary.validate(root)

    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if archive.comment:
                fail("package archive comment must be empty")
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                fail("package archive contains a duplicate ZIP entry")
            if len(names) != len({name.casefold() for name in names}):
                fail("package archive contains a case-insensitive path collision")
            if names != sorted(names, key=lambda value: value.encode("utf-8")):
                fail("package archive entries are not in canonical byte order")
            member_names = [name for name in names if name != builder.MANIFEST_NAME]
            if any(name.lower().endswith(NESTED_ARCHIVE_SUFFIXES) for name in member_names):
                fail("package archive contains a nested archive")
            if any(name.lower().endswith(BINARY_SUFFIXES) for name in member_names):
                fail("package archive contains a binary artifact")
            for info in infos:
                posix = PurePosixPath(info.filename)
                if (
                    not info.filename
                    or "\\" in info.filename
                    or posix.is_absolute()
                    or ".." in posix.parts
                    or str(posix) != info.filename
                ):
                    fail(f"package archive contains an unsafe or non-canonical path: {info.filename}")
                if info.is_dir():
                    fail(f"package archive contains a directory entry: {info.filename}")
            try:
                manifest_bytes = archive.read(builder.MANIFEST_NAME)
                manifest = json.loads(manifest_bytes.decode("utf-8"))
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                fail(f"package archive contains an invalid package manifest: {exc}")
            if not isinstance(manifest, dict):
                fail("package manifest must be a JSON object")
            canonical_manifest = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
            if manifest_bytes != canonical_manifest:
                fail("package manifest JSON serialization is not canonical")
            if manifest.get("package_class") != "internal-validation":
                fail("package is not internal-validation only")
            if manifest.get("product_profile") != "enterprise-openssl":
                fail("package is not the supported enterprise-openssl profile")
            boundary.validate_manifest(root, manifest)

            expected_modes = {item["path"]: item["mode"] for item in manifest["files"]}
            expected_modes[builder.MANIFEST_NAME] = "0644"
            expected_names = sorted(expected_modes, key=lambda value: value.encode("utf-8"))
            if names != expected_names:
                fail("package archive file list does not exactly match the package manifest")
            timestamp = builder.zip_timestamp(int(manifest["source_date_epoch"]))
            contents: dict[str, bytes] = {}
            for info in infos:
                name = info.filename
                if info.date_time != timestamp:
                    fail(f"package archive timestamp is not normalized: {name}")
                if info.compress_type != zipfile.ZIP_STORED:
                    fail(f"package archive compression method is not deterministic: {name}")
                if info.create_system != 3 or info.create_version != 20 or info.extract_version != 20:
                    fail(f"package archive platform metadata is not normalized: {name}")
                if info.extra or info.comment or info.internal_attr:
                    fail(f"package archive contains non-empty extra metadata: {name}")
                expected_utf8_flag = any(ord(character) > 127 for character in name)
                if info.flag_bits not in {0, 0x800} or bool(info.flag_bits & 0x800) != expected_utf8_flag:
                    fail(f"package archive filename flags are not normalized: {name}")
                unix_mode = (info.external_attr >> 16) & 0xffff
                if stat.S_IFMT(unix_mode) != stat.S_IFREG or f"{stat.S_IMODE(unix_mode):04o}" != expected_modes[name]:
                    fail(f"package archive file mode mismatch: {name}")
                data = archive.read(info)
                if info.file_size != len(data) or info.CRC != zlib.crc32(data):
                    fail(f"package archive size or CRC mismatch: {name}")
                contents[name] = data
    except (OSError, zipfile.BadZipFile) as exc:
        fail(f"invalid package archive: {exc}")

    for item in manifest["files"]:
        data = contents[item["path"]]
        if len(data) != item["size"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            fail(f"package archive content mismatch: {item['path']}")
    if manifest["dependency_inventory_sha256"] != hashlib.sha256(
        contents["packaging/dependency-license-inventory.json"]
    ).hexdigest():
        fail("embedded dependency inventory digest mismatch")
    if manifest["third_party_notices_sha256"] != hashlib.sha256(contents["THIRD_PARTY_NOTICES.json"]).hexdigest():
        fail("embedded third-party notices digest mismatch")
    serialized = json.dumps(manifest, sort_keys=True)
    if re.search(r"(?:[A-Za-z]:[\\/]|/(?:home|Users|var|tmp)/)", serialized):
        fail("package manifest exposes an absolute local path")

    archive_bytes = path.read_bytes()
    archive_sha256 = hashlib.sha256(archive_bytes).hexdigest()
    if validate_sidecars:
        checksum_path = Path(f"{path}.sha256")
        build_path = path.with_suffix(".build.json")
        expected_checksum = f"{archive_sha256}  {path.name}\n"
        try:
            checksum = checksum_path.read_text(encoding="utf-8")
        except OSError as exc:
            fail(f"missing archive SHA-256 sidecar: {exc}")
        if checksum != expected_checksum:
            fail("archive SHA-256 sidecar mismatch")
        build = read_json(build_path, "build sidecar")
        if set(build) != BUILD_FIELDS:
            fail("build sidecar fields are invalid")
        expected_build = {
            "archive_filename": path.name,
            "archive_sha256": archive_sha256,
            "archive_size": len(archive_bytes),
            "enterprise_commit": manifest["enterprise_commit"],
            "community_baseline_commit": manifest["community_baseline_commit"],
            "package_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "archive_format": "zip",
            "reproducible": True,
        }
        if build != expected_build:
            fail("build sidecar does not match the package archive")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--root", default=ROOT, type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    validate_package(args.archive, args.root)
    print("reproducible internal package ok")


if __name__ == "__main__":
    main()
