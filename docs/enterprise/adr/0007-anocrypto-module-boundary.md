# ADR 0007: AnoCrypto Module And PKI Codec Boundary

## Status

Accepted target architecture; implementation pending.

This ADR defines a migration boundary. It does not establish AnoCrypto parity,
KCMVP validation, or production readiness. OpenSSL remains the active and
default implementation.

## Context

The current public `anopki::crypto::Backend` contract is backend-neutral at the
operation level. It exposes CSR inspection, certificate issuance, CRL
generation, OCSP request inspection, OCSP response generation, and responder
validation without exposing OpenSSL types.

The OpenSSL implementation beneath that contract is not internally separated.
`src/core/csr.cpp`, `issue.cpp`, `crl.cpp`, and `ocsp.cpp` combine PKI object
handling, cryptographic operations, random generation, and local file-key
loading. The service has a separate `key_ref` readiness boundary, but the C++
signing path still opens the referenced file and imports the private key.

The AnoCrypto adapter implements only skeleton metadata and self-test wiring.
Its five parity operations remain `unsupported_pending`.

## Current OpenSSL Usage Map

| Category | Current calls and locations | Target responsibility |
| --- | --- | --- |
| PEM and DER encoding/decoding | `PEM_read_bio_X509_REQ`, `PEM_read_bio_X509`, `PEM_write_bio_X509`, `PEM_read_bio_X509_CRL`, `d2i_X509_CRL_bio`, `PEM_write_bio_X509_CRL`, `d2i_OCSP_REQUEST_bio`, `i2d_OCSP_RESPONSE_bio` in the four core files | PKI codec |
| ASN.1 object handling | `ASN1_TIME`, `ASN1_INTEGER`, `ASN1_OBJECT`, extension decoding, OID conversion, and OpenSSL stacks throughout CSR, issuance, CRL, and OCSP code | PKI codec |
| X.509 certificate and extension construction | `X509_new`, names, validity, serials, public keys, `X509V3_EXT_*`, profile and SAN extensions in `issue.cpp` | PKI codec, except random serial bytes supplied by crypto module |
| CSR parsing and validation | CSR PEM parsing and metadata extraction in `csr.cpp`; proof-of-possession verification through `X509_REQ_verify` in `issue.cpp` | PKI codec extracts signed bytes, signature, algorithm, and SPKI; crypto module verifies |
| CRL construction | CRL object, revoked entries, reason and CRL-number extensions, sorting, and PEM output in `crl.cpp` | PKI codec |
| OCSP parsing and response construction | Request DER, CertID and nonce handling, responder certificate policy, BasicResponse status construction, and response DER in `ocsp.cpp` | PKI codec; cryptographic verification and signing delegated |
| Hashing | Digest selection through `EVP_sha*`; OCSP CertID hashing is currently hidden inside `OCSP_cert_to_id` | Crypto module for computed digests; codec owns DigestInfo/CertID encoding and identifies bytes to hash |
| Signature generation | `X509_sign`, `X509_CRL_sign`, and `OCSP_basic_sign` | Key provider is the signing entry point; its software implementation may use the crypto module |
| Signature verification | `X509_REQ_verify` and `X509_verify` | Crypto module, after the codec extracts canonical signed bytes and signature metadata |
| Random generation | `BN_rand` creates certificate serial numbers in `issue.cpp` | Crypto module DRBG; issuance policy converts returned bytes to a positive compliant serial |
| Private-key loading and handling | `BIO_new_file`, file reads, and `PEM_read_bio_PrivateKey` in issuance, CRL, and OCSP signing | Key provider; file provider remains local/dev only |
| Secure memory and zeroization | OpenSSL object destructors free keys, but the core has no explicit cleanse or secure-heap call | Crypto module for module secrets; key provider for provider buffers and credentials |

The test suite also uses OpenSSL to create and inspect fixtures. Test fixture
tooling is not part of the runtime module boundary and may continue to use
OpenSSL while recording the tool version.

## Decision

