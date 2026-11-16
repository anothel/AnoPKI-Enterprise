# Disposable HA prerequisite fixture

This fixture currently tests only **Patroni bootstrap cancellation when its
required watchdog is absent**. It is not a deployment configuration or full HA
qualification. Do not enable automatic or off watchdog mode to get a green run.

Run on Linux amd64 with Docker, Python 3.12 and OpenSSL:

```sh
python scripts/test_verify_postgres_ha_prerequisites.py
python scripts/verify-postgres-ha-prerequisites.py --commit "$(git rev-parse HEAD)"
```

The runner requires a clean committed checkout. It creates an internal Docker
network, three mutually authenticated etcd peers and one isolated Patroni node;
there are no host ports, host volumes or host devices. No external DSN is
accepted. Temporary credentials/configurations and database files are discarded.
Downloads are restricted to reviewed PyPI artifacts with SHA-256 checks. Image
build installation is offline and hash-locked; source-only python-etcd and ydiff
use hash-locked build tools. No packages are installed on the host.

The test requires healthy three-member etcd quorum, Patroni's specific watchdog
bootstrap-cancellation event, nonzero Patroni exit, stopped PostgreSQL and no
leader key. Missing evidence or an unrelated crash fails. Bootstrap may briefly
run PostgreSQL before Patroni checks the watchdog: the node listens only on its
own loopback, and application clients are never attached. This test does not
establish that required-watchdog mode prevents every transient bootstrap write.

Evidence contains symbolic boolean observations, exact source/tree/input hashes,
immutable image ID and elapsed observation time (not RTO). Raw subprocess logs
are omitted; the recognized refusal is represented as a structured event.
`ha_qualified` is always false. Cleanup failure fails the run. The process-group
timeout mechanism is shared with the unchanged Phase 3 runner. An external
SIGKILL/host failure cannot guarantee cleanup; inspect resources labeled
`com.anopki.phase4.prerequisite` on the disposable host after interruption.

These upstream artifacts are test infrastructure, not Enterprise distribution
inputs. Existing SDK, Community and release/license gates are unchanged. See
[the design](../../docs/enterprise/postgres-ha-qualification.md) for assumptions,
remaining automatic failover scenarios and independent review requirements.
