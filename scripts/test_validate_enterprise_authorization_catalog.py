#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Negative checks for the Enterprise authorization catalog validator."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-enterprise-authorization-catalog.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_enterprise_authorization_catalog", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def copy_inputs(root: Path) -> Path:
    for relative in (
        "service/internal/httpapi/server.go",
        "docs/enterprise/authorization-action-catalog.json",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return root / "docs/enterprise/authorization-action-catalog.json"


def mutate(root: Path, change) -> None:
    path = copy_inputs(root)
    value = json.loads(path.read_text(encoding="utf-8"))
    change(value)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def expect_failure(change, expected: str) -> None:
    validator = load_validator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mutate(root, change)
        try:
            validator.validate(root)
        except SystemExit as exc:
            assert expected in str(exc), str(exc)
        else:
            raise AssertionError("authorization catalog validator unexpectedly passed")


def expect_server_failure(expected: str) -> None:
    validator = load_validator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        copy_inputs(root)
        server = root / "service/internal/httpapi/server.go"
        server.write_text(server.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        try:
            validator.validate(root)
        except SystemExit as exc:
            assert expected in str(exc), str(exc)
        else:
            raise AssertionError("authorization catalog validator unexpectedly passed")


def test_current_catalog_passes() -> None:
    load_validator().validate(ROOT)


def test_missing_route_fails() -> None:
    expect_failure(lambda value: value["actions"].pop(0), "protected route coverage mismatch")


def test_duplicate_action_fails() -> None:
    expect_failure(lambda value: value["actions"].append(dict(value["actions"][0])), "duplicate authorization action ID")


def test_conflicting_route_fails() -> None:
    expect_failure(
        lambda value: value["actions"][1].__setitem__(
            "current_route_or_operation", value["actions"][0]["current_route_or_operation"]
        ),
        "duplicate protected route",
    )


def test_unknown_route_fails() -> None:
    expect_failure(
        lambda value: value["actions"][0].__setitem__("current_route_or_operation", "GET /unknown"),
        "protected route coverage mismatch",
    )


def test_unknown_action_fails() -> None:
    expect_failure(
        lambda value: value["actions"][0].__setitem__("id", "unknown.action"),
        "authorization action mapping fixture changed",
    )


def test_unknown_resource_fails() -> None:
    expect_failure(
        lambda value: value["actions"][0].__setitem__("resource_type", "unknown"),
        "unknown resource type",
    )


def test_route_fixture_hash_fails() -> None:
    expect_server_failure("server.go changed")


def test_duplicate_resource_fails() -> None:
    expect_failure(lambda value: value["resource_types"].append(value["resource_types"][0]), "resource types contain duplicates")


def test_public_route_as_protected_fails() -> None:
    def change(value):
        action = value["actions"][-1]
        action.update({"status": "implemented", "ownership": "community", "current_route_or_operation": "POST /ocsp"})
    expect_failure(change, "public route must not be registered as a protected action")


def test_current_route_as_future_fails() -> None:
    def change(value):
        value["actions"][0]["status"] = "future"
        value["actions"][0]["ownership"] = "enterprise"
    expect_failure(change, "future action must not claim a current implemented route")


def test_oidc_implemented_claim_fails() -> None:
    def change(value):
        value["actions"][0]["id"] = "oidc.login"
    expect_failure(change, "OIDC/SAML must not be marked")


def test_approval_workflow_claim_fails() -> None:
    expect_failure(lambda value: value.__setitem__("approval_workflow_status", "implemented"), "must not claim an implemented approval workflow")


def test_unknown_status_fails() -> None:
    expect_failure(lambda value: value["actions"][0].__setitem__("status", "active"), "status is invalid")


def test_legacy_scope_drift_fails() -> None:
    expect_failure(lambda value: value["actions"][0].__setitem__("legacy_required_scope", "write"), "legacy scope does not match")


def test_authentication_claim_drift_fails() -> None:
    expect_failure(lambda value: value["authentication_implementations"].append("saml"), "OIDC/SAML are not implemented")


def main() -> None:
    test_current_catalog_passes()
    test_missing_route_fails()
    test_duplicate_action_fails()
    test_conflicting_route_fails()
    test_unknown_route_fails()
    test_unknown_action_fails()
    test_unknown_resource_fails()
    test_route_fixture_hash_fails()
    test_duplicate_resource_fails()
    test_public_route_as_protected_fails()
    test_current_route_as_future_fails()
    test_oidc_implemented_claim_fails()
    test_approval_workflow_claim_fails()
    test_unknown_status_fails()
    test_legacy_scope_drift_fails()
    test_authentication_claim_drift_fails()
    print("enterprise authorization catalog validator tests ok")


if __name__ == "__main__":
    main()
