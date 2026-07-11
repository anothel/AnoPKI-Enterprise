# AnoCrypto Integration Plan

The Enterprise tree contains a C99 AnoCrypto skeleton so build files, repository
layout, and validation scripts can be wired before the real implementation arrives.
The skeleton is available only when `ANOPKI_ENABLE_ANOCRYPTO_BACKEND=ON`; it is
not the default production backend.

[ADR 0007](adr/0007-anocrypto-module-boundary.md) defines the target internal
split: a PKI codec owns ASN.1 and PKI formats, AnoCrypto owns cryptographic
primitives and module state, and key providers own `key_ref` resolution and
signing authorization. The public operation-level backend contract remains the
outer compatibility boundary.

## Gate sequence

1. Preserve OpenSSL-backed behavior as the baseline.
2. Introduce the internal codec/module/provider contracts from ADR 0007 without
   exposing OpenSSL types.
3. Generate OpenSSL golden fixtures.
4. Implement SHA-256 known-answer and negative tests as the first AnoCrypto
   vertical slice; this does not complete a PKI parity operation.
5. Extract prepare/sign/finalize paths and implement equivalent AnoCrypto-backed
   behavior one operation at a time.
6. Normalize backend errors so raw cryptographic errors do not become public API
   contracts.
7. Record codec, crypto module, provider, validated-mode, compiler, OS, and
   release artifact evidence independently.
8. Switch the Enterprise default only after parity, security review, and rollback
   evidence are complete.

## Current status

The current `enterprise/anocrypto` code is a skeleton. It is not a cryptographic
implementation and not KCMVP validated.

OpenSSL remains the compatibility and fallback backend until CSR, issuance, CRL,
OCSP, ACME, release evidence, and rollback parity are proven. KCMVP wording must
stay target, planned, or preparation-only until approved certification evidence
exists.

The migration may use OpenSSL as the PKI codec while AnoCrypto primitives are
introduced. Such a build is a hybrid and must report both components; it is not
evidence that the five AnoCrypto parity operations are complete.
