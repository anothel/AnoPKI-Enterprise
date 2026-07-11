# Enterprise Private Release Evidence

Each Enterprise release candidate should record both upstream Community evidence and
Enterprise overlay evidence.

## Required additions

| Area | Evidence |
| --- | --- |
| PKI codec | name, version, source/build identity, and format/operation coverage |
| Crypto module | name, version, source/build identity, self-test and approved-mode status |
| Key provider | provider class and implementation, readiness, key binding, and exportability result |
| Validated mode | requested/active state, algorithm result, operating environment, and evidence identifier |
| Compatibility fallback | enabled/used state, operation, selected implementation, and reason |
| AnoCrypto parity | fixture result for each operation, including `unsupported_pending` |
| Commercial overlay | source commit, license manifest, customer package manifest |
| Provider integrations | HSM/KMS/PKCS#11 readiness, non-exportability, audit metadata |
| Deployment adapters | target version, post-deploy check, rollback result |
| Compliance | KCMVP status wording, evidence pointers, customer restrictions |

Record parity using `tests/fixtures/backend-parity/manifest.txt` and the result
states defined in [Crypto backend parity](../reference/crypto-backend-parity.md).
Current AnoCrypto skeleton operations are `unsupported_pending`; skipped parity
is a release gap, not evidence of implementation or production readiness.

Current evidence must identify OpenSSL as both the PKI codec and cryptographic
implementation. During a future hybrid migration it must identify OpenSSL as
the codec and AnoCrypto as the crypto module separately. KCMVP evidence, if
approved later, applies only to the exact module, configuration, algorithms,
and operating environment named by that evidence; it does not cover the codec,
provider, service, or complete product by implication.
