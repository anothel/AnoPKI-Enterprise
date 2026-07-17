#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Validate Enterprise package policy, license inventory, manifests, and archives."""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import re
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-package-manifest.py"
INVENTORY_FIELDS = {
    "schema_version",
    "product",
    "edition",
    "generated_from_commit",
    "community_baseline_commit",
    "commercial_license_status",
    "customer_distribution_authorized",
    "components",
}
COMPONENT_FIELDS = {
    "name",
    "ownership",
    "source_scope",
    "license_expression",
    "license_file",
    "distribution_scope",
    "required_notices",
    "redistribution_allowed",
    "customer_package_allowed",
    "evidence_status",
}
POLICY_FIELDS = {
    "schema_version",
    "product",
    "edition",
    "commercial_license_status",
    "customer_distribution_authorized",
    "package_classes",
    "profiles",
    "forbidden_path_patterns",
    "approved_generated_paths",
}
MANIFEST_FIELDS = {
    "schema_version",
    "product",
    "edition",
    "product_profile",
    "enterprise_commit",
    "community_baseline_commit",
    "package_class",
    "commercial_license_status",
    "customer_distribution_authorized",
    "selected_adapter",
    "fallback_enabled",
    "fallback_used",
    "files",
    "licenses",
    "notices",
    "production_ready",
    "kcmvp_status",
}
FILE_FIELDS = {"path", "sha256", "ownership", "license_expression", "distribution_scope"}
REQUIRED_COMPONENTS = {
    "synchronized-community-mpl-files",
    "enterprise-commercial-overlay",
    "openssl-runtime-dependency",
    "go-module-dependencies",
    "anocrypto-c-external-sdk",
    "generated-metadata-and-evidence",
    "test-only-fixtures",
    "build-only-tools",
    "customer-documentation",
}
COPIED_ANOCRYPTO_PREFIXES = (
    "enterprise/anocrypto/include/",
    "enterprise/anocrypto/src/",
    "third_party/anocrypto/",
    "vendor/anocrypto/",
)
BINARY_SUFFIXES = (".a", ".dll", ".dylib", ".lib", ".so")


def fail(message: str) -> None:
    raise SystemExit(message)


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_package_manifest", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        fail("cannot load package manifest generator")
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def require_exact_fields(value: dict[str, object], expected: set[str], label: str) -> None:
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    if missing or extra:
        details = [*(f"missing: {item}" for item in missing), *(f"unknown: {item}" for item in extra)]
        fail(f"{label} fields are invalid:\n" + "\n".join(details))


def component_map(inventory: dict[str, object]) -> dict[str, dict[str, object]]:
    values = inventory.get("components")
    if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
        fail("license inventory components must be objects")
    components: dict[str, dict[str, object]] = {}
    for component in values:
        require_exact_fields(component, COMPONENT_FIELDS, "license inventory component")
        name = component.get("name")
        if not isinstance(name, str) or not name or name in components:
            fail("license inventory component names must be unique non-empty strings")
        if not isinstance(component.get("source_scope"), list) or not component["source_scope"]:
            fail(f"license inventory component has no source scope: {name}")
        if not isinstance(component.get("required_notices"), list):
            fail(f"license inventory component notices must be a list: {name}")
        if not isinstance(component.get("redistribution_allowed"), bool) or not isinstance(
            component.get("customer_package_allowed"), bool
        ):
            fail(f"license inventory component distribution flags are invalid: {name}")
        components[name] = component
    missing = sorted(REQUIRED_COMPONENTS - set(components))
    if missing:
        fail("license inventory missing component categories:\n" + "\n".join(missing))
    return components


