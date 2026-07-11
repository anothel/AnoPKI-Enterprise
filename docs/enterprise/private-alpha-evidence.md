# Enterprise Private Alpha Evidence

Status: local private-alpha engineering gate passed. CI execution and all
distribution remain blocked.

## Version And Edition Model

| Field | Value |
| --- | --- |
| Community baseline | `2be155780d4b024c76b0a901ec130e83fc221f2f` |
| Base version | `0.1.0-alpha.0` |
| Edition | AnoPKI Enterprise |
| Enterprise overlay version | `unreleased` |
| Enterprise overlay status | `private-alpha` |
| Active backend | OpenSSL |
| AnoCrypto | Opt-in skeleton; pending |
| KCMVP | Not validated; no evidence |
| Commercial license | Placeholder; distribution blocked |
| HSM/KMS/PKCS#11 | Not implemented |

The service `/version`, C++ library version, release workflow, and release
artifact names use the base version. Enterprise edition and backend status are
separate metadata and do not create a production release version.

## AnoCrypto Parity Status

All five required operations remain `unsupported_pending`:

- CSR parse
- certificate issuance
- CRL generation/signing
- OCSP decode
- OCSP response signing

Skeleton self-test and registration success prove build wiring only. The pending
parity CTest remains an explicit skip and is not production evidence.

## Verification Result

- Enterprise boundary, docs, version, release-evidence, release-artifact,
  service-contract, core-contract, and secret checks passed.
- Community baseline drift validation passed at the recorded commit.
- Go test, vet, and build passed.
- CMake configure and Debug build passed with OpenSSL 3.6.3 and the opt-in
  AnoCrypto skeleton enabled.
- CTest discovered 11 tests: 10 executed and passed; the AnoCrypto parity test
  was explicitly skipped as `unsupported_pending`.
- `anocrypto_skeleton` label selected two tests and both passed.
- `anocrypto_parity_pending` label selected one test and it remained skipped.

Private-alpha engineering readiness is achieved for internal testing on this
worktree. A reviewed commit and CI run are still required for durable evidence.
Commercial distribution and production distribution remain prohibited while
the Enterprise license is a placeholder.
