# Phase 4 Fencing Feasibility — 2026-11-18 UTC

## Engineering Decision

**Keep positive automatic failover blocked.** Latest main was fetched and
verified at `11049521d4f4f7daad45a6a2481d8b003c788d67`, tree
`6e53e49bdb9d72540dcca6094cbf5e4b59274190`; PRs #4, #5 and #6 are merged.
The initially restored checkout was clean on `work` at `dbd1a1e`. Work continues
in this disposable Cloud checkout on `codex/phase4-fencing-feasibility`.
No related issue is confirmed. Earlier branch instructions are historical.

Patroni + etcd remains the smallest **conditional target architecture**: three
PostgreSQL/Patroni guests with three etcd voters, co-located for this bounded
lab, plus independent reset facilities and an observer/control path. Its
upstream synchronous membership protocol avoids adding a separate promotion
controller. It is not viable for positive testing on the currently established
infrastructure. Pacemaker/Corosync + PAF remains a conditional alternative when
a supported external off-fence is available, with an additional unresolved
synchronous candidate eligibility proof. Neither is qualified here.

The smallest currently safe executable slice remains the existing four-container
negative fixture (three etcd members, one isolated bootstrap node). No positive
cluster, custom consensus, promotion hook, fencing proxy or deployment is added.
This change adds prerequisite regressions and a current decision/evidence record;
it does not repeat or reclassify the implementation delivered in PRs #4–#6.

## Current Environment Boundary

Read-only checks on this executor observed Linux x86_64, uid 1000, Docker Engine
29.9.2, API 1.56/minimum 1.40, with rootless, seccomp and cgroup namespaces.
The explicit local socket `/var/run/docker.sock` is usable and resolves to
`/run/codex-docker/docker.sock`. `/dev/kvm`, `/dev/watchdog`, `/dev/watchdog0`
and `/sys/class/watchdog` were absent. No `qemu-system-x86_64`, `virsh`,
`patroni`, `etcd`, `pacemakerd`, `corosync` or `fence_docker` executable was
found on PATH. Container-packaged tools are separate from host PATH.

The Cloud status for this task reports a connected, running environment with
restricted outbound networking, no configured secrets, runtime variables or
outbound identities, and an SSH portal. No independent watchdog/hypervisor
control API or authenticated restricted fencing endpoint is configured or
otherwise established. This is bounded inspection, not proof that no external
provider could supply one. The SSH portal and Docker access are not such proof.
No watchdog was opened, host paused/reset or external resource fenced.

Docker's trusted host kernel/daemon can conditionally fence a guest process.
That boundary would exclude host/daemon failure, compromise and correlated
storage loss. It does not supply the independently timed reset required by the
Patroni model. A paused guest's virtual-clock watchdog and guest softdog do not
establish the required pause/resume exclusion. Installing software would not
resolve this infrastructure proof.

Git fetch works; the installed `gh` reports an invalid `GH_TOKEN`. Do not expose
or copy it. Provider connector access is used if shell writes are unavailable.
No failed prior executor's cleanup or state is inferred from this host.

## Concrete Safety Requirements And Verification Limits

