# Changelog

All notable changes to this project will be recorded here.

This project is pre-1.0. Release candidates must record exact verification
commands and known gaps before tagging.

## Unreleased (`v0.1.0-alpha.0` candidate)

### Added

- A tamper-evident `sha256-v1` audit chain with monotonic sequence, migration
  backfill, Memory/SQLite/PostgreSQL verification, fail-closed append and
  retention, prune checkpoints, integrity API, and recovery evidence.
- Exact-commit audit-integrity, intermediate-issuer rollover, multi-node
  single-writer, and PostgreSQL backup/restore verification runners plus CI and
  release artifacts.
- A fail-closed audit-repair and dead-letter replay drill proving current
  signing/policy evidence reconstruction, idempotent repair, scoped replay,
  preserved attempt history, recovered delivery, redaction, and exact-commit
  release binding.
- A fail-closed CRL/OCSP outage-and-recovery drill covering lifecycle
  atomicity, public 502 mapping, no phantom publication or success audit,
  recovery numbering, signing evidence, and release archive validation.
- Stable allow/reject/unknown policy-decision audit metadata with redacted
  validation-evidence references across enrollment, issuance, retry, and repair.
- A deterministic fail-closed SQLite backup/restore drill with redacted
  evidence, release archive validation, and dirty-migration, CRL-state, and
  private-key-material regression checks.
- Shared Community/OpenSSL ECDSA P-256 signing regression coverage for
  certificate issuance, CRL generation, and OCSP responses, with non-interactive
  encrypted-PEM rejection across all three `FileKeyProvider` operation boundaries.
- A fail-closed Enterprise Go release verification runner with explicit
  baseline/analysis/full profiles, pinned analysis tools, redacted local
  evidence, separate Enterprise commit and Community baseline fields, and no
  commercial-release, AnoCrypto-C parity, fallback, or KCMVP success claim.
- Strict Go parsing of `anopki-core backend info`, additive `/version` backend
  and KeyProvider policy metadata, and Enterprise/OpenSSL release artifacts that
  bind backend capabilities without exposing key refs.
- Shared Community/OpenSSL certificate-issuance, CRL-signing, and
  OCSP-response-signing `FileKeyProvider` slices, single-provider resolver,
  test-only software-token contract, and redacted signing-result evidence.
- Enterprise/OpenSSL release metadata generation and validation with
  `anocrypto_used=false`, no fallback, and `kcmvp_status=not_applicable`.
- ADR 0007 selecting a deliberately scoped hybrid KeyProvider signing boundary and certificate-issuance file-provider first slice.
- Backend identity, capability, readiness, stable error, and explicit product-profile metadata with `anopki-core backend info`.
- CI workflow for docs validation, service contract parity, secret baseline
  scan, Go service tests/build, PostgreSQL migration integration, and C++
  CMake/CTest.
- MPL-2.0 license file and docs-as-code validation.
- Release readiness, security, contribution, architecture, policy, operation,
  runbook, compliance, and ACME conformance documentation.
- Lifecycle service foundations for identity, issuer, certificate profile,
  enrollment, issuance, revocation, suspension, renewal, reissue, audit,
  outbox, webhook delivery, CRL, OCSP, and ACME adapter flows.
- Issued-certificate DER golden coverage for SAN, KU, EKU, Basic Constraints,
  AIA, CRL Distribution Points, SKI, and AKI.
- Profile algorithm policy for CSR public key algorithm, minimum key size, and
  selected signing algorithm.
- Release evidence manifest for artifact, SBOM, signing, scan, and
  compatibility decisions, validated in CI.
- Tagged release workflow for Linux amd64 service/core archives, checksums,
  CycloneDX SBOM, and cosign signatures.
- Documentation index and documentation governance rules that separate maintained
  public repository docs from internal or GPT project source material.
- Crypto backend strategy and ADR 0006 recording AnoCrypto as the intended
  backend direction while OpenSSL-backed core operations remain the current
  implementation.
- Release evidence fields for recording the active crypto backend and the
  intended AnoCrypto migration direction per release candidate.
- Docs validator guard for previous-name identifiers outside migration,
  compatibility, or historical documentation contexts.
- Backend-neutral crypto parity fixtures and OpenSSL parity reporting for CSR,
  issuance, CRL, and OCSP operations.
- Draft local release evidence for the `v0.1.0-alpha.0` candidate.
- Physically separated backend-neutral core dispatch from the Community OpenSSL adapter while preserving all existing CLI and golden contracts.

### Changed

- Release-evidence validation pins canonical audit-replay minimum-Go tuple
  spelling and rejects formatting drift.
- The shared C++ OpenSSL parity harness builds without the range-loop
  temporary-binding or unused-helper warnings fixed by Community.
- OpenSSL certificate, CRL, and OCSP signing resolve one adapter-private
  provider and no longer open signing private-key files directly.
- Go readiness remains preflight; durable signing evidence comes from the
  completed C++ provider path.
- Roadmap is future-only; completed work belongs in reference docs, runbooks,
  or this changelog.
- Public docs are curated around the AnoPKI name, `ANOPKI_*` environment
  variables, `anopki-service`, `anopki-core`, `X-AnoPKI-*`, and `MPL-2.0`
  license wording.
- Root README now delegates the detailed documentation map to `docs/INDEX.md`
  to reduce duplicate documentation drift.
- Version metadata accepts SemVer prerelease identifiers while CMake uses the
  numeric `0.1.0` project version and binaries report `0.1.0-alpha.0`.
- `anopki_core` no longer links OpenSSL directly; `anopki_openssl_adapter` owns OpenSSL operations and dependency diagnostics.

### Known Gaps

- Certbot live smoke remains environment-gated on Linux or elevated Windows.
- Local ZIP baseline verification does not close Go service tests/builds when
  the host Go toolchain is older than the repository requirement and cannot
  download the requested toolchain.
- Git working-tree status, GitHub Actions CI URLs, tagged release artifacts,
  SBOM output, cosign signatures, and Go lint/security scanner evidence must be
  recorded from the real repository before tagging a release candidate.
- Full compatibility evidence, HSM/KMS provider boundary, external audit
  anchoring/SIEM integration, EAB, and DNS-01 remain future work.
