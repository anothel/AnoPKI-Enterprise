# Enterprise PostgreSQL Failover And Recovery Qualification

This Phase 2 slice tests application-node lease recovery against one disposable
PostgreSQL 16 server. It does not test PostgreSQL primary election, replication,
network partitions, process termination during an external signing operation,
or production key-provider recovery. No production-readiness claim follows.

## Source And Adaptation

The consumed Community baseline stays
`ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc`. Community is frozen and unchanged at
`49142ff50f5b37ba142d18cf61b60d8b287bdb49`. Selected tests/runner were read from
that frozen commit, originally introduced by
`5348a478ff1117482a8d168b655dad290367b188`:

| Frozen source | New Enterprise file |
| --- | --- |
| `service/internal/lifecycle/postgres_multi_node_failover_test.go` | `service/internal/lifecycle/enterprise_postgres_failover_test.go` |
| `scripts/verify-postgres-multi-node-failover.py` | `scripts/verify-enterprise-postgres-failover.py` |
| `scripts/test_verify_postgres_multi_node_failover.py` | `scripts/test_verify_enterprise_postgres_failover.py` |

MPL-2.0 source notices are retained. This selected adaptation is not a bulk
synchronization and does not advance either Community or SDK pins.

The original issuance test reproduced a duplicate audit-event primary key:
independent simulated nodes restart the same counter ID generator. Enterprise
uses its existing production `UUIDGenerator` instead. No lifecycle/store code
or public API/CLI contract changes are required. Lease and retry assertions
remain intact. Signing results are fixtures; no crypto adapter executes here.

The original helper dropped `public`. The adaptation creates a unique owned
schema per test, fixes each independent pgx pool's search path to that schema,
checks PostgreSQL major version 16 and distinct backend connections, and drops
only that schema after both pools close. Setup errors omit driver diagnostics
that could contain credentials. Use a disposable database and a dedicated role
with schema-creation permissions; do not use a production database.

## Assertions And Evidence

- Issuance: active leases cannot be stolen; expired leases transfer; stale
  persistence is rejected; the successful result finalizes; retry returns the
  same certificate without another signing request and retains finalized state.
- CRL: active claims are protected; expiry transfers the same number; stale
  completion is rejected; publication/claim deletion commit together and the
  next number is contiguous.
- Outbox: a claim-only simulated crash runs no handler; expiry moves processing
  to the other node once in this scenario; stale completion is attempted while
  the new lease is still processing and again after completion. It rejects
  without changing the current lease and rolls back its attempt, leaving one
  successful attempt. This is not a general
  exactly-once external delivery guarantee.

The runner requires `ANOPKI_POSTGRES_FAILOVER_DSN`, Go 1.26.11+, all three exact
Go test names to pass with `-race -count=1`, and no missing/skipped/conflicting
terminal results. A supplied `--commit` must match checkout HEAD. It retains
Enterprise and Community identities, source hashes, dirty-tree status and
redacted logs. A dirty local run is diagnostic evidence, not an immutable
hosted source qualification. Credentials in URI and keyword DSNs, decoded
passwords (including JSON/HTML escapes and spaced libpq assignments), local
paths and private-key markers are redacted or cause output
omission and failure. No DSN is put in command-line arguments or evidence.

```sh
python scripts/test_verify_enterprise_postgres_failover.py
# Set ANOPKI_POSTGRES_FAILOVER_DSN through your local environment/secret mechanism.
python scripts/verify-enterprise-postgres-failover.py \
  --out-dir .tmp/enterprise-postgres-failover/local
```

The new CI job requires a disposable PostgreSQL 16 service, uploads evidence
on success or failure and fails on any missing or skipped required test. The
existing `PostgreSQL 16 backup and restore drill` remains a separate required
qualification: transaction rollback and `pg_dump`/`pg_restore` state preservation.
The shared restore runner still emits inherited Community labels; its exact
commit identifies execution on Enterprise source, not Enterprise release
attestation. A reviewed Enterprise recovery evidence envelope is a next priority.
Review both jobs' artifacts for the same integration commit; do not relabel
these as database HA or reassign their commit identities after documentation
changes. See [project status](../PROJECT_STATUS.md) for verified run identities.

## Remaining Qualification

Infrastructure-level failover needs an explicitly selected topology and test
harness: PostgreSQL primary/standby roles, replication mode, promotion/fencing,
network fault control, connection routing, recovery objectives, and authorized
disposable infrastructure. Production signer crash/retry needs the exact SDK
and provider-specific idempotency/recovery contract. None is inferred from the
application-node tests or historical SDK parity records.
