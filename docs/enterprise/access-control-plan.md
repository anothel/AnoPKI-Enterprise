# Enterprise Access-Control Plan

Status: planned. SSO, first-class RBAC, and ABAC are not implemented.
Community remains API-key based with `read`, `write`, and `operator` scopes.

## Integration Boundary

Enterprise authentication and authorization belong in an overlay before the
existing Community HTTP handlers. Successful Enterprise authentication creates
a principal context; Enterprise policy evaluates that principal, action, and
resource attributes before calling the unchanged Community handler. Denial is
fail-closed. Public CRL, OCSP, and ACME protocol behavior stays unchanged.

OIDC is the first integration target. Validate issuer, audience, signature,
expiry, and required claims against configured provider metadata. Use the
stable `(issuer, subject)` pair as user identity; email and display name are
descriptive only.

SAML remains a later compatibility path. A SAML service-provider boundary may
establish an Enterprise session or exchange a validated assertion for a
short-lived internal token. Raw SAML assertions must not reach Community
handlers or enter logs, audit records, or long-lived storage.

Provider-specific SDKs, login UI, session storage, and identity-provider
selection wait until a real customer identity provider is chosen.

## User And Group Mapping

- Map each external user to a stable provider plus subject identifier.
- Normalize configured group claims or SAML group attributes to exact group
  names; do not infer roles from email domains or partial string matches.
- Map allow-listed groups to Enterprise roles through versioned configuration.
- Give unmapped users no protected API access.
- Record mapping version and matched groups in authorization audit metadata.
- Apply mapping changes only to new authentication/session evaluation; revoke
  existing sessions when urgent access removal is required.

## Roles

| Role | Allowed responsibility |
| --- | --- |
| Requester | Create and view identities and enrollment requests within allowed attributes. |
| Approver | Approve or reject permitted enrollment requests; cannot approve own production request. |
| Operator | Manage issuers, profiles, revocation, CRL/OCSP, operations, and access configuration. |
| Auditor | Read lifecycle, inventory, audit, and release evidence without mutation. |
| Break-glass | Time-limited emergency Operator access under the flow below. |

Roles grant actions, not unrestricted resource access. Operator access may
still be constrained by issuer, profile, or environment policy. Default deny
applies when no role grants the requested action.

## ABAC Attributes

Policy evaluates these canonical resource attributes:

- `owner`
- `team`
- `service`
- `environment`
- `issuer`
- `profile`

Identity-provider claims supply principal ownership/team membership. Enterprise
configuration supplies allowed services, environments, issuers, and profiles
for each role or group. Resource fields supply the comparison values. Missing
required attributes deny access; request payload alone is not trusted when a
persisted resource value exists.

Initial policy rules should cover exact-match and allow-list checks only.
Requester and Approver must match permitted owner, team, service, environment,
issuer, and profile values. Production approval must enforce requester/approver
separation. Complex policy languages wait until these rules prove insufficient.

## Break-Glass Flow

1. Two authorized operators approve an incident-linked request with scope and
   expiry, using an out-of-band process available during identity-provider
   outage.
2. Retrieve or create a named `operator` API key from protected emergency
   storage with the shortest practical expiry and actor prefix `break-glass-`.
3. Record incident ID, approvers, reason, start time, expiry, and requested
   scope before use.
4. Alert on every use and apply normal audit recording; break-glass does not
   bypass lifecycle policy or input validation.
5. Disable or rotate the key after use, terminate related sessions, and review
   all actions before incident closure.

Emergency credentials must not depend on OIDC or SAML availability. They must
not become a normal fallback for authorization denial.

## Audit Metadata

Enterprise-authenticated requests add:

```text
auth_method
identity_provider
principal_subject
principal_display_name
principal_groups
principal_roles
session_id_or_token_fingerprint
access_mapping_version
authorization_action
authorization_result
authorization_reason
resource_owner
resource_team
resource_service
resource_environment
resource_issuer
resource_profile
break_glass_incident_id
```

Record only fields applicable to the request. Never record access tokens, ID
tokens, SAML assertions, session secrets, API keys, or unredacted credentials.
Authorization failures must retain request/trace correlation and a stable
reason without exposing provider internals.

## Migration From API-Key Mode

1. Keep Community `api_key` mode as the baseline and preserve current route
   scope behavior.
2. Add Enterprise dual mode for selected internal users. API keys still
   enforce access while SSO identity and proposed policy decisions are audited.
3. Enable SSO enforcement for a pilot group; retain API keys for service
   accounts and tested break-glass use.
4. Disable human API keys after role/attribute mappings, denial tests, session
   expiry, provider outage, and break-glass drills pass.
5. Migrate service accounts only after a separate machine-identity design is
   selected. Do not force human SSO semantics onto automated clients.

Each phase needs a rollback to the prior Enterprise mode and evidence that
Community API-key behavior remains unchanged. SSO/RBAC/ABAC must not be called
available or production-ready until implementation, negative authorization
tests, provider integration tests, and release evidence exist.
