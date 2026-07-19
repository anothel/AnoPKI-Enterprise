# Commercial Packaging Boundary

This document records an engineering control, not legal advice or final
commercial terms. Owner and legal review remain separate release approvals.

## Current Decision

AnoPKI Enterprise customer distribution is not authorized. The final
commercial license, third-party notices, hosted qualification, and customer
package allow-lists are incomplete. Local qualification does not waive the
hosted GitHub Actions billing/spending blocker.

The repository defines two package classes:

| Class | Current authorization | Purpose |
| --- | --- | --- |
| `internal-validation` | Authorized for private use | Reproducible ZIP/TGZ inputs for engineering tests and evidence review. It is never customer distribution. |
| `customer-release` | Blocked | Customer delivery only after legal, license, notice, hosted qualification, commercial authorization, and archive/member gates pass. |

`packaging/package-policy.json` is the machine-readable authority.
Each product profile and package class binds to one exact path allow-list under
`packaging/manifests/`. Customer allow-lists are deliberately empty while
distribution is unauthorized.

## Ownership And License Boundary

Synchronized Community files retain MPL-2.0. They are not relabeled as an
Enterprise commercial overlay, and any distribution must retain the applicable
license and source/notice obligations. Enterprise-only paths use
`LicenseRef-AnoPKI-Enterprise`; its current file is an internal placeholder and
does not authorize customer or production distribution.

OpenSSL and Go module dependencies remain separate third-party inventory items.
Their resolved release notices must be supplied before customer packaging.
AnoCrypto-C is an external SDK with a separate license. Its source and headers
must not be copied into this repository or a package.

## Profile Separation

`enterprise-openssl` selects only the Community OpenSSL adapter. Automatic
adapter/provider/profile fallback remains disabled and OpenSSL KCMVP status is
`not_applicable`.

`enterprise-anocrypto-c` selects only the external SDK adapter. Internal
integration validation may include the adapter and evidence tooling, but no SDK
source, header, credential, or binary may enter the package without exact SDK
evidence and resolved external license terms. Parity is `unsupported_pending`,
production readiness is false, and KCMVP is `not_validated`.

## File And Archive Controls

The generator accepts only normalized, exact allow-listed paths that are
tracked by Git or explicitly approved as generated artifacts. It records a
SHA-256 digest and license ownership for every member in deterministic path
order. The boundary validator rejects:

- unallow-listed, missing, or digest-mismatched files;
- simultaneous OpenSSL and AnoCrypto-C adapters;
- fallback claims;
- build output, caches, credentials, secrets, private keys, and unsafe paths;
- copied external AnoCrypto-C SDK source/header material or an unevidenced binary;
- archive members that do not exactly match `package-manifest.json`;
- customer relabeling of an internal package;
- unsupported production, hosted-success, or KCMVP claims.

Private customer operational evidence and the test-only software token are not
eligible for a customer package. The empty customer allow-lists keep that rule
fail-closed until a reviewed file-by-file distribution plan replaces them.

## Release Integration

The Enterprise release guard reads the inventory and policy before packaging.
The release-artifact validator requires customer packaging metadata to be
complete and authorized. Today those checks must block. A successful internal
manifest generation is evidence only for the internal validation boundary; it
is not customer authorization or a hosted qualification result.
