# Phase 4 PostgreSQL HA Qualification Design

Status: architecture proposal and implementation contract; **not implemented or
qualified**. Recorded 2026-11-16. Base main was fetched and verified as
`6827dbdeca9b6f1136e03c570abdf3d5809a0eb3` (merged Phase 3).
Branch: `codex/phase4-ha-split-brain-qualification`. No related issue confirmed.
This design was written before any Phase 4 runtime or harness changes.

## Existing Evidence And Boundaries

Read together with [project status](../PROJECT_STATUS.md),
[Phase 2](postgres-failover-qualification.md), and
[Phase 3](postgres-primary-qualification.md).

* Phase 2 exercises application leases, stale compare-and-swap rejection,
  issuance, CRL and outbox on one database. Its clocks and signers are fixtures.
* Phase 3 uses two disposable Docker containers, physical replication and
  `remote_apply`. The test kills and verifies the primary stopped, manually
  promotes the standby, then clears synchronous standby requirements. That last
  availability step must not be copied into Phase 4.
* Phase 3's retained artifact qualifies implementation
  `5a78265e39cf4e70aeb382552db88973e58eaa9d`, tree
  `1fcbb949bfbc25d3abf39afe354f68c6d2768c73`. Its four observations include an
  intentional asynchronous loss case. None measures detection or election.
  Later documentation or merge commits must not replace these identities.
* `enterprise_postgres_topology_test.go` supplies owned-resource cleanup,
  retained pgx pools, application row digests and audit verification.
  `enterprise_postgres_primary_test.go` supplies application recovery assertions.
  Reuse assertions deliberately, not its manual promotion policy or trust HBA.
* `verify-postgres-primary.py` requires clean exact source, strips inherited
  PostgreSQL and Go overrides, requires every test result and typed metric,
  omits raw diagnostics, and kills subprocess groups before label-scoped cleanup.
  These protections remain required. New evidence must cover all new inputs.
* Existing CI independently runs application failover, primary failover,
  backup/restore, integration, security analysis and frozen-baseline gates.
  Keep these jobs and their failure semantics unchanged.

The missing SDK object `98f544a574f70b387c300f171243b4e87174937a` remains the
separate [historical provenance blocker](sdk-pin-recovery.md). Community remains
frozen at `49142ff50f5b37ba142d18cf61b60d8b287bdb49`, with consumed baseline
`ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc`. No repinning is part of this work.

## Approaches And Recommendation

1. **Patroni + three-member etcd + required watchdog:** recommended engineering
   choice. Patroni owns PostgreSQL roles, synchronous membership and DCS lease
   handling; etcd owns consensus. A watchdog outside the guest process failure
   domain fences a primary whose Patroni cannot demote PostgreSQL. This matches
   the current PostgreSQL/pgx stack. Watchdog qualification is mandatory.
2. **Pacemaker/Corosync + PostgreSQL resource agent + STONITH:** established and
   viable, especially with an existing supported power-fence provider. It adds
   a second operational stack and resource-agent qualification not present here.
   Reconsider if the available disposable infrastructure supports reliable
   external power fencing but cannot supply a suitable Patroni watchdog.
3. **Docker-only Patroni with process kills or softdog:** useful diagnostic
   simulation, rejected as the final fencing qualification. Containers share a
   kernel; killing Patroni, losing its network or pausing its process does not
   prove an independently timed fence of PostgreSQL. A proxy is not a fence.

No custom consensus, election, leader lease or promotion controller is allowed.
The test orchestrator injects faults and observes results; it must not promote a
candidate or restore availability in a scenario claiming automatic failover.

## Proposed Disposable Architecture

Use three isolated disposable database VMs, each with PostgreSQL 16, Patroni and
one etcd member. Three database copies allow one node to fail while the survivor
continues with a synchronous standby. Co-location is a bounded lab economy,
not a production failure-domain recommendation. Use a separate observer/client
process and an out-of-band hypervisor control channel. All VMs, virtual switches,
disks and credentials are generated for one run; never accept existing resource
IDs, external database DSNs or a production hypervisor inventory.

