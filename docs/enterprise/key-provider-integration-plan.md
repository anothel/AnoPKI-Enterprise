# Enterprise Key Provider Integration Plan

ADR 0007 selects a deliberately scoped hybrid signing boundary. Enterprise reuses the Community/OpenSSL file-provider seam and may later add PKCS#11/local HSM providers compatible with the OpenSSL adapter.

Remote KMS is not implemented. Before adding a vendor SDK, Enterprise must prototype adapter-compatible signing versus a prepare/sign/finalize protocol and record persistence, idempotency, retry, audit, and credential boundaries.

Enterprise/AnoCrypto-C provider support remains blocked until the external SDK exposes the necessary signing/key-handle contract. No provider failure may fall back to OpenSSL, a file key, or another product profile.
