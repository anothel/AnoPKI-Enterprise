# Authorization next work

The Enterprise foundation includes a decision contract, fail-closed engine,
deterministic fingerprints, action/resource catalog, route coverage validator,
and tests. The [generic Community authorization seam](authorization-integration-boundary.md)
is available through `RequestAuthorizer` and `NewWithAuthorizer`. An injected
authorizer runs on matched protected routes after authentication and legacy scope
checks. Public routes bypass the hook. The service entry point uses a nil
authorizer, so existing runtime scope enforcement remains in effect. Enterprise
engine integration is pending.

Recommended order:

1. Define the Enterprise adapter from authenticated Community identity/context to normalized `Subject` and `AuthorizationRequest`. Map catalog actions and resources and translate decisions to stable HTTP and audit behavior. Preserve existing public routes and `read`/`write`/`operator` behavior in compatibility tests. Use only normalized inputs and omit raw tokens, assertions, bodies, CSR/certificate contents, and local paths.
2. Select reviewed production action/resource identifiers and a policy-set distribution/storage model. Add migrations only in that separate task; do not ship the test fixture as a default policy.
3. Integrate `DecisionEvidence` with audit redaction and persistence, then verify correlation without treating SHA-256 as a signature or tamper-evidence proof.
4. Implement approval request persistence, approver separation, single/dual control, replay/idempotency, and expiry. Only then may `approval_required` trigger a workflow.
5. Implement OIDC or SAML authentication separately, including issuer/metadata validation, key rotation, replay protections, logout/session policy, and normalized subject mapping.
6. Add administration APIs/UI only after authorization protects them and bootstrap/recovery paths are defined.
7. Re-run security review, full regression, hosted qualification, release evidence, and production readiness gates.

Do not advertise `oidc`, `saml`, `rbac`, `abac`, `dual-control`, or `production-authorization` as implemented edition features from this foundation.
