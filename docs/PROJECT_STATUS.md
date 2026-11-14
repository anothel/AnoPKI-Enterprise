# AnoPKI Project Status

Verified on 2026-11-15 (Asia/Seoul) in Codex Cloud, corresponding to 2026-11-14
UTC during verification. This is an engineering recovery record,
not production qualification, release authorization, or a cryptographic
certification claim. Historical evidence remains bound to its original commits.

## Source And Synchronization

| Source | Verified revision and meaning |
| --- | --- |
| Enterprise implementation consumed for this review | `c1e0bbbefa2003657c7fefdf5924f964c4bab3ec`; clean initial checkout matched remote `main`. Work proceeds on `codex/resume-anopki-validation`. |
| Recorded Community pin | `ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc`; `.edition/edition.json`, sync documentation and validator agree. |
| Frozen Community remote | `49142ff50f5b37ba142d18cf61b60d8b287bdb49`; two commits beyond the consumed pin. No Community edits, commits or pushes were made. |
| Unconsumed Community work | `5348a478ff1117482a8d168b655dad290367b188` adds PostgreSQL multi-node test/evidence coverage; `49142ff` freezes the project and fixes portable Python evidence runners. The combined delta affects 38 files. It was assessed without advancing the pin. |
| Enterprise crypto evidence input | `sdk-manifests/anocrypto-c/p3-11-local-evidence.json` names Enterprise **pre-change baseline** `c3f7b679782f52c90311b7b7670b577ee972c1f6`, Community `ab9d765`, and SDK `98f544a574f70b387c300f171243b4e87174937a`. It is not a new validation of current Enterprise HEAD. |
| SDK remote observed | `b3d5e6551b2bcc38b39602592476146e4b81b9b0`. The recorded `98f544a` is absent from reachable history and an exact fetch fails with `upload-pack: not our ref`. No newer SDK was substituted. |

Before fixes, the baseline validator confirmed 199 exact shared files and 29
mixed files. This branch retains 195 exact files, four explicitly pinned
Enterprise patches, and the same mixed boundaries. Both upstream and patched
normalized hashes are enforced, including rejection of unlisted drift. See
[upstream synchronization](enterprise/upstream-sync.md). Histories remain
separate; the Community baseline metadata is unchanged.

## Reconstructed Architecture And Feature State

```text
Operator / ACME client
  -> Go HTTP RA: authentication, scopes, request safety, authorization hook
  -> lifecycle: policy, enrollments, durable issuance, audit, status, outbox
  -> SQL repository: SQLite / PostgreSQL (memory implementation for tests)
  -> corecli subprocess: one existing CLI operation + private evidence sidecar
  -> C++ backend-neutral Core
  -> immutable OpenSSL OR AnoCrypto-C adapter -> selected key provider / SDK
```

| Area | Source-backed state | Incomplete work / limits |
| --- | --- | --- |
| Lifecycle | Identity, issuer/profile management, enrollment/approval, issue, renewal/reissue, revoke/suspend, expiration scan; SQL migrations and durable issuance attempts exist. | Production operations and infrastructure failover qualification remain open. |
| CRL / OCSP | Publication, status handling, delegated responders, signing and outage/recovery tests exist. | Real production signer and external availability evidence remain open. |
| ACME | Account/order/authz, nonce handling, HTTP-01, finalize and certificate retrieval exist; harness preflight and service-start self-tests run locally. | No live certbot/lego interoperability run was performed in this review; DNS-01/EAB remain deferred. |
| Auth / authorization | API keys, scopes, generic bounded evaluator seam, audit correlation, and Enterprise decision engine/contracts exist. | Enterprise engine is not connected to runtime enforcement; SSO/full RBAC and read-only authorization audit coverage remain incomplete. |
| Audit / notifications | SHA-256 audit chain, backfill/checkpoints/integrity API, repair, outbox leases, webhook retry and dead letters exist. | Independent external anchoring/SIEM export and real traffic-shift qualification remain open. |
| OpenSSL profile | Default Enterprise profile reuses Community adapter and supports all eight advertised operation capabilities. Local OpenSSL 3.5.7 build/tests passed. | Exportable file keys cannot establish production key protection. |
| AnoCrypto-C profile | `c1e0bbb` adds a bounded PKI codec/provider and eight operation capabilities; local parity is recorded historically. Runtime target consumes external `AnoCryptoC::AnoCryptoC`, with OpenSSL used by independent tests. | Exact historical SDK cannot currently be fetched, so runtime parity was not rerun. Hosted qualification and independent codec review remain required. |
| Packaging / release | Edition, license inventory, internal manifest, deterministic package and release gates exist. | Commercial license/authorization, hosted evidence, production provider and customer distribution remain blocked. |

