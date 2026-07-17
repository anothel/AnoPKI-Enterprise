#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Self-checks for exact-tree Community synchronization governance."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = "71f0e898c32a7d6e00d0725eeab6ca150ccaa0af"
PREVIOUS = "b4b5c475c3cb2f98f5bb6c180786c11a12a1dac8"


def main() -> None:
    doc = (ROOT / "docs/enterprise/upstream-sync.md").read_text(encoding="utf-8")
    script = (ROOT / "scripts/sync-community-upstream.ps1").read_text(encoding="utf-8")
    validator = (ROOT / "scripts/validate-community-baseline.py").read_text(encoding="utf-8")

    required_doc_text = [
        "git remote add community",
        "git fetch community",
        TARGET,
        PREVIOUS,
        "exact target tree",
        "Community-only",
        "python scripts\\validate-community-baseline.py",
        "Never push Enterprise-only material back to Community",
    ]
    missing = [text for text in required_doc_text if text not in doc]
    if missing:
        raise SystemExit("upstream sync doc missing exact-tree guidance:\n" + "\n".join(missing))

    forbidden = ["git merge", "git rebase", "git cherry-pick", "git subtree"]
    present = [text for text in forbidden if text in doc or text in script]
    if present:
        raise SystemExit("sync governance contains forbidden history integration commands:\n" + "\n".join(present))

    required_script_text = [
        "TargetCommit",
        TARGET,
        PREVIOUS,
        'Invoke-Git @("cat-file", "-e"',
        'Invoke-Git @("diff", "--name-status"',
        "validate-community-baseline.py",
        "pinned target tree",
    ]
    missing = [text for text in required_script_text if text not in script]
    if missing:
        raise SystemExit("sync helper missing exact-tree safety markers:\n" + "\n".join(missing))

    required_validator_text = [
        f'BASELINE_COMMIT = "{TARGET}"',
        "COMMUNITY_ONLY_FILES",
        "MIXED_REQUIRED_TEXT",
        "stale files deleted by Community target",
        "drifted exact Community files",
        "src/backends/openssl/key_providers/file_key_provider.cpp",
        "test_generate_enterprise_release_metadata.py",
    ]
    missing = [text for text in required_validator_text if text not in validator]
    if missing:
        raise SystemExit("baseline validator missing exact-tree coverage:\n" + "\n".join(missing))

    print("sync helper tests ok")


if __name__ == "__main__":
    main()
