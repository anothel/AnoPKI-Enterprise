# Enterprise Private Release Evidence

Each Enterprise release candidate should record both upstream Community evidence and
Enterprise overlay evidence.

## Required additions

| Area | Evidence |
| --- | --- |
| AnoCrypto | backend name, version, source hash, self-test result, fixture parity |
| Commercial overlay | source commit, license manifest, customer package manifest |
| Provider integrations | HSM/KMS/PKCS#11 readiness, non-exportability, audit metadata |
| Deployment adapters | target version, post-deploy check, rollback result |
| Compliance | KCMVP status wording, evidence pointers, customer restrictions |
