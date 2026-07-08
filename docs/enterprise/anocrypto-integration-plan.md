# AnoCrypto Integration Plan

The Enterprise tree contains a C99 AnoCrypto skeleton so build files, repository
layout, and validation scripts can be wired before the real implementation arrives.

## Gate sequence

1. Preserve OpenSSL-backed behavior as the baseline.
2. Expand the crypto backend contract for CSR parse, certificate issue, CRL sign,
   OCSP decode, and OCSP sign operations.
3. Generate OpenSSL golden fixtures.
4. Implement equivalent AnoCrypto-backed behavior.
5. Normalize backend errors so raw cryptographic errors do not become public API
   contracts.
6. Record backend name, version, compiler, OS, and release artifact evidence.
7. Switch the Enterprise default only after parity, security review, and rollback
   evidence are complete.

## Current status

The current `enterprise/anocrypto` code is a skeleton. It is not a cryptographic
implementation and not KCMVP validated.
