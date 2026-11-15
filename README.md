# AnoPKI

`AnoPKI` is an operational PKI lifecycle service project.

The goal is not only to generate certificates. The goal is to model and operate certificate lifecycle infrastructure: identity, enrollment, issuance policy, renewal, revocation, status publication, audit, notification, and ACME automation.

## Scope

Current implementation includes:

- C++ core CLI for CSR inspection, certificate issuance, CRL generation, and OCSP DER processing.
- Go HTTP service for lifecycle APIs and persistence.
- Identity, issuer, certificate profile, enrollment, approval, issuance, revocation, suspension, renewal, reissue, and expiration scan flows.
- CRL publication and OCSP response handling.
- Delegated OCSP responder registration and rotation.
- API key authentication with operator, write, and read scopes.
- Audit metadata, lifecycle outbox events, webhook notification endpoints, bounded retry, and dead-letter handling.
- ACME-shaped protocol adapter with account, order, authorization, HTTP-01 challenge, finalize, and certificate download flows.

See [docs/ROADMAP.md](docs/ROADMAP.md) for future work and
[Release readiness action plan](docs/reference/release-readiness-action-plan.md)
for the current execution order derived from the uploaded analysis reports.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `include/anopki` | C++ public headers for core PKI operations. |
| `src/core` | Backend-neutral C++ operation dispatch. |
| `src/backends/openssl` | Community OpenSSL adapter implementation. |
| `src/cli` | `anopki-core` CLI entrypoint used by the service. |
| `tests` | C++ core and CLI contract tests. |
| `service` | Go lifecycle API service. |
| `service/internal/store` | SQL and in-memory persistence. |
| `service/internal/lifecycle` | Lifecycle domain service, workers, outbox, notifications. |
| `service/internal/httpapi` | HTTP and ACME protocol adapter. |
| `docs/reference` | Stable operator/developer reference docs. |
| `docs/runbooks` | Manual verification and demo runbooks. |
| `scripts/acme-smoke` | Opt-in ACME client smoke harness scaffold. |

## Prerequisites

- Go 1.26.11+
- CMake 3.20+
- C++20 toolchain
- OpenSSL development libraries

On Windows, set `OPENSSL_ROOT_DIR` to the vcpkg triplet root, not its `bin`
directory. Example:

```powershell
$env:OPENSSL_ROOT_DIR = "C:\vcpkg\installed\x64-windows"
```

The local verification wrapper also checks `VCPKG_ROOT`, the common
`C:\vcpkg\installed\x64-windows` path, and repo-local
`vcpkg_installed\x64-windows`. It adds the detected `bin` directory only to
the child verification process PATH, restores PATH afterward, and fails before
building if `libcrypto*.dll` is unavailable. A missing runtime commonly appears
as Windows exit `0xc0000135` when running CTest directly.

## Build And Test

Build and test the C++ core:

```powershell
cmake -S . -B build -DOPENSSL_ROOT_DIR="$env:OPENSSL_ROOT_DIR"
cmake --build build --config Debug
ctest --test-dir build -C Debug --output-on-failure
```

Test and build the Go service:

```powershell
cd service
go test ./...
go build ./cmd/anopki-service
```

## Quickstart Smoke Checklist

Use this deterministic checklist before trusting a local change or release
candidate. Expected output is shown after each command.

Run the local wrapper for the default docs, release metadata, contract,
secret-baseline, ACME smoke harness, C++ build/test, and Enterprise supported-Go
baseline evidence checks:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-local.ps1
# local verification ok
```

To inspect the wrapped commands without running them:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-local.ps1 -List
```

