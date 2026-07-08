#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Self-checks for the Enterprise Community sync helper."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    doc = (ROOT / "docs/enterprise/upstream-sync.md").read_text(encoding="utf-8")
    script = (ROOT / "scripts/sync-community-upstream.ps1").read_text(encoding="utf-8")

    required_doc_text = [
        "git remote add community",
        "git fetch community",
        "git merge --no-ff community/main",
        "Never push Enterprise-only material back to Community",
        "python scripts\\validate-enterprise-boundary.py",
        "python scripts\\validate-docs.py",
    ]
    missing = [text for text in required_doc_text if text not in doc]
    if missing:
        raise SystemExit("upstream sync doc missing required text:\n" + "\n".join(missing))

    forbidden_script_text = ["git push", "git merge", "git reset"]
    present = [text for text in forbidden_script_text if text in script]
    if present:
        raise SystemExit("sync helper must not run destructive git commands:\n" + "\n".join(present))

    required_script_text = [
        "git remote get-url",
        "git remote add",
        "git fetch",
        "git status --short",
        "validate-enterprise-boundary.py",
        "validate-docs.py",
    ]
    missing = [text for text in required_script_text if text not in script]
    if missing:
        raise SystemExit("sync helper missing required safety text:\n" + "\n".join(missing))

    print("sync helper tests ok")


if __name__ == "__main__":
    main()
