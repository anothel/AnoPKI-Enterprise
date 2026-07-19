# AnoCrypto-C Handoff Current Status (Pending)

Recorded source state: Enterprise
`152a657c8cc49775e8fa3bf33a3819b62c9d8e36`, Community
`acb71b8f4e9133d9c25dad1be3bca58209fba0d7`.

## Current State

| Field | Value |
| --- | --- |
| SDK execution | `not_run` |
| Capability observation | `unverified` |
| Operation parity | `unsupported_pending` |
| Production ready | `false` |
| Fallback enabled / used | `false` / `false` |
| KCMVP | `not_validated` |
| Commercial license | `incomplete` |
| Hosted qualification | `REMOTE_DEFERRED/BLOCKED_EXTERNAL` |

AnoCrypto-C PKI capabilities are not implemented in this adapter. It reports
runtime identity/readiness metadata only when the external SDK is present and
throws `backend.capability_unavailable` for the eight PKI backend operations.

## Source And Test Index

- adapter contract: `include/anopki/enterprise/anocrypto_backend.hpp`
- adapter source: `src/backends/anocrypto_c/anocrypto_backend.cpp`
  (`unsupported_pending` operations)
- SDK consumption test: `enterprise/tests/anocrypto_sdk_integration_test.cpp`
- capability/no-fallback test: `enterprise/tests/anocrypto_no_fallback_test.cpp`
- parity-pending test: `enterprise/tests/anocrypto_parity_pending_test.cpp`
- trusted workflow: `.github/workflows/anocrypto-sdk-integration.yml`
- evidence schema/example: `sdk-manifests/anocrypto-c/README.md` and
  `sdk-manifests/anocrypto-c/example-evidence.json`
- release gates: `docs/enterprise/backend-profile-release-gates.md`

## Current Work Queue

1. Decide high-level SDK PKI APIs versus Enterprise-owned codec model.
2. Discover exact SDK capabilities and pin clean source/archive SHA-256.
3. Record ABI, build fingerprint, package target, platform/toolchain, license,
   readiness, self-test, thread-safety, lifetime, and zeroization contracts.
4. Run the protected trusted-SDK workflow and validate dependency failure,
   capability-unavailable, and no-fallback evidence.
5. Close phase-1 parity in order: `csr_parse`, `certificate_issue`,
   `crl_generate_sign`, `ocsp_decode`, `ocsp_response_sign`.
6. Close remaining full backend operations, key/certificate binding, and
   signing-evidence behavior.
7. Review production non-exportable provider ownership and exact KCMVP claim
   scope only after the implementation/evidence exists.

## Canonical Handoff Files

- `docs/enterprise/anocrypto-sdk-capability-requirements.md`
- `docs/enterprise/anocrypto-operation-parity-matrix.md`
- `docs/enterprise/anocrypto-product-sdk-responsibility-boundary.md`
- `docs/enterprise/handoff/anocrypto-required-capabilities.json`
- `docs/enterprise/handoff/anocrypto-gap-matrix.json`
- `docs/enterprise/handoff/operation-responsibility-matrix.json`
