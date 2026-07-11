# Backend Profile Release Gates

## Community/OpenSSL

Required:

- Community full functional tests
- OpenSSL golden fixtures
- service/core contract validation
- security and supply-chain evidence

Release result: public Community release candidate allowed.

## Enterprise/OpenSSL

Required:

- synchronized reviewed Community baseline
- all Community/OpenSSL tests
- Enterprise layer tests
- Enterprise licensing and packaging evidence

Release result: commercial release candidate allowed. Metadata must say
`backend=openssl`, `anocrypto_used=false`, and KCMVP is not applicable to this
profile.

## Enterprise/AnoCrypto-C

Required before production:

- external SDK found and pinned
- exact dependency metadata recorded
- all required operation capabilities available
- Community-level positive and negative parity tests
- explicit capability failure tests
- no OpenSSL fallback tests
- Enterprise layer tests
- provider/key-boundary review
- release artifact and supply-chain evidence

Until complete:

- profile status is `development` or `integration`
- production packaging fails closed
- unsupported operations return capability-unavailable
- marketing must not claim full Community parity or KCMVP validation

## Required Release Metadata

```text
edition
product_profile
selected_adapter
backend_dependency
backend_version
backend_capabilities
key_provider
fallback_used
production_ready
kcmvp_status
kcmvp_evidence
```
