#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Render deterministic third-party notices from tracked evidence inventory."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = Path("packaging/dependency-license-inventory.json")
OUTPUTS = {
    Path("THIRD_PARTY_NOTICES.md"): "markdown",
    Path("THIRD_PARTY_NOTICES.json"): "json",
}
LOCAL_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|/(?:home|Users|var|tmp)/)")


def fail(message: str) -> None:
    raise SystemExit(message)


def read_inventory(root: Path) -> dict[str, object]:
    try:
        value = json.loads((root / INVENTORY).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid dependency license inventory: {exc}")
    if not isinstance(value, dict) or not isinstance(value.get("dependencies"), list):
        fail("dependency license inventory must contain a dependencies list")
    return value


def git_head(root: Path) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False)
    value = result.stdout.strip()
    if result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", value):
        fail(result.stderr.strip() or "unable to resolve Enterprise commit")
    return value


def dependency_key(item: dict[str, object]) -> tuple[str, str, str, str]:
    license_files = item.get("license_files")
    first_license = min(license_files) if isinstance(license_files, list) and license_files else ""
    return str(item.get("type")), str(item.get("module_or_package")), str(item.get("version")), first_license


def normalized_inventory(inventory: dict[str, object]) -> dict[str, object]:
    value = deepcopy(inventory)
    dependencies = value["dependencies"]
    if not all(isinstance(item, dict) for item in dependencies):
        fail("dependency entries must be objects")
    value["dependencies"] = sorted(dependencies, key=dependency_key)
    return value


def render_json(inventory: dict[str, object]) -> str:
    return json.dumps(normalized_inventory(inventory), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def evidence_lines(item: dict[str, object], field: str) -> list[str]:
    paths = item.get(field)
    hashes = item.get("license_file_sha256")
    if not isinstance(paths, list) or not isinstance(hashes, dict):
        fail(f"invalid {field} for {item.get('name')}")
    if not paths:
        return ["  - None"]
    return [f"  - [{path}]({path}) - SHA-256 `{hashes.get(path, 'missing')}`" for path in sorted(paths)]


def component_lines(item: dict[str, object]) -> list[str]:
    components = item.get("license_components", [])
    if not isinstance(components, list):
        fail(f"invalid license_components for {item.get('name')}")
    if not components:
        return []
    lines = ["- License component mapping:"]
    for component in components:
        if not isinstance(component, dict) or not isinstance(component.get("scope"), list):
            fail(f"invalid license component for {item.get('name')}")
        scope = ", ".join(f"`{value}`" for value in component["scope"])
        lines.append(
            f"  - `{component.get('license_expression')}`: {scope}; "
            f"evidence [{component.get('evidence_file')}]({component.get('evidence_file')})"
        )
    return lines


def render_markdown(inventory: dict[str, object]) -> str:
    inventory = normalized_inventory(inventory)
    lines = [
        "# Third-Party Notices",
        "",
        "This file is generated from `packaging/dependency-license-inventory.json`.",
        "It is evidence metadata, not legal advice or a replacement for the included license texts.",
        "",
        f"- Product: {inventory.get('product')}",
        f"- Edition: {inventory.get('edition')}",
        f"- Enterprise commit: `{inventory.get('enterprise_commit')}`",
        f"- Community baseline: `{inventory.get('community_baseline_commit')}`",
        f"- Unresolved dependencies: {inventory.get('unresolved_count')}",
        f"- Customer distribution ready: {str(inventory.get('customer_distribution_ready')).lower()}",
        "",
    ]
    for item in inventory["dependencies"]:
        direct = "Direct" if item.get("direct") is True else "Indirect"
        provenance = json.dumps(item.get("provenance"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        review = "required" if item.get("redistribution_review_required") is True else "complete"
        allowed = "allowed" if item.get("customer_package_allowed") is True else "blocked"
        lines.extend(
            [
                f"## {item.get('name')}",
                "",
                f"- Component: `{item.get('module_or_package')}` (`{item.get('type')}`)",
                f"- Version: `{item.get('version')}`",
                f"- Direct/Indirect: {direct}",
                f"- License expression: `{item.get('license_expression')}`",
                *component_lines(item),
                f"- Evidence status: `{item.get('evidence_status')}`",
                f"- Source/provenance: `{item.get('source')}`; `{provenance}`",
                "- Included license files:",
                *evidence_lines(item, "license_files"),
                "- Included notices:",
                *evidence_lines(item, "notice_files"),
                f"- Redistribution review status: {review}; customer package {allowed}",
                "",
            ]
        )
    return "\n".join(lines)


def build_outputs(root: Path = ROOT) -> dict[Path, str]:
    inventory = read_inventory(root)
    outputs = {
        Path("THIRD_PARTY_NOTICES.md"): render_markdown(inventory),
        Path("THIRD_PARTY_NOTICES.json"): render_json(inventory),
    }
    for path, content in outputs.items():
        if LOCAL_PATH_RE.search(content):
            fail(f"generated notice exposes an absolute local path: {path}")
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT, type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--refresh-commit", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.check and args.refresh_commit:
        fail("--check and --refresh-commit cannot be combined")
    if args.refresh_commit:
        inventory = read_inventory(root)
        inventory["enterprise_commit"] = git_head(root)
        (root / INVENTORY).write_text(render_json(inventory), encoding="utf-8", newline="\n")
    stale: list[str] = []
    for path, content in build_outputs(root).items():
        target = root / path
        if args.check:
            try:
                current = target.read_text(encoding="utf-8")
            except OSError:
                current = ""
            if current != content:
                stale.append(path.as_posix())
        else:
            target.write_text(content, encoding="utf-8", newline="\n")
    if stale:
        fail("stale generated third-party notices:\n" + "\n".join(stale))
    print("third-party notices ok" if args.check else "third-party notices generated")


if __name__ == "__main__":
    main()
