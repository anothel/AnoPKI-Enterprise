# Enterprise authorization decision contract

Status: implemented as an Enterprise-owned contract and policy-engine foundation. It is not connected to HTTP runtime enforcement and is not production authorization.

## Authentication and authorization

Authentication proves who a caller is. Current runtime authentication supports only `dev` and `api_key`. `oidc`, `saml`, and `service_identity` are reserved normalized subject values; this contract does not implement those protocols.

Authorization decides whether a normalized subject may perform an action on a resource. The engine never accepts an API key, bearer token, JWT, SAML assertion, cookie, password, or session as input.

## Subject

`Subject` contains only:

- `id`: required.
- `kind`: `human` or `service`.
- `authentication_method`: `dev`, `api_key`, `oidc`, `saml`, or `service_identity`.
- `roles`: normalized, deduplicated, byte-sorted identifiers. Empty roles and wildcards are invalid.
- `attributes`: exact-match values under normalized, byte-stable keys.

Credential and raw identity artifact keys are rejected from attributes. OIDC/SAML enum values express a future input contract, not runtime support.

## Authorization request

`AuthorizationRequest` contains `action`, `resource_type`, optional `resource_id`, `environment`, `product_profile`, optional `request_id`, and exact-match attributes.

Allowed environments are `development`, `test`, `staging`, and `production`. The current allowed product profile is `enterprise-openssl`. Actions and resource types must exist in the catalog supplied to the engine, and each action maps to exactly one resource type. Collection operations may omit `resource_id`.

Request attributes reject raw request bodies, secrets, CSR/certificate contents, key references, and local paths. Callers must explicitly derive minimal authorization attributes.

## Policy and policy set

A policy has required `id`, `version`, `effect`, subject/role selectors, actions, resource types, conditions, and `approval_requirement`.

- Effects: `allow`, `deny`.
- Approval requirements: `none`, `single`, `dual`.
- At least one subject or role selector is required; implicit broad policies and `*` are rejected.
- Actions cannot be empty and must exist in the supplied catalog.
- Resource types must exist in the supplied catalog and match every selected action.
- Duplicate policy IDs are rejected, including equal or conflicting versions.
- Conditions support exact equality only: `environment`, `product_profile`, `subject.id`, `subject.kind`, `subject.authentication_method`, `subject.<attribute>`, and `request.<attribute>`.
- Regex, scripts, arbitrary evaluators, and implicit wildcards are not policy features.

Policy order has no meaning. Canonicalization sorts policies and selector lists before calculating `SHA-256(canonical policy set JSON)`.

## Decision

Results are `allow`, `deny`, and `approval_required`. Every decision carries stable correlation fields: result, reason code, subject/action/resource identifiers, sorted matched policy IDs, policy-set ID/version/SHA-256, approval requirement, and request ID.

Precedence:

1. Invalid subject, request, catalog, policy set, or canonical fingerprint -> `deny`.
2. Matching explicit deny -> `deny`.
3. Matching `single` or `dual` approval policy -> `approval_required`.
4. Matching ordinary allow -> `allow`.
5. No valid allow -> `deny`.

Explicit deny always wins over approval and allow. `approval_required` is not an approval execution or persistence workflow.

Stable reason codes:

- `authz.allowed`
- `authz.approval_required`
- `authz.subject_missing`
- `authz.subject_invalid`
- `authz.action_unknown`
- `authz.resource_unknown`
- `authz.policy_invalid`
- `authz.explicit_deny`
- `authz.no_matching_allow`
- `authz.context_mismatch`

Default behavior is deny. Constructors and decision evaluation do not use panic as a contract.

## Canonical encoding and evidence

Subject, request, policy set, and decision support compact deterministic JSON. Maps have stable key order; normalized lists and matched policy IDs are sorted; policy input order, map insertion order, whitespace, line endings, current time, and local paths do not affect policy fingerprints.

`DecisionEvidence` is a secret-free DTO reserved for later audit integration. It permits subject ID/kind/authentication method, action/resource identifiers, result/reason, matched policy IDs, policy-set identity/hash, approval requirement, and request ID. It contains no raw credential or identity artifact.

The policy-set SHA-256 is correlation evidence only. It is not a digital signature and does not prove tamper-evident storage.
