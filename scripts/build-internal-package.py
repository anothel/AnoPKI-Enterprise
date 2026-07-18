#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Build a deterministic, internal-only AnoPKI Enterprise source package."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import stat
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "package-manifest.json"


def fail(message: str) -> None:
    raise SystemExit(message)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        fail(f"cannot load {path.name}")
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode:
        fail(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def require_clean_head(root: Path) -> str:
    head = git(root, "rev-parse", "HEAD")
    if len(head) != 40 or any(character not in "0123456789abcdef" for character in head):
        fail("package build requires an exact Git HEAD commit")
    dirty = git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if dirty:
        fail("package build requires a clean working tree:\n" + dirty)
    return head


def zip_timestamp(epoch: int) -> tuple[int, int, int, int, int, int]:
    if epoch < 315532800:
        return (1980, 1, 1, 0, 0, 0)
    if epoch >= 4354819200:
        return (2107, 12, 31, 23, 59, 58)
    value = datetime.fromtimestamp(epoch, timezone.utc)
    return (value.year, value.month, value.day, value.hour, value.minute, value.second // 2 * 2)


def zip_bytes(entries: dict[str, tuple[bytes, str]], epoch: int) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        archive.comment = b""
        for path in sorted(entries, key=lambda value: value.encode("utf-8")):
            data, mode = entries[path]
            info = zipfile.ZipInfo(path, zip_timestamp(epoch))
            info.create_system = 3
            info.create_version = 20
            info.extract_version = 20
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = (stat.S_IFREG | int(mode, 8)) << 16
            info.internal_attr = 0
            info.extra = b""
            info.comment = b""
            archive.writestr(info, data)
    return output.getvalue()


def build_package(
    root: Path,
    out: Path,
    profile: str = "enterprise-openssl",
    package_class: str = "internal-validation",
    archive_format: str = "zip",
    require_clean: bool = True,
) -> dict[str, object]:
    root = root.resolve()
    if profile != "enterprise-openssl":
        fail("only enterprise-openssl internal packaging is supported")
    if package_class != "internal-validation":
        fail("customer release package creation is not authorized")
    if archive_format != "zip" or out.suffix.lower() != ".zip":
        fail("only deterministic ZIP output is supported")
    head = require_clean_head(root) if require_clean else git(root, "rev-parse", "HEAD")

    generator = load_module("generate_package_manifest", ROOT / "scripts/generate-package-manifest.py")
    boundary = load_module("validate_package_boundary", ROOT / "scripts/validate-package-boundary.py")
    boundary.validate(root)
    manifest = generator.build_manifest(root, profile, package_class, archive_format)
    if manifest["enterprise_commit"] != head:
        fail("generated package manifest does not bind the exact HEAD")

    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    paths = [item["path"] for item in manifest["files"]]
    entries = generator.git_files(root, paths)
    entries[MANIFEST_NAME] = (manifest_bytes, "0644")
    archive_bytes = zip_bytes(entries, int(manifest["source_date_epoch"]))
    archive_sha256 = hashlib.sha256(archive_bytes).hexdigest()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    build = {
        "archive_filename": out.name,
        "archive_sha256": archive_sha256,
        "archive_size": len(archive_bytes),
        "enterprise_commit": manifest["enterprise_commit"],
        "community_baseline_commit": manifest["community_baseline_commit"],
        "package_manifest_sha256": manifest_sha256,
        "archive_format": archive_format,
        "reproducible": True,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(archive_bytes)
    Path(f"{out}.sha256").write_text(f"{archive_sha256}  {out.name}\n", encoding="utf-8", newline="\n")
    out.with_suffix(".build.json").write_text(
        json.dumps(build, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return build


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT, type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--profile", required=True, choices=("enterprise-openssl", "enterprise-anocrypto-c"))
    parser.add_argument("--package-class", default="internal-validation")
    parser.add_argument("--format", required=True, choices=("zip", "tar.gz"))
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    build = build_package(args.root, args.out, args.profile, args.package_class, args.format)
    print(f"internal package built: {args.out}")
    print(f"sha256: {build['archive_sha256']}")


if __name__ == "__main__":
    main()
