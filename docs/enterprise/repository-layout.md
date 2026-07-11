# Enterprise Repository Layout

Recommended ownership layout:

```text
anopki-enterprise/
  README.md
  community/ or synchronized shared tree/
    include/anopki/                 # backend-neutral Core contract
    src/core/                       # shared Core
    src/backends/openssl/           # Community OpenSSL adapter
    service/

  enterprise/
    licensing/
    auth/
    ui/
    deploy/
    reports/

  include/anopki/enterprise/
    anocrypto_backend.hpp

  src/backends/anocrypto_c/
    anocrypto_backend.cpp           # adapter only; no algorithms

  cmake/presets or profiles/
    enterprise-openssl
    enterprise-anocrypto-c

  sdk-manifests/anocrypto-c/
    <pinned build metadata; no credentials>

  docs/enterprise/
  packaging/
  LICENSES/
```

Do not add an embedded `anocrypto/src`, algorithm vectors, self-test
implementation, or copied private SDK source to the Enterprise repository.

## Sync Rule

- Community is the upstream owner of Core and the OpenSSL adapter.
- Generic contract changes go to Community first.
- Enterprise periodically synchronizes the reviewed Community baseline.
- Enterprise does not duplicate or fork the OpenSSL adapter.
- Enterprise CI runs Community tests plus Enterprise profile tests.
- Shared-baseline drift checks exclude only documented Enterprise-owned paths.

## Build Profile Rule

- `Enterprise/OpenSSL` links the Community OpenSSL adapter.
- `Enterprise/AnoCrypto-C` links the Enterprise AnoCrypto-C adapter and external
  `AnoCryptoC::AnoCryptoC` package.
- A single operation must not switch adapter after startup.