def validate_inventory(root: Path, inventory: dict[str, object], policy: dict[str, object], edition: dict[str, object]) -> None:
    require_exact_fields(inventory, INVENTORY_FIELDS, "license inventory")
    require_exact_fields(policy, POLICY_FIELDS, "package policy")
    if inventory.get("schema_version") != 1 or policy.get("schema_version") != 1:
        fail("packaging schema version must be 1")
    for key, expected in (("product", "AnoPKI Enterprise"), ("edition", "enterprise")):
        if inventory.get(key) != expected or policy.get(key) != expected:
            fail(f"packaging {key} identity is invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", str(inventory.get("generated_from_commit", ""))):
        fail("license inventory generated_from_commit must be an exact commit")
    if inventory.get("community_baseline_commit") != edition.get("community_baseline_commit"):
        fail("license inventory Community baseline does not match edition metadata")
    if inventory.get("commercial_license_status") != edition.get("commercial_license_status"):
        fail("license inventory commercial license status does not match edition metadata")
    if inventory.get("customer_distribution_authorized") != edition.get("commercial_release_authorized"):
        fail("license inventory customer authorization does not match edition metadata")
    if policy.get("commercial_license_status") != inventory.get("commercial_license_status") or policy.get(
        "customer_distribution_authorized"
    ) != inventory.get("customer_distribution_authorized"):
        fail("package policy and license inventory state do not match")

    components = component_map(inventory)
    community = components["synchronized-community-mpl-files"]
    if community.get("license_expression") != "MPL-2.0" or community.get("license_file") != "LICENSES/MPL-2.0.txt":
        fail("synchronized Community files must retain MPL-2.0 license evidence")
    if "ENTERPRISE-LICENSE-NOTICE.md" not in community.get("required_notices", []):
        fail("MPL-2.0 customer source/overlay notice is missing")
    enterprise = components["enterprise-commercial-overlay"]
    if enterprise.get("license_expression") != "LicenseRef-AnoPKI-Enterprise":
        fail("Enterprise commercial overlay must not be labeled as MPL-2.0")
    if enterprise.get("customer_package_allowed") is not False:
        fail("incomplete Enterprise commercial overlay cannot enter a customer package")
    for name in ("openssl-runtime-dependency", "go-module-dependencies", "anocrypto-c-external-sdk"):
        component = components[name]
        license_file = component.get("license_file")
        if license_file is not None and (not isinstance(license_file, str) or not (root / license_file).is_file()):
            fail(f"external component license evidence is missing: {name}")
    anocrypto = components["anocrypto-c-external-sdk"]
    if anocrypto.get("license_expression") != "NOASSERTION" or anocrypto.get("customer_package_allowed") is not False:
        fail("unresolved AnoCrypto-C SDK license must remain customer-blocked")

    classes = policy.get("package_classes")
    profiles = policy.get("profiles")
    if not isinstance(classes, dict) or set(classes) != {"internal-validation", "customer-release"}:
        fail("package policy must define internal-validation and customer-release")
    internal = classes["internal-validation"]
    customer = classes["customer-release"]
    if not isinstance(internal, dict) or internal.get("authorized") is not True or internal.get("customer_distribution") is not False:
        fail("internal validation policy must be authorized only for non-customer use")
    if not isinstance(customer, dict) or customer.get("authorized") is not False or customer.get("customer_distribution") is not True:
        fail("current customer release policy must remain unauthorized")
    customer_blockers = customer.get("blockers")
    required_customer_blockers = {
        "final commercial license is incomplete",
        "third-party license inventory is incomplete",
        "hosted qualification is incomplete",
        "commercial release authorization is absent",
        "required notices are missing",
        "customer allow-lists and archive-member binding are incomplete",
    }
    if not isinstance(customer_blockers, list) or not required_customer_blockers.issubset(set(customer_blockers)):
        fail("customer package policy is missing fail-closed blockers")
    if not isinstance(profiles, dict) or set(profiles) != {"enterprise-openssl", "enterprise-anocrypto-c"}:
        fail("package policy profiles are invalid")
    if profiles["enterprise-openssl"].get("selected_adapter") != "openssl":
        fail("Enterprise/OpenSSL package policy selects the wrong adapter")
    anocrypto_policy = profiles["enterprise-anocrypto-c"]
    if anocrypto_policy.get("selected_adapter") != "anocrypto-c" or anocrypto_policy.get("kcmvp_status") != "not_validated":
        fail("Enterprise/AnoCrypto-C policy must remain not validated")
    required_anocrypto_blockers = {
        "exact trusted SDK evidence is absent",
        "external SDK license is unresolved",
        "PKI operation parity is incomplete",
        "production readiness is false",
        "KCMVP is not validated",
        "fallback detection must remain false",
    }
    if not isinstance(anocrypto_policy.get("additional_blockers"), list) or not required_anocrypto_blockers.issubset(
        set(anocrypto_policy["additional_blockers"])
    ):
        fail("Enterprise/AnoCrypto-C package policy is missing fail-closed blockers")
    if any(profile.get("production_ready") is not False for profile in profiles.values() if isinstance(profile, dict)):
        fail("current package profiles must remain not production ready")


