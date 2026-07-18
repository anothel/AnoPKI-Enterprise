#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Generate a deterministic manifest from an explicit Enterprise package allow-list."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from io import BytesIO
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = Path("packaging/license-inventory.json")
DEPENDENCY_INVENTORY_PATH = Path("packaging/dependency-license-inventory.json")
POLICY_PATH = Path("packaging/package-policy.json")
SHA_RE = re.compile(r"[0-9a-f]{40}")


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


def normalized_path(value: str) -> str:
    value = value.replace("\\", "/")
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or str(path) != value:
        fail(f"allow-list path is not normalized and relative: {value!r}")
    if re.match(r"^[A-Za-z]:", value):
        fail(f"allow-list path must not be absolute: {value!r}")
    if any(character in value for character in "*?[]"):
        fail(f"allow-list path must be exact, not a glob: {value}")
    return value


def parse_allowlist(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        fail(f"cannot read package allow-list {path}: {exc}")
    values = [normalized_path(line.strip()) for line in lines if line.strip() and not line.lstrip().startswith("#")]
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        fail("duplicate package allow-list paths:\n" + "\n".join(duplicates))
    case_counts = Counter(value.casefold() for value in values)
    collisions = sorted(value for value in values if case_counts[value.casefold()] > 1)
    if collisions:
        fail("case-insensitive package path collision:\n" + "\n".join(collisions))
    return sorted(values, key=lambda value: value.encode("utf-8"))


def git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    value = result.stdout.strip()
    if result.returncode != 0 or not SHA_RE.fullmatch(value):
        fail(result.stderr.strip() or "unable to resolve exact Enterprise commit")
    return value


def source_date_epoch(root: Path) -> int:
    result = subprocess.run(
        ["git", "show", "-s", "--format=%ct", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    value = result.stdout.strip()
    if result.returncode != 0 or not re.fullmatch(r"-?[0-9]+", value):
        fail(result.stderr.strip() or "unable to resolve SOURCE_DATE_EPOCH from HEAD")
    epoch = int(value)
    injected = os.environ.get("SOURCE_DATE_EPOCH")
    if injected is not None and (not re.fullmatch(r"-?[0-9]+", injected) or int(injected) != epoch):
        fail("SOURCE_DATE_EPOCH must exactly match the HEAD commit timestamp")
    return epoch


def git_files(root: Path, paths: list[str]) -> dict[str, tuple[bytes, str]]:
    tree = subprocess.run(
        ["git", "ls-tree", "-rz", "HEAD"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if tree.returncode != 0:
        fail(tree.stderr.decode(errors="replace").strip() or "unable to inspect HEAD tree")
    head_entries: dict[str, tuple[str, bytes]] = {}
    for record in tree.stdout.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, object_id = metadata.split()
        path = raw_path.decode("utf-8")
        if kind == b"blob":
            head_entries[path] = (mode.decode("ascii"), object_id)

    index = subprocess.run(
        ["git", "ls-files", "--stage", "-z"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if index.returncode != 0:
        fail(index.stderr.decode(errors="replace").strip() or "unable to inspect Git index")
    entries: dict[str, tuple[str, bytes]] = {}
    for record in index.stdout.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, object_id, stage = metadata.split()
        if stage == b"0":
            entries[raw_path.decode("utf-8")] = (mode.decode("ascii"), object_id)

    missing = sorted((set(paths) - set(entries)) | (set(paths) - set(head_entries)))
    if missing:
        fail("package allow-list contains paths absent from HEAD or index:\n" + "\n".join(missing))
    mismatched = sorted(path for path in paths if entries[path] != head_entries[path])
    if mismatched:
        fail("package index entry does not match HEAD:\n" + "\n".join(mismatched))
    invalid_modes = sorted(path for path in paths if entries[path][0] not in {"100644", "100755"})
    if invalid_modes:
        fail("package contains a symlink or unsupported Git mode:\n" + "\n".join(invalid_modes))

    process = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=root,
        input=b"".join(entries[path][1] + b"\n" for path in paths),
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        fail(process.stderr.decode(errors="replace").strip() or "unable to read package blobs from HEAD")
    output = BytesIO(process.stdout)
    result: dict[str, tuple[bytes, str]] = {}
    for path in paths:
        header = output.readline().split()
        if len(header) != 3 or header[1] != b"blob" or not header[2].isdigit():
            fail(f"invalid Git blob response for package path: {path}")
        data = output.read(int(header[2]))
        if len(data) != int(header[2]) or output.read(1) != b"\n":
            fail(f"truncated Git blob response for package path: {path}")
        result[path] = (data, "0755" if entries[path][0] == "100755" else "0644")
    return result


def component_for_path(components: list[dict[str, object]], path: str) -> dict[str, object]:
    for component in components:
        scopes = component.get("source_scope")
        if not isinstance(scopes, list):
            continue
        if any(isinstance(pattern, str) and not pattern.startswith("external:") and fnmatch.fnmatchcase(path, pattern) for pattern in scopes):
            return component
    fail(f"package path is not covered by the license inventory: {path}")


def selected_components(
    components: list[dict[str, object]], file_components: list[dict[str, object]], profile: str, paths: list[str]
) -> list[dict[str, object]]:
    names = {str(component["name"]) for component in file_components}
    if any(path.startswith("service/") for path in paths):
        names.add("go-module-dependencies")
    names.add("openssl-runtime-dependency" if profile == "enterprise-openssl" else "anocrypto-c-external-sdk")
    return sorted((component for component in components if str(component.get("name")) in names), key=lambda item: str(item["name"]))


def build_manifest(root: Path, profile: str, package_class: str, archive_format: str = "zip") -> dict[str, object]:
    root = root.resolve()
    inventory = read_json(root / INVENTORY_PATH, "license inventory")
    dependency_inventory = read_json(root / DEPENDENCY_INVENTORY_PATH, "dependency license inventory")
    policy = read_json(root / POLICY_PATH, "package policy")
    edition_metadata = read_json(root / ".edition/edition.json", "edition metadata")
    profiles = policy.get("profiles")
    classes = policy.get("package_classes")
    if not isinstance(profiles, dict) or profile not in profiles:
        fail(f"unknown package profile: {profile}")
    if not isinstance(classes, dict) or package_class not in classes:
        fail(f"unknown package class: {package_class}")
    profile_policy = profiles[profile]
    class_policy = classes[package_class]
    if not isinstance(profile_policy, dict) or not isinstance(class_policy, dict):
        fail("invalid package policy structure")
    formats = class_policy.get("allowed_archive_formats")
    if archive_format != "zip" or not isinstance(formats, list) or archive_format not in formats:
        fail(f"unsupported archive format for {package_class}: {archive_format}")

    if package_class == "customer-release":
        blockers: list[str] = []
        if inventory.get("commercial_license_status") != "complete":
            blockers.append("final commercial license is incomplete")
        if inventory.get("customer_distribution_authorized") is not True:
            blockers.append("customer distribution is not authorized by the license inventory")
        if policy.get("customer_distribution_authorized") is not True or class_policy.get("authorized") is not True:
            blockers.append("customer package policy is not authorized")
        if profile_policy.get("production_ready") is not True:
            blockers.append(f"{profile} is not production ready")
        dependencies = dependency_inventory.get("dependencies")
        if dependency_inventory.get("unresolved_count") != 0 or not isinstance(dependencies, list):
            blockers.append("third-party dependency license evidence is unresolved")
        elif any(
            not isinstance(item, dict)
            or item.get("evidence_status") != "verified"
            or item.get("redistribution_review_required") is not False
            or item.get("customer_package_allowed") is not True
            for item in dependencies
        ):
            blockers.append("third-party dependency redistribution review is incomplete")
        components = inventory.get("components")
        if profile == "enterprise-anocrypto-c" and isinstance(components, list):
            anocrypto = next(
                (item for item in components if isinstance(item, dict) and item.get("name") == "anocrypto-c-external-sdk"),
                {},
            )
            if anocrypto.get("evidence_status") == "external_license_unresolved":
                blockers.append("AnoCrypto-C SDK license is unresolved")
        if blockers:
            fail("customer release blocked:\n" + "\n".join(blockers))

    manifests = profile_policy.get("manifests")
    if not isinstance(manifests, dict) or not isinstance(manifests.get(package_class), str):
        fail(f"missing allow-list binding for {profile}/{package_class}")
    paths = parse_allowlist(root / str(manifests[package_class]))
    if not paths:
        fail(f"package allow-list is empty: {profile}/{package_class}")

    dependencies = dependency_inventory.get("dependencies")
    if not isinstance(dependencies, list) or not all(isinstance(item, dict) for item in dependencies):
        fail("dependency license inventory dependencies must be objects")
    required_dependency_paths = {
        "THIRD_PARTY_NOTICES.md",
        "THIRD_PARTY_NOTICES.json",
        DEPENDENCY_INVENTORY_PATH.as_posix(),
        *(
            path
            for item in dependencies
            for field in ("license_files", "notice_files")
            for path in item.get(field, [])
            if isinstance(path, str)
        ),
    }
    missing_dependency_paths = sorted(required_dependency_paths - set(paths))
    if missing_dependency_paths:
        fail("package allow-list is missing dependency license evidence:\n" + "\n".join(missing_dependency_paths))

    approved_generated = policy.get("approved_generated_paths")
    if not isinstance(approved_generated, list) or not all(isinstance(item, str) for item in approved_generated):
        fail("approved_generated_paths must be a list of exact paths")
    if approved_generated:
        fail("internal packages require every allow-listed path to be tracked")
    sources = git_files(root, paths)

    components_value = inventory.get("components")
    if not isinstance(components_value, list) or not all(isinstance(item, dict) for item in components_value):
        fail("license inventory components must be objects")
    components: list[dict[str, object]] = components_value
    files: list[dict[str, object]] = []
    file_components: list[dict[str, object]] = []
    for path in paths:
        data, mode = sources[path]
        component = component_for_path(components, path)
        file_components.append(component)
        files.append(
            {
                "path": path,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
                "ownership": component["ownership"],
                "license_expression": component["license_expression"],
                "distribution_scope": component["distribution_scope"],
                "mode": mode,
            }
        )

    included = selected_components(components, file_components, profile, paths)
    licenses = [
        {
            "component": component["name"],
            "license_expression": component["license_expression"],
            "license_file": component["license_file"],
            "evidence_status": component["evidence_status"],
        }
        for component in included
    ]
    notices = sorted(
        {
            notice
            for component in included
            for notice in component["required_notices"]
            if isinstance(notice, str)
        }
    )
    manifest = {
        "schema_version": 1,
        "product": inventory.get("product"),
        "edition": inventory.get("edition"),
        "product_profile": profile,
        "enterprise_commit": git_head(root),
        "community_baseline_commit": inventory.get("community_baseline_commit"),
        "source_date_epoch": source_date_epoch(root),
        "archive_format": archive_format,
        "dependency_inventory_sha256": hashlib.sha256(sources[DEPENDENCY_INVENTORY_PATH.as_posix()][0]).hexdigest(),
        "third_party_notices_sha256": hashlib.sha256(sources["THIRD_PARTY_NOTICES.json"][0]).hexdigest(),
        "package_class": package_class,
        "commercial_license_status": inventory.get("commercial_license_status"),
        "customer_distribution_authorized": inventory.get("customer_distribution_authorized"),
        "selected_adapter": profile_policy.get("selected_adapter"),
        "fallback_enabled": False,
        "fallback_used": False,
        "files": files,
        "licenses": licenses,
        "notices": notices,
        "production_ready": profile_policy.get("production_ready"),
        "kcmvp_status": edition_metadata.get("kcmvp_status"),
    }
    serialized = json.dumps(manifest, sort_keys=True)
    if re.search(r"(?:[A-Za-z]:[\\/]|/(?:home|Users|var|tmp)/)", serialized):
        fail("generated package manifest exposes an absolute local path")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT, type=Path)
    parser.add_argument("--profile", required=True, choices=("enterprise-openssl", "enterprise-anocrypto-c"))
    parser.add_argument("--package-class", required=True, choices=("internal-validation", "customer-release"))
    parser.add_argument("--archive-format", default="zip", choices=("zip",))
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    manifest = build_manifest(args.root, args.profile, args.package_class, args.archive_format)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"package manifest generated: {args.out}")


if __name__ == "__main__":
    main()
