# Backend Capability Contract

P3-11 local evidence state: `sdk_execution=passed_102`,
`capability_observation=verified`, `operation_parity=local_parity_verified`,
`production_ready=false`, `fallback_enabled=false`, and
`kcmvp_status=not_validated`.

| Stable operation | AnoCrypto-C profile | Evidence |
| --- | --- | --- |
| csr_inspect | implemented | RSA/P-256 PoP, SAN, malformed/signature negatives |
| certificate_issue | implemented | RSA SHA-256/384/512, P-256 SHA-256, binding/provider negatives |
| crl_generate | implemented | RSA/P-256 signing, semantics, failure/no-output checks |
| crl_inspect | implemented | PEM/DER semantics and malformed/signature negatives |
| ocsp_request_inspect | implemented | multi-CertID, nonce, strict DER negatives |
| ocsp_issuer_inspect | implemented | exact Name/SPKI-bit inputs; restricted SHA-1 and SHA-2 |
| ocsp_response_generate | implemented | RSA/P-256, nonce/status/time semantics, binding/provider negatives |
| ocsp_responder_validate | implemented | issuer signature, EKU, validity and mismatch negatives |

The external package remains pinned to `AnoCryptoC::AnoCryptoC`, version
`0.1.0-p3-10-restricted-sha1-ocsp-certid`, commit
`98f544a574f70b387c300f171243b4e87174937a`. Enterprise owns PKI encoding and
provider policy; SDK public APIs own primitives and key handles. No SDK source
or public API is vendored or changed.

Capability completion is local Phase 1 evidence. It does not authorize a
customer package, production install/export, hosted qualification, KCMVP claim,
external signing, timestamp, or tag.
