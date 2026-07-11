# ADR 0007: External AnoCrypto-C SDK Adapter Boundary

## Status

Accepted; supersedes the embedded AnoCrypto prototype and SHA-256 vertical-slice plan.

## Decision

AnoCrypto-C is developed, tested, packaged, and versioned in its separate repository.
AnoPKI Enterprise consumes the installed CMake package `AnoCryptoC::AnoCryptoC`
through an Enterprise-owned adapter. AnoPKI does not copy or reimplement algorithms,
self-tests, module state, DRBG, random services, or zeroization.

OpenSSL remains the active Enterprise/OpenSSL profile. The AnoCrypto-C adapter is an
integration target only until the backend-neutral Community Core and required operation
capabilities are available. Unsupported operations return
`backend.capability_unavailable` and never call OpenSSL automatically.

## Consequences

- Embedded `enterprise/anocrypto/src` and copied public headers are prohibited.
- SDK absence or incompatibility fails the AnoCrypto-C integration configuration.
- SDK version, build identity ABI, fingerprint, platform, and capability evidence are
  release metadata.
- KCMVP claims apply only to exact valid AnoCrypto-C evidence and do not validate the
  whole AnoPKI Enterprise product automatically.
