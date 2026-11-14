# Enterprise Upstream Sync

AnoPKI Enterprise is a reviewed overlay that consumes Community-owned Core,
OpenSSL adapter, Go service, public contracts, common tests, and validators from
one exact target tree. Git histories remain unrelated and are never joined.

Current synchronized baseline:
`ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc`.

## Reviewed Enterprise Fixes Against The Frozen Baseline

Community is frozen at `49142ff50f5b37ba142d18cf61b60d8b287bdb49`;
Enterprise continues to consume the pinned baseline above. The later
`5348a47` failover tests and `49142ff` closeout/runner changes have not been
bulk synchronized. Community source and history remain read-only.

Four explicit Enterprise patches are applied to shared files:

| File | Verified reason |
| --- | --- |
| `scripts/acme-smoke/test-run-certbot-smoke.ps1` | Linux rejects `-WindowStyle`; the child runner must use the active PowerShell executable. Paths with spaces exercise subprocess quoting. |
| `service/cmd/anopki-service/main_test.go` | Remove the unused helper rejected by pinned staticcheck 2026.1 (`U1000`). |
| `service/internal/store/sqlstore_outbox.go` | Use a typed, NULL-safe deadline comparison; PostgreSQL rejects the original untyped `$14 IS NULL` expression. |
| `service/internal/store/migrate.go` | Preserve row-close errors alongside audit-backfill read/parse errors; pinned gosec reports unchecked close calls. |

`validate-community-baseline.py` pins the normalized upstream and patched
SHA-256 for each file. All other shared bytes still match the baseline exactly;
unlisted changes and further changes to these files fail validation. These
exceptions require review with their diffs and regression results, and must be
reconciled explicitly if a later sync is selected. They do not advance the
Community pin or claim that Community contains the fixes.

## Remote And Target Verification

Use a remote named `community`:

```powershell
git remote add community <community-url-or-local-path>
git fetch community
git cat-file -e "ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc^{commit}"
```

For local sibling repositories:

```powershell
git remote add community ..\AnoPKI-Community
git fetch community
```

The pinned SHA is authoritative. A later `community/main` must not replace it
implicitly.

## Exact-Tree Strategy

Recalculate the full diff from the previous baseline to the pinned target:

```powershell
git diff --name-status `
  acb71b8f4e9133d9c25dad1be3bca58209fba0d7 `
  ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc
```

Extract allow-listed shared paths from the exact target tree. Do not use branch
HEAD as the source:

```powershell
$Target = "ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc"
git restore --source=$Target --worktree -- <allow-listed-shared-paths>
```

Community-owned files must equal target blobs byte-for-byte after normalized
line endings. Shared files deleted by the target must be absent. In particular,
`src/core/openssl_backend.hpp` must not exist.

Do not join unrelated histories through merge, rebase, cherry-pick, subtree, or
forced history operations.

## Ownership Classes

Exact shared paths include target files under:

- `include/anopki/` public contracts,
- `src/core/`,
- `src/backends/openssl/`,
- `src/cli/`,
- `service/`, excluding Enterprise-only additions not present in the target,
- common `tests/`,
- common Community boundary, Core CLI, and KeyProvider validators.

Mixed files require reviewed manual integration. They include CMake product
assembly, Enterprise workflows, root product docs, release validators, local
verification wrappers, and Enterprise-aware public architecture/evidence docs.
The baseline validator checks explicit required structure instead of accepting
arbitrary drift.

Community-only files are excluded exactly. The Community release generator and
its test remain absent because they force `community-openssl` and
`edition=community`. Enterprise uses
`scripts/generate-enterprise-release-metadata.py` and its own fail-closed tests.

Enterprise-owned paths remain private, including:

- `enterprise/`,
- `docs/enterprise/`,
- `include/anopki/enterprise/`,
- `service/internal/enterprise/`,
- `src/backends/anocrypto_c/`,
- `src/enterprise/`,
- commercial license and private evidence files.

## Profile Boundaries

`enterprise-openssl` reuses the Community OpenSSL adapter without a fork and
assembles its config header, ABI/build fingerprint, FileKeyProvider/resolver,
and OpenSSL tests. `enterprise-anocrypto-c` consumes only the external
`AnoCryptoC::AnoCryptoC` package and must not link OpenSSL or fall back to it.
Missing SDK configuration must fail.

Enterprise/OpenSSL release metadata records `selected_backend=openssl`,
`anocrypto_used=false`, `fallback_enabled=false`, `fallback_used=false`, and
`kcmvp_status=not_applicable`. Enterprise/AnoCrypto-C production release blocked
with parity, trusted SDK evidence, and `kcmvp_status=not_validated` pending.

## Helper And Verification

The helper is read-only except for optional remote setup/fetch. It verifies the
pinned commit and prints the exact baseline diff:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-community-upstream.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-community-upstream.ps1 -Fetch
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-community-upstream.ps1 -Verify
```

After shared extraction and mixed integration, update baseline metadata last,
then run:

```powershell
python scripts\test_validate_enterprise_boundary.py
python scripts\validate-enterprise-boundary.py
python scripts\test_sync_community_upstream.py
python scripts\test_validate_community_baseline.py
python scripts\validate-community-baseline.py
python scripts\test_validate_key_provider_boundary.py
python scripts\validate-key-provider-boundary.py
python scripts\validate-enterprise-release.py --expect-blocked
```

Never push Enterprise-only material back to Community. Never record trusted SDK,
KCMVP, commercial release, or production-provider success without exact evidence.
