# Reproducible Internal Packaging

## Scope

The deterministic package is a private `internal-validation` source and license-evidence bundle for the `enterprise-openssl` profile. The implementation baseline is Enterprise commit `6785d18c28f08f027682898faee21319263295ef`, synchronized from Community commit `96297b14d2f681b75861032d9871a41d6e689c78`.

This package is not customer-release authorization. It does not complete the commercial license, hosted qualification, production readiness, or KCMVP validation gates. Customer packages and the `enterprise-anocrypto-c` customer profile remain blocked before archive creation.

## Deterministic inputs

Only exact paths in the tracked profile allow-list are packaged. Each index entry must match `HEAD`; content comes from its Git blob rather than working-tree bytes. File modes come from the Git index: `100644` becomes `0644`, and `100755` becomes `0755`. Symlinks, untracked inputs, duplicate paths, and case-insensitive path collisions are rejected. A clean working tree is required.

`SOURCE_DATE_EPOCH` is the decimal value of `git show -s --format=%ct HEAD`. An environment value is accepted only when it exactly matches that commit timestamp. ZIP timestamps use UTC, round seconds down to the ZIP two-second interval, clamp dates before 1980 to `1980-01-01 00:00:00`, and clamp dates after 2107 to `2107-12-31 23:59:58`.

## ZIP normalization

Entries use canonical UTF-8 byte ordering. No directory entries are emitted. Each member has the normalized timestamp, Unix creator metadata, Git-derived mode, empty comment, empty extra field, and `ZIP_STORED` compression. Python sets the UTF-8 filename flag only when a name contains non-ASCII characters; current canonical paths are ASCII. Stored entries avoid zlib-version output differences.

`tar.gz` is intentionally unsupported. Its gzip and tar writer metadata plus compressor-version behavior would require another independently proven byte-stability contract.

## Manifest and sidecars

`package-manifest.json` is completed before archive creation and embedded as a regular `0644` member. It binds every other member's canonical path, Git-blob SHA-256, size, ownership, license expression, distribution scope, and mode. It does not contain the archive digest.

For `name.zip`, the builder writes `name.zip.sha256` and `name.build.json`. The build sidecar binds the archive digest and size, Enterprise and Community revisions, embedded manifest digest, format, and reproducibility result.

## Build and validate

```powershell
python scripts\build-internal-package.py `
  --profile enterprise-openssl `
  --format zip `
  --out .tmp\enterprise-openssl-internal.zip

python scripts\validate-reproducible-package.py `
  .tmp\enterprise-openssl-internal.zip
```

For same-checkout verification, delete outputs and run the builder at least three times, using different ignored output directories, then compare SHA-256 values and bytes. For fresh-checkout verification, create two independent `git clone --no-local` clones, checkout the same exact commit, confirm clean status and submodule state, run the same commands in each clone, and compare archive bytes, build sidecars, entry lists, CRCs, SHA-256 values, modes, and timestamps.
