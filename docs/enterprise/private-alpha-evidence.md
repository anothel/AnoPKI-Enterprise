# Enterprise Private Alpha Evidence

Status: local private-alpha engineering gate passes for the Enterprise/OpenSSL
profile. CI execution and all customer/production distribution remain blocked.

## Version And Edition Model

| Field | Value |
| --- | --- |
| Community baseline | `2be155780d4b024c76b0a901ec130e83fc221f2f` |
| Base version | `0.1.0-alpha.0` |
| Edition | AnoPKI Enterprise |
| Enterprise overlay version | `unreleased` |
| Enterprise overlay status | `private-alpha` |
| Active backend | OpenSSL |
| AnoCrypto-C integration | External SDK adapter boundary; SDK not configured |
| AnoCrypto-C module self-test | Owned by the external SDK; not executed by this baseline |
| AnoCrypto-C capability set | Unverified until a pinned external SDK is supplied |
| PKI parity | Required operations remain `unsupported_pending` |
| Validated mode | `false` |
| KCMVP | Not validated; no evidence |
| Commercial license | Placeholder; distribution blocked |
| HSM/KMS/PKCS#11 | Not implemented |

The service `/version`, C++ library version, release workflow, and release
artifact names use the Community base version. Enterprise edition and adapter
status are separate metadata and do not create a production release version.

## AnoCrypto-C Integration Status

The old embedded AnoCrypto implementation and copied headers have been removed.
Enterprise now owns only an adapter source boundary that consumes the separately
installed CMake package `AnoCryptoC::AnoCryptoC`.

Current state:

- default Enterprise/OpenSSL configuration requires no AnoCrypto-C SDK,
- enabling the SDK integration without a package fails CMake configuration,
- a real SDK integration run has not yet been recorded,
- CSR inspection, certificate issuance, CRL generation, OCSP inspection,
  OCSP response generation, and responder validation remain unavailable through
  the AnoCrypto-C adapter,
- unavailable operations return `backend.capability_unavailable`,
- OpenSSL is never an automatic fallback from the AnoCrypto-C adapter.

## Local Verification Result

- Enterprise boundary, docs, version, release-evidence, service-contract,
  core-contract, and secret checks passed.
- Enterprise/OpenSSL CMake configure and build passed with OpenSSL 3.5.5 in the
  audit environment.
- Enterprise/OpenSSL CTest: 8 tests passed and the AnoCrypto-C parity test was
  explicitly skipped as `unsupported_pending`.
- Missing-SDK configuration was verified to fail when
  `ANOPKI_ENABLE_ANOCRYPTO_SDK_INTEGRATION=ON` and `AnoCryptoC` was unavailable.
- The adapter compiled against an out-of-tree contract stub only to validate the
  CMake/C++ consumer boundary. That is not real AnoCrypto-C integration evidence.

A reviewed commit, real private CI run, and a pinned real AnoCrypto-C SDK run are
still required for durable evidence. Commercial and production distribution
remain prohibited while the Enterprise license is a placeholder.

## Real Private CI Evidence

Do not replace `PENDING` values until a reviewed commit completes a real private
GitHub Actions run.

| Evidence field | Value |
| --- | --- |
| Reviewed commit SHA | `PENDING` |
| GitHub Actions run URL | `PENDING` |
| Community baseline commit | `2be155780d4b024c76b0a901ec130e83fc221f2f` |
| Active OpenSSL version | `PENDING` |
| Enterprise metadata result | `PENDING` |
| AnoCrypto-C SDK integration result | `PENDING` |
| Pending parity result | `PENDING` |
| License status | Commercial placeholder; distribution blocked |
| KCMVP status | Not validated; no evidence |
| Provider status | HSM/KMS/PKCS#11 not implemented |
| Distribution prohibition | Customer and production distribution prohibited |