Pin the exact PostgreSQL, Patroni, etcd, guest OS and hypervisor artifacts and
transitive install inputs with digests before building the executable harness.
Versions are not selected or claimed tested by this design. Retain upstream
source revisions and the installed configuration alongside the run evidence.
Consult the selected-version upstream contracts:
[Patroni replication](https://patroni.readthedocs.io/en/latest/replication_modes.html),
[Patroni watchdog](https://patroni.readthedocs.io/en/latest/watchdog.html), and
[etcd failure modes](https://etcd.io/docs/v3.5/op-guide/failures/).
These moving documentation links are references, not immutable source evidence.

Configure Patroni `synchronous_mode: true`, `synchronous_mode_strict: true`,
`synchronous_node_count: 1`, PostgreSQL `synchronous_commit: remote_apply`,
`fsync: on`, `full_page_writes: on`, and `watchdog.mode: required`. Disable DCS
failsafe mode for this bounded model. Keep synchronous replication required
after promotion; no availability fallback to asynchronous commits. Do not force
promotion of a node Patroni does not consider safe. A recovered primary may
remain unable to commit until a synchronous follower is ready.

Initially use `ttl: 30`, `loop_wait: 5`, `retry_timeout: 5` seconds and watchdog
`safety_margin: -1` (Patroni half-TTL mode), subject to validation against the selected version.
Check Patroni's timeout constraints and the actual programmed watchdog deadline,
including device rounding. Inject scheduling pauses specifically between DCS
renewal and watchdog keepalive: a generic SIGSTOP test can miss this window.
Do not use a watchdog interval greater than half the TTL; the initial design's
20-second interval for a 30-second TTL was rejected in independent review.
A candidate must not become writable before the former leader is fenced or has
verifiably demoted under the upstream protocol. An HTTP health check alone is
not this evidence. Collect the DCS lease transitions and watchdog reset events.

Each VM needs a dedicated watchdog capable of hard reset independently of guest
Patroni scheduling (for example a hypervisor-emulated device with a documented
host timer). Qualify the particular device, driver, reset action, suspend/resume
behavior and timing margin before trusting it. `softdog`, a shared host device,
`watchdog.mode: automatic`, or mere `/dev/watchdog` presence are insufficient.
Do not mount the host watchdog into multiple containers. PostgreSQL must never
start directly on boot; Patroni and its required watchdog gate all role changes.

Use per-run SCRAM database credentials, verified TLS for client and replication
connections, mutually authenticated etcd peer/client TLS, and authenticated
Patroni administration. Generate a temporary CA; never export keys or credential
files as evidence. Restrict client access to loopback or an isolated observer
network. No trust HBA, host networking, public service listener, shared data
volume, production secret or deployment template is introduced. Test-only
credentials do not become deployment defaults.

## Failure Assumptions And Safety Limits

* etcd's majority protocol and Patroni's selected-version safety behavior are
  trusted dependencies, not reimplemented. Two of three etcd members are needed
  to acquire/renew leadership. A minority must not elect a writable primary.
* A correctly functioning independent watchdog is a safety assumption. Detectable
  arm/keepalive failures must prevent leadership or cause safe demotion. Silent
  watchdog hardware/hypervisor failure combined with a stalled controller is an
  excluded compound fault unless an independently reliable external fence is
  added. Quorum cannot solve it. If that assumption cannot be justified for the
  chosen backend, do not enable automatic failover or claim qualification.
* Nodes are crash/omission faulty, not Byzantine. Guest root, a compromised
  hypervisor, forged watchdog evidence or an operator bypassing Patroni is out
  of scope. The disposable host and management channel are trusted.
* Watchdog expiration must halt writes before DCS leadership can transfer.
  Paused controllers, stalled guests and network partitions are distinct faults.
  Test host pause/resume separately: if watchdog timing freezes while other
  nodes proceed, this fencing backend is unsuitable and qualification fails.
* The observer must retain direct independent paths to each database during
  partitions; an unreachable old primary is unknown, not proven fenced.
  Every observation gap is reported and prevents a strong non-overlap verdict.
* A successful remote-apply commit requires one eligible standby, not survival
  of arbitrary simultaneous disk loss. Loss of both acknowledged copies,
  correlated hypervisor/storage failure, WAL corruption and power-loss storage
  semantics remain unqualified. Finite tests cannot prove all schedules.
* No SLA, production readiness, exactly-once delivery, real signer recovery,
  SDK parity or cryptographic certification follows. An ambiguous client commit
  can have persisted; do not count it as an acknowledged loss or blindly retry
  an external side effect.

## Required Scenario Matrix

Each scenario starts with fresh resources and a clean committed-source identity.
The orchestrator enforces a hard deadline and cleans only owned resources.

| Fault | Required observation and acceptance |
| --- | --- |
| Primary VM power loss | Automatic detection/election; retained pgx pool reconnects; synchronous follower ready before successful recovered write; all acknowledged markers preserved. |
| Primary loses only DCS access, clients still reach it | Demotion or watchdog reset precedes new writable role; old held transaction cannot commit after takeover; minority never wins. |
| Primary loses replication but retains DCS | Commits block/fail while no safe synchronous follower exists; no durability downgrade. An alternate eligible follower may restore writes only through Patroni's safe membership transition. |
| Asymmetric DCS/replication partition | Exercise both directions and mixed fault paths; inspect actual rules and packet counters; no two writable roles and no acknowledged divergence. |
| Two etcd members lost | No new election; former leader demotes/fences on expiry; no successful writes beyond the safe lease interval. Transient writes before expiry are not mislabeled a failure. |
| Patroni SIGSTOP while PostgreSQL remains reachable | Independent watchdog reset occurs before another node becomes writable; killing the test controller must not be what fences PostgreSQL. |
| Watchdog missing/unusable before promotion | Patroni cannot become primary. No automatic fallback, no success verdict from a skipped test. |
| Watchdog failure after arming / paused guest | Detectable failure must block leadership or cause safe demotion. Test renewal/keepalive boundary stalls and host pause/resume. Silent fence failure plus a stalled controller is outside the watchdog-only model; it requires independent external fencing for coverage. |
| Stale established client and uncommitted transaction | Stale connection and transaction fail after takeover; direct old-primary probes reject writes; a retained multi-host pool recovers and still reports remote_apply. |
| Old-primary restart and rejoin | After reset, quarantine the rebooted node from client writes and candidacy until Patroni-controlled rewind or fresh clone and timeline reconciliation finish. No direct PostgreSQL restart; it rejoins read-only and catches up before becoming synchronous. Failed rewind stays quarantined or is rebuilt. |
| Second node loss after failover | Lose the remaining synchronous follower; commits block/fail. Never clear synchronous_standby_names to make the test pass. |
| Heal quorum and networks | Resume only through upstream safe role/membership handling, verify one primary and complete state comparison; no manual force-promotion. |

Repeated direct probes include SQL role state and attempted writes on *every*
node, including a disconnected former leader via the observer network. Record
both writable-role overlap and acknowledged-commit overlap; a blocked synchronous
commit does not prove the old node is read-only. Probe sampling is supporting
evidence, not proof of continuous exclusion. Correlate role transitions, fencing
and monotonic observer times; missing data or an unbounded timing uncertainty is
inconclusive and fails qualification.

Run issuance, CRL and outbox recovery using real lifecycle/store code and fixture
signers across the successful fault scenarios. Preserve active-lease rejection,
expired takeover, stale completion rejection both during and after the new
lease, issuance retry without resigning, one certificate-issued audit event,
contiguous CRL numbers, atomic publication/claim removal, outbox attempt rollback,
logical table digests and audit-chain verification. Retain Phase 2/3 verbatim.
Fixture-clock lease tests stay labeled separately; include at least one actual
wall-clock lease-expiry observation and report its duration separately from DB
recovery. Do not shorten production lease constants to make CI faster.

## Evidence And CI Acceptance

Maintain an observer-side append-only acknowledgement ledger with unique probe
IDs and payload hashes. After failover/rejoin, compare *all* acknowledged IDs
and application state on the selected timeline; separately classify uncertain
outcomes, rolled-back work and unacknowledged extra rows. Any acknowledged loss
fails the synchronous scenario. Report observed missing count and the observation
window, not a universal zero-RPO guarantee.

Record monotonic fault injection, detection, old-primary demotion/reset,
promotion, synchronous-follower readiness and first recovered application commit.
RTO is the observed interval to that application commit; a connection or leader
health response is not recovery. Preserve censored/time-out observations without
inventing a duration or loss estimate. Host scheduling contributes to results.

The runner must replace old success before preflight, require exact clean HEAD,
record tree and input hashes, sanitize inherited configuration, and fail on
missing/skipped/duplicate/conflicting scenarios, missing fences, non-finite or
misordered metrics, unknown durability, observation gaps, source mutation or
cleanup failure. Report head and tested CI integration commits separately.
Export allowlisted structured events with symbolic node IDs and sanitized logs;
never raw credentials, private keys, DSNs, arbitrary driver output or guest
images. Preserve source attribution on failure as well as success.

Add regressions for every evidence rejection, redaction across chunked/escaped
streams, stale success replacement and subprocess-descendant cleanup. Add a
separate bounded Phase 4 CI job only when its dedicated ephemeral VM runner can
actually exercise the required fence. Capability failure must fail that job,
not skip it or report HA passed. Untrusted PRs must not access persistent or
production infrastructure. Existing Phase 2/3 and security jobs remain required.
An independent security/correctness review must inspect the harness, upstream
configuration, negative fault tests, CI boundary and exact retained evidence
before qualification is declared complete.

## Current Execution Blockers

The current workspace has Docker CLI but sandbox access to its socket fails.
The escalated daemon capability check was not executed: automatic approval
review reported a usage limit (not an unsafe-action determination). No KVM or
watchdog device, QEMU executable, Patroni or etcd executable was found in the
bounded local capability inspection. This is not proof that no suitable external
disposable runner exists; none is confirmed or provisioned here.

Therefore no Phase 4 cluster was created, no failover result was measured, and no
HA safety conclusion is claimed. Docker access alone would not satisfy the VM
watchdog requirement. The next executable step needs a confirmed disposable VM
backend with independent watchdog/reset timing, immutable artifact inputs and
permission to control only its generated resources. The implementation plan is
in [the Phase 4 plan](postgres-ha-implementation-plan.md).

## Independent Design Review

A separate read-only reviewer found a high-priority watchdog renewal/keepalive
timing gap in the initial proposal, plus missing distinctions for silent device
failure and reset/rejoin quarantine. This revision uses half-TTL mode, requires
the boundary-specific pause test, states the functioning-watchdog assumption,
and specifies post-reset quarantine. These are design corrections, not tested
fixes. Independent review of the eventual implementation and evidence remains
required. No runtime security approval or HA qualification follows.

## Design-Stage Local Checks

Documentation validation, secret-baseline scan, seven Phase 3 runner unit tests,
33 Phase 2 runner self-test scenarios, expected-blocked Enterprise release
validation and `git diff --check` passed on this documentation working tree.
The Community baseline validator could not execute: the local object database
lacks `ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc`. This is an input blocker, not a
baseline pass; no pin or validator was changed. No live PostgreSQL test, full Go
suite or hosted CI result is claimed for Phase 4. Documentation-only changes do
not replace historical runtime evidence.