| Requirement | Patroni + etcd | Pacemaker/Corosync + PAF | Current evidence |
| --- | --- | --- | --- |
| Exclusive writable primary | Required independent watchdog/reset; actual reset before another leader may write, including pause between lease renewal and keepalive, guest stall and hypervisor pause/resume. Half-TTL configuration alone is insufficient. | STONITH off on exact immutable generated identity, followed by confirmed stopped state before promotion. API acceptance, timeout, reboot, observer kill or lost client route is insufficient. | Negative missing-watchdog refusal executed; no successful exclusion/reset boundary qualified. |
| Quorum | Three mutually authenticated etcd voters; majority required; no failsafe mode or manual/forced promotion bypass. | Three votes, majority, `stonith-enabled=true`, `startup-fencing=true`, `stonith-action=off`, `no-quorum-policy=stop`, at most one promoted resource. No two-node quorum exception. | Three-member health executed in the existing negative fixture; quorum loss/healing and election safety not executed. |
| Synchronous eligibility | Upstream authoritative `/sync` membership and timeline rules, including transitions; no forced promotion of an ineligible node. | Supported upstream configuration must prove the promoted node contains all acknowledged commits even if the last synchronous recipient is unavailable. Highest reachable LSN and `maxlag` do not prove this. | Source review only; no positive membership-transition or candidate-loss scenario executed. |
| Commit durability | `synchronous_mode=true`, strict mode, one required follower; PostgreSQL `remote_apply`, fsync and full-page writes. Verify actual settings on every client session and after promotion. | Same PostgreSQL durability; a safe follower is required after promotion, with no asynchronous fallback. | Generated negative-fixture settings protected by regressions; no synchronous replication or post-promotion durability result inferred. |
| Old-primary quarantine | Reset guest cannot start writable PostgreSQL or accept clients outside Patroni-controlled recovery; upstream rewind/reclone and timeline/system-ID checks precede rejoin. | Keep off, disable restart/unfencing into old data, require upstream-controlled rewind/reclone and timeline/system-ID checks. | Required design only; quarantine and failed-rewind/rejoin remain unexecuted. |
| Management isolation | Independent timer and observer/control route outside injected faults; known timing bounds and device rounding. | Authenticated out-of-band service limited to generated immutable IDs for one active run; no Docker socket or broad daemon credentials in guests. Deny foreign/stale IDs, aliases, arbitrary paths, create/exec/start/restart and expired runs; serialize teardown with in-flight fences. | No such service exists in this change. Its authorization, failure and API compatibility tests remain blocked. |
| Safety verdict | Direct observations of every node, protocol/reset events and bounded uncertainty; missing data blocks a verdict. | Same; denied, failed, ambiguous or timed-out fences and management partitions must block promotion. | No continuous exclusion or partition evidence. Sampling or unreachable endpoints cannot stand in for a fence. |

For both candidates, retain an observer acknowledgement ledger, distinguish
uncertain outcomes, verify all acknowledged IDs and application state on the
surviving timeline, and test a second failure. No safe eligible candidate or no
safe synchronous follower means unavailable service, never relaxed durability.
Phase 3's clearing of synchronous standby requirements must not be reused.

## Architecture Review

The exact upstream sources from the recovery record were fetched again for
read-only inspection. These are reviewed source identities, not a new pinned,
installed complete HA stack:

