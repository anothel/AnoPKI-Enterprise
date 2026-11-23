# M2 Enterprise OpenSSL acceptance

[PKI-20](https://anothel.atlassian.net/browse/PKI-20) · [Enterprise #13](https://github.com/anothel/AnoPKI-Enterprise/issues/13) · [Handover](https://anothel.atlassian.net/wiki/spaces/AnoPKI/pages/2621531) · [Acceptance evidence](https://anothel.atlassian.net/wiki/spaces/AnoPKI/pages/2228228)

## Offline preflight

Use a clean Linux checkout, Python 3.11+, CMake 3.20+, a C++20 compiler, OpenSSL 3 CLI and development libraries, and `ldd`. Run from the repository root with the expected **full** source SHA. Save stdout outside the checkout.

```sh
python3 scripts/m2-openssl-acceptance/test_offline.py -v
python3 scripts/m2-openssl-acceptance/accept.py --commit FULL_SOURCE_SHA > /tmp/m2-openssl-preflight.json
```

Preflight configures a fresh CMake build with `ANOPKI_ENTERPRISE_EDITION=ON`, `ANOPKI_PRODUCT_PROFILE=enterprise-openssl`, and `BUILD_SHARED_LIBS=OFF`. It uses the CI Debug configuration to retain native test assertions. It checks the CLI backend identity, all eight capabilities, disabled fallback, the build fingerprint, the dynamically linked OpenSSL library, and the existing native fixture tests. The Python offline tests independently verify synthetic certificate, CRL and OCSP artifacts and reject incorrect profile metadata and signed status results. Preflight reports the live cases as `NOT_RUN`.

## Approved loopback lifecycle

The owner must approve the exact checkout, Linux runner, local SQLite database, temporary file keys and scope before invocation. Use the approval record's nonsecret identifier. The runner needs Go 1.26.11+ on PATH and a populated Go module cache. The harness disables Go toolchain and module downloads during the run.

```sh
python3 scripts/m2-openssl-acceptance/accept.py --commit FULL_SOURCE_SHA \
  --approval APPROVAL_REFERENCE > /tmp/m2-openssl-live.json
```

The harness builds and launches the Go service and its outbox worker. It creates its own loopback listener address, SQLite database, API keys, CA and CSR files in a private temporary directory. The harness confirms ownership of the listener through Linux procfs before sending credentials. The service invokes the freshly built native CLI. The run compares service and CLI backend metadata and checks the CLI digest at completion.

- API-key access uses operator, writer and reader credentials. It checks missing and invalid tokens, forbidden mutations, invalid CSR, SAN mismatch, issuance before approval and duplicate approval.
- Issuance verifies the certificate chain, subject alternative names, CSR public key, profile extensions and issuer/serial. Replay with the CA key temporarily absent checks that the API returns the same signed result.
- Revocation verifies inventory state and the public CRL publication. The harness converts the served PEM to DER, validates the signature, issuer association, CRL number, validity and revoked serial, then checks that CRL-based verification rejects the leaf.
- OCSP verifies the signature and nonce against the original request, issuer and serial lookup, status and validity for good, revoked and unknown serials. Malformed DER and incorrect media type exercise the error paths.
- The harness checks lifecycle audit actors, absence of raw credentials and the key path in audit events, audit-chain integrity and completed revocation outbox delivery.

The JSON records commands with temporary paths redacted, HTTP methods/paths/statuses, toolchain versions, backend identity, binary and signed artifact digests, partial results and cleanup. The service is terminated and reaped before removing the temporary database and keys. Child output, HTTP bodies, tokens, private keys and raw DER are excluded from the report. `service_cleanup` records service exit independently from scratch cleanup.

## Evidence limits

Results apply to the exact source SHA and toolchain in the report. The baseline OpenSSL CRL generator omits the authority key identifier extension. CRL issuer evidence comes from the signed issuer distinguished name and certificate verification. Live SQLite HTTP acceptance, owner disposition and independent review require their own evidence. Selected AnoCrypto-C SDK, protected workflows, PostgreSQL, HA, durable signing fault injection and production key providers are outside this harness. `EXTERNAL_RELEASE_NOT_AUTHORIZED`.
