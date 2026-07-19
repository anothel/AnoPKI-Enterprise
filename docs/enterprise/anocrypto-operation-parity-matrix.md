# Operation Parity Gaps And Upstream Requirements

Recorded source state: Enterprise
`152a657c8cc49775e8fa3bf33a3819b62c9d8e36`, Community
`96297b14d2f681b75861032d9871a41d6e689c78`.

Allowed results: semantic_equal, exact_der_equal, unsupported_pending, failure.

`skip` is not a passing result. No operation below may move from
`unsupported_pending` without a real pinned SDK run and the listed positive,
negative, dependency-failure, and no-fallback evidence.

| Operation | OpenSSL implementation | AnoCrypto-C state | Result | Current blocker (pending) |
| --- | --- | --- | --- | --- |
| csr_parse | src/backends/openssl/csr.cpp | throws backend.capability_unavailable; unsupported_pending | unsupported_pending | exact AnoCrypto-C PKI/API capability discovery and trusted SDK execution not run |
| certificate_issue | src/backends/openssl/issue.cpp | throws backend.capability_unavailable; unsupported_pending | unsupported_pending | SDK certificate/signing and key-handle contracts unverified |
| crl_generate_sign | src/backends/openssl/crl.cpp | throws backend.capability_unavailable; unsupported_pending | unsupported_pending | SDK CRL/signing and key-handle contracts unverified |
| ocsp_decode | src/backends/openssl/ocsp.cpp | throws backend.capability_unavailable; unsupported_pending | unsupported_pending | SDK OCSP/ASN.1 capability unverified; issuer-inspection no-fallback assertion absent |
| ocsp_response_sign | src/backends/openssl/ocsp.cpp | throws backend.capability_unavailable; unsupported_pending | unsupported_pending | SDK OCSP response/signing contracts unverified; responder-validation no-fallback assertion absent |

## csr_parse

- current openssl implementation: src/backends/openssl/csr.cpp
- current anocrypto c adapter state: throws backend.capability_unavailable; unsupported_pending
- required sdk functionality: CSR PEM/DER decode, ASN.1 field extraction and CSR signature validation, or sufficient verified primitives for an Enterprise-owned codec
- required enterprise adapter work: map CSR input, normalized output and stable failures without OpenSSL
- required fixture: backend-neutral valid/invalid CSR fixtures covering RSA and approved algorithm scope
- positive test: run same fixture through OpenSSL and AnoCrypto-C; compare normalized CsrInfo
- negative test: malformed encoding and invalid CSR signature fail with stable redacted errors
- no fallback test: enterprise/tests/anocrypto_no_fallback_test.cpp
- acceptance criteria: semantic_equal, or exact_der_equal where a fixed DER fixture applies
- current blocker: `unsupported_pending`; exact AnoCrypto-C PKI/API capability discovery and trusted SDK execution pending
- current status: unsupported_pending

## certificate_issue

- current openssl implementation: src/backends/openssl/issue.cpp
- current anocrypto c adapter state: throws backend.capability_unavailable; unsupported_pending
- required sdk functionality: X.509 certificate encode/sign or verified signing primitives plus chosen PKI codec model
- required enterprise adapter work: preserve IssueRequest/IssueResult, profile validation, key binding, error mapping and signing evidence
- required fixture: fixed CSR, issuer, profile and key-provider fixtures
- positive test: compare decoded certificate semantics and verify signature with independent parser
- negative test: invalid profile, algorithm mismatch, key binding mismatch and provider failure
- no fallback test: enterprise/tests/anocrypto_no_fallback_test.cpp plus provider failure assertion
- acceptance criteria: semantic_equal; exact_der_equal only where serial/time/signature inputs are fixed
- current blocker: SDK certificate/signing and key-handle contracts unverified
- current status: unsupported_pending

## crl_generate_sign

- current openssl implementation: src/backends/openssl/crl.cpp
- current anocrypto c adapter state: throws backend.capability_unavailable; unsupported_pending
- required sdk functionality: X.509 CRL encode/sign or verified primitives plus chosen PKI codec model
- required enterprise adapter work: map CRL request/result, provider boundary, stable failures and signing evidence
- required fixture: fixed issuer, CRL number, update times and revoked-entry set
- positive test: compare decoded CRL semantics and verify signature
- negative test: bad times, invalid reason, key mismatch and provider failure
- no fallback test: enterprise/tests/anocrypto_no_fallback_test.cpp plus provider failure assertion
- acceptance criteria: semantic_equal; exact_der_equal when all encoding and signing inputs are deterministic
- current blocker: SDK CRL/signing and key-handle contracts unverified
- current status: unsupported_pending

## ocsp_decode

- current openssl implementation: src/backends/openssl/ocsp.cpp
- current anocrypto c adapter state: throws backend.capability_unavailable; unsupported_pending
- required sdk functionality: OCSP request DER decode, certificate-ID and nonce extraction, issuer hash derivation
- required enterprise adapter work: map request/issuer inspection contracts and reject malformed or unsupported input
- required fixture: tests/fixtures/ocsp curated request plus malformed and multi-request variants
- positive test: compare certificate IDs, hash algorithms and nonce semantics
- negative test: malformed DER, unsupported digest and issuer mismatch
- no fallback test: extend enterprise/tests/anocrypto_no_fallback_test.cpp for issuer inspection
- acceptance criteria: semantic_equal against curated fixtures
- current blocker: SDK OCSP/ASN.1 capability unverified; issuer-inspection no-fallback assertion absent
- current status: unsupported_pending

## ocsp_response_sign

- current openssl implementation: src/backends/openssl/ocsp.cpp
- current anocrypto c adapter state: throws backend.capability_unavailable; unsupported_pending
- required sdk functionality: OCSP BasicResponse encode/sign, responder validation or verified primitives plus chosen codec model
- required enterprise adapter work: map response contracts, responder validation, provider boundary and signing evidence
- required fixture: fixed issuer/responder certificates, request, status set and update times
- positive test: compare decoded response semantics and independently verify signature/responder chain
- negative test: unauthorized responder, stale time, mismatched issuer/key and provider failure
- no fallback test: enterprise/tests/anocrypto_no_fallback_test.cpp; add responder-validation assertion
- acceptance criteria: semantic_equal; exact_der_equal only for deterministic encoding/signature cases
- current blocker: SDK OCSP response/signing contracts unverified; responder-validation no-fallback assertion absent
- current status: unsupported_pending
