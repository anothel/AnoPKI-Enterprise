# Enterprise License Notice

AnoPKI Enterprise is a mixed-license private repository. The root `LICENSE`
routes files with SPDX identifiers to their license and this notice defines the
path policy for documentation without SPDX headers.

## MPL-2.0 Material

Community-derived source and documentation remain MPL-2.0. Source files that
require headers use `SPDX-License-Identifier: MPL-2.0`. The authoritative text
is [LICENSES/MPL-2.0.txt](LICENSES/MPL-2.0.txt).

Do not remove MPL-2.0 notices or relicense Community-derived files as
proprietary. Distribution of modified MPL-covered files requires review of the
applicable MPL-2.0 source obligations.

## Enterprise-Only Material

Enterprise-only implementation paths use
`SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise`. The current terms are
in
[LICENSES/LicenseRef-AnoPKI-Enterprise.txt](LICENSES/LicenseRef-AnoPKI-Enterprise.txt).

Known Enterprise-only paths include:

- `enterprise/`
- `docs/enterprise/`
- `include/anopki/enterprise/`
- `service/internal/enterprise/`
- `src/enterprise/`
- `src/core/crypto/anocrypto_backend.*`

The Enterprise terms are an internal placeholder, not an approved customer
license. Customer distribution and production distribution remain prohibited
until owner/legal review replaces the placeholder with an approved commercial
agreement.

## Third-Party Material

Exact OpenSSL and Go module license evidence is stored under
[`LICENSES/third-party/`](LICENSES/third-party/). The selected dependency graph,
versions, provenance, evidence hashes, and review state are recorded in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and
[`packaging/dependency-license-inventory.json`](packaging/dependency-license-inventory.json).

Recorded evidence does not itself authorize customer distribution. The
commercial license, dependency redistribution review, package allow-list,
hosted qualification, and release authorization gates remain fail-closed.
