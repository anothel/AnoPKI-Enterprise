# Phase 4 Continuation And Hosted Evidence

Full Phase 4 HA qualification remains incomplete. The implemented slice proves
required-watchdog bootstrap refusal, not successful automatic failover or
split-brain prevention. Preserve the original
[design](postgres-ha-qualification.md),
[implementation plan](postgres-ha-implementation-plan.md), and
[fixture instructions](../../tests/ha/README.md).

## Fresh Recovery — 2026-11-17

PR #5 has also merged at `c063b7b72da69130e2d248c0ba045b203e88762d`. Continue
on `codex/phase4-ha-implementation` in a new draft PR, superseding the branch
instructions below. The [fresh recovery decision](phase4-recovery.md) records
current capabilities, independent artifact inspection and unresolved fencing
and durability prerequisites. Earlier unobserved local completion remains unknown.

## Repository State

GitHub reports [PR #4](https://github.com/anothel/AnoPKI-Enterprise/pull/4)
merged at `dbd1a1e6f5c7c13ee39a50511470b113a8a99ff9`. The task agent did not
perform that merge. A connector comparison confirmed main identical to that
commit when this continuation was prepared. Do not reuse the old PR's draft
status or infer that its merge qualifies full HA.

Continue on `codex/phase4-ha-qualification-continuation` in a new draft PR.
No merge, tag, release, publication or deployment is authorized.

## Observed Hosted Evidence

| Identity | Value |
| --- | --- |
| Source head | `96f111baaf61faada929d95753923fa7f670a887` |
| Watchdog job checkout / tested PR integration commit | `569161f3c57d8981f71c35aeaf6079904b46078c` |
| Existing CI | [43868795693](https://github.com/anothel/AnoPKI-Enterprise/actions/runs/43868795693), 27/27 jobs successful |
| Watchdog prerequisite CI | [43868795709](https://github.com/anothel/AnoPKI-Enterprise/actions/runs/43868795709), successful |
| Watchdog job | `133304154107`, 11 regressions and live refusal step successful |
| Watchdog artifact | `14227050469`, `anopki-postgres-ha-watchdog-prerequisite`, 1018 bytes |
| GitHub-reported artifact ZIP SHA-256 | `933d22dd60a5de4f7d2ee7d11d7ae985230d0acba7022d80fbc08e9960795839` |

The watchdog checkout log names the integration commit above and says:
`Watchdog prerequisite: passed; HA remains unqualified`. The upload log and
artifact metadata agree on the ZIP digest. This is GitHub-reported integrity,
not an independently recomputed downloaded ZIP hash. The artifact was obtained
through the connector, but its contents could not be independently unpacked in
the failed execution environment. Do not invent its observation duration or
substitute the later main merge or documentation commit into its source fields.

The existing CI job listing confirms successful application-node failover,
primary failover, PostgreSQL integration/recovery, Go analysis and baseline,
secret, package and expected-blocked release gates. Relevant artifacts from that
run retain the same source head in GitHub metadata:

| Artifact | ID | GitHub-reported ZIP SHA-256 |
| --- | --- | --- |
| Application-node failover | `14225809046` | `82e1ff9056ad13ab99b3015dcd868235212a255507498fe4b75f6dda0d352fb9` |
| Primary failover | `14227050765` | `86f36bffb899ee5ad1ad54fbb1a13ffb41f495702a5a7f92b65d1e3865264ed3` |
| PostgreSQL recovery | `14227495009` | `86a6916c437e88cf723ef212f82af72dc82e85fb1ac7d6df545369c602d7b3e1` |
| Go analysis | `14225784546` | `c9ac05f189a373ac6d8ca8c89bc4dbf1b8834305d2b0207a3d7e4e7dfed26894` |

These artifacts were identified from metadata, not independently inspected.
Successful existing jobs retain their existing scope; they do not establish
positive fencing, partition safety, real signer recovery or production readiness.
No post-merge main-push CI result is asserted here.

## Implementation And Review Findings Already Addressed

The negative fixture uses pinned images and hash-locked Python inputs, an
internal Docker bridge, per-run mutually authenticated etcd TLS, SCRAM and
verified PostgreSQL control TLS, a read-only root, private tmpfs files,
unprivileged processes, Docker init and ownership-scoped cleanup. It accepts no
external database DSN and mounts no host devices or Docker socket into guests.
It always records `ha_qualified: false`.

Independent architecture review corrected the watchdog renewal/keepalive timing
assumption to require half-TTL behavior, explicit functioning-device assumptions
and old-primary quarantine. Independent code review reproduced false passed
evidence after interruption and malformed empty etcd responses interpreted as
absence of leadership; regressions now reject both. Live diagnosis corrected
read-only-root configuration transfer, inherited proxy routing, the password-file
location and child-process reaping. All 58 Python files in the pinned Patroni
4.1.5 wheel matched upstream commit
`235fdb3990513c7852da8dc51e9cb92b6d0e4907` in the earlier workspace comparison.

The bootstrap watchdog check occurs after initial PostgreSQL startup. The
isolated fixture can observe a transient writable bootstrap process; it does
not prove that every startup path is permanently non-writable before fencing
is armed. Application clients are not attached to that bootstrap network.

## Next Implementation Decision

The initial Patroni design still requires an independently timed watchdog or
reliable external fence. Installing QEMU alone is insufficient: the reviewed
QEMU i6300esb device uses a virtual clock that stops when the VM stops. This does
not meet the design's pause/resume requirement.

A source-reviewed alternative is a bounded Docker lab using established
Pacemaker/Corosync, PAF (`pgsqlms`) and upstream `fence_docker`. It can be
evaluated without writing a new consensus or leader-election algorithm. It
must explicitly trust the host kernel and Docker daemon and exclude their
failure or compromise from its qualified fault model.

Before implementing that alternative, amend the architecture and plan to specify:

1. Three cluster/database nodes, majority quorum, fencing and startup fencing
   enabled, no-quorum stop behavior, and confirmed power-off before replacement
   primary promotion.
2. An authenticated out-of-band fencing boundary restricted to generated run
   resources. Never expose the shared host Docker socket to cluster guests,
   reuse production credentials, or allow arbitrary Docker operations.
3. Immutable upstream fencing/resource-agent inputs and Docker API compatibility.
   A successful API request is not confirmation that the old primary stopped.
4. Continuous `remote_apply` and a synchronous follower requirement after
   promotion. PAF's highest-available-LSN selection and `maxlag` alone do not
   prove preservation of all acknowledged commits.
5. Safe old-data quarantine, rewind/reclone and controlled rejoin; automatic
   restart of a fenced former primary must not bypass those checks.
6. Fail-closed behavior when fencing, quorum, candidate durability or complete
   observation cannot be established. A failed scenario must not be changed
   into a skip or a success by relaxing the configuration.

Do not replace Patroni with a quick custom hook that kills peers. Source review
identified unresolved old-owner identity, stale request, restart and synchronous
follower-recovery hazards in that shortcut. The Docker alternative is not yet
implemented or qualified; its integration needs independent review.

## Remaining Qualification

Implement and measure the original acceptance matrix: automatic detection and
election; symmetric/asymmetric partitions; quorum loss; stalled controllers;
fencing failure; no overlapping writable primaries; old-primary rejoin; retained
client reconnection and stale transaction rejection; issuance, CRL, outbox,
audit and lease consistency; acknowledged/uncertain outcome accounting; and
observed RTO/RPO without SLA claims. Preserve all Phase 2/3 verification and
security gates. Obtain independent review of the complete implementation and
exact-source evidence before describing Phase 4 as qualified.

## Execution Handoff

The former cloud workspace is failed. Its provider reported
`github_connector_not_configured` and instructed reconnecting the GitHub account
for that workspace and starting a new cloud task. The GitHub connector still
works for repository inspection, but that does not restore the executor.
A separate local Phase 3 rerun was also denied by automatic approval review
because of a usage limit; it was not executed and is not a new passing result.

The last exact-remote-head local watchdog run had started when execution became
unavailable. Its final result and cleanup were not observed. Do not claim either;
when recovering the disposable host, inspect only resources labeled
`com.anopki.phase4.prerequisite` and use the runner's ownership-scoped cleanup.
Earlier diagnostic and local-tree runs are not replacements for hosted evidence.

On a fresh task, check out latest main and this continuation branch, inspect
any newer user changes, reread project status and the design, independently
download/hash/unpack the retained artifacts, then continue the architecture and
implementation work. Do not silently change the frozen Community baseline or
the missing historical AnoCrypto-C SDK pin
`98f544a574f70b387c300f171243b4e87174937a`.
