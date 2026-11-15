# Exact Historical AnoCrypto-C SDK Recovery

Checked on 2026-11-15 UTC. The SDK pin is unchanged. Repository access works;
the required historical object and original artifacts have not been recovered.

| Required historical identity | Value |
| --- | --- |
| Source commit | `98f544a574f70b387c300f171243b4e87174937a` |
| Original source ZIP SHA-256 | `913979ceea9110de5dbfe9e6702c634071102b00901840763367ca83e15d59c4` |
| Original installed Windows DLL SHA-256 | `7dd56b00f38699509e90a62968ec0ff2c37a2735e4479c0df4a2c60f8b2e26cd` |
| Recorded local consumer evidence | `sdk-manifests/anocrypto-c/p3-11-local-evidence.json` |

## Verified Recovery Checks

- `anothel/AnoCrypto-C` is readable. Its advertised main is
  `b3d5e6551b2bcc38b39602592476146e4b81b9b0`; remote heads/tags advertise only
  main and no tags. A separate no-checkout reference clone was used read-only.
- `git cat-file` cannot find the pinned commit locally. Direct fetch of the
  exact SHA fails with `upload-pack: not our ref`.
- GitHub's commit API returns HTTP 422, `No commit found for SHA`, for the pin.
- The GitHub releases collection is empty, the all-state pull-request collection
  is empty, and the Actions query for that exact `head_sha` returns zero runs.
- Accessible current SDK documentation, including
  `docs/product/PROJECT_SOURCE_REPLACEMENT_PLAN.md` and
  `docs/product/DOWNSTREAM_SOURCE_BASELINES.md`, corroborates the historical
  commit, source-ZIP and installed-DLL identities. Those references do not
  restore the missing object or prove current execution.
- No matching SDK/archive input was identified among available uploaded/shared
  workspace filenames. This is a bounded search, not proof that no owner backup
  exists elsewhere.

Current SDK main, or an earlier restricted-SHA-1 implementation commit, is not
an identity-equivalent substitute. Matching functionality or a version string
cannot establish the pinned artifact's provenance. No SDK checkout was used to
build, repin, or qualify AnoPKI, and Community was not modified.

## Missing Inputs And Acceptance

1. An owner-held Git bundle/repository backup containing the exact commit and
   its reachable objects, or the original source ZIP matching the recorded
   `913979…` SHA-256 with its source/provenance record. A source ZIP alone does
   not reconstruct the exact Git commit unless Git metadata is also available.
2. The original installed SDK archive/build manifest, headers and library from
   the recorded platform, with toolchain/build/package provenance. Reproducing
   the historical Windows record additionally requires the original DLL matching
   `7dd56b…`; other platforms are expected to have different artifact hashes.
3. Trusted owner/CI provenance binding SDK source, platform/toolchain and install
   artifacts to the Enterprise consumer commit, followed by a newly recorded
   hosted run of the adapter, eight-operation parity, no-fallback and purity
   checks on the exact recovered input.

Inspect recovered inputs in scratch, verify hashes and object identity before
execution, and retain historical records as historical. Any proposed baseline
change is a separate explicit decision. SDK hosted parity, production provider,
commercial distribution and KCMVP gates remain intact and unresolved.
