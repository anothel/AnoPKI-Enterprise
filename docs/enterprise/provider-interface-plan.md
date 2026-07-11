# Enterprise Provider Interface Plan

This plan separates Enterprise key providers from crypto backends.

- Key providers answer where a private key lives and whether it is exportable.
- Crypto backends answer which implementation performs parsing, encoding, and
  cryptographic operations.
- Production issuer and OCSP responder keys must use `key_ref` values backed by
  non-exportable providers.
- File keys are local/dev only and must fail closed in production mode.

No real HSM, KMS, or PKCS#11 provider is implemented by this plan.

## Provider Contract

Enterprise provider implementations should expose:

- `DescribeKey(key_ref)`: returns provider class, algorithm, public-key binding
  material, exportability, and stable provider identity.
- `Sign(key_ref, algorithm, digest_or_tbs)`: signs certificate, CRL, or OCSP
  material without returning private key bytes.
- `CheckReady(key_ref)`: verifies provider reachability, key availability,
  authentication state, and policy readiness before signing paths run.
- Audit metadata: records provider class, provider id, key id or alias,
  exportability, operation type, request/trace id, and stable result code.

Audit metadata must not include private key bytes, provider credentials, PINs,
session tokens, raw file paths, or raw provider errors that may contain secrets.

## Fail-Closed Conditions

Production mode must reject signing when:

- a `file:` or bare filesystem key is selected,
- provider readiness cannot be checked,
- provider metadata says the key is exportable,
- provider algorithm metadata does not match the requested profile,
- provider identity or key binding differs from registered issuer/responder
  metadata,
- provider errors cannot be mapped to a redacted stable result code.

## Backlog

1. Add a mock software-token provider for tests and local demos.
2. Add a mock PKCS#11 provider facade that exercises slot/token/key lookup and
   non-exportability metadata without a real HSM.
3. Wire provider readiness into issuer, CRL, and OCSP signing tests.
4. Record provider readiness and non-exportability in private release evidence.
5. Select one real deployment target before implementing any production HSM,
   KMS, or PKCS#11 provider.
