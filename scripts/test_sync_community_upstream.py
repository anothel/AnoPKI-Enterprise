#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Self-checks for exact-tree Community synchronization governance."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = "ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc"
PREVIOUS = "acb71b8f4e9133d9c25dad1be3bca58209fba0d7"


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
        "exact lowercase 40-character SHA",
        "must not reuse the stale previous baseline",
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
        'COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")',
        "must not reuse the stale previous baseline",
        "COMMUNITY_ONLY_FILES",
        "MIXED_REQUIRED_TEXT",
        "stale files deleted by Community target",
        "drifted exact Community files",
        "src/backends/openssl/key_providers/file_key_provider.cpp",
        "test_generate_enterprise_release_metadata.py",
        "anopki-recovery-verification",
        "anopki-status-outage-verification",
        "anopki-audit-replay-verification",
    ]
    missing = [text for text in required_validator_text if text not in validator]
    if missing:
        raise SystemExit("baseline validator missing exact-tree coverage:\n" + "\n".join(missing))

    print("sync helper tests ok")


if __name__ == "__main__":
    main()
