# AnoPKI Project Status

Verified on 2026-11-15 (Asia/Seoul) in Codex Cloud, corresponding to 2026-11-14
UTC during verification. This is an engineering recovery record,
not production qualification, release authorization, or a cryptographic
certification claim. Historical evidence remains bound to its original commits.

## Go Security Qualification Follow-up — 2026-11-15

Current security work continues from PR #1 commit
`4a8d4d6f573bf5beb9d74a01a9beece56be74b38`. Hosted run
[43623921554](https://github.com/anothel/AnoPKI-Enterprise/actions/runs/43623921554)
completed 24 jobs successfully; Go analysis failed because govulncheck reported
19 reachable vulnerabilities. The supplied analysis artifact identifies the
Go 1.26.5 standard library (fixed through 1.26.11) and `x/text` v0.29.0
(fixed in v0.41.0). This supersedes the earlier uncertainty about that hosted
failure: it was a positive security finding, not a scanner outage.

### Patch And Compatibility Boundary

- Production, release, analysis and operational validation use Go **1.26.11**.
  The module directive and maintained runner minimums enforce that floor.
  `--minimum-go` may raise it but cannot downgrade it. Regression tests observed
  both vulnerable-compiler acceptance and floor-downgrade acceptance before
  their fixes, then rejected both after the fixes.
- The supported compatibility matrix is **1.26.11 / 1.27.4**, confirmed against
  Go's current release metadata. Go 1.25 executable qualification is retired.
  Older versions in dated evidence below remain historical observations.
- `x/text` is **v0.41.0**. Selected transitive updates are `x/sync` v0.22.0,
  `x/mod` v0.38.0 and `x/tools` v0.48.0. Each dependency declares a Go 1.25.0
  module minimum; the stricter project floor comes from the security policy.
  The selected graph contains 34 non-main modules, with exact module checksums,
  zip hashes and discovered license/patent texts recorded. Three additional
  test/support modules receive matching evidence as part of the full snapshot.
- The production x/text path is pgx SCRAM authentication:
  `main.go` selects the pgx driver; `pgconn/auth_scram.go` normalizes the configured
  database password with `secure/precis.OpaqueString.String`. Existing SQL and
  HTTP contracts are unchanged. No bespoke input filter or scanner suppression
  replaces the dependency fix.
- Frozen Community stays at its recorded `ab9d765` pin. There are now 175
  unchanged exact files, 24 exact reviewed patches and 29 mixed files. The new
  exceptions bind only the updated module files, prerequisites, drill minimums
  and synthetic fixtures. The AnoCrypto-C source pin and all SDK, KCMVP,
  commercial authorization and production-provider claims remain unchanged.

### Changed Files And Validation

| Change | Files | Validation / remaining limits |
| --- | --- | --- |
| Patched compiler and floor | `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `service/go.mod`, `scripts/verify-go-release.py`, eight `scripts/verify-*-drill.py` / reliability / hash-chain / authorization runners | Local Go test, vet, build, race and staticcheck pass on 1.26.11. Existing floor and evidence tests are updated; old compilers and explicit floor downgrades fail closed. Hosted qualification of the pushed commit remains required. |
| Dependency closure | `service/go.mod`, `service/go.sum` | `go mod verify` passes. PostgreSQL integration, outbox CAS and audit-close regressions pass on both the normal disposable DB and a SCRAM-authenticated PostgreSQL 16 DB with a generated non-ASCII password. Credentials are neither committed nor logged. |
| License/package provenance | `packaging/dependency-license-inventory.json`, both internal package manifests, both `THIRD_PARTY_NOTICES` outputs, exact versioned texts under `LICENSES/third-party/go/` | License validator passes. All immutable package self-tests pass against snapshot `82067e8` containing the new texts; the HEAD/index guard is preserved. Customer distribution is still prohibited. |
| Verification contracts | `scripts/validate-release-evidence.py`, `scripts/validate-release-artifacts.py`, matching tests and drill fixtures, `scripts/validate-community-baseline.py` | Security-floor and release-artifact tests pass. Hash pairs retain exact frozen-upstream bytes and reject unreviewed drift. The documented minimum check now requires the floor label rather than accepting an unrelated compiler pin elsewhere in the row. |
| Current instructions and evidence | `README.md`, `CONTRIBUTING.md`, `docs/operations/backup-restore-runbook.md`, `docs/reference/release-evidence.md`, `docs/enterprise/upstream-sync.md`, this status file | Current prerequisites are consistent. Dated past results are retained as history. No merge, tag, release workflow execution or publishing is authorized by this update. |

Local full verification completed: test, vet, build, race, staticcheck and
gosec passed; govulncheck failed because the cloud network denies
`https://vuln.go.dev/index/modules.json.gz`. The full local gate therefore
remains **failed**, not vulnerability-clean. All 37 Python self-test scripts
pass on the immutable candidate snapshot `82067e8` (which changes no branch
refs), including the four package tests that correctly required new evidence
files to exist in HEAD. PostgreSQL regressions pass using both the ordinary
disposable database and SCRAM authentication with a generated non-ASCII
password. Module verification, license and exact-baseline checks pass. CTest passes
15/15 and the full ACME harness self-test passes with Go 1.26.11. The actual
Go 1.25.12 compiler also rejects the new module directive before compilation. Hosted govulncheck on the exact pushed commit is required;
any remaining findings must be investigated without weakening the gate.

The following sections preserve the original architecture recovery and its
historical test results. They do not describe the new Go qualification state.

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

The subsequent
[CI run 43623547792](https://github.com/anothel/AnoPKI-Enterprise/actions/runs/43623547792),
for runner-correction commit `6de6a4eba6f41e4288672befab7cf29b399f66f3`,
passed PostgreSQL backup/restore, confirming the environment correction.
The first run's Go analysis failure is narrowed to govulncheck, but its runner
captures detailed diagnostics in files and the upload was skipped on failure.
The cause of the hosted govulncheck failure is therefore unresolved; the local
`Forbidden` result must not be assumed to explain the hosted failure. Go
baseline/analysis artifacts now upload even after failure, while preserving
the failing check and missing-evidence errors. Qualification of the final
revision remains required.

| Completed change and files | Reproduction / validation | Remaining risk |
| --- | --- | --- |
| ACME portability: `scripts/acme-smoke/test-run-certbot-smoke.ps1` | Linux PowerShell 7.4.13 rejected unconditional `-WindowStyle Hidden`; use `-NoNewWindow` and the active host executable. Full self-test passes, now with spaces in stub/project paths and existing exit-code assertions. | Windows PowerShell was not available for a fresh run. No live ACME-client claim. |
| Staticcheck: `service/cmd/anopki-service/main_test.go` | Pinned staticcheck 2026.1 reported `U1000` for unused `httptestResponseBody`; remove only that helper. Staticcheck then passes. | This is test-code cleanup, not a runtime change. CI's Go 1.26.5 was not exercised here. |
| PostgreSQL outbox: `service/internal/store/sqlstore_outbox.go`, `service/internal/store/outbox_cas_regression_test.go` | New test reproduces SQLSTATE `42P08` at `$14 IS NULL`. `IS NOT DISTINCT FROM $14` provides typed NULL-safe equality. PostgreSQL 16 and SQLite regressions pass, including wrong/stale deadline rejection; PostgreSQL integration passes. | Full primary-election/network-partition testing is outside this local DB test. |
| Audit error handling: `service/internal/store/migrate.go`, `service/internal/store/audit_backfill_close_test.go` | Pinned gosec v2.25.0 reported three unchecked closes. Preserve explicit close errors with `errors.Join`. Driver-level regressions fail before and pass after the fix while retaining primary scan/parse errors. Migration/backfill tests pass; gosec reports zero issues. | Rare failure diagnostics can now include both errors; public API/CLI schemas are unchanged. `database/sql` may suppress a secondary driver error when it automatically closes rows after an iteration failure; regressions establish the explicit scan/parse close paths. |
| Sync guard: `scripts/validate-community-baseline.py`, new `scripts/test_validate_community_baseline.py`, `.github/workflows/ci.yml`, `docs/enterprise/upstream-sync.md` | Four exact upstream/patched hash pairs allow only these reviewed fixes. Real-Git fixture tests cover patched acceptance, CRLF normalization, unrelated drift, upstream mismatch, missing files and unknown exception paths. Added CI execution for the regression script. | Future shared edits must explicitly reconcile patch hashes; this is not a bulk baseline sync. |
| Recovery runner: `.github/workflows/ci.yml`, `.github/workflows/release.yml` | Hosted run `43623291642` proves the `ubuntu-latest` PostgreSQL 18 client mismatch. Pin only jobs that execute the version-16 recovery drill to Ubuntu 24.04. Existing workflow/release validators remain applicable. | Final hosted rerun is required; no release dry-run or publishing workflow was invoked. |
| Failed-check diagnostics: `.github/workflows/ci.yml` | First hosted analysis reached govulncheck but skipped uploading its captured failure log. Go baseline/analysis uploads now run with `always()`, preserving the actual failed result and strict missing-file handling. | The next failed hosted run must supply its diagnostic artifact before root cause can be established. |
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
