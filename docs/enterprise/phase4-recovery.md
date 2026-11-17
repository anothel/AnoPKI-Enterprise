# Phase 4 Fresh Workspace Recovery — 2026-11-17

## Decision And Scope

**Positive automatic failover remains blocked; HA is not qualified.** Resume
from main `c063b7b72da69130e2d248c0ba045b203e88762d` (tree
`505007c68e47237070cdc1c9f8147ae9c62a4310`) on
`codex/phase4-ha-implementation`, with a new draft PR. No related issue is
confirmed. Preserve the [acceptance matrix](postgres-ha-qualification.md), all
Phase 1–3 tests, watchdog prerequisite, security/release gates and frozen pins.

Ruling: finish recovery, architecture review and existing verification before
attempting Task 1 provisioning. Tasks 1–4 of the [implementation plan](postgres-ha-implementation-plan.md)
remain incomplete because neither fencing option has its required safety
boundary established. This costs progress toward live HA qualification; it
avoids promoting a possibly stale replacement without confirmed exclusion.
No new consensus, election, promotion hook or fault simulator is introduced.

## Recovery Findings

The fresh checkout initially named local branch `work` at `dbd1a1e`. Fetching
origin recovered latest main above. GitHub independently confirmed PR #4 merged
at `dbd1a1e6f5c7c13ee39a50511470b113a8a99ff9` and PR #5 merged at
`c063b7b72da69130e2d248c0ba045b203e88762d`; #5 adds continuation/status/evidence
documentation, not HA runtime. Remote heads observed were main,
`codex/phase2-multi-node-qualification` and `codex/resume-anopki-validation`.
Neither former Phase 4 branch was present. Local status was clean; local
`git fsck --no-reflogs --unreachable` reported no recoverable unreachable objects.
These observations do not establish that the failed workspace preserved anything.

The old `github_connector_not_configured` remains a historical provider failure;
this task cannot inspect that failed executor or determine its internal cause.
The new executor and repository connector work. Default shell fetch failed at
the sandbox proxy; elevated fetch succeeded. GitHub CLI reports invalid
`GH_TOKEN`; do not print or copy it. Use the functioning connector for the new
branch/PR if CLI writes are unavailable. None of this recovers the old run's
unobserved final result or cleanup. On this host, a label-scoped container
inventory found no `com.anopki.phase4.prerequisite` containers; this says nothing
about resources on the old host. Do not perform broad Docker cleanup.

## Available Infrastructure And Revised Failure Assumptions

Read-only local inspection found Docker Engine 29.9.2, Linux amd64, API 1.56,
minimum API 1.40, running rootless with slirp4netns. Socket access requires
execution permission outside the default sandbox. No `/dev/kvm`,
`/dev/watchdog`, or `qemu-system-x86_64` executable was found. No external
hypervisor/watchdog service or restricted fencing endpoint is confirmed.
Docker availability is sufficient for the existing negative fixture only.

| Approach | Safety boundary | Current decision |
| --- | --- | --- |
| Patroni + etcd + required independently timed watchdog | Reset timer must continue through guest/controller stalls and pause/resume; fence precedes lease transfer; strict synchronous membership retained. | Retain preferred design; no suitable watchdog/reset backend available here. Do not substitute softdog or QEMU virtual-clock watchdog. |
| Pacemaker/Corosync + PAF + fence_docker | Majority quorum and confirmed off precede promotion; trusted host kernel/daemon and out-of-band control service remain responsive; synchronous candidate eligibility must be established. | Possible bounded lab, not yet a safe implementation selection. Missing restricted fencing service, pinned complete stack and durable candidate-selection proof. |

For the Docker alternative only, explicitly trust the host kernel, daemon and
management boundary. Host compromise, host/kernel/daemon failure, correlated
storage loss and management-service compromise are outside that proposed lab
model. Docker process termination is therefore a **conditional fence inside a
trusted host**, never independent host fencing or production qualification.
Rootless scheduling/network behavior still needs live fault validation.

A future lab must use three voting/database nodes, `stonith-enabled=true`,
`startup-fencing=true`, `stonith-action=off`, `no-quorum-policy=stop`, and at most one promoted
resource. Disable unfencing/automatic restart into old writable data. Require
an off operation and confirmed stopped state on the exact generated container
identity before promotion, not an API success or a reboot/restart cycle. Keep
fenced data quarantined until upstream-controlled rewind/reclone and timeline
checks complete; database boot and client access cannot bypass quarantine.

The management path must be separate from injected data/quorum partitions,
authenticated, and limited to exact immutable container IDs generated for one
run. Never mount a shared Docker socket or provide unrestricted daemon TLS
credentials to cluster guests. Deny foreign IDs, names/aliases, arbitrary API
paths, create/exec/start/restart and requests from an expired run. Serialize
teardown with in-flight fences; do not reuse identities. Missing/ambiguous
status, denied/failed/timed-out fences, stale identity and management partitions
must block promotion. Endpoint design and authorization need independent review
before cluster code receives any management access. This is a fence transport
boundary, not permission to implement an election controller.

## Source Review Of The Alternative

These exact upstream revisions were downloaded for read-only review, not
selected as installation/distribution pins:

