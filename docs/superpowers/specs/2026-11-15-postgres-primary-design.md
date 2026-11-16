# Phase 3 PostgreSQL primary qualification design

Qualify infrastructure failure separately from Phase 2 application-node recovery.
Use PostgreSQL 16.16 primary and physical standby in a unique disposable Docker
bridge network, ephemeral tmpfs data, no restart policy, and random loopback-only
client ports. Accept no external DSN. Trust authentication is confined to these
synthetic disposable instances. Preserve Community and SDK pins and existing gates.

Approaches considered: local PostgreSQL processes require host installation and
user management; Patroni adds election/quorum scope. Select two Docker instances
with explicit kill/inspect fencing and manual promotion: minimal reproducible
infrastructure evidence without claiming an HA control plane.

Synchronous remote_apply commits establish the no-loss boundary. Keep application
pools alive with pgx multi-host target_session_attrs=read-write. Hold a transaction
and connection on the old primary, SIGKILL it, inspect stopped state before
promotion, prove old writer failure, promote, disable synchronous wait on the
single surviving server, and measure reconnection with a committed write. Reuse
Phase 2 lifecycle assertions in separate Phase 3 tests, with the failure between
initial claims and takeover. Compare whole-schema logical state before/after,
then verify stale issuance/CRL/outbox lease rejection and audit integrity.

A separate asynchronous case pauses replay, commits a marker on the primary,
kills it, promotes the paused standby, and measures whether the marker survived.
This demonstrates possible acknowledged loss; it is not a statistical RPO bound.
Recovery is measured from fault injection through fencing, promotion and first
successful client write. No SLA threshold is invented.

Non-goals: automatic election, partitions, external STONITH, old-primary rejoin,
real signing/SDK, service HTTP routing, correlated host failure, production HA.
Raw test diagnostics remain local; publish allowlisted structured measurements
and exact commit/tree identity. Dirty evidence is diagnostic only. CI uses the
same Docker harness under race instrumentation and fails on skips/missing tests.
