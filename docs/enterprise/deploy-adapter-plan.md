# Enterprise Deployment Adapter Plan

Status: planned. No Enterprise deployment adapter is implemented yet.

Deployment adapters are separate from crypto backends and key providers. They
move an issued workload certificate to its runtime target; they must never read
or deploy CA issuer or OCSP responder private keys.

## Adapter Order

| Order | Target | Reason |
| ---: | --- | --- |
| 1 | Kubernetes Secret | Native API, narrow first contract, and testable with a local or mock Kubernetes API. |
| 2 | Load balancer | Common commercial target; implement only after selecting a concrete vendor and API. |
| 3 | Nginx/Apache | Requires host file ownership, atomic replacement, reload, and process-specific checks. |
| 4 | Java keystore | Adds keystore format, alias, password, and JVM reload concerns. |
| 5 | IIS/Windows | Adds Windows certificate-store identity, ACL, binding, and platform-specific rollback behavior. |

Only the Kubernetes Secret adapter is selected for first implementation.
Later adapters remain backlog items until a real operator target fixes their
API, authentication, and health-check requirements.

## Kubernetes Secret Contract

### Inputs

- target cluster identity, namespace, and Secret name;
- issued leaf certificate and required chain in PEM form;
- matching workload private key only when the enrollment flow explicitly
  provides an exportable key;
- expected certificate fingerprint or serial number;
- optional labels and annotations;
- post-deploy TLS endpoint, SNI name, timeout, and trust roots.

The adapter must reject mismatched certificate/key input. It must not resolve
an issuer or responder `key_ref` into private key bytes. A non-exportable
workload key is unsupported by this adapter and requires a future CSI or
external-key integration.

### Required Permissions

Use a dedicated service account scoped to the target namespace. It needs
`get`, `create`, and `update` on Secrets. A pre-created-Secret policy may omit
`create`. It does not need `list`, `watch`, or `delete`, cluster-wide access,
or permission to read unrelated Secrets.

Workload restart permissions are outside the first adapter. The consuming
controller must watch the Secret and reload it. Targets that require pod
template changes need a later, separately authorized rollout integration.

### Rollout And Update

1. Validate target, certificate chain, key match, and expected identity.
2. Read the current Secret and retain its prior data in memory for this
   deployment attempt only.
3. Create or update a `kubernetes.io/tls` Secret using the observed
   `resourceVersion` so concurrent changes fail instead of being overwritten.
4. Wait for the configured endpoint to present the expected certificate.
5. Report success only after the post-deploy health check passes.

Secret data, private keys, and credentials must never enter logs or audit
metadata.

### Rollback

If the health check fails, restore the previous Secret data with a new
`resourceVersion` precondition, then verify that the previous certificate is
served. If no previous Secret existed, delete is not automatic; mark the
deployment failed and require operator cleanup under separate authorization.
Rollback conflict or rollback health-check failure is a critical failure and
must not be reported as a successful deployment.

The in-memory rollback window does not survive adapter process failure. A
durable rollback design that does not persist plaintext private keys is a
release gate before this adapter can be called production-ready.

### Post-Deploy Health Check

Open a TLS connection to the configured endpoint with the configured SNI and
trust roots. Require the served leaf fingerprint or serial to match the new
certificate, verify its chain and validity window, and enforce a bounded
timeout. HTTP application checks may be added only when the target requires
them; TLS identity is the first adapter's required check.

### Audit Events

Record `deploy.started`, `deploy.secret_updated`, `deploy.health_passed`,
`deploy.health_failed`, `deploy.rollback_started`, `deploy.rollback_completed`,
and `deploy.rollback_failed` as applicable. Metadata includes request/trace ID,
actor, cluster identifier, namespace, Secret name, certificate fingerprint or
serial, previous and new Kubernetes resource versions, result, duration, and a
stable redacted error code.

### Failure Modes

- invalid certificate chain, key mismatch, wrong target identity, or expired/not-yet-valid certificate;
- authentication or RBAC denial;
- missing namespace, API timeout, quota failure, or Kubernetes API outage;
- concurrent Secret update detected by `resourceVersion` conflict;
- consuming controller does not reload before timeout;
- endpoint serves the previous or an unexpected certificate;
- health endpoint is unreachable or trust validation fails;
- rollback update conflicts, fails, or does not restore endpoint health;
- adapter process exits after update and before in-memory rollback completes.

All failures are fail-closed: retain lifecycle/audit evidence, expose a stable
error, and never claim deployment success without the required health check.
