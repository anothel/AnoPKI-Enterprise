# Phase 4 PostgreSQL HA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Qualify automatic PostgreSQL failover and split-brain prevention on owned disposable infrastructure, preserving synchronous durability.

**Architecture:** Patroni manages three PostgreSQL nodes using a three-member etcd quorum. Each database VM has an independently timed, required watchdog; the observer injects faults without implementing promotion or election.

**Tech Stack:** PostgreSQL 16, Patroni, etcd, disposable Linux VMs, Go/pgx lifecycle tests, Python evidence runner. Exact new infrastructure artifact versions/digests must be selected and reviewed in Task 1 before executable provisioning is implemented.

**Spec:** [Phase 4 design](postgres-ha-qualification.md).

## Global Constraints

- Base: `6827dbdeca9b6f1136e03c570abdf3d5809a0eb3`; branch `codex/phase4-ha-split-brain-qualification`.
- Keep Phase 2/3 tests, all security/release gates, Community and AnoCrypto-C pins unchanged.
- `synchronous_mode: true`, `synchronous_mode_strict: true`, `synchronous_node_count: 1`, `synchronous_commit: remote_apply`; no asynchronous availability fallback.
- Required independent watchdog; no custom election, consensus or promotion controller.
- Disposable generated resources only; no deployment, merge, release, tag or publication.
- Fixture signing only; no production readiness, SLA, exactly-once or real signer recovery claims.
- Implementation is blocked until the VM/fencing backend is available. This plan is not executable qualification evidence.

## Review Focus

- Hypervisor pause/resume freezes a virtual watchdog while another node promotes: Task 1 rejects that fencing backend.
- Old primary unreachable to the observer but still reachable to clients: Task 2 reports inconclusive rather than fenced.
- Cancellation produces an unknown commit outcome: Task 3 distinguishes acknowledged, uncertain and rolled-back operations.
- A stalled Patroni leaves PostgreSQL writing: Task 2 requires independent reset timing, not test-controller termination.
- Failed reruns retain stale green artifacts or leak secrets: Task 4 replaces artifacts before preflight and exports only validated fields.

## Implemented Preliminary Slice

A separate required-watchdog bootstrap-refusal fixture now exists in
`tests/ha/`, `scripts/verify-postgres-ha-prerequisites.py`, its regression script
and `.github/workflows/postgres-ha-prerequisites.yml`. It exercises the actual
Patroni refusal against three etcd peers and never marks HA qualified. This
resolves the executable negative prerequisite only; the tasks below remain
open. Docker and historical Community-object access now work. Source review
identified Pacemaker/Corosync/PAF with external Docker fencing as an alternative
for further evaluation; no positive fencing backend is yet qualified.

## Task 1: Establish And Pin A Suitable Disposable Backend

Files to create: `tests/ha/README.md`, `tests/ha/artifacts.json`,
`tests/ha/patroni.yml.in`, `tests/ha/guest-init.sh`, `scripts/ha_vm_backend.py`,
`scripts/test_ha_vm_backend.py`.

- [ ] Confirm a disposable hypervisor API/runner and independent watchdog device/reset behavior; record its trust boundary and selected-version upstream references in the design. Stop if only container/process fencing is available.
- [ ] Lock OS, PostgreSQL, Patroni, etcd, hypervisor and transitive dependencies by digest/source revision; reject mutable/unverified inputs before provisioning.
- [ ] Write failing backend tests for external-resource refusal, partial startup cleanup, unique ownership, deadline termination and absence of a usable watchdog.
- [ ] Implement `create_run(run_id: str) -> Run` and `destroy_run(run: Run) -> None` in `ha_vm_backend.py`. `Run` records only generated resource IDs, symbolic node mappings and private credential paths; never accept caller resource IDs or DSNs.
- [ ] Implement isolated per-run networks/disks/credentials and verified TLS/SCRAM initialization; disable direct PostgreSQL boot and require Patroni's watchdog.
- [ ] Run `python scripts/test_ha_vm_backend.py`; all negative cases must pass before real provisioning.
- [ ] Measure watchdog expiration under Patroni SIGSTOP, pauses between DCS renewal and watchdog keepalive, guest scheduling stall and hypervisor pause/resume. Reject the backend if the timer can expire after another node may promote. Record measured uncertainty and actual programmed deadlines.
- [ ] Commit only sanitized source/configuration; no VM images or keys.

## Task 2: Automatic Failover And Partition Scenarios

