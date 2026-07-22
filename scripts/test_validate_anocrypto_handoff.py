#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Validate the current AnoCrypto-C handoff matrices."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "docs" / "enterprise" / "handoff"
ENTERPRISE_COMMIT = "152a657c8cc49775e8fa3bf33a3819b62c9d8e36"
COMMUNITY_COMMIT = "ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc"

BACKEND_OPERATIONS = {
    "csr_inspect",
    "certificate_issue",
    "crl_generate",
    "crl_inspect",
    "ocsp_request_inspect",
    "ocsp_issuer_inspect",
    "ocsp_response_generate",
    "ocsp_responder_validate",
}
PARITY_OPERATIONS = {
    "csr_parse",
    "certificate_issue",
    "crl_generate_sign",
    "ocsp_decode",
    "ocsp_response_sign",
}
RESPONSIBILITY_OPERATIONS = {
    "CSR PEM/DER parse",
    "CSR signature validation",
    "certificate issue",
    "CRL generate",
    "CRL inspect",
    "OCSP request decode",
    "OCSP issuer identification",
    "OCSP response generate",
    "OCSP responder certificate validation",
    "backend metadata/readiness",
    "key/certificate binding validation",
    "signing evidence generation",
}
RESPONSIBILITY_FIELDS = {
    "operation",
    "backend_neutral_behavior",
    "required_crypto_primitives",
    "key_provider_responsibilities",
    "sdk_responsibilities",
    "enterprise_adapter_responsibilities",
    "community_responsibilities",
    "enterprise_product_responsibilities",
    "current_status",
    "blockers",
    "acceptance_tests",
}


def load(name: str) -> dict[str, object]:
    value = json.loads((HANDOFF / name).read_text(encoding="utf-8"))
    assert value["schema_version"] == 1
    assert value["enterprise_commit"] == ENTERPRISE_COMMIT
    assert value["community_baseline_commit"] == COMMUNITY_COMMIT
    return value


def main() -> None:
    capabilities = load("anocrypto-required-capabilities.json")
    assert capabilities["observed_anocrypto_capabilities"] == []
    assert {row["stable_operation_name"] for row in capabilities["capabilities"]} == BACKEND_OPERATIONS
    assert all(row["current_anocrypto_c_state"] == "unsupported_pending" for row in capabilities["capabilities"])

    gaps = load("anocrypto-gap-matrix.json")
    allowed = {"semantic_equal", "exact_der_equal", "unsupported_pending", "failure"}
    assert set(gaps["allowed_results"]) == allowed
    assert {row["operation"] for row in gaps["operations"]} == PARITY_OPERATIONS
    assert all(row["current_status"] in allowed and row["current_status"] != "skip" for row in gaps["operations"])

    responsibilities = load("operation-responsibility-matrix.json")
    rows = responsibilities["operations"]
    assert RESPONSIBILITY_OPERATIONS.issubset({row["operation"] for row in rows})
    assert all(set(row) == RESPONSIBILITY_FIELDS and row["blockers"] and row["acceptance_tests"] for row in rows)

    status = (ROOT / "docs" / "enterprise" / "anocrypto-handoff-current-status.md").read_text(encoding="utf-8")
    for marker in ("not_run", "unverified", "unsupported_pending", "Production ready", "Decide high-level SDK"):
        assert marker in status
    print("AnoCrypto-C handoff matrices ok")


if __name__ == "__main__":
    main()
