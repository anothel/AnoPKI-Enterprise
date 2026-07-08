# Enterprise Upstream Sync

Keep `anopki-enterprise` as a reviewed overlay on top of `anopki-community`.
Community remains the OpenSSL-backed public upstream. Enterprise adds private
overlay code and must not become a separate product fork unless a change is
explicitly Enterprise-only.

## Community Remote Setup

Use a remote named `community`:

```powershell
git remote add community <community-url-or-local-path>
git fetch community
```

For local sibling repos:

```powershell
git remote add community ..\AnoPKI-Community
git fetch community
```

The helper script can print the same safe preview and optionally configure or
fetch the remote:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-community-upstream.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-community-upstream.ps1 -ConfigureRemote -CommunityUrl ..\AnoPKI-Community
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-community-upstream.ps1 -Fetch
```

The helper does not run publish or integration commands. Review and integrate
manually.

## Sync Strategy

Use a normal Git remote and reviewed merge while Community and Enterprise share
repository layout and history:

```powershell
git fetch community
git log --oneline HEAD..community/main
git diff --stat HEAD...community/main
git diff --name-status HEAD...community/main
git merge --no-ff community/main
```

Do not use subtree or submodule layout for the current repository shape. Those
add packaging and path indirection without solving the current problem. Revisit
subtree or submodule only if Enterprise must consume Community as a vendored
component with intentionally separate history.

If Git reports unrelated histories, stop. Do not force a history join without a
separate migration plan.

## Conflict Handling

For shared files, prefer the Community version unless Enterprise has a documented
overlay reason. Shared behavior includes lifecycle state transitions, public API,
OpenAPI, core CLI JSON contract, ACME behavior, public docs, and OpenSSL-backed
core behavior.

For Enterprise-only files, keep the private side in these boundaries:

- `enterprise/`
- `docs/enterprise/`
- `include/anopki/enterprise/`
- `service/internal/enterprise/`
- `src/enterprise/`
- `src/core/crypto/anocrypto_backend.*`
- `ENTERPRISE-LICENSE-NOTICE.md`

If a conflict mixes shared and Enterprise-only logic, keep shared behavior
compatible with Community and move private behavior behind an Enterprise overlay
boundary. Do not remove existing behavior unless a test proves it obsolete or
broken.

## Required Post-Merge Checks

Run the Community baseline in the Community checkout before trusting the source
revision:

```powershell
cd ..\AnoPKI-Community
python scripts\validate-community-boundary.py
python scripts\validate-docs.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-local.ps1 -List
```

Run Enterprise boundary and docs checks after the merge:

```powershell
cd ..\AnoPKI-Enterprise
python scripts\validate-enterprise-boundary.py
python scripts\validate-docs.py
python scripts\test_sync_community_upstream.py
```

Run Enterprise-specific tests when Enterprise overlay files changed:

```powershell
cmake -S . -B build
cmake --build build --config Debug
ctest --test-dir build -C Debug --output-on-failure
cd service
go test ./...
```

## Checklist

- Run Community baseline checks in `anopki-community`.
- Fetch and review `community/main` before merging.
- Resolve shared-file conflicts toward Community unless an Enterprise overlay
  reason is documented.
- Run Enterprise boundary checks.
- Run Enterprise-specific tests.
- Confirm no private secrets or license files leak to Community.
- Confirm no Enterprise-only paths, commercial license notices, AnoCrypto
  implementation, SSO/RBAC, HSM/KMS providers, UI, deployment adapters, or
  proprietary docs are pushed back to Community.

## Never Push Back To Community

Never push Enterprise-only material back to Community:

- `ENTERPRISE-LICENSE-NOTICE.md`
- `enterprise/`
- `docs/enterprise/`
- `include/anopki/enterprise/`
- `service/internal/enterprise/`
- `src/enterprise/`
- `src/core/crypto/anocrypto_backend.*`
- commercial terms, customer docs, private release evidence, secrets, keys,
  AnoCrypto implementation, SSO/RBAC, HSM/KMS/KMS provider code, UI, deployment
  adapters, and proprietary packaging.

Community may document AnoCrypto as an intended direction, but it must stay
OpenSSL-backed until code, parity fixtures, tests, release evidence, and review
prove otherwise.