def validate_hosted_state(edition: dict[str, object]) -> None:
    hosted = edition.get("hosted_ci")
    trusted = edition.get("trusted_anocrypto_sdk_lane")
    if not isinstance(hosted, dict) or not isinstance(trusted, dict):
        fail("structured hosted CI and trusted SDK state are required")
    if hosted.get("runner_assigned") is False and hosted.get("remote_validation") in {"passed", "success"}:
        fail("runner-assignment blocker cannot be recorded as hosted success")
    if hosted.get("steps_executed") == 0 and hosted.get("classification") in {"CI_SUCCESS", "PASSED", "SUCCESS"}:
        fail("zero hosted steps cannot be recorded as hosted success")
    if trusted.get("execution") == "not_run" and trusted.get("status") in {"completed", "passed", "success"}:
        fail("trusted SDK not_run cannot be recorded as completed")
    if trusted.get("kcmvp_status") == "validated" or edition.get("kcmvp_status") == "validated":
        fail("KCMVP validated claim has no certification evidence")


def validate_file_security(paths: list[str], policy: dict[str, object]) -> None:
    patterns = policy.get("forbidden_path_patterns")
    if not isinstance(patterns, list) or not all(isinstance(pattern, str) for pattern in patterns):
        fail("forbidden_path_patterns must be strings")
    forbidden = sorted(path for path in paths if any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns))
    if forbidden:
        fail("package contains forbidden build/cache/secret path:\n" + "\n".join(forbidden))
    copied = sorted(path for path in paths if path.startswith(COPIED_ANOCRYPTO_PREFIXES))
    if copied:
        fail("package contains copied AnoCrypto-C source or headers:\n" + "\n".join(copied))
    sdk_binaries = [path for path in paths if "anocrypto" in path.lower() and path.lower().endswith(BINARY_SUFFIXES)]
    if sdk_binaries and "sdk-manifests/anocrypto-c/evidence.json" not in paths:
        fail("package contains an AnoCrypto-C SDK binary without exact SDK evidence")
    has_openssl = any(path.startswith("src/backends/openssl/") for path in paths)
    has_anocrypto = any(path.startswith("src/backends/anocrypto_c/") for path in paths)
    if has_openssl and has_anocrypto:
        fail("package contains both OpenSSL and AnoCrypto-C adapters")


