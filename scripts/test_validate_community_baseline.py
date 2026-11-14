#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Exercise exact baseline and reviewed-patch checks against a real Git tree."""

import hashlib
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("baseline", ROOT / "scripts/validate-community-baseline.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), "-c", "user.name=Baseline Test", "-c", "user.email=test@example.invalid", *args],
        stderr=subprocess.DEVNULL,
    ).decode().strip()


def rejected(root, expected):
    try:
        validator.validate(root)
    except SystemExit as exc:
        assert expected in str(exc), str(exc)
    else:
        raise AssertionError("unreviewed drift was accepted")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        git(root, "init", "-b", "baseline-test")
        shared = root / "shared.txt"
        shared.write_bytes(b"upstream\n")
        git(root, "add", "shared.txt")
        git(root, "commit", "-m", "previous")
        validator.PREVIOUS_BASELINE_COMMIT = git(root, "rev-parse", "HEAD")
        (root / "unchanged.txt").write_bytes(b"unchanged\n")
        git(root, "add", "unchanged.txt")
        git(root, "commit", "-m", "pinned")
        validator.BASELINE_COMMIT = git(root, "rev-parse", "HEAD")
        (root / ".edition").mkdir()
        (root / ".edition/edition.json").write_text(json.dumps({
            "community_baseline_commit": validator.BASELINE_COMMIT,
        }))
        validator.MIXED_REQUIRED_TEXT = {}
        validator.COMMUNITY_ONLY_FILES = set()
        validator.ENTERPRISE_REQUIRED_FILES = set()
        validator.REVIEWED_ENTERPRISE_PATCHES = {}
        validator.validate(root)
        shared.write_bytes(b"reviewed fix\n")
        rejected(root, "drifted exact Community files")
        validator.REVIEWED_ENTERPRISE_PATCHES = {
            "shared.txt": (
                hashlib.sha256(b"upstream\n").hexdigest(),
                hashlib.sha256(b"reviewed fix\n").hexdigest(),
            ),
        }
        validator.validate(root)
        shared.write_bytes(b"reviewed fix\r\n")
        validator.validate(root)
        shared.write_bytes(b"unreviewed change\n")
        rejected(root, "drifted exact Community files")
        shared.write_bytes(b"reviewed fix\n")
        (root / "unchanged.txt").write_bytes(b"unreviewed other file\n")
        rejected(root, "unchanged.txt")
        (root / "unchanged.txt").write_bytes(b"unchanged\n")
        validator.REVIEWED_ENTERPRISE_PATCHES["shared.txt"] = (
            hashlib.sha256(b"different upstream\n").hexdigest(),
            hashlib.sha256(b"reviewed fix\n").hexdigest(),
        )
        rejected(root, "drifted exact Community files")
        shared.unlink()
        rejected(root, "missing exact Community files")
        validator.REVIEWED_ENTERPRISE_PATCHES = {"unknown.txt": ("", "")}
        rejected(root, "reviewed patches outside exact Community files")
    print("Community baseline patch tests ok")


if __name__ == "__main__":
    main()
