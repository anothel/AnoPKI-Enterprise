#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Verify Community-owned files against the recorded Enterprise baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_COMMIT = "2be155780d4b024c76b0a901ec130e83fc221f2f"

EXCLUDED_PREFIXES = (
    ".edition/",
    "docs/edition/",
    "docs/enterprise/",
    "docs-pack/",
    "enterprise/",
    "include/anopki/enterprise/",
    "LICENSES/",
    "service/internal/enterprise/",
    "src/backends/anocrypto_c/",
    "src/enterprise/",
)
EXCLUDED_FILES = {
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
    "CMakeLists.txt",
    "EDITION.md",
    "ENTERPRISE-LICENSE-NOTICE.md",
    "LICENSE",
    "scripts/test_validate_community_boundary.py",
    "scripts/test_validate_docs.py",
    "scripts/test_validate_version_metadata.py",
    "scripts/validate-community-boundary.py",
    "scripts/validate-docs.py",
    "scripts/validate-version-metadata.py",
}
ALLOWED_PATCHES = {
    # Deterministic checksum corruption; upstream baseline can mutate a filename instead of the digest.
    "scripts/test_validate_release_artifacts.py": "46403195b1f2529d4c45ae0cc2d2173de7bbbf2e3cf359b286e9be054ee5b4cf",
}


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
    )
    if result.returncode != 0:
        message = result.stderr.decode(errors="replace").strip()
        raise SystemExit(message or f"git {' '.join(args)} failed")
    return result.stdout


def excluded(path: str) -> bool:
    return path in EXCLUDED_FILES or path.startswith(EXCLUDED_PREFIXES)


def normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def validate(root: Path) -> None:
    root = root.resolve()
    edition = json.loads((root / ".edition/edition.json").read_text(encoding="utf-8"))
    if edition.get("community_baseline_commit") != BASELINE_COMMIT:
        raise SystemExit("Enterprise edition metadata does not match recorded Community baseline")

    git(root, "cat-file", "-e", f"{BASELINE_COMMIT}^{{commit}}")
    paths = git(root, "ls-tree", "-r", "--name-only", BASELINE_COMMIT).decode().splitlines()
    missing: list[str] = []
    changed: list[str] = []
    for rel in paths:
        if excluded(rel):
            continue
        path = root / rel
        if not path.is_file():
            missing.append(rel)
            continue
        upstream = git(root, "show", f"{BASELINE_COMMIT}:{rel}")
        current = normalized(path.read_bytes())
        if current != normalized(upstream) and ALLOWED_PATCHES.get(rel) != hashlib.sha256(current).hexdigest():
            changed.append(rel)

    if missing or changed:
        details = []
        if missing:
            details.append("missing Community baseline files:\n" + "\n".join(missing))
        if changed:
            details.append("drifted Community baseline files:\n" + "\n".join(changed))
        raise SystemExit("\n".join(details))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT, type=Path)
    args = parser.parse_args()
    validate(args.root)
    print(f"community baseline ok: {BASELINE_COMMIT}")


if __name__ == "__main__":
    main()