```powershell
python scripts\validate-docs.py
# docs ok

python scripts\test_validate_docs.py
# docs validator tests ok

python scripts\test_webhook_receiver_verification.py
# webhook receiver verification tests passed: 10

python scripts\test_verify_local.py
# verify-local tests ok

python scripts\test_validate_version_metadata.py
# version metadata tests ok

python scripts\validate-version-metadata.py
# version metadata ok

python scripts\test_generate_enterprise_release_metadata.py
# Enterprise release metadata generator tests ok

python scripts\test_verify_go_release.py
# Go release verification runner tests ok

python scripts\verify-go-release.py --profile baseline --out-dir .tmp\go-evidence\enterprise-verify-local
# requires Go 1.26.11+; records Enterprise commit and Community baseline separately

python scripts\test_verify_recovery_drill.py
# recovery drill tests passed: 5

python scripts\verify-recovery-drill.py --out-dir .tmp\recovery-evidence\verify-local
# recovery drill passed: 12 checks

python scripts\test_verify_status_outage_drill.py
# status outage drill tests passed: 5

python scripts\verify-status-outage-drill.py --out-dir .tmp\status-outage-evidence\verify-local
# requires Go 1.26.11+ and proves CRL/OCSP failure and recovery semantics

python scripts\test_verify_audit_replay_drill.py
# audit/replay drill tests passed: 5

python scripts\verify-audit-replay-drill.py --out-dir .tmp\audit-replay-evidence\verify-local
# requires Go 1.26.11+ and proves idempotent audit repair and scoped dead-letter recovery

python scripts\test_verify_audit_integrity_drill.py
# Audit integrity drill tests passed: 8

python scripts\verify-audit-integrity-drill.py --out-dir .tmp\audit-integrity-evidence\verify-local
# requires Go 1.26.11+; local run proves Memory/SQLite/API integrity and release CI additionally requires PostgreSQL parity

python scripts\test_verify_authorization_boundary.py
# authorization boundary drill tests passed: 7

python scripts\verify-authorization-boundary.py --out-dir .tmp\authorization-boundary-evidence\verify-local
# requires Go 1.26.11+ and proves authentication/scope ordering, timeout, redaction, Audit correlation and race-clean behavior

python scripts\test_verify_issuer_rollover_drill.py
# issuer rollover drill tests passed: 5

python scripts\verify-issuer-rollover-drill.py --out-dir .tmp\issuer-rollover-evidence\verify-local
# requires Go 1.26.11+ and proves atomic same-root rollover and rollback semantics

python scripts\test_verify_multi_node_reliability.py
# multi-node reliability drill tests passed: 5

python scripts\verify-multi-node-reliability.py --out-dir .tmp\multi-node-evidence\verify-local
# requires Go 1.26.11+ and proves single-writer issuance, CRL and Outbox lease semantics

python scripts\test_verify_enterprise_postgres_failover.py
# Requires a disposable PostgreSQL 16 DSN in ANOPKI_POSTGRES_FAILOVER_DSN.
python scripts\verify-enterprise-postgres-failover.py --out-dir .tmp\enterprise-postgres-failover\local
# Application-node lease recovery under race instrumentation; see docs/enterprise/postgres-failover-qualification.md.

python scripts\test_verify_postgres_recovery_drill.py
# PostgreSQL recovery drill tests passed: 5

# Optional full PostgreSQL 16 drill; requires psql, pg_dump, pg_restore and a disposable DSN.
$env:ANOPKI_POSTGRES_RECOVERY_DSN = "postgres://anopki:anopki@localhost:5432/anopki_recovery_control?sslmode=disable"
python scripts\verify-postgres-recovery-drill.py --out-dir .tmp\postgres-recovery-evidence\verify-local
# requires Go 1.26.11+ and proves transaction rollback plus pg_dump/pg_restore state preservation

python scripts\test_validate_release_artifacts.py
# release artifact tests ok

python scripts\test_validate_service_contracts.py
# service contract validator tests ok

python scripts\validate-service-contracts.py
# service contracts ok

python scripts\test_validate_core_cli_contracts.py
# core CLI contract validator tests ok

python scripts\validate-core-cli-contracts.py
# core CLI contracts ok

python scripts\test_validate_release_evidence.py
# release evidence validator tests ok

python scripts\validate-release-evidence.py
# release evidence ok

python scripts\test_security_baseline_scan.py
# security baseline scan tests ok

python scripts\security-baseline-scan.py
# secret baseline scan ok

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\acme-smoke\test-run-certbot-smoke.ps1
# run-certbot-smoke tests passed

cmake -S . -B build
# configure succeeds

cmake --build build --config Debug
# build succeeds

ctest --test-dir build -C Debug --output-on-failure
# all C++ tests pass

cd service
go test ./...
# all listed packages exit ok

go vet ./...
# exit 0

go build -o .tmp\verify-local\anopki-service.exe ./cmd/anopki-service
# exit 0
```

## Product Profile Build

Enterprise builds select one explicit profile:

```powershell
cmake -S . -B build-openssl -DANOPKI_PRODUCT_PROFILE=enterprise-openssl -DOPENSSL_ROOT_DIR="$env:OPENSSL_ROOT_DIR"

cmake -S . -B build-anocrypto -DANOPKI_PRODUCT_PROFILE=enterprise-anocrypto-c -DANOCRYPTO_SDK_ROOT="C:\sdk\anocrypto"
```

The selected profile and adapter metadata can be inspected with:

```powershell
.\build-openssl\Debug\anopki-core.exe backend info
```

Backend selection is immutable for the artifact and automatic fallback is disabled.

## Run Locally

Build `anopki-core` first, then run the service with `ANOPKI_CORE_BIN` pointing at the CLI binary.
Local defaults are listed in [.env.example](.env.example).

```powershell
cd service
$env:ANOPKI_ADDR = ":8080"
$env:ANOPKI_DB_DRIVER = "sqlite"
$env:ANOPKI_DB_DSN = "anopki.db"
$env:ANOPKI_CORE_BIN = "..\build-openssl\Debug\anopki-core.exe"
go run ./cmd/anopki-service
```

