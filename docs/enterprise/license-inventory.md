# License Inventory Baseline

This inventory is an engineering record, not legal advice and not a final
commercial license. Legal review and owner approval remain separate gates.

The authoritative machine-readable record is
`packaging/license-inventory.json`. It is tied to Enterprise source commit
`68b379e7684c9d8b44c53728949774088352a9d9` and synchronized Community baseline
`ae3ddee72dd05f274b9bbae1b514cdc4c4de03f5`.

## Recorded Components

| Component | Recorded license state | Customer package state |
| --- | --- | --- |
| Synchronized Community files | MPL-2.0; retain the MPL text and mixed-license/source notice | Component may be distributable only after package-level gates and legal review |
| Enterprise commercial overlay | `LicenseRef-AnoPKI-Enterprise` internal placeholder | Blocked; final terms are incomplete |
| OpenSSL runtime/dependency | OpenSSL 3.6.3 from vcpkg `x64-windows`; Apache-2.0 text recorded | Evidence verified; blocked pending redistribution/legal review and package-level gates |
| Go module dependencies | All 34 selected modules recorded from the exact module graph | Evidence verified; blocked pending redistribution/legal review and package-level gates |
| AnoCrypto-C external SDK | Separate external license unresolved | Blocked; SDK material is not copied and trusted execution is not run |
| Generated metadata/evidence | Enterprise private evidence | Internal only |
| Test-only fixtures | MPL-2.0 test material | Excluded from customer packages, including the software token fixture |
| Build-only tools | Mixed build inputs; not release payload | Excluded |
| Customer documentation | Enterprise terms; legal review required | Blocked |

The root `LICENSE` and `ENTERPRISE-LICENSE-NOTICE.md` route mixed-license
material. `LICENSES/MPL-2.0.txt` is the recorded Community license text.
`LICENSES/LicenseRef-AnoPKI-Enterprise.txt` is still a non-release-ready
placeholder. Exact OpenSSL and Go dependency evidence is recorded in
`packaging/dependency-license-inventory.json`, `THIRD_PARTY_NOTICES.*`, and
`LICENSES/third-party/`. The repository does not invent missing AnoCrypto-C
terms.

## Current Release State

- `commercial_license_status`: `incomplete`
- `customer_distribution_authorized`: `false`
- dependency evidence unresolved count: `0`
- dependency redistribution review: required
- hosted qualification: `REMOTE_DEFERRED/BLOCKED_EXTERNAL`
- trusted AnoCrypto-C SDK execution: `not_run` / `REMOTE_UNVERIFIED`
- AnoCrypto-C parity: `unsupported_pending`
- production readiness: `false`
- KCMVP: `not_validated`
- automatic fallback: disabled and unused

The GitHub Actions capacity blocker does not represent a code failure, a test
pass, or a waiver. No customer release may be generated until this inventory,
all required notices, exact package contents, hosted qualification, and
commercial authorization are independently complete.
