# AnoCrypto-C Product/SDK Responsibility Boundary

P3-11 keeps the fixed boundary below.

| Owner | Responsibilities |
| --- | --- |
| AnoCrypto-C | module lifecycle/self-tests, key handles, RSA-2048, P-256 ECDSA, signature SHA-2, restricted OCSP CertID SHA-1 |
| Enterprise adapter | bounded PEM/DER/PKI codec, AlgorithmIdentifier, ECDSA raw/DER conversion, key references, provider policy, key binding, errors, evidence, no fallback |
| Community | unchanged backend-neutral operation contracts, OpenSSL implementation, fixtures and semantic reference |
| Enterprise product | profile selection, authorization, persistence/audit, release and distribution gates |

The adapter-private file provider parses supported unencrypted PKCS#8, PKCS#1,
and SEC1 keys, imports components through the public SDK API, verifies the
certificate public key, signs once, destroys the handle, and writes redacted
evidence only after the operation result exists. Production mode rejects an
exportable `file:` reference before opening it.

All eight backend operations are `implemented_local_parity_verified`. The
machine-readable operation matrix is
`docs/enterprise/handoff/operation-responsibility-matrix.json`.

This boundary does not imply production readiness. A non-exportable production
provider, hosted qualification, redistribution review, customer authorization,
and KCMVP validation remain deferred.