AnoPKI keeps the public operation-level `Backend` contract while introducing
three internal responsibilities for Enterprise parity work.

### AnoCrypto `CryptoModule`

AnoCrypto will own cryptographic primitives, module self-tests, approved/error
state, DRBG output, hashing, signature generation and verification, module-owned
software-key handling, and zeroization. Its C99 ABI is the validation boundary.
The wrapper may translate types and errors but must not duplicate primitive
implementations outside that boundary.

### `PkiCodec`

A separate PKI codec will own PEM and DER framing, ASN.1 object handling, X.509
and extension construction, CSR structure parsing, CRL construction, and OCSP
object parsing and construction. It will produce or consume canonical byte
buffers plus structured metadata. It will not load private keys or select key
providers.

OpenSSL may remain the PKI codec during migration. This use must be reported as
an OpenSSL codec, not hidden behind a claim that the complete PKI backend is
AnoCrypto. A future codec can replace OpenSSL without changing the AnoCrypto C99
primitive ABI.

### `KeyProvider`

The key provider owns `key_ref` resolution, key location, exportability,
readiness, provider audit metadata, and signing authorization. Production keys
must remain non-exportable and private key bytes must not enter the service
database.

All signing enters through `KeyProvider::Sign`. A local/dev software provider
may import a short-lived key into an opaque AnoCrypto handle and invoke the
crypto module. HSM, KMS, and PKCS#11 providers may sign remotely and therefore
need not use the local crypto module for that operation. The PKI codec never
receives a private key or provider credential.

## Minimal Interface Proposal

These are design contracts, not current production headers. `Bytes` is an owned
byte buffer, `ByteView` is a bounded immutable view, and every result carries a
stable AnoPKI error code. No OpenSSL, AnoCrypto, HSM, or cloud SDK type may cross
these interfaces.

```text
PkiCodec
  Metadata() -> { name, version, status }
  ParseCsr(encoded_object) -> ParsedCsr
    ParsedCsr = { metadata, spki_der, signed_bytes, signature, signature_algorithm }
  PrepareCertificate(spec, issuer_metadata) -> SignableObject
  PrepareCrl(spec, issuer_metadata) -> SignableObject
  ParseOcspRequest(der) -> ParsedOcspRequest
  PrepareOcspResponse(request, statuses, signer_metadata) -> SignableObject
  FinalizeSignedObject(signable, signature) -> EncodedObject

CryptoModule
  Metadata() -> { name, version, status, self_test_status, approved_mode_status }
  CheckReady(requested_mode) -> Result
  Hash(algorithm_id, input: ByteView) -> Bytes
  Verify(algorithm_id, public_key_der: ByteView,
         signed_bytes: ByteView, signature: ByteView) -> Result
  Random(purpose, output_length) -> Bytes
  ImportSoftwareKey(secret: SecretByteView) -> OpaqueKeyHandle
  Sign(handle, algorithm_id, signed_bytes: ByteView) -> Bytes
  DestroyKey(handle) -> Result

KeyProvider
  DescribeKey(key_ref) -> { provider_class, provider_id, key_id,
                            algorithm_id, public_key_der, exportability }
  CheckReady(key_ref, operation) -> Result
  Sign(key_ref, algorithm_id, signed_bytes: ByteView, audit_context) -> Signature
```

`SecretByteView` is allowed only between a local/dev provider and the module
import call. It must never be serialized, logged, cached in the service, or
passed to the codec. Production providers fail closed if exportability,
readiness, key binding, or algorithm policy cannot be established.

Algorithm identifiers must be closed, versioned values rather than free-form
OpenSSL names. Structured metadata must distinguish key algorithm, digest,
signature scheme, parameters, and encoding. Unknown identifiers fail closed.

## Error Boundary

Internal interfaces return stable codes in these classes:

- `invalid_encoding`, `invalid_structure`, and `invalid_signature`;
- `unsupported_algorithm` and `policy_rejected`;
- `crypto_self_test_failed`, `crypto_failed_state`, and
  `validated_mode_unavailable`;
