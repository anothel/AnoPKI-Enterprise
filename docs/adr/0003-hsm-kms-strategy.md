# ADR 0003: HSM/KMS Strategy

## Status

Proposed.

## Decision

Production issuers and responders should use non-exportable key references
through HSM, KMS, or PKCS#11 providers. File-backed keys are local/dev only.

Key provider work is separate from crypto backend work. A key provider answers
where the private key lives and whether it is exportable. A crypto backend
answers which implementation performs parsing, encoding, and cryptographic
operations.

The first provider work should use mock software-token and mock PKCS#11 paths
to prove `DescribeKey`, `Sign`, `CheckReady`, audit metadata, and production
fail-closed behavior before any real HSM or cloud KMS integration is added.

## Consequences

- API and audit should prove private key material was not exported.
- Key ceremony and dual-control evidence are required before production use.
- Provider implementation is deferred until one deployment target is selected.
- Production mode must reject file keys, exportable provider metadata, readiness
  failures, and provider/key metadata mismatches.
