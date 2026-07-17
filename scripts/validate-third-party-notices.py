#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Validate tracked dependency license evidence without a module cache."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = Path("packaging/dependency-license-inventory.json")
LEGACY_INVENTORY_PATH = Path("packaging/license-inventory.json")
POLICY_PATH = Path("packaging/package-policy.json")
GENERATOR = ROOT / "scripts/generate-third-party-notices.py"
ATTRIBUTES_PATH = Path(".gitattributes")
WHITESPACE_EVIDENCE_PATH = "LICENSES/third-party/go/gopkg.in_check.v1/v1.0.0-20201130134442-10cb98267c6c/LICENSE"
WHITESPACE_ATTRIBUTE = "whitespace=-trailing-space"
SHA_RE = re.compile(r"[0-9a-f]{64}")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
LOCAL_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|/(?:home|Users|var|tmp)/)")
TOP_FIELDS = {
    "schema_version",
    "product",
    "edition",
    "enterprise_commit",
    "community_baseline_commit",
    "generated_from",
    "dependencies",
    "unresolved_count",
    "customer_distribution_ready",
}
DEPENDENCY_FIELDS = {
    "name",
    "type",
    "module_or_package",
    "version",
    "direct",
    "source",
    "source_sha256",
    "license_expression",
    "license_files",
    "license_file_sha256",
    "notice_files",
    "provenance",
    "evidence_status",
    "redistribution_review_required",
    "customer_package_allowed",
}
OPTIONAL_DEPENDENCY_FIELDS = {"license_components"}


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


def require_fields(value: dict[str, object], expected: set[str], label: str) -> None:
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    if missing or extra:
        fail(f"{label} fields are invalid: missing={missing}, unknown={extra}")


