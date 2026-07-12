# External AnoCrypto-C Adapter Plan

## Position

AnoCrypto-C is a separate external C99 project and SDK. The Enterprise
repository does not implement its cryptographic algorithms, module lifecycle,
self-tests, random service, or zeroization.

Enterprise owns only the AnoPKI adapter, configuration, integration tests,
metadata, packaging policy, and operation parity evidence.

## Dependency Contract

The adapter consumes the installed CMake package:

```cmake
find_package(AnoCryptoC 0.1.0 EXACT CONFIG REQUIRED)
target_link_libraries(anopki_enterprise_anocrypto PRIVATE AnoCryptoC::AnoCryptoC)
```

The Enterprise build must pin and record the exact SDK artifact, version, build
identity/fingerprint, platform, compiler/runtime compatibility, and license.

## Adapter Contract

The AnoCrypto-C adapter implements the same operation-level contract as the
Community OpenSSL adapter:

- CSR inspect
- certificate issue
- CRL generate
- OCSP request inspect
- OCSP response generate
- responder certificate validate
- backend identity/version/capabilities
- stable error mapping

The adapter must not declare unsupported SDK functions or emulate support using
OpenSSL.

## Current Partial Capability Rule

While the external SDK lacks a required operation:

- advertise the capability as unavailable,
- return a stable `backend.capability_unavailable` error,
- verify that no OpenSSL call occurs,
- keep the relevant parity state pending,
- block the Enterprise/AnoCrypto-C production release profile.

## No Fallback

AnoCrypto-C failure, initialization error, or missing capability must not cause
an OpenSSL retry. Customers needing OpenSSL select `Enterprise/OpenSSL` before
startup/build.

## Release Gate

Enterprise/AnoCrypto-C is production-releasable only after:

- all required Community operation capabilities are implemented,
- OpenSSL and AnoCrypto-C positive/negative parity evidence passes,
- missing-capability and dependency-failure tests pass,
- no-fallback tests prove OpenSSL was not invoked,
- exact SDK and artifact evidence is attached,
- security review covers key handling and failures,
- KCMVP wording is limited to valid exact-module evidence.

## Public Claim Rule

| 상태 | 허용 문구 |
| --- | --- |
| capability 일부 구현 | AnoCrypto-C integration profile under development; not production-ready |
| full parity, 검증 전 | AnoCrypto-C-backed Enterprise profile; KCMVP not validated |
| KCMVP 시험 중 | KCMVP verification in progress for the listed AnoCrypto-C module; not validated |
| 검증 완료 | KCMVP-validated AnoCrypto-C module only for the listed version/build/platform |

AnoPKI 전체가 자동으로 검증된 것으로 표현하지 않습니다.

## Explicit Product Profile

The adapter is assembled only by selecting
`ANOPKI_PRODUCT_PROFILE=enterprise-anocrypto-c`. The OpenSSL adapter is not
linked into that artifact. Missing SDK configuration fails during CMake
configuration. Current SDK capability metadata is empty for operation-level PKI
functions, so those requests return `backend.capability_unavailable`.
