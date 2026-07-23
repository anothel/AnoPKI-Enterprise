# AnoCrypto-C P3-11 Operation Parity

Recorded baselines: Enterprise `c3f7b679782f52c90311b7b7670b577ee972c1f6`
and Community `ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc`.

Allowed results are `semantic_equal`, `exact_der_equal`,
`local_parity_verified`, and `failure`. A skip is never a pass.

| Operation | AnoCrypto-C result | Independent evidence | No fallback |
| --- | --- | --- | --- |
| CSR parse/PoP | `semantic_equal` | RSA/P-256 OpenSSL verification and malformed/invalid signature cases | verified |
| Certificate issue | `semantic_equal` | RSA SHA-256/384/512 and P-256 decoded semantics/signatures | verified |
| CRL generate/inspect | `semantic_equal` | RSA/P-256 decoded semantics/signatures and negative cases | verified |
| OCSP decode/CertID | `semantic_equal` | nonce/multi-CertID plus exact SHA-1 Name/SPKI boundary fixture | verified |
| OCSP response/responder | `semantic_equal` | RSA/P-256 decoded semantics/signatures, nonce, EKU/validity negatives | verified |

OpenSSL is linked only into independent test executables. The AnoCrypto runtime,
adapter, SDK, integration test, and no-fallback test are scanned separately for
OpenSSL imports and symbols.