## Crypto, Provider, Concurrency And Recovery Review

- Backend selection is immutable at build time. The missing-SDK configuration
  fails explicitly; no backend or provider fallback was added. Core capability
  checks and stable provider errors preserve the existing API/CLI contracts.
- The OpenSSL adapter resolves one provider, checks algorithm/certificate
  binding, rejects exportable production keys, and writes signing evidence only
  after signing. CTest exercises file/provider errors, mismatched evidence,
  software-token contracts, golden results and CLI contracts. The software
  token is test-only; it is not a production HSM implementation.
- The Go runner creates a private temporary sidecar, rejects unknown fields,
  trailing JSON and inconsistent operation/algorithm/binding/fallback evidence.
  Certificate evidence persists on the issuance attempt; CRL/OCSP use their
  operation result. Readiness and `/version` metadata are not signing proof.
- AnoCrypto-C source checks key-reference class, production exportability,
  algorithm, public-key binding, SDK status and evidence write failure. SDK
  handles use RAII. Private PEM/DER and scalar/CRT vectors use ordinary C++
  storage without explicit secure erasure: review memory lifetime and cleanup
  before any stronger key-protection claim.
- AnoCrypto-C backend instances initialize/shutdown module state; the default
  backend is a function-static instance inside each CLI process. Multiple
  backend-instance ownership, constructor failure cleanup after module init,
  and SDK thread-safety remain unverified against the missing exact SDK.
  No speculative lifecycle rewrite was made.
- Durable signing results, compare-and-swap leases, transactional finalization,
  audit repair and outbox lease recovery exist. The new SQL regression verifies
  NULL/non-NULL lease claims and stale-node rejection on both SQL engines.
  Signing that succeeds before sidecar persistence can leave an unreturned
  signature; remote/billed signers need an explicit idempotency/recovery design.
- The default Go service uses UUID IDs. Frozen upstream's simulated nodes each
  use a fresh `threadSafeIDGenerator` counter starting at `id-1`; its issuance
  failover test therefore collides with existing audit IDs. That fixture failure
  does not establish a production UUID collision.

These are scoped source/test observations, not an exhaustive security audit.
No credentials or private-key material were included in evidence or this report.

## CI Investigation And Completed Changes

