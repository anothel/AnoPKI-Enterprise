# Enterprise Edition Boundary

AnoPKI Enterprise is the private commercial edition. It should track Community
closely and add Enterprise-only modules rather than forking lifecycle behavior
without a clear reason.

## Enterprise-only areas

- AnoCrypto implementation and backend adapter.
- KCMVP preparation, submission, and customer evidence packs.
- Commercial license, support, and SLA material.
- SSO/OIDC/SAML, RBAC/ABAC, approval workflows, and operator directory integration.
- HSM/KMS/PKCS#11 provider implementations.
- HSM/KMS/PKCS#11 provider planning belongs in
  [Enterprise provider interface plan](provider-interface-plan.md) until real
  provider work starts.
- Productized deploy adapters and rollback checks; initial target planning is
  in the [Enterprise deployment adapter plan](deploy-adapter-plan.md).
- SIEM export, tamper-evident audit storage, and compliance reports.

## Shared upstream areas

Keep these aligned with Community whenever possible:

- lifecycle state transitions,
- public API and OpenAPI contract,
- core CLI JSON contract,
- ACME protocol behavior,
- public docs that describe shared behavior,
- security fixes and release evidence baseline.