def validate_manifest(root: Path, manifest: dict[str, object], generator=None) -> None:
    require_exact_fields(manifest, MANIFEST_FIELDS, "package manifest")
    if manifest.get("schema_version") != 1 or manifest.get("product") != "AnoPKI Enterprise" or manifest.get("edition") != "enterprise":
        fail("package manifest identity is invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("enterprise_commit", ""))):
        fail("package manifest Enterprise commit is invalid")
    if manifest.get("fallback_enabled") is not False or manifest.get("fallback_used") is not False:
        fail("package manifest enables or records fallback")
    if manifest.get("kcmvp_status") == "validated":
        fail("package manifest makes an unsupported KCMVP validated claim")
    if manifest.get("package_class") == "customer-release":
        if manifest.get("commercial_license_status") != "complete":
            fail("customer package lacks final commercial license")
        if manifest.get("customer_distribution_authorized") is not True:
            fail("internal validation manifest cannot be relabeled as a customer package")
        notices = manifest.get("notices")
        required = {"LICENSES/MPL-2.0.txt", "ENTERPRISE-LICENSE-NOTICE.md"}
        if not isinstance(notices, list) or not required.issubset(set(notices)):
            fail("customer package is missing MPL-2.0 license/source notice")

    files = manifest.get("files")
    if not isinstance(files, list) or not files or not all(isinstance(item, dict) for item in files):
        fail("package manifest files must be a non-empty list")
    paths: list[str] = []
    for item in files:
        require_exact_fields(item, FILE_FIELDS, "package manifest file")
        path = item.get("path")
        if not isinstance(path, str) or PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts:
            fail("package manifest contains a non-relative file path")
        if not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", ""))):
            fail(f"package manifest SHA-256 is invalid: {path}")
        paths.append(path)
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        fail("package manifest file paths must be sorted and unique")
    validate_file_security(paths, read_json(root / "packaging/package-policy.json"))

    generator = generator or load_generator()
    expected = generator.build_manifest(root, str(manifest["product_profile"]), str(manifest["package_class"]))
    if manifest != expected:
        for expected_file, actual_file in zip(expected["files"], files):
            if expected_file.get("path") == actual_file.get("path") and expected_file.get("sha256") != actual_file.get("sha256"):
                fail(f"package manifest SHA-256 mismatch: {actual_file.get('path')}")
        expected_paths = {item["path"] for item in expected["files"]}
        extra = sorted(set(paths) - expected_paths)
        if extra:
            fail("package manifest contains unallowlisted files:\n" + "\n".join(extra))
        fail("package manifest does not match deterministic policy output")


def archive_contents(path: Path) -> dict[str, bytes]:
    values: dict[str, bytes] = {}
    if path.name.endswith(".zip"):
        try:
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    name = info.filename.removeprefix("./")
                    if name in values:
                        fail(f"package archive contains duplicate member: {name}")
                    values[name] = archive.read(info)
        except zipfile.BadZipFile as exc:
            fail(f"invalid package archive: {exc}")
    elif path.name.endswith((".tar.gz", ".tgz")):
        try:
            with tarfile.open(path, "r:gz") as archive:
                for member in archive.getmembers():
                    if member.isdir():
                        continue
                    if not member.isfile():
                        fail(f"package archive contains non-regular member: {member.name}")
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        fail(f"cannot read package archive member: {member.name}")
                    name = member.name.removeprefix("./")
                    if name in values:
                        fail(f"package archive contains duplicate member: {name}")
                    values[name] = extracted.read()
        except tarfile.TarError as exc:
            fail(f"invalid package archive: {exc}")
    else:
        fail("package archive must be .zip, .tar.gz, or .tgz")
    for name in values:
        posix = PurePosixPath(name)
        if not name or posix.is_absolute() or ".." in posix.parts:
            fail(f"package archive contains unsafe member: {name}")
    return values


def validate_archive(path: Path, manifest: dict[str, object]) -> None:
    values = archive_contents(path)
    files = manifest["files"]
    expected = {item["path"]: item["sha256"] for item in files}
    allowed = set(expected) | {"package-manifest.json"}
    if set(values) != allowed:
        missing = sorted(allowed - set(values))
        extra = sorted(set(values) - allowed)
        fail("package archive/member mismatch:\n" + "\n".join([*(f"missing: {item}" for item in missing), *(f"extra: {item}" for item in extra)]))
    try:
        embedded = json.loads(values["package-manifest.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"package archive contains invalid package-manifest.json: {exc}")
    if embedded != manifest:
        fail("package archive embedded manifest does not match validated package-manifest.json")
    import hashlib

    for name, digest in expected.items():
        if hashlib.sha256(values[name]).hexdigest() != digest:
            fail(f"package archive SHA-256 mismatch: {name}")


def read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid JSON {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"JSON value must be an object: {path}")
    return value


def validate(root: Path = ROOT) -> None:
    root = root.resolve()
    inventory = read_json(root / "packaging/license-inventory.json")
    policy = read_json(root / "packaging/package-policy.json")
    edition = read_json(root / ".edition/edition.json")
    validate_inventory(root, inventory, policy, edition)
    validate_hosted_state(edition)
    generator = load_generator()
    for profile in ("enterprise-openssl", "enterprise-anocrypto-c"):
        internal = generator.build_manifest(root, profile, "internal-validation")
        validate_manifest(root, internal, generator)
        customer_allowlist = policy["profiles"][profile]["manifests"]["customer-release"]
        if generator.parse_allowlist(root / customer_allowlist):
            fail(f"unauthorized customer allow-list must remain empty: {profile}")
        try:
            generator.build_manifest(root, profile, "customer-release")
        except SystemExit as exc:
            if "customer release blocked" not in str(exc):
                raise
        else:
            fail(f"current customer package unexpectedly authorized: {profile}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    validate(args.root)
    if args.archive and not args.manifest:
        fail("--archive requires --manifest")
    if args.manifest:
        manifest = read_json(args.manifest)
        validate_manifest(args.root.resolve(), manifest)
        if args.archive:
            validate_archive(args.archive, manifest)
    print("package boundary ok")


if __name__ == "__main__":
    main()
