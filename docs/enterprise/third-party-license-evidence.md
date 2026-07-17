# Third-Party License Evidence

This is an engineering evidence procedure, not legal advice or a legal opinion.
License classification records conservative text matches from exact dependency
versions. Redistribution and customer release still require owner/legal review.

## Evidence Baseline

`packaging/dependency-license-inventory.json` is the machine-readable source for
`THIRD_PARTY_NOTICES.md` and `THIRD_PARTY_NOTICES.json`. It records every module
in the selected `service/go.mod` graph plus the OpenSSL installation selected by
the Enterprise/OpenSSL CMake profile. `LICENSES/third-party/` contains only the
license, notice, and patent texts found in those exact sources; line endings are
normalized to LF and SHA-256 values are recorded in the inventory.

OpenSSL evidence currently identifies:

- version `3.6.3`
- CMake target `OpenSSL::Crypto`
- vcpkg triplet `x64-windows`
- `lib/libcrypto.lib` and `bin/libcrypto-3-x64.dll`
- installed package evidence `share/openssl/copyright`
- license expression `Apache-2.0`

The repository does not copy OpenSSL libraries or DLLs.

## Go Module Graph

From `service/`, set `GOTOOLCHAIN=local`, then run:

```powershell
go list -m -json all
go mod graph
go mod verify
```

The inventory uses every selected non-main module, not only direct `require`
entries. Exact module content and `go.mod` sums are retained in `service/go.sum`.
The validator compares its offline selected-module snapshot to the inventory,
including version, direct/indirect state, replacement state, and checksums.
Standard-library packages are not third-party modules.

Evidence directory names are deterministic: replace every module-path
character outside `[A-Za-z0-9._-]` with `_`, then append the exact version
unchanged. For example, `github.com/google/uuid@v1.6.0` maps to
`LICENSES/third-party/go/github.com_google_uuid/v1.6.0/`. Validation binds this
path back to module and version provenance.

## Deterministic Notices

Generate and verify notices from tracked inventory and evidence:

```powershell
python scripts\generate-third-party-notices.py
python scripts\generate-third-party-notices.py --check
python scripts\validate-third-party-notices.py
```

Output ordering is dependency type, module/package, version, then license path.
Generated output contains no timestamp, user name, temporary path, absolute
module-cache path, or secret. Validation needs tracked evidence only; collection
may require the exact Go module cache and installed OpenSSL prefix.

Unknown or missing text is never inferred from a package name or description.
It becomes `license_expression=NOASSERTION`, `evidence_status=unresolved`, and
`customer_package_allowed=false`. Any unresolved dependency blocks customer
package generation before archive creation.

`gopkg.in/yaml.v3@v3.0.1` is not treated as a user-selectable dual license. Its
exact license assigns MIT to eight named libyaml-derived files and Apache-2.0
to all remaining project files. The inventory therefore keeps the aggregate
`MIT AND Apache-2.0` result and records both exact component scopes; validation
rejects a missing or altered mapping.

## Packaging Gates

Internal-validation manifests include both notices, the dependency inventory,
and every recorded evidence file. Package manifests bind the dependency
inventory SHA-256. Archive validation rejects missing, extra, stale, unlisted,
or hash-mismatched evidence.

Customer release remains blocked because commercial terms are incomplete,
distribution is unauthorized, redistribution review is incomplete, hosted
qualification is not complete, and customer allow-lists are empty. AnoCrypto-C
remains separate: its owner must supply exact SDK license evidence before its
`NOASSERTION` / `external_license_unresolved` state can change. KCMVP remains
`not_validated`.

## Dependency Update Procedure

1. Confirm a clean `main` worktree and exact HEAD/baseline commits.
2. Run the Go graph commands and download only missing exact selected versions.
3. Copy only discovered candidate license/notice texts, normalize LF, and record
   content, module-zip, and provenance hashes.
4. Configure and build `enterprise-openssl`; record the selected installed
   version, target, triplet, library, runtime, and package-manager evidence.
5. Update `packaging/dependency-license-inventory.json` and exact internal
   allow-lists; never guess an unrecognized license.
6. Regenerate notices, run both third-party tests/validators, then package and
   existing repository validation.
7. After the evidence source commit exists, run
   `python scripts\generate-third-party-notices.py --refresh-commit` and commit
   that metadata refresh. The recorded commit is provenance, avoiding an
   impossible self-referential commit hash.
