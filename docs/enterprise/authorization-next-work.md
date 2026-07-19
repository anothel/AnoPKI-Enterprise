# Authorization next work

Current result: contract, fail-closed engine foundation, deterministic fingerprints, action/resource catalog, route coverage validator, and tests. No runtime enforcement changed.

Recommended order:

1. Propose a backend-neutral Community authorization seam upstream. Preserve existing public routes and `read`/`write`/`operator` behavior in compatibility tests.
2. Define the Enterprise adapter from authenticated Community identity/context to normalized `Subject` and `AuthorizationRequest`. Do not pass raw tokens, assertions, bodies, CSR/certificate contents, or local paths.
3. Select reviewed production action/resource identifiers and a policy-set distribution/storage model. Add migrations only in that separate task; do not ship the test fixture as a default policy.
4. Integrate `DecisionEvidence` with audit redaction and persistence, then verify correlation without treating SHA-256 as a signature or tamper-evidence proof.
5. Implement approval request persistence, approver separation, single/dual control, replay/idempotency, and expiry. Only then may `approval_required` trigger a workflow.
6. Implement OIDC or SAML authentication separately, including issuer/metadata validation, key rotation, replay protections, logout/session policy, and normalized subject mapping.
7. Add administration APIs/UI only after authorization protects them and bootstrap/recovery paths are defined.
8. Re-run security review, full regression, hosted qualification, release evidence, and production readiness gates.

Do not advertise `oidc`, `saml`, `rbac`, `abac`, `dual-control`, or `production-authorization` as implemented edition features from this foundation.