Files to create: `scripts/ha_scenarios.py`, `scripts/test_ha_scenarios.py`,
`service/internal/lifecycle/enterprise_postgres_ha_topology_test.go`.

Interfaces: use Task 1 `Run`; `run_scenario(run: Run, scenario: str) -> dict`
returns observer-side typed events, never raw subprocess logs. Fixed scenario
names correspond to every row of the design's scenario matrix.

- [ ] Write failing tests that reject missing direct-node visibility, overlapping writable roles, absent reset evidence, disabled strict synchronization and any manual promotion by the orchestrator.
- [ ] Implement fault injection only over generated VM/network identities, with a separate observer and management path. Record verified directional rules and counters.
- [ ] Exercise the complete matrix, including second failure, quorum healing, absent watchdog, stalled Patroni and unsafe post-arming watchdog behavior.
- [ ] Rejoin only via Patroni-controlled rewind or fresh clone; test failed rewind and old-node restart with a different timeline. Never boot old PostgreSQL directly.
- [ ] Observe every node directly, correlate DCS lease/fence/role events, and fail inconclusive observation windows. Sampling alone must not establish continuous non-overlap.
- [ ] Run backend/scenario unit regressions and the real scenarios on the pinned backend. Commit only after both are assessed; preserve failures without a safety claim.

## Task 3: Application Consistency And Client Recovery

File to create: `service/internal/lifecycle/enterprise_postgres_ha_test.go`.

Interfaces: the topology helper provides owned endpoints to retained pgx pools,
`remote_apply` session checks, direct-node observations and fault events. Adapt
Phase 2/3 assertion logic into new tests; do not replace those tests.

- [ ] Add failing tests for stale held-transaction commit after takeover, retained-pool reconnection, and loss of an acknowledged unique probe marker.
- [ ] Add issuance, CRL and outbox scenarios preserving active-lease protection, stale CAS during/after takeover, audit integrity, row digests, contiguous CRL numbering and no redundant fixture signing.
- [ ] Add an observer acknowledgement ledger and classify uncertain cancellation results separately; validate all acknowledged IDs on the recovered timeline and after rejoin.
- [ ] Add one actual lease-expiry run alongside labeled fixture-clock assertions. Keep production durations unchanged and separate database recovery from lease recovery timings.
- [ ] Run new tests under `-race -count=1` on disposable infrastructure. Run unchanged Phase 2/3 qualification and full Go race/vet checks on the same exact source.
- [ ] Commit with measured limitations; never infer signer or SDK recovery.

## Task 4: Evidence Regressions And CI

Files to create: `scripts/verify-postgres-ha.py`,
`scripts/test_verify_postgres_ha.py`, `.github/workflows/postgres-ha.yml`.

Interfaces: `run(out: Path, explicit_commit: str) -> dict` writes a failed or
passed source-bound envelope. Consume typed observer events from Tasks 2/3;
export only a strictly validated, versioned schema.

- [ ] Write failing regressions for stale success replacement, source mismatch/change, skipped/missing/conflicting scenarios, unknown fence, unknown durability, invalid/non-finite timings, observation gaps and cleanup failure.
- [ ] Cover secrets embedded in chunked/escaped logs and descendant processes that survive parent timeout. Do not export raw diagnostics.
- [ ] Implement a clean-source preflight and input hashes, inherited-environment neutralization, hard run deadline and ownership-scoped cleanup. Preserve failed evidence even on preflight errors.
- [ ] Add a bounded CI job on a dedicated ephemeral backend. Capability failure is a failure, never a skip or successful HA result. Untrusted PR code must not obtain production or persistent runner credentials.
- [ ] Run all new regressions; run existing Phase 2/3 runner regressions, docs/baseline/secret/package/release checks without changing expectations.
- [ ] Retain exact source head, tested integration commit, tree, artifact hashes, sanitized event/log outputs and observed RTO/RPO. Report hosted and local outcomes separately.

## Task 5: Independent Review And Draft PR Completion

- [ ] Obtain independent security/correctness review of the implemented diff and exact-source evidence. The initial architecture review does not satisfy this gate.
- [ ] Reproduce/fix review findings with regressions, then rerun affected checks against the new exact commit.
- [ ] Update project status, documentation index and draft PR with findings, failed/inconclusive scenarios, measurements and remaining risks.
- [ ] Leave the PR draft and unmerged. Preserve the missing historical SDK blocker.
