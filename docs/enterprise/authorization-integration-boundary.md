# Enterprise authorization integration boundary

## Current Community runtime

Community-owned `service/internal/httpapi/server.go` performs authentication and authorization together:

- Authentication modes: `dev`, `api_key`.
- API key scopes: `read`, `write`, `operator`.
- `write` also satisfies read; `operator` satisfies all current scopes.
- Public endpoints: ACME protocol operations, OCSP response, CRL publication reads.
- Protected endpoint scope selection: operator prefixes/expiration scan, then GET as read, all remaining methods as write.
- Authenticated actor: request context value; `X-Actor` is the dev fallback.
- Request metadata: request ID, traceparent, client IP, user agent, auth method, and start time are attached to context.
- Lifecycle audit events combine actor/request/API-key metadata and apply existing sensitive-field redaction before store persistence.

The locked mapping is recorded in `authorization-action-catalog.json`: 52 protected routes, 19 public routes, current legacy scope behavior, and a SHA-256 fixture for `server.go`.

## Enterprise-owned implementation

`service/internal/enterprise/authorization` owns normalized subject/request/policy/decision contracts, deterministic encoding, policy-set fingerprints, fail-closed evaluation, approval-required decisions, and the future audit evidence DTO.

This work does not modify:

- `service/internal/httpapi`, `lifecycle`, `domain`, or `store`.
- Current HTTP route authorization or API key scope semantics.
- Audit persistence or database schema.
- Login, customer/role administration APIs, UI, or approval persistence/execution.
- OIDC or SAML protocols.

No production default policy is provided. Test roles and fixtures are examples, not final product roles.

## Future integration seam

Runtime integration needs a generic Community-owned seam that can receive an authenticated identity and return an authorization result without importing Enterprise code into Community packages. That shared seam must be proposed and implemented upstream before this Enterprise engine can replace HTTP scope checks.

A later Enterprise adapter may normalize authenticated identity into `Subject`, map the Community route/operation to catalog action/resource identifiers, invoke the engine, and translate the result to stable HTTP/audit behavior. It must preserve current public endpoints and legacy scope behavior until an explicitly reviewed migration changes them.

Audit integration may persist only `DecisionEvidence`. Raw API keys, token hashes, JWTs, SAML assertions, cookies, passwords, private keys, PINs, credentials, full CSRs/certificates, request bodies, and local paths remain forbidden.

## Release boundary

The decision contract is implemented; runtime enforcement is unchanged. Customer release and hosted qualification remain blocked. AnoCrypto-C remains an external SDK that is not configured or implemented here; KCMVP is not validated; production authorization is not implemented.
