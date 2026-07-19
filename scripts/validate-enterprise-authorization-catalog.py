#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Validate the Enterprise authorization catalog against a locked route fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = "service/internal/httpapi/server.go"
SERVER_SHA256 = "ece1c85d270e53c4fa1a677c647e19295fb54cb05f274c108508299bee963390"
CATALOG_PATH = "docs/enterprise/authorization-action-catalog.json"
TOP_FIELDS = {
    "schema_version",
    "source",
    "authentication_implementations",
    "approval_workflow_status",
    "actions",
    "resource_types",
    "legacy_scope_mapping",
    "public_routes",
}
ACTION_FIELDS = {
    "id",
    "resource_type",
    "operation_class",
    "current_route_or_operation",
    "legacy_required_scope",
    "approval_capable",
    "ownership",
    "status",
}
PUBLIC_ROUTES = {
    "GET /acme/directory",
    "HEAD /acme/new-nonce",
    "GET /acme/new-nonce",
    "POST /acme/new-account",
    "POST /acme/account/{id}",
    "POST /acme/new-order",
    "POST /acme/key-change",
    "GET /acme/order/{id}",
    "POST /acme/order/{id}",
    "GET /acme/authz/{id}",
    "POST /acme/authz/{id}",
    "POST /acme/challenge/{id}",
    "POST /acme/order/{id}/finalize",
    "POST /acme/revoke-cert",
    "GET /acme/cert/{id}",
    "POST /acme/cert/{id}",
    "GET /crls/{id}",
    "GET /issuers/{id}/crl",
    "POST /ocsp",
}
PROTECTED_ROUTES = {
    "GET /debug/vars",
    "POST /identities",
    "GET /identities",
    "GET /identities/{id}",
    "POST /issuers",
    "GET /issuers/{id}/chain",
    "POST /issuers/{id}/ocsp-responders",
    "GET /issuers/{id}/ocsp-responders",
    "POST /issuers/{id}/ocsp-responders/rotate",
    "POST /issuers/{id}/ocsp-responders/{responderID}/disable",
    "POST /notification-endpoints",
    "GET /notification-endpoints",
    "POST /notification-endpoints/{id}/disable",
    "GET /outbox/messages",
    "POST /outbox/messages/dead-letter/replay",
    "POST /outbox/messages/{id}/retry",
    "GET /operator/certificate-inventory",
    "GET /operator/expiry-slo",
    "POST /api-keys",
    "GET /api-keys",
    "POST /api-keys/{id}/rotate",
    "POST /api-keys/{id}/disable",
    "POST /acme/accounts",
    "GET /acme/accounts",
    "POST /acme/orders",
    "GET /acme/orders/{id}",
    "GET /acme/orders/{id}/authorizations",
    "POST /acme/orders/{id}/finalize",
    "GET /acme/authorizations/{id}/challenges",
    "POST /acme/challenges/{id}/complete",
    "POST /certificate-profiles",
    "GET /certificate-profiles",
    "GET /certificate-profiles/{id}",
    "POST /enrollments",
    "GET /enrollments",
    "GET /enrollments/{id}",
    "POST /enrollments/{id}/approve",
    "POST /enrollments/{id}/reject",
    "POST /certificates",
    "GET /certificates",
    "POST /certificates/expiration-scan",
    "GET /certificates/{id}",
    "POST /certificates/{id}/revoke",
    "POST /certificates/{id}/suspend",
    "POST /certificates/{id}/resume",
    "POST /certificates/{id}/renew",
    "POST /certificates/{id}/reissue",
    "POST /crls",
    "GET /audit-events",
    "POST /audit-events/retention/prune",
    "POST /audit-events/repair/issuance",
    "GET /trust/anchors",
}
REQUIRED_RESOURCE_TYPES = {
    "identity",
    "issuer",
    "certificate",
    "revocation",
    "crl",
    "ocsp_responder",
    "ocsp_response",
    "notification_endpoint",
    "outbox",
    "audit_event",
    "api_key",
    "operator_inventory",
    "acme_account",
    "acme_order",
    "acme_authorization",
    "acme_challenge",
    "policy_configuration",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def read_catalog(root: Path) -> dict[str, object]:
    try:
        value = json.loads((root / CATALOG_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid authorization catalog: {exc}")
    if not isinstance(value, dict):
        fail("authorization catalog must be an object")
    return value


def required_scope(route: str) -> str:
    method, path = route.split(" ", 1)
    if path.startswith(("/api-keys", "/outbox/", "/audit-events", "/operator/")):
        return "operator"
    if method == "POST" and path == "/certificates/expiration-scan":
        return "operator"
    return "read" if method == "GET" else "write"


def validate(root: Path = ROOT) -> None:
    root = root.resolve()
    catalog = read_catalog(root)
    if set(catalog) != TOP_FIELDS:
        fail("authorization catalog top-level fields are invalid")
    if catalog["schema_version"] != 1:
        fail("authorization catalog schema version is invalid")

    source = catalog["source"]
    if not isinstance(source, dict) or set(source) != {"path", "sha256"} or source.get("path") != SERVER_PATH:
        fail("authorization catalog source fixture is invalid")
    try:
        actual_sha256 = hashlib.sha256((root / SERVER_PATH).read_bytes()).hexdigest()
    except OSError as exc:
        fail(f"cannot read authorization source fixture: {exc}")
    if actual_sha256 != SERVER_SHA256 or source.get("sha256") != SERVER_SHA256:
        fail("server.go changed; review routes and update the explicit authorization fixture checksum")

    implementations = catalog["authentication_implementations"]
    if not isinstance(implementations, list) or len(implementations) != len(set(implementations)) or set(implementations) != {"dev", "api_key"}:
        fail("authentication implementations must remain dev and api_key only; OIDC/SAML are not implemented")
    if catalog["approval_workflow_status"] != "not_implemented":
        fail("approval requirement support must not claim an implemented approval workflow")

    resources = catalog["resource_types"]
    if not isinstance(resources, list) or not all(isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_]*", value) for value in resources):
        fail("authorization resource types are invalid")
    if len(resources) != len(set(resources)):
        fail("authorization resource types contain duplicates")
    if not REQUIRED_RESOURCE_TYPES.issubset(resources):
        fail("authorization catalog is missing required resource types")

    expected_mapping = {
        "read": ["read"],
        "write": ["read", "write"],
        "operator": ["read", "write", "operator"],
    }
    if catalog["legacy_scope_mapping"] != expected_mapping:
        fail("legacy scope mapping changed current read/write/operator semantics")

    public_routes = catalog["public_routes"]
    if not isinstance(public_routes, list) or len(public_routes) != len(set(public_routes)):
        fail("public route fixture contains duplicates")
    if set(public_routes) != PUBLIC_ROUTES:
        fail("public route fixture does not match the locked server route set")

    actions = catalog["actions"]
    if not isinstance(actions, list) or not actions or not all(isinstance(action, dict) for action in actions):
        fail("authorization actions must be a non-empty object list")
    action_ids: set[str] = set()
    implemented_routes: set[str] = set()
    for action in actions:
        if set(action) != ACTION_FIELDS:
            fail("authorization action fields are invalid")
        action_id = action["id"]
        if not isinstance(action_id, str) or not re.fullmatch(r"[a-z][a-z0-9_.]*", action_id):
            fail("authorization action ID is invalid")
        if action_id in action_ids:
            fail(f"duplicate authorization action ID: {action_id}")
        action_ids.add(action_id)
        if action["resource_type"] not in resources:
            fail(f"authorization action uses an unknown resource type: {action_id}")
        if action["operation_class"] not in {"read", "write", "operator"}:
            fail(f"authorization action uses an unknown operation class: {action_id}")
        if action["legacy_required_scope"] not in {"read", "write", "operator"}:
            fail(f"authorization action uses an unknown legacy scope: {action_id}")
        if not isinstance(action["approval_capable"], bool):
            fail(f"authorization action approval_capable must be boolean: {action_id}")
        if action["ownership"] not in {"community", "enterprise"}:
            fail(f"authorization action ownership is invalid: {action_id}")
        if action["status"] not in {"implemented", "future"}:
            fail(f"authorization action status is invalid: {action_id}")
        serialized = json.dumps(action).lower()
        if action["status"] == "implemented" and ("oidc" in serialized or "saml" in serialized):
            fail("OIDC/SAML must not be marked as an implemented authentication capability")

        operation = action["current_route_or_operation"]
        if not isinstance(operation, str):
            fail(f"authorization action operation is invalid: {action_id}")
        if action["status"] == "future":
            if not operation.startswith("future:"):
                fail("future action must not claim a current implemented route")
            if action["ownership"] != "enterprise":
                fail("future Enterprise authorization actions must remain Enterprise-owned")
            continue
        if not re.fullmatch(r"(?:GET|POST|HEAD) /\S+", operation):
            fail(f"implemented action does not identify a current route: {action_id}")
        if operation in PUBLIC_ROUTES:
            fail(f"public route must not be registered as a protected action: {operation}")
        if operation in implemented_routes:
            fail(f"duplicate protected route: {operation}")
        if action["ownership"] != "community":
            fail(f"current server route must retain Community ownership: {operation}")
        if action["legacy_required_scope"] != required_scope(operation):
            fail(f"legacy scope does not match current server behavior: {operation}")
        implemented_routes.add(operation)

    missing = sorted(PROTECTED_ROUTES - implemented_routes)
    extra = sorted(implemented_routes - PROTECTED_ROUTES)
    if missing or extra:
        details = [*(f"missing: {route}" for route in missing), *(f"unexpected: {route}" for route in extra)]
        fail("protected route coverage mismatch:\n" + "\n".join(details))
    if len(PUBLIC_ROUTES | PROTECTED_ROUTES) != 71 or PUBLIC_ROUTES & PROTECTED_ROUTES:
        fail("internal authorization route fixture is inconsistent")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT, type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    validate(args.root)
    print(f"enterprise authorization catalog ok: {len(PROTECTED_ROUTES)} protected, {len(PUBLIC_ROUTES)} public")


if __name__ == "__main__":
    main()