| Source | Revision | Relevant contract |
| --- | --- | --- |
| [Patroni watchdog](https://github.com/patroni/patroni/blob/235fdb3990513c7852da8dc51e9cb92b6d0e4907/patroni/watchdog/base.py) | `235fdb3990513c7852da8dc51e9cb92b6d0e4907` | Half-TTL computes `ttl // 2`; required mode rejects unsafe activation. Device operation and actual timing remain external assumptions. |
| [Patroni HA](https://github.com/patroni/patroni/blob/235fdb3990513c7852da8dc51e9cb92b6d0e4907/patroni/ha.py) | same | `update_lock` calls keepalive after DCS renewal; `is_healthiest_node` restricts ordinary synchronous-mode races using `/sync`. This makes the renewal/keepalive pause and membership-transition tests mandatory. |
| [PAF pgsqlms](https://github.com/ClusterLabs/PAF/blob/9653351a128f56246d58e8a50faecc1e98d82faa/script/pgsqlms) | `9653351a128f56246d58e8a50faecc1e98d82faa` | Pre-promotion publishes participant LSNs; promotion compares available timeline/LSN locations. This is not by itself an authoritative synchronous acknowledgement set. |
| [fence_docker](https://github.com/ClusterLabs/fence-agents/blob/c6d1b7e8892661f1204572a8b5ce1241a451fe9b/agents/docker/fence_docker.py) / [shared fence action](https://github.com/ClusterLabs/fence-agents/blob/c6d1b7e8892661f1204572a8b5ce1241a451fe9b/lib/fencing.py.py) | `c6d1b7e8892661f1204572a8b5ce1241a451fe9b` | Off kills, status inspects `State.Running`, reboot restarts; the common off path polls status. Default API 1.11 is below this daemon's minimum 1.40. |

The unresolved PAF example is unchanged but decisive: A acknowledges with
synchronous B; A is fenced; B's PostgreSQL becomes unavailable while cluster
membership retains quorum with C. C's highest *available* LSN is not evidence
that it received A's acknowledged transaction. The integration must refuse C
unless an established protocol proves eligibility. This is not a demonstrated
PAF vulnerability and is not solved here with a custom eligibility ledger/hook.
Requiring every eligible standby to acknowledge is a possible design direction,
but would still require a supported configuration and proof across membership
changes; no such integration is selected or claimed tested.

## Executed Local Evidence

Before edits, the unchanged negative fixture passed on exact clean main
`1104952`. Its [verbatim allowlisted payload](evidence/postgres-ha-prerequisite-1104952.json)
records healthy three-member etcd, specific required-watchdog bootstrap refusal,
stopped PostgreSQL, no leader key and successful owned cleanup. Observation
interval was 2.3861089639999875 seconds, **not RTO**. The payload's source commit,
tree and input hashes remain those of main, never a later documentation commit.
The retained JSON SHA-256 is
`dbbf393f95faffcbb2649303045da8b6765707269c013579f783f66542ee6105`.
`ha_qualified: false`; no cryptographic backend was executed. Bootstrap may
briefly run writable PostgreSQL before the watchdog check, isolated from clients.

Four new regression methods extend the existing prerequisite suite from 11 to
15 tests. They protect durability in both emitted configuration layers, required
follower count/failsafe refusal, half-TTL timing inputs, loopback bootstrap
listeners/HBA, and isolated Docker guest setup without host mounts/devices or
published ports. Six in-memory unsafe source mutations were independently
rejected: fsync off, zero followers, failsafe enabled, non-half-TTL margin,
public bootstrap listener and host Docker socket mount. The original on-disk
runner was never changed. These are configuration/command construction tests,
not successful fences, device timing tests or candidate promotion evidence.

Existing 7 Phase 3 and 33 Phase 2 runner regressions also pass. Full Go
`go test -race -p 1 ./...` and `go vet ./...` pass with Go 1.26.11. No external
database DSN was supplied; optional live database tests in that local suite do
not provide fresh Phase 2/3 runtime evidence. Docs and docs-validator tests,
secret scan, package and KeyProvider boundary checks, frozen Community baseline
and expected-blocked release validation pass. The first baseline attempt lacked
the historical Community object; fetching the unchanged exact object resolved
that input blocker without repinning. Hosted and independent review results
are recorded with the draft PR; pending checks must not be inferred successful
from these local results.

The OpenSSL C++ build and all 15 CTest cases pass. These checks preserve the
existing core contract coverage; they do not execute AnoCrypto-C SDK parity.

## Exact Blockers And Next Implementation

1. Obtain a disposable provider with reset timing outside the paused guest and
   controller failure domain, plus generated-resource-only control. Pin the
   full stack and prove actual reset deadlines under the original fault matrix.
   Patroni is preferred once this boundary is demonstrated.
2. If only trusted-host external off-fencing is available, first establish and
   independently review the restricted service contract, immutable identity
   lifecycle, supported Docker API and failure/refusal tests. Separately resolve
   PAF synchronous candidate eligibility using an established integration. A
   working fence alone does not authorize promotion.
3. Only after both exclusion and durability prerequisites pass, resume Tasks
   1–4 of the [implementation plan](postgres-ha-implementation-plan.md), preserving
   all [acceptance scenarios](postgres-ha-qualification.md). Add automatic
   failover, partitions, controller stalls, fence refusal, quarantine/rejoin,
   second failure and application consistency evidence incrementally.

Full HA qualification, production readiness and RTO/RPO guarantees remain
unclaimed. Community and AnoCrypto-C pins, historical SDK blocker, Phase 1–3
checks and security/release gates are unchanged. No merge, tag, release,
deployment or publication is authorized.
