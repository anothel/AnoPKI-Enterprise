# Phase 3 PostgreSQL Primary Failover Qualification

This bounded test uses a disposable PostgreSQL 16.16 primary and physical standby.
It extends [Phase 2 application-node qualification](postgres-failover-qualification.md)
without changing production lifecycle/store code, Community or AnoCrypto-C pins.

## Topology And Reproduction

The Go harness creates a unique Docker bridge and two containers, tmpfs data,
no restart policy, and random loopback-only client ports. The image is pinned:
`postgres:16.16@sha256:dd2bf3ce2dc83a81674cf7f217fcfd8a5009a4b325dda5b843bfee82a06cff6f`.
No external DSN is accepted. Trust authentication is for synthetic disposable
fixtures only; the host and its other containers are a trusted test boundary.
Do not reuse this configuration for deployment. A Docker daemon and Go 1.26.11+
with race support are required on Linux. Image pull requires network access.

```sh
python scripts/test_verify_postgres_primary.py
python scripts/verify-postgres-primary.py --out-dir .tmp/postgres-primary/local
```

The runner requires a clean checkout and exact HEAD (optional `--commit` must
match). It disables external Go workspaces, flags and config and strips inherited
PostgreSQL overrides. It runs four exact required tests under `-race -count=1`.
Missing/skipped/conflicting test or package outcomes fail qualification. Metrics
must have exactly the allowlisted fields, finite ordered times, valid state
hashes and the expected data-loss result. Raw command diagnostics are omitted.
A failed invocation replaces previous success before preflight. Unique run
labels and process-group termination allow runner cleanup after test timeout;
normal Go cleanup removes each container and network. External runner/host
SIGKILL cannot guarantee cleanup; use a disposable host and inspect owned
`com.anopki.phase3.run` resources after interruption.

## Verified Assertions

Three synchronous scenarios use `remote_apply`, verify application session mode
and a synchronous standby, and prime independent pools before failure. Initial
issuance, CRL and outbox claims are created using real application/store code.
Signing output is a fixture; no cryptographic adapter or real signer executes.

Each scenario holds an uncommitted transaction, checks standby write rejection,
SIGKILLs the primary, confirms its stopped state, and rejects further writes and
commit on the old transaction. Only then does the harness promote the standby.
The surviving server explicitly drops synchronous-standby requirements, since
there is no second replica after failure. This availability step reduces
redundancy; it is not an automatic HA policy. The existing multi-host pgx pool
reconnects and commits a probe. All application tables have identical logical
row digests across promotion, preserving acknowledged state and excluding the
uncommitted transaction. Audit chain verification runs after lifecycle recovery.

Post-promotion assertions retain active-lease protection, expired takeover,
stale issuance/CRL/outbox compare-and-swap rejection, idempotent issuance without
resigning, exactly one certificate-issued audit event, contiguous CRL numbering,
and one outbox handler/attempt in the claim-only crash scenario. This is not a
general exactly-once delivery claim. Clocks advance deterministically for lease
expiry: measured database recovery time excludes real lease expiry waits.

The asynchronous scenario first observes replay through the baseline WAL LSN,
stops the standby receiver by changing its connection to an unreachable local
endpoint, confirms no receiver, then pauses replay. It commits one primary
marker, fences the primary, promotes the standby, reconnects the primed pool,
and proves that one acknowledged marker is lost. This intentionally induced
lag is a loss demonstration, not a measured general asynchronous RPO bound.

Measurements are elapsed monotonic seconds from fault injection through:
confirmed stopped state; completed promotion and survivor configuration; and
first successful write on the retained pool. They include local Docker control
latency, exclude detection/election/lease expiry, and are observations, not SLAs.

## Limits And Evidence

Not tested: automatic detection/election, quorum, network partitions, external
STONITH, DNS/proxy/HTTP service routing, old-primary rejoin/rewind, a second
failure, correlated host/storage failures, WAL corruption, real signer crash or
provider/SDK recovery. Fencing here means the owned primary process is stopped
and never restarted. These results do not qualify production HA.

The new independent CI job retains an Enterprise primary-failover JSON artifact
on success or failure and leaves existing application failover, integration,
backup/restore, security and pin gates intact. Exact local and hosted identities
are recorded in [project status](../PROJECT_STATUS.md); never transfer evidence
to a later commit merely because its source looks similar.