def parse_go_sum(path: Path) -> tuple[dict[tuple[str, str], str], dict[tuple[str, str], str]]:
    module_sums: dict[tuple[str, str], str] = {}
    go_mod_sums: dict[tuple[str, str], str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        fail(f"cannot read service/go.sum: {exc}")
    for line in lines:
        parts = line.split()
        if len(parts) != 3:
            fail(f"invalid service/go.sum line: {line}")
        module, version, digest = parts
        target = go_mod_sums if version.endswith("/go.mod") else module_sums
        version = version.removesuffix("/go.mod")
        key = (module, version)
        if key in target and target[key] != digest:
            fail(f"conflicting service/go.sum entry: {module}@{version}")
        target[key] = digest
    return module_sums, go_mod_sums


def parse_go_mod(path: Path) -> tuple[dict[str, tuple[str, bool]], dict[str, str]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        fail(f"cannot read service/go.mod: {exc}")
    requirements: dict[str, tuple[str, bool]] = {}
    replacements: dict[str, str] = {}
    in_require = False
    in_replace = False
    for raw in lines:
        stripped = raw.strip()
        if stripped == "require (":
            in_require = True
            continue
        if stripped == "replace (":
            in_replace = True
            continue
        if stripped == ")":
            in_require = in_replace = False
            continue
        if not stripped or stripped.startswith("//"):
            continue
        if in_require or stripped.startswith("require "):
            value = stripped.removeprefix("require ").strip()
            code, _, comment = value.partition("//")
            parts = code.split()
            if len(parts) != 2:
                fail(f"unsupported service/go.mod require: {raw}")
            requirements[parts[0]] = (parts[1], "indirect" not in comment)
        elif in_replace or stripped.startswith("replace "):
            value = stripped.removeprefix("replace ").strip()
            left, separator, right = value.partition("=>")
            if not separator or not left.strip() or not right.strip():
                fail(f"unsupported service/go.mod replace: {raw}")
            replacements[left.split()[0]] = right.strip()
    return requirements, replacements


def classify_license(text: str) -> str:
    if (
        "covered by two different licenses: MIT and Apache" in text
        and "Permission is hereby granted" in text
        and "Licensed under the Apache License, Version 2.0" in text
    ):
        return "MIT AND Apache-2.0"
    if re.search(r"Apache License\s+Version 2\.0", text) or "Licensed under the Apache License, Version 2.0" in text:
        return "Apache-2.0"
    if "Permission to use, copy, modify, and/or distribute this software" in text and "with or without fee" in text:
        return "ISC"
    if "Permission is hereby granted, free of charge" in text:
        return "MIT"
    if "Redistribution and use in source and binary forms" in text:
        three_clause = re.search(
            r"Neither the name|Neither the names|names? of (?:its|the) contributors may not|3\. Neither", text
        )
        return "BSD-3-Clause" if three_clause else "BSD-2-Clause"
    return "NOASSERTION"


def expected_license_components(text: str, evidence_file: str) -> list[dict[str, object]]:
    if "covered by two different licenses: MIT and Apache" not in text:
        return []
    return [
        {
            "evidence_file": evidence_file,
            "license_expression": "MIT",
            "scope": [
                "apic.go",
                "emitterc.go",
                "parserc.go",
                "readerc.go",
                "scannerc.go",
                "writerc.go",
                "yamlh.go",
                "yamlprivateh.go",
            ],
        },
        {
            "evidence_file": evidence_file,
            "license_expression": "Apache-2.0",
            "scope": ["all remaining project files"],
        },
    ]


def normalized_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str):
        fail(f"{label} must be a path string")
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or str(path) != value or not value.startswith("LICENSES/third-party/"):
        fail(f"{label} is not a normalized third-party evidence path: {value!r}")
    return value


def safe_module_name(module: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", module)


def validate_evidence(root: Path, dependency: dict[str, object]) -> None:
    license_files = dependency.get("license_files")
    notice_files = dependency.get("notice_files")
    hashes = dependency.get("license_file_sha256")
    if not isinstance(license_files, list) or not isinstance(notice_files, list) or not isinstance(hashes, dict):
        fail(f"invalid evidence lists for {dependency.get('name')}")
    if license_files != sorted(set(license_files)) or notice_files != sorted(set(notice_files)):
        fail(f"evidence paths must be sorted and unique for {dependency.get('name')}")
    paths = [normalized_relative_path(item, "evidence path") for item in [*license_files, *notice_files]]
    if set(hashes) != set(paths):
        fail(f"evidence SHA-256 map mismatch for {dependency.get('name')}")
    license_text = ""
    for path in paths:
        source = root / path
        try:
            data = source.read_bytes()
        except OSError as exc:
            fail(f"missing dependency evidence {path}: {exc}")
        if b"\r" in data:
            fail(f"dependency evidence is not LF-normalized: {path}")
        digest = hashlib.sha256(data).hexdigest()
        if hashes.get(path) != digest:
            fail(f"dependency evidence SHA-256 mismatch: {path}")
        if path in license_files:
            try:
                license_text += data.decode("utf-8")
            except UnicodeDecodeError as exc:
                fail(f"dependency license is not UTF-8 text: {path}: {exc}")
    expression = classify_license(license_text)
    expected = dependency.get("license_expression")
    status = dependency.get("evidence_status")
    component_file = license_files[0] if len(license_files) == 1 else ""
    components = dependency.get("license_components", [])
    if components != expected_license_components(license_text, component_file):
        fail(f"license component mapping mismatch for {dependency.get('name')}")
    if expression == "NOASSERTION" or not license_files:
        if expected != "NOASSERTION" or status != "unresolved" or dependency.get("customer_package_allowed") is not False:
            fail(f"unrecognized license evidence must fail closed: {dependency.get('name')}")
    elif expected != expression or status != "verified":
        fail(f"license expression/evidence mismatch for {dependency.get('name')}: {expected} != {expression}")


def validate_go_dependencies(root: Path, dependencies: list[dict[str, object]]) -> None:
    module_sums, go_mod_sums = parse_go_sum(root / "service/go.sum")
    requirements, replacements = parse_go_mod(root / "service/go.mod")
    go_dependencies = [item for item in dependencies if item.get("type") == "go-module"]
    inventory_pairs = {(str(item.get("module_or_package")), str(item.get("version"))) for item in go_dependencies}
    if len(inventory_pairs) != len(go_dependencies):
        fail("duplicate Go dependency inventory entry")
    if inventory_pairs != set(module_sums):
        missing = sorted(set(module_sums) - inventory_pairs)
        extra = sorted(inventory_pairs - set(module_sums))
        fail(f"Go selected graph/inventory mismatch: missing={missing}, extra={extra}")
    for item in go_dependencies:
        module = str(item["module_or_package"])
        version = str(item["version"])
        evidence_prefix = f"LICENSES/third-party/go/{safe_module_name(module)}/{version}/"
        if any(
            not str(path).startswith(evidence_prefix)
            for field in ("license_files", "notice_files")
            for path in item.get(field, [])
        ):
            fail(f"Go evidence path/module provenance mismatch: {module}@{version}")
        provenance = item.get("provenance")
        if not isinstance(provenance, dict):
            fail(f"missing Go provenance: {module}@{version}")
        required = requirements.get(module)
        expected_direct = bool(required and required == (version, True))
        if required and required[0] != version:
            fail(f"service/go.mod selected version mismatch: {module}@{required[0]} != {version}")
        if item.get("direct") is not expected_direct:
            fail(f"Go direct/indirect mismatch: {module}@{version}")
        replacement = replacements.get(module)
        if provenance.get("replacement") != replacement:
            fail(f"Go replacement mismatch: {module}@{version}")
        if provenance.get("module_sum") != module_sums[(module, version)]:
            fail(f"Go module checksum provenance mismatch: {module}@{version}")
        if provenance.get("go_mod_sum") != go_mod_sums.get((module, version)):
            fail(f"Go go.mod checksum provenance mismatch: {module}@{version}")
        if provenance.get("go_sum_present") is not True:
            fail(f"Go go.sum evidence is absent: {module}@{version}")
        if item.get("source") != f"go-module-zip:{module}@{version}" or not SHA_RE.fullmatch(str(item.get("source_sha256", ""))):
            fail(f"Go module source provenance is invalid: {module}@{version}")


def validate_openssl(dependencies: list[dict[str, object]]) -> None:
    values = [item for item in dependencies if item.get("type") == "openssl"]
    if len(values) != 1:
        fail("dependency inventory must contain one OpenSSL installation")
    item = values[0]
    provenance = item.get("provenance")
    expected = {
        "name": "OpenSSL",
        "module_or_package": "openssl:x64-windows",
        "version": "3.6.3",
        "source": "vcpkg:openssl:x64-windows",
        "license_expression": "Apache-2.0",
        "evidence_status": "verified",
    }
    for field, value in expected.items():
        if item.get(field) != value:
            fail(f"OpenSSL version/license provenance mismatch: {field}")
    if item.get("license_files") != ["LICENSES/third-party/openssl/copyright"] or item.get("notice_files") != []:
        fail("OpenSSL installed license evidence path is invalid")
    if not isinstance(provenance, dict) or provenance.get("cmake_imported_target") != "OpenSSL::Crypto":
        fail("OpenSSL CMake target provenance is invalid")
    if provenance.get("architecture") != "x64" or "x64-windows" not in str(provenance.get("installation_source")):
        fail("OpenSSL installation architecture/provenance is invalid")
    if not SHA_RE.fullmatch(str(item.get("source_sha256", ""))):
        fail("OpenSSL package source SHA-256 is invalid")


def validate_legacy_state(root: Path) -> None:
    inventory = read_json(root / LEGACY_INVENTORY_PATH, "license inventory")
    policy = read_json(root / POLICY_PATH, "package policy")
    components = inventory.get("components")
    if not isinstance(components, list) or not all(isinstance(item, dict) for item in components):
        fail("legacy license inventory components are invalid")
    by_name = {str(item.get("name")): item for item in components}
    openssl = by_name.get("openssl-runtime-dependency", {})
    go_modules = by_name.get("go-module-dependencies", {})
    anocrypto = by_name.get("anocrypto-c-external-sdk", {})
    if openssl.get("license_expression") != "Apache-2.0" or openssl.get("evidence_status") != "verified":
        fail("legacy OpenSSL license inventory is stale")
    if go_modules.get("evidence_status") != "verified":
        fail("legacy Go dependency license inventory is stale")
    if (
        anocrypto.get("license_expression") != "NOASSERTION"
        or anocrypto.get("evidence_status") != "external_license_unresolved"
        or anocrypto.get("customer_package_allowed") is not False
    ):
        fail("AnoCrypto-C external license state must remain unresolved and customer-blocked")
    if inventory.get("commercial_license_status") != "incomplete" or inventory.get("customer_distribution_authorized") is not False:
        fail("commercial license/customer authorization must remain fail-closed")
    classes = policy.get("package_classes")
    if not isinstance(classes, dict) or classes.get("customer-release", {}).get("authorized") is not False:
        fail("customer package policy must remain unauthorized")


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_third_party_notices", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        fail("cannot load third-party notice generator")
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_attributes(root: Path) -> None:
    try:
        lines = (root / ATTRIBUTES_PATH).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        fail(f"invalid third-party whitespace policy: {exc}")
    rules = []
    for raw in lines:
        parts = raw.partition("#")[0].split()
        if len(parts) > 1 and any(
            item in {"whitespace", "-whitespace", "!whitespace"} or item.startswith("whitespace=")
            for item in parts[1:]
        ):
            rules.append(parts)
    if rules != [[WHITESPACE_EVIDENCE_PATH, WHITESPACE_ATTRIBUTE]]:
        fail("third-party whitespace policy must contain only the exact pinned evidence exception")


def validate_inventory(root: Path, inventory: dict[str, object]) -> None:
    require_fields(inventory, TOP_FIELDS, "dependency license inventory")
    if inventory.get("schema_version") != 1 or inventory.get("product") != "AnoPKI Enterprise" or inventory.get("edition") != "enterprise":
        fail("dependency license inventory identity is invalid")
    if not COMMIT_RE.fullmatch(str(inventory.get("enterprise_commit", ""))) or not COMMIT_RE.fullmatch(
        str(inventory.get("community_baseline_commit", ""))
    ):
        fail("dependency license inventory commit provenance is invalid")
    dependencies = inventory.get("dependencies")
    if not isinstance(dependencies, list) or not dependencies or not all(isinstance(item, dict) for item in dependencies):
        fail("dependency license inventory dependencies are invalid")
    generator = load_generator()
    if dependencies != sorted(dependencies, key=generator.dependency_key):
        fail("dependency inventory order is not deterministic")
    for item in dependencies:
        require_fields(
            {key: value for key, value in item.items() if key not in OPTIONAL_DEPENDENCY_FIELDS},
            DEPENDENCY_FIELDS,
            "dependency",
        )
        if item.get("type") not in {"go-module", "openssl"} or not isinstance(item.get("direct"), bool):
            fail(f"invalid dependency identity: {item.get('name')}")
        validate_evidence(root, item)
    unresolved = sum(item.get("evidence_status") != "verified" for item in dependencies)
    if inventory.get("unresolved_count") != unresolved:
        fail("dependency unresolved_count mismatch")
    ready = unresolved == 0 and all(item.get("customer_package_allowed") is True for item in dependencies)
    if inventory.get("customer_distribution_ready") is not ready:
        fail("dependency customer_distribution_ready mismatch")
    validate_go_dependencies(root, dependencies)
    validate_openssl(dependencies)


def validate(root: Path = ROOT) -> None:
    root = root.resolve()
    validate_attributes(root)
    inventory = read_json(root / INVENTORY_PATH, "dependency license inventory")
    validate_inventory(root, inventory)
    generator = load_generator()
    for path, expected in generator.build_outputs(root).items():
        try:
            current = (root / path).read_text(encoding="utf-8")
        except OSError as exc:
            fail(f"missing generated notice {path}: {exc}")
        if current != expected:
            fail(f"stale generated notice: {path}")
    serialized = json.dumps(inventory, sort_keys=True) + (root / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    if LOCAL_PATH_RE.search(serialized) or "ANOCRYPTO_C_READ_TOKEN" in serialized:
        fail("third-party evidence exposes a local path or secret name")
    validate_legacy_state(root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT, type=Path)
    args = parser.parse_args()
    validate(args.root)
    print("third-party notices valid")


if __name__ == "__main__":
    main()
