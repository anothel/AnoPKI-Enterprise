# Backend Capability Contract

Current evidence state: `sdk_execution=not_run`,
`capability_observation=unverified`, `operation_parity=unsupported_pending`,
`production_ready=false`, `fallback_enabled=false`, and
`kcmvp_status=not_validated`. An empty advertised capability set is not proof
that the SDK lacks a capability; it means no trusted observation exists.

| Stable operation | Input | Output | Required metadata | OpenSSL | AnoCrypto-C | Unavailable error | Release impact |
| --- | --- | --- | --- | --- | --- | --- | --- |
| csr_inspect | CSR PEM text | CsrInfo: subject, DNS/IP SANs, public-key metadata, signature metadata, extension OIDs | backend id, dependency name, dependency version, build fingerprint, ABI version, readiness, capability set, selected product profile, fallback_enabled=false | available | unsupported_pending | backend.capability_unavailable | blocks Enterprise/AnoCrypto-C production release |
| certificate_issue | IssueRequest: CSR, issuer certificate, issuer key reference, validity and certificate profile fields | IssueResult: certificate PEM, serial, subject and validity | backend id, dependency name, dependency version, build fingerprint, ABI version, readiness, capability set, selected product profile, fallback_enabled=false | available | unsupported_pending | backend.capability_unavailable | blocks Enterprise/AnoCrypto-C production release |
| crl_generate | GenerateCRLRequest: issuer certificate, issuer key reference, CRL number, update times and revoked entries | GenerateCRLResult: signed CRL PEM | backend id, dependency name, dependency version, build fingerprint, ABI version, readiness, capability set, selected product profile, fallback_enabled=false | available | unsupported_pending | backend.capability_unavailable | blocks Enterprise/AnoCrypto-C production release |
| crl_inspect | CRL PEM or DER | CRLInfo: issuer, update times, CRL number and revoked entries | backend id, dependency name, dependency version, build fingerprint, ABI version, readiness, capability set, selected product profile, fallback_enabled=false | available | unsupported_pending | backend.capability_unavailable | blocks Enterprise/AnoCrypto-C production release |
| ocsp_request_inspect | OCSP request DER | OCSPRequestInfo: certificate IDs and nonce metadata | backend id, dependency name, dependency version, build fingerprint, ABI version, readiness, capability set, selected product profile, fallback_enabled=false | available | unsupported_pending | backend.capability_unavailable | blocks Enterprise/AnoCrypto-C production release |
| ocsp_issuer_inspect | issuer certificate PEM and requested hash algorithm | OCSPIssuerInfo: issuer name hash, issuer key hash and hash algorithm | backend id, dependency name, dependency version, build fingerprint, ABI version, readiness, capability set, selected product profile, fallback_enabled=false | available | unsupported_pending | backend.capability_unavailable | blocks Enterprise/AnoCrypto-C production release |
| ocsp_response_generate | GenerateOCSPResponseRequest: request DER, issuer certificate, issuer key reference, update times and statuses | GenerateOCSPResponseResult: signed OCSP response DER | backend id, dependency name, dependency version, build fingerprint, ABI version, readiness, capability set, selected product profile, fallback_enabled=false | available | unsupported_pending | backend.capability_unavailable | blocks Enterprise/AnoCrypto-C production release |
| ocsp_responder_validate | issuer certificate PEM and responder certificate PEM | ValidateOCSPResponderResult: valid boolean | backend id, dependency name, dependency version, build fingerprint, ABI version, readiness, capability set, selected product profile, fallback_enabled=false | available | unsupported_pending | backend.capability_unavailable | blocks Enterprise/AnoCrypto-C production release |

AnoCrypto-C PKI capabilities are not implemented in this adapter; the observed
operation capability set is empty pending trusted discovery and execution.

## SDK Integration Requirements

- exact SDK source commit, source archive name, and archive SHA-256;
- exact `AnoCryptoC` 0.1.0 CMake config package and imported target
  `AnoCryptoC::AnoCryptoC`;
- runtime ABI version `1`, non-empty build fingerprint, and deterministic build
  manifest bound to the Enterprise consumer commit;
- readiness, module operational state, and self-test state from the runtime;
- machine-readable operation capabilities matching the stable names above;
- documented thread safety, object ownership/lifetime, and zeroization rules;
- stable native-to-`backend.*` error mapping with no path, key, credential, or
  raw native-error leakage;
- exact dependency license and build manifest;
- explicit key-handle/provider ownership and key/certificate binding behavior;
- capability-unavailable, dependency-failure, and no-OpenSSL-fallback tests.

The source and test index is
`docs/enterprise/anocrypto-handoff-current-status.md` (pending); the canonical machine
contract is `docs/enterprise/handoff/anocrypto-required-capabilities.json`.