The recorded Enterprise hosted run
[29579430288](https://github.com/anothel/AnoPKI-Enterprise/actions/runs/29579430288)
is for `22f5ebde6bfe2e3b40f874bb52dd5957152e4f22` and the older Community
`71f0e898c32a7d6e00d0725eeab6ca150ccaa0af`. The provider still returns 17 failed
jobs with no steps or log URLs. Repository evidence classifies it as a billing /
spending-limit runner-allocation blocker. It is neither a test failure nor a
successful qualification of this branch. The connector's commit-run lookup
filters PR events; an empty response does not prove there were no push runs.
No hosted run was manually triggered in this review.

Opening draft PR #1 automatically started
[CI run 43623291642](https://github.com/anothel/AnoPKI-Enterprise/actions/runs/43623291642)
for implementation commit `d1e2e9cc81800e2fa09e9488fae5ef6c9a412fd4`.
Runners were allocated and the ACME harness, PostgreSQL integration, Go 1.25.12
baseline, C++ core, audit-integrity/replay and multiple operational drills
passed. Thus the historical runner-allocation blocker is not a current blocker
for this run. Full hosted qualification is still pending. Its backup/restore
job failed before tests because Ubuntu's unversioned client package installed
PostgreSQL 18 while the drill requires 16 (`psql major must be 16`). The affected
CI job and release-build job are pinned to Ubuntu 24.04; the version guard is
unchanged and the release workflow was not executed. The newer review commit
must complete its own hosted checks; results are not inherited from this run.

| Completed change and files | Reproduction / validation | Remaining risk |
| --- | --- | --- |
| ACME portability: `scripts/acme-smoke/test-run-certbot-smoke.ps1` | Linux PowerShell 7.4.13 rejected unconditional `-WindowStyle Hidden`; use `-NoNewWindow` and the active host executable. Full self-test passes, now with spaces in stub/project paths and existing exit-code assertions. | Windows PowerShell was not available for a fresh run. No live ACME-client claim. |
| Staticcheck: `service/cmd/anopki-service/main_test.go` | Pinned staticcheck 2026.1 reported `U1000` for unused `httptestResponseBody`; remove only that helper. Staticcheck then passes. | This is test-code cleanup, not a runtime change. CI's Go 1.26.5 was not exercised here. |
| PostgreSQL outbox: `service/internal/store/sqlstore_outbox.go`, `service/internal/store/outbox_cas_regression_test.go` | New test reproduces SQLSTATE `42P08` at `$14 IS NULL`. `IS NOT DISTINCT FROM $14` provides typed NULL-safe equality. PostgreSQL 16 and SQLite regressions pass, including wrong/stale deadline rejection; PostgreSQL integration passes. | Full primary-election/network-partition testing is outside this local DB test. |
| Audit error handling: `service/internal/store/migrate.go`, `service/internal/store/audit_backfill_close_test.go` | Pinned gosec v2.25.0 reported three unchecked closes. Preserve explicit close errors with `errors.Join`. Driver-level regressions fail before and pass after the fix while retaining primary scan/parse errors. Migration/backfill tests pass; gosec reports zero issues. | Rare failure diagnostics can now include both errors; public API/CLI schemas are unchanged. `database/sql` may suppress a secondary driver error when it automatically closes rows after an iteration failure; regressions establish the explicit scan/parse close paths. |
| Sync guard: `scripts/validate-community-baseline.py`, new `scripts/test_validate_community_baseline.py`, `.github/workflows/ci.yml`, `docs/enterprise/upstream-sync.md` | Four exact upstream/patched hash pairs allow only these reviewed fixes. Real-Git fixture tests cover patched acceptance, CRLF normalization, unrelated drift, upstream mismatch, missing files and unknown exception paths. Added CI execution for the regression script. | Future shared edits must explicitly reconcile patch hashes; this is not a bulk baseline sync. |
| Recovery runner: `.github/workflows/ci.yml`, `.github/workflows/release.yml` | Hosted run `43623291642` proves the `ubuntu-latest` PostgreSQL 18 client mismatch. Pin only jobs that execute the version-16 recovery drill to Ubuntu 24.04. Existing workflow/release validators remain applicable. | Final hosted rerun is required; no release dry-run or publishing workflow was invoked. |
| Recovery context: `docs/PROJECT_STATUS.md`, `docs/INDEX.md` | Maintained status, source SHAs, architecture, results, limitations and priorities; documentation validation checks links and repository conventions. | Historical readiness metadata elsewhere remains conservative and must not be upgraded without new evidence. |

## Verification Record

Commands ran in Enterprise unless marked Community. Activate this cloud's
prepared tools with `source /workspace/.onboarding/activate.sh`; local PowerShell
was installed under `/workspace/scratch/powershell`. PostgreSQL ran in a
loopback-only disposable PostgreSQL 16 container, using separate integration
and failover databases. Tests reset their database schema: use disposable DSNs.

| Command / check | Observed result |
| --- | --- |
| `go test ./...`, `go vet ./...`, `go build ./cmd/anopki-service` (output directed to ignored scratch) | Passed on Go 1.25.12, Linux/amd64. PostgreSQL tests without a configured DSN skip; separate live run below verifies the integration subset. |
| `verify-go-release.py --profile analysis` and subsequent full run | Race, staticcheck 2026.1 and gosec v2.25.0 pass after fixes. govulncheck v1.1.4 cannot fetch `https://vuln.go.dev/index/modules.json.gz` (`Forbidden`); overall gate remains failed. No vulnerability-clean result is claimed. |
| `go test -p 1 ./internal/store ./internal/httpapi -run PostgresIntegration -count=1 -v` with disposable DSN | Passed, including new outbox CAS regression, migration/repository parity and ACME nonce persistence. |
| `go test ./internal/store -run 'TestAuditBackfillPreservesCloseErrorAfterReadFailure\|OutboxCompareAndSwap\|Migration' -count=1 -v` | Passed. The audit close-error tests were observed failing before the fix; PostgreSQL CAS also failed before its fix and passed with a live DSN afterward. |
| `cmake -S . -B build-openssl -DANOPKI_PRODUCT_PROFILE=enterprise-openssl -DCMAKE_BUILD_TYPE=Debug`, build, CTest | Build passed; 15/15 CTests passed on OpenSSL 3.5.7. |
| AnoCrypto-C profile with required package explicitly unavailable | CMake failed as expected. Actual SDK-dependent tests were not run. |
| `pwsh -NoProfile -File scripts/acme-smoke/test-run-certbot-smoke.ps1` | Passed after process fixes; preflight, missing-client exit codes, timeout and fake service startup exercised. |
| Python `scripts/test_*.py` self-tests | 37/37 passed after PowerShell setup, including the new baseline-guard tests. Initially `test_verify_local.py` was blocked by absent PowerShell; rerun passed. |
| Docs, service/CLI contracts, KeyProvider, AnoCrypto boundary, baseline, secret-baseline validators | Passed. `validate-enterprise-release.py --expect-blocked` confirms release remains blocked. |
| `verify-multi-node-reliability.py` and `verify-recovery-drill.py` with ignored output directories | Passed: 10 multi-node checks and 12 recovery checks. These are local application/restore drills, not infrastructure-level failover qualification. |
| Frozen Community: `go test -p 1 ./internal/lifecycle -run PostgresMultiNode -count=1 -v` on an unchanged disposable archive of `49142ff` | Issuance failed with duplicate audit ID (`23505`); CRL failover passed; outbox traffic shift failed with untyped parameter (`42P08`). Same two failures reproduced on an isolated database. No full failover success is claimed. |

Local redacted Go runner evidence is in `.tmp/resume-evidence/` (ignored, not
release artifacts). It was generated against the branch's working tree based
on `c1e0bbb`; the runner records Git HEAD but does not fingerprint uncommitted
changes. It must not be presented as immutable qualification of that SHA or
of a later review commit. Review the branch diff and rerun qualification on the
exact final commit before release. Raw disposable test logs stay in cloud
scratch; only safe findings are recorded here.

## Next Development Phase

1. **Restore reproducible validation inputs.** Recover the exact `98f544a` SDK
   source/artifact and reconcile the historical pre-change Enterprise baseline
   with the actual consumer commit. Verify SDK hashes, rerun eight-operation
   parity/no-fallback/purity tests and review the custom ASN.1/PKI codec before
   accepting new parity claims. Do not silently choose current SDK HEAD.
2. **Close CI blockers on an exact review commit.** Allow `vuln.go.dev` in the
   cloud network configuration, verify the recovery-runner correction, and complete the
   supported Go matrix plus ACME/PostgreSQL checks. Restore CLI API credentials
   if `gh` is needed; the connected provider and Git transport can read the
   repositories despite the CLI reporting invalid authentication.
3. **Choose a bounded Enterprise failover evidence slice.** Consume/adapt the
   frozen `5348a47` tests with noncolliding simulated node IDs; retain stale
   lease, duplicate-signing and outbox assertions. Incorporate portable evidence
   runners deliberately. Keep Community frozen and do not relabel application
   lease recovery as PostgreSQL primary failover.
4. **Select one production key-provider target.** Define non-exportability,
   identity/binding, credential handling, cancellation, memory cleanup,
   idempotency, retry and recovery responsibilities before implementing
   PKCS#11/HSM/KMS support. Preserve stable errors and zero implicit fallback.
5. **Connect Enterprise authorization deliberately.** Review the existing
   decision contract/catalog and generic hook before enabling enforcement;
   define timeout behavior, read-only decision evidence and migration semantics.
6. **Qualify operations and distribution.** Run backup/restore, outage,
   audit-replay/integrity, rollover and traffic-shift evidence on exact commits;
   reconcile conservative metadata only when evidence exists. Commercial
   licensing, production readiness and KCMVP remain unapproved/unvalidated.