For a 10-minute local issuance smoke, build the core CLI, then let the ACME
harness start a temporary service and issue through lego:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\acme-smoke\run-certbot-smoke.ps1 `
  -Client lego `
  -LegoPath .tmp\lego-bin\lego.exe `
  -StartService `
  -Run `
  -DirectoryTimeoutSec 60 `
  -WorkDir .tmp\acme-smoke-verify `
  -DbDsn .tmp\acme-smoke-verify\anopki.db `
  -ServiceBin .tmp\acme-smoke-verify\anopki-service.exe `
  -ServiceLogDir .tmp\acme-smoke-verify\service-logs `
  -HTTPSProxyBin .tmp\acme-smoke-verify\acme-https-proxy.exe
```

For local development, auth defaults to `dev` mode and accepts `X-Actor`.

For API-key mode:

```powershell
$env:ANOPKI_AUTH_MODE = "api_key"
$env:ANOPKI_BOOTSTRAP_API_KEY = "change-me"
$env:ANOPKI_BOOTSTRAP_API_KEY_ACTOR = "ops-admin"
$env:ANOPKI_API_KEY_PEPPER = "local-dev-pepper-0123456789abcdef"
go run ./cmd/anopki-service
```

## Documentation

Start with the [Documentation Index](docs/INDEX.md). It is the canonical map for public repository docs and keeps this README from becoming a duplicate documentation tree.

Most-used docs:

- [Service README](service/README.md): API behavior, configuration, ACME status, auth, workers, and operator endpoints.
- [Roadmap](docs/ROADMAP.md): future-only priorities, defer/delete rules, and remaining risk areas.
- [Security policy](SECURITY.md): reporting, supported status, production expectations, known constraints, and disclosure process.
- [Contributing guide](CONTRIBUTING.md): prerequisites, local verification, roadmap rules, documentation expectations, and commit guidance.
- [Project scope](docs/reference/project-scope.md): supported PKI domains, explicit non-goals, and current boundaries.
- [Target architecture](docs/reference/target-architecture.md): component boundaries and production shape.
- [Crypto backend strategy](docs/reference/crypto-backend-strategy.md): backend-neutral core, explicit Enterprise/OpenSSL and Enterprise/AnoCrypto-C profiles, external SDK integration, and no-fallback gates.
- [Release process](docs/runbooks/release-process.md): release candidate checklist, verification, metadata, and approval gates.
- [Release evidence](docs/reference/release-evidence.md): artifact, SBOM, signing, scan, compatibility, and backend evidence baseline.
- [Documentation governance](docs/reference/documentation-governance.md): what belongs in Git, what belongs in internal/GPT project sources, and how to retire stale docs.

Current execution focus: close Enterprise release evidence, keep shared
FileKeyProvider/golden/no-fallback validators stable, and obtain trusted external
AnoCrypto-C capability-parity evidence.
Separately select a real production
non-exportable provider. Public TLS issuance fails closed unless the configured
lint hook accepts the CSR/profile before signing; external lint tool selection
and fixtures remain future work.

## License

AnoPKI Enterprise is a mixed-license private repository. Community-derived
files remain MPL-2.0; Enterprise-only files use the current internal
`LicenseRef-AnoPKI-Enterprise` placeholder. See [LICENSE](LICENSE) and
[ENTERPRISE-LICENSE-NOTICE.md](ENTERPRISE-LICENSE-NOTICE.md). Customer and
production distribution are not authorized.

## Current Status

This is a lifecycle-service implementation in progress. Core lifecycle, profile policy, status publication, auth, audit, notifications, security/contribution docs, CI workflow, and ACME adapter foundations exist. Live lego and certbot HTTP-01 smokes reach account, order, challenge validation, finalize, and certificate response against a harness-started local service. Current priority is release-candidate trust: API/doc/code parity, negative failure-mode tests, compatibility evidence, and release operations.

| Release boundary | Current state |
| --- | --- |
| Enterprise/OpenSSL internal validation package | Manifest generation enabled; customer distribution is not implied |
| Enterprise/OpenSSL customer package | Blocked by incomplete license/notices, hosted qualification, and commercial authorization |
| Enterprise/AnoCrypto-C internal validation package | Adapter/evidence inputs only; external SDK is not copied |
| Enterprise/AnoCrypto-C customer package | Blocked; trusted SDK not run, parity pending, production false, KCMVP not validated |


### Trusted AnoCrypto-C SDK integration

Ordinary pull-request CI does not fetch private AnoCrypto-C source. A protected manual
workflow accepts an exact source commit and uses the read-only
`ANOCRYPTO_C_READ_TOKEN` secret to build, test, install, hash, and consume the
external SDK. See `sdk-manifests/anocrypto-c/README.md`. A successful workflow
proves package consumption and no-fallback behavior only; PKI operation parity
remains pending until the external SDK exposes and passes those operations.


Enterprise provider architecture: [Key provider integration plan](docs/enterprise/key-provider-integration-plan.md).
