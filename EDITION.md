# AnoPKI Enterprise Edition

This repository is the private **AnoPKI Enterprise** codebase.

Enterprise is intended to track the Community codebase while adding private
commercial overlays such as the AnoCrypto backend integration, productized
deployment adapters, advanced access control, compliance evidence, and commercial
packaging.

## Important status

The included AnoCrypto files are integration skeletons only. They are not a
production cryptographic implementation, not a KCMVP-validated module, and not
evidence that AnoPKI has switched away from the OpenSSL-backed behavior.

OpenSSL remains the compatibility baseline until CSR, issuance, CRL, OCSP, ACME,
and release evidence parity is proven.
