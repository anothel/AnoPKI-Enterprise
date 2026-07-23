# Enterprise Private Release Evidence

Each Enterprise release candidate records both the synchronized Community
baseline and Enterprise overlay evidence.

## Required Additions

| Area | Evidence |
| --- | --- |
| Product profile | `Enterprise/OpenSSL` or `Enterprise/AnoCrypto-C`; selected before startup/build |
| Selected adapter | adapter name, version, dependency, capabilities, and no-fallback result |
| Key provider | provider class, readiness, key binding, signing authorization, and exportability result |
| Validated mode | requested/active state, exact module/build/environment, and evidence identifier |
| AnoCrypto-C SDK | exact artifact, package/runtime version, build identity ABI, fingerprint, platform, compiler/runtime, and license |
| AnoCrypto-C parity | result for every required operation; no skip is accepted |
| Commercial overlay | source commit, license manifest, and customer package manifest |
| Provider integrations | HSM/KMS/PKCS#11 readiness, non-exportability, and audit metadata |
| Deployment adapters | target version, post-deploy check, and rollback result |
| Compliance | KCMVP wording, exact evidence pointers, and customer restrictions |

There is no automatic compatibility fallback. Customers requiring OpenSSL use
the separately selected `Enterprise/OpenSSL` profile. An AnoCrypto-C operation
must not retry through OpenSSL.

Parity uses `tests/fixtures/backend-parity/manifest.txt` and the states defined
in [Crypto backend parity](../reference/crypto-backend-parity.md). P3-11 records
local semantic parity for all operations; a skipped result remains a release
gap, not implementation evidence.

KCMVP evidence, if approved later, applies only to the exact external module,
configuration, algorithms, and operating environment named by that evidence.
It does not validate the codec, provider, service, Enterprise layer, or complete
product by implication.

## Current Implementation State

| Field | Current value |
| --- | --- |
| Product profile | Enterprise/OpenSSL |
| Selected adapter | Separated Community OpenSSL adapter (`anopki_openssl_adapter`) |
| Active operation backend | OpenSSL |
| AnoCrypto-C adapter | Eight operations implemented through the pinned external SDK |
| AnoCrypto-C SDK version/fingerprint | Recorded in `sdk-manifests/anocrypto-c/p3-11-local-evidence.json` |
| PKI operation parity | `local_parity_verified`; hosted qualification not run |
| Automatic fallback | Prohibited; not implemented |
| Validated mode | `false` |
| KCMVP evidence | None; not validated |
| Distribution | Prohibited while commercial license remains placeholder |

## Trusted SDK Evidence File

For `Enterprise/AnoCrypto-C`, attach the generated
`anocrypto-sdk-evidence.json` and matching SDK archive. Validate them with:

```text
python scripts/validate-anocrypto-sdk-evidence.py <evidence.json> --artifact <sdk-archive>
```

The evidence must identify the exact AnoCrypto-C source commit, exact Enterprise
consumer commit, workflow ref/run/attempt, deterministic installed-artifact SHA-256, bundled
dependency license and SDK manifest, runtime version, build-identity ABI, build fingerprint, toolchain, external and consumer
test results, no-OpenSSL-linkage and no-fallback results, PKI parity, and
`not_validated` KCMVP status. Branch or moving-tag references are not release evidence.
