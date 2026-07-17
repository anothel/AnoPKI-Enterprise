# PKI Operation Responsibility Matrix

AnoCrypto-C does not own the Go service or HTTP API, ACME, DB/lifecycle,
audit/recovery drills, release/package operation, commercial licensing,
OIDC/SAML, RBAC, UI, SIEM, or customer workflow. Enterprise owns those product
concerns.

SDK or adapter-boundary concerns are the exact SDK version/commit, ABI and build
fingerprint, `AnoCryptoC::AnoCryptoC`, readiness/module/self-test state,
machine-readable capabilities, thread safety and lifetime, zeroization, stable
error mapping, exact license/build manifest, key-handle behavior, and proof that
fallback is disabled and unused.

The canonical machine matrix is
`docs/enterprise/handoff/operation-responsibility-matrix.json`; every row there
also records blockers and acceptance tests.

## Open Codec Decision

Status: `design_decision_required`.

- Model A: AnoCrypto-C supplies high-level ASN.1/PEM/DER and
  X.509/CSR/CRL/OCSP APIs.
- Model B: Enterprise owns the PKI codec/operation layer and uses verified
  AnoCrypto-C crypto primitives.

Neither model is production-validated. Do not implement both speculatively.

| PKI operation | Backend-neutral behavior | Required crypto primitives | Key-provider responsibility | AnoCrypto-C SDK responsibility | Enterprise adapter responsibility | Community responsibility | Enterprise product responsibility | Current status (all pending/unverified) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CSR PEM/DER parse | decode CSR, normalize requested subject/SAN/public-key/signature metadata | PEM/base64, ASN.1 DER, hash, public-key signature verification | none | provide high-level CSR APIs or verified primitives under the selected codec model; capability unverified | map Core input/output/errors, never invoke OpenSSL fallback | own backend-neutral contract, provide OpenSSL adapter and fixtures | validate API input, apply profile policy, audit stable result | unsupported_pending |
| CSR signature validation | verify CSR proof-of-possession and return stable validity/error semantics | ASN.1 DER, hash, RSA/ECDSA verification per approved scope | none | verify CSR signature or expose verified public-key primitives; capability unverified | map verification result and stable errors, no fallback | define behavior and OpenSSL reference implementation | reject invalid CSR before lifecycle transition | unsupported_pending |
| certificate issue | apply IssueRequest and certificate profile, produce normalized IssueResult | X.509 ASN.1 encode, hash, certificate signature | resolve non-exportable issuer key reference, check readiness/binding, sign without exporting private bytes | certificate encode/sign or required primitives; capability unverified | map request/result, enforce provider and no-fallback boundary, emit signing evidence | own contract, profiles, OpenSSL adapter and golden fixtures | authorize issuance, persist result/evidence, audit lifecycle | unsupported_pending |
| certificate signature | sign certificate TBS using requested algorithm and selected key reference | hash, RSA/ECDSA signature per approved scope | own handle/reference and signing authorization, prevent export, return redacted evidence | perform or support selected signature primitive; capability unverified | bridge codec TBS to provider/SDK once, validate returned evidence | define shared signing semantics and OpenSSL reference behavior | bind operation/request identity and retain evidence | unsupported_pending |
| CRL generate | encode issuer, update interval, CRL number and revoked entries | X.509 CRL ASN.1 encode, hash | none until signing | CRL encoding or required primitives; capability unverified | map GenerateCRLRequest/Result and stable errors | own contract, OpenSSL implementation and fixtures | select revoked entries and publication lifecycle | unsupported_pending |
| CRL sign | sign CRL TBS with selected issuer key reference | hash, RSA/ECDSA signature per approved scope | non-exportable issuer key resolution, binding/readiness/signing evidence | signature primitive or key-handle operation; capability unverified | invoke selected signer once and preserve no-fallback evidence | shared signing contract and OpenSSL reference | audit and publish only proven result | unsupported_pending |
| CRL inspect | decode CRL PEM/DER and normalize issuer, updates, number and entries | PEM/base64, ASN.1 DER | none | CRL decode API or required primitives; capability unverified | map CRLInfo and stable malformed-input errors | own contract and OpenSSL reference behavior | display/use normalized revocation metadata | unsupported_pending |
| OCSP request decode | decode request DER, certificate IDs and nonce | ASN.1 DER, hash identifier parsing | none | OCSP request decode or required primitives; capability unverified | map OCSPRequestInfo and stable errors | own contract, OpenSSL implementation and curated fixtures | request admission and response lookup | unsupported_pending |
| OCSP issuer identification | derive issuer name/key hashes for requested digest | X.509 parse, hash | none | issuer hash API or required primitives; capability unverified | map OCSPIssuerInfo and reject unsupported digest | own contract and OpenSSL reference | match request to issuer | unsupported_pending |
| OCSP response generate | encode statuses, update times and responder data into BasicOCSPResponse | OCSP ASN.1 encode, hash | none until signing | OCSP response encode or required primitives; capability unverified | map GenerateOCSPResponseRequest/Result | own contract, OpenSSL implementation and fixtures | authorize status data and response lifetime | unsupported_pending |
| OCSP response sign | sign OCSP response using selected responder key | hash, RSA/ECDSA signature per approved scope | resolve non-exportable responder key, binding/readiness/signing evidence | signature or key-handle operation; capability unverified | invoke selected signer once and validate evidence | shared signing semantics and OpenSSL reference | serve only verified, evidenced response | unsupported_pending |
| OCSP responder certificate validation | validate responder certificate against issuer and required usage | X.509 parse, chain/signature verification | none | responder validation or required primitives; capability unverified | map boolean/stable errors and reject invalid responder | own contract and OpenSSL reference | select authorized responder certificate | unsupported_pending |
| backend metadata/readiness | report identity, dependency, version, fingerprint, ABI, readiness and capabilities | module init, module state/self-test reporting | separate readiness check; no backend selection | return exact runtime version, build identity/fingerprint and operational state | fail closed on mismatch/init/non-operational state, advertise no unverified PKI capabilities | own BackendInfo and stable error contract | record profile/dependency metadata and gate release | contract_present_execution_not_run |
| key/certificate binding validation | prove selected signing key matches issuer/responder certificate | public-key derivation/comparison or sign/verify proof | return binding result without exporting private key | support handle/public-key binding where it owns key handles; capability unverified | reject mismatch before returning artifact, redact native errors | define shared binding semantics and OpenSSL tests | register expected issuer/responder binding | unsupported_pending |
| signing evidence generation | record stable operation/provider/key/result correlation without secrets | none beyond completed signing operation | return provider identity, key identity, readiness/exportability and fallback=false evidence | return safe module/build/result identity where applicable; capability unverified | emit evidence only for actual selected signing path, redact path/native error data | define shared provider evidence semantics | bind evidence to request/trace/lifecycle and retain securely | unsupported_pending |

AnoCrypto-C owns only verified SDK/module primitives or high-level APIs. Product authorization, lifecycle, persistence, provider selection and audit remain Enterprise responsibilities.
