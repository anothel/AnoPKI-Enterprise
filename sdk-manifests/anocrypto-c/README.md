# AnoCrypto-C SDK Pin And Evidence

P3-11 local Phase 1 evidence is recorded separately in
`p3-11-local-evidence.json`. It is not hosted qualification evidence and does
not authorize production or customer distribution.

This directory documents the trusted SDK integration contract. AnoCrypto-C is
not vendored into this repository. A trusted workflow checks out an exact
40-character source commit, builds and tests the external project, installs its
CMake package, packages the installed SDK, records the artifact SHA-256, and
then builds the `enterprise-anocrypto-c` profile against that installed prefix.

Required facts for each trusted run:

- source repository and exact AnoCrypto-C commit,
- Enterprise repository, exact consumer commit, workflow ref, run ID, and attempt,
- package version,
- installed SDK archive name and SHA-256,
- deterministic archive settings, bundled dependency license, and embedded SDK build manifest,
- target OS and architecture,
- compiler and CMake versions,
- runtime version, build-identity ABI, and build fingerprint,
- module readiness, selected backend, capability set, and no-fallback result,
- external SDK tests, Enterprise integration tests, and no-OpenSSL-linkage results,
- CI run URL and KCMVP status.

The generated evidence file is a workflow artifact. It is not committed as a
release claim until reviewed. The example JSON is intentionally marked
`example_only` and is not valid release evidence.

Trusted CI requires the repository secret `ANOCRYPTO_C_READ_TOKEN`. The token
must be read-only, must not be exposed to fork pull requests, and must be able
to read `anothel/AnoCrypto-C` after that repository is made private.