* [PAF 9653351](https://github.com/ClusterLabs/PAF/blob/9653351a128f56246d58e8a50faecc1e98d82faa/script/pgsqlms):
  `pgsql_promote` compares timeline/received LSN among available participants;
  `pgsql_notify_pre_promote` builds the participant set. `maxlag` scoring does
  not encode the authoritative synchronous acknowledgment set.
* [fence-agents c6d1b7e](https://github.com/ClusterLabs/fence-agents/blob/c6d1b7e8892661f1204572a8b5ce1241a451fe9b/agents/docker/fence_docker.py):
  off sends container kill, status inspects `State.Running`, and reboot-cycle
  sends restart. The shared `lib/fencing.py.py` asynchronous path polls status;
  the off request alone is not its success criterion. Default API 1.11 is
  incompatible with this daemon's minimum 1.40. An explicit supported version
  and real response/error-path testing are prerequisites, not a runtime result.

Example requiring a safety proof: primary A acknowledges with synchronous B;
A fails; B's PostgreSQL/resource becomes unavailable while Corosync membership
still has quorum with C. Highest available LSN on C is not proof that C has
A's acknowledged commit. Continuous `remote_apply` and `maxlag` cannot alone
bridge that gap. An established configuration must refuse promotion when the
necessary durable candidate cannot be established, including during synchronous
membership transitions. Do not solve this with a bespoke membership ledger or
promotion/election hook. No such configuration has been established or tested
here; this is an integration blocker, not a demonstrated upstream vulnerability.

## Conditions For Resuming Implementation

1. Supply a disposable independently timed watchdog/reset backend, or establish
   the bounded trusted-host fence service above and verify upstream agent/API
   compatibility with pinned stack inputs. No production or persistent runner.
2. Review synchronous candidate eligibility and follower recovery. Keep
   `remote_apply`, fsync, full-page writes and a required synchronous follower
   after promotion; when no safe follower exists, writes block/fail. Do not copy
   Phase 3's removal of synchronous standby requirements.
3. Only then implement the original incremental negative and positive scenarios:
   quorum loss/healing; automatic promotion; symmetric/asymmetric DCS and
   replication partitions; stalled controllers; failed/denied/ambiguous fencing;
   old-primary quarantine, failed rewind and rejoin; second follower loss;
   continuous exclusion and stale held-transaction rejection.
4. Exercise retained client pools, acknowledged/uncertain marker accounting,
   issuance, CRL, outbox, audit and real/fixture lease timing. Observe every node
   directly; missing visibility prevents a safety verdict. Report measured
   application-commit RTO and acknowledged loss only for executed scenarios.
5. Run existing regressions and hosted gates unchanged, obtain independent
   implementation/evidence review, and retain exact head/integration/tree and
   artifact digests before any qualification statement.

No new positive scenarios or RTO/RPO measurements are claimed in this recovery.
No SLA, production readiness, real signer recovery, SDK parity, merge, tag,
publication, release or deployment follows.

## Independently Recovered Historical Artifact

Artifact `14227050469` from watchdog run `43868795709` was downloaded as a
1018-byte ZIP and independently hashed/unpacked in this fresh executor. SHA-256
is `933d22dd60a5de4f7d2ee7d11d7ae985230d0acba7022d80fbc08e9960795839`, matching
the prior GitHub-reported digest. Its sole JSON entry records passed refusal,
all four required observations, owned cleanup true, `ha_qualified: false`, and
1.6354249490000257 seconds of observation (not RTO). Source commit is integration
`569161f3c57d8981f71c35aeaf6079904b46078c`, tree
`8d73bcc0fe380adb829d1d8f3f87342dd29bbbf1`, head `96f111b` as identified by the
historical workflow record. The verbatim allowlisted payload is retained in
[evidence](evidence/postgres-ha-prerequisite-569161f.json). Later merge or
recovery commits must not replace these identities. Other historical artifacts
listed in the continuation have not been independently unpacked by this task.

## Fresh Local Verification

The existing negative fixture was rerun on clean exact main `c063b7b`, before
any documentation edits. Its [verbatim payload](evidence/postgres-ha-prerequisite-c063b7b.json)
records all four observations, successful owned cleanup and 4.459297192999998
seconds of observation. `ha_qualified` remains false. Retained JSON SHA-256 is
`0efb287366c01bfd02fd9396edaf808b57dca523d33767f5aec754d7673555d4`;
the historical extracted JSON SHA-256 is
`57e79206d3bc26d232b0b844807dd3be07c8db8b4ab12749dc9e6d1e22c346b0`.
Image identity is recorded per run, not assumed reproducible across builds.

Local 11 watchdog, 7 Phase 3 runner and 33 Phase 2 runner regressions pass.
Full `go test -race -p 1 ./...` passes using the downloaded pinned Go 1.26.11
toolchain. No external/live PostgreSQL DSN was supplied to that suite; its
optional database tests do not establish fresh live Phase 2/3 results.
Docs and docs-validator tests, secret scan, package and KeyProvider boundary,
frozen Community baseline and expected-blocked release checks pass. The first
baseline attempt lacked the historical object; fetching the exact unchanged
object from AnoPKI-Community resolved that input blocker without repinning.
The system `go` executable is not the Go compiler; use the onboarding Go
launcher and its module-selected toolchain. Hosted CI must separately validate
the new PR head/integration, including existing live database jobs.

Independent read-only source review confirmed the off-versus-reboot distinction,
API compatibility work, restricted management boundary and unresolved durable
candidate proof. That review does not qualify an implementation that does not
yet exist. The old failed executor and its resources remain uninspected.