- `key_not_found`, `key_not_ready`, `key_binding_mismatch`, and
  `key_not_non_exportable`;
- `random_generation_failed`, `sign_failed`, and `verify_failed`;
- `internal_failure` for redacted unexpected failures.

The operation adapter maps these to the existing stable core and service errors
such as `csr.parse_failed`, `issue.sign_failed`, `crl.create_failed`, and
`ocsp.sign_failed`, which the service already reduces to public domain errors.
Raw OpenSSL errors, AnoCrypto diagnostics, provider messages, paths, key
references, and credentials do not cross the CLI or HTTP API boundary.

## Migration And Compatibility

1. Current mode remains the existing OpenSSL operation backend.
2. The first hybrid mode is opt-in: OpenSSL PKI codec, AnoCrypto primitives where
   implemented, and an explicitly selected key provider.
3. Unsupported hybrid operations remain `unsupported_pending`; they do not
   silently fall back and pass AnoCrypto parity.
4. Compatibility mode may route a whole operation to the existing OpenSSL
   backend when explicitly configured. Evidence records that fallback and the
   reason.
5. A requested validated mode fails closed on module self-test failure,
   disallowed algorithm, unavailable approved state, or unapproved fallback.
6. OpenSSL remains the default until every required operation has parity,
   negative tests, rollback evidence, and security review.

Per-primitive fallback inside one signed artifact is prohibited because it
would make implementation and validation evidence ambiguous.

## Release And KCMVP Evidence

Release evidence records these fields independently:

| Field | Required value |
| --- | --- |
| PKI codec | name, version, source/build identity, and status |
| Crypto module | name, version, source/build identity, self-test result, and implementation status |
| Key provider | class, implementation, key exportability result, and readiness result |
| Validated mode | requested/active state, approved algorithm result, evidence identifier, and operating environment |
| Compatibility fallback | enabled/used state, operation, reason, and implementation selected |

The current implementation records OpenSSL for both PKI object handling and
cryptographic operations. A future hybrid records OpenSSL as PKI codec and
AnoCrypto as crypto module; it must not shorten that to an unqualified
`AnoCrypto backend` claim.

KCMVP evidence applies only to the exact AnoCrypto module version, build,
configuration, approved mode, algorithms, and operating environment covered by
the evidence. It does not automatically validate the PKI codec, service, key
provider, deployment, or whole AnoPKI product. Until approved evidence exists,
wording remains target, planned, preparation, or not validated.

## First Vertical Slice

Implement SHA-256 hashing through the C99 `CryptoModule` ABI first. This proves
module initialization, self-test/error state, backend-neutral buffers,
algorithm identifiers, error translation, and release metadata without
entangling ASN.1 or private-key handling.

Acceptance criteria:

- Community source and behavior remain unchanged; OpenSSL remains default.
- AnoCrypto remains an opt-in Enterprise build.
- SHA-256 known-answer tests cover at least the empty input and `abc` vectors.
- Negative tests cover an unsupported algorithm, invalid buffer contract, and
  forced module failed state in a test-only configuration.
- The wrapper maps failures to stable codes without exposing raw module errors.
- Metadata records codec, module, provider class, and validated-mode status
  independently.
- Tests prove inputs, digests, and errors are not logged; no private key is used
  by this slice.
- Documentation makes no KCMVP or production-readiness claim.
- None of the five PKI parity operations leaves `unsupported_pending` until its
  complete codec/module/provider path and fixture assertions exist.

## Consequences And Deferred Decisions

- The current `Backend` implementation must eventually become orchestration,
  not a second cryptographic implementation.
- OpenSSL calls that combine object construction and signing require a
  prepare/sign/finalize extraction before AnoCrypto can sign those objects.
- Exact algorithm identifier and parameter registries need a focused contract
  change before signature work.
- Whether an eventual non-OpenSSL codec is project-owned or third-party remains
  open; it must preserve the byte-level contracts and parser security tests.
- Real provider implementations, validated-mode policy, and certification
  scope remain separate work.
