# Enterprise Private Alpha Evidence

Status: local private-alpha engineering gate passes for the Enterprise/OpenSSL
profile. Hosted qualification is deferred because GitHub Actions blocked runner
allocation before code execution. All customer/production distribution remains
blocked.

## Version And Edition Model

| Field | Value |
| --- | --- |
| Community baseline | `ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc` |
| Base version | `0.1.0-alpha.0` |
| Edition | AnoPKI Enterprise |
| Enterprise overlay version | `unreleased` |
| Enterprise overlay status | `private-alpha` |
| Active backend | OpenSSL |
| AnoCrypto-C integration | External SDK adapter boundary; SDK not configured |
| AnoCrypto-C module self-test | Owned by the external SDK; not executed by this baseline |
| AnoCrypto-C capability set | Unverified until a pinned external SDK is supplied |
| PKI parity | Required operations remain `unsupported_pending` |
| Validated mode | `false` |
| KCMVP | Not validated; no evidence |
| Commercial license | Placeholder; distribution blocked |
| HSM/KMS/PKCS#11 | Not implemented |

The service `/version`, C++ library version, release workflow, and release
artifact names use the Community base version. Enterprise edition and adapter
status are separate metadata and do not create a production release version.

The current tree contains the shared Community/OpenSSL tree synchronized to the
reviewed baseline above. The hosted attempt recorded below remains historical
evidence for its exact older Enterprise commit and Community baseline. Durable
hosted CI evidence remains required before release review.

## Authorization Boundary Limitations

The synchronized exact-commit evidence preserves these known limitations for
E4-02B or a later enhanced-audit task:

- a successful read handler that creates no lifecycle audit event has no
  standalone authorization audit record,
- failure-audit persistence failure never converts a denied request to allow,
- evaluator timeout remains cooperative context cancellation, and
- the Enterprise authorization engine remains unconnected.

## AnoCrypto-C Integration Status

The old embedded AnoCrypto implementation and copied headers have been removed.
Enterprise now owns only an adapter source boundary that consumes the separately
installed CMake package `AnoCryptoC::AnoCryptoC`.

Current state:

- default Enterprise/OpenSSL configuration requires no AnoCrypto-C SDK,
- enabling the SDK integration without a package fails CMake configuration,
- a real SDK integration run has not yet been recorded,
- CSR inspection, certificate issuance, CRL generation, OCSP inspection,
  OCSP response generation, and responder validation remain unavailable through
  the AnoCrypto-C adapter,
- unavailable operations return `backend.capability_unavailable`,
- OpenSSL is never an automatic fallback from the AnoCrypto-C adapter.

## Local Verification Result

- Enterprise boundary, docs, version, release-evidence, service-contract,
  core-contract, and secret checks passed.
- Enterprise/OpenSSL CMake configure and build passed with OpenSSL 3.5.5 in the
  audit environment. The backend-neutral `anopki_core` archive had no OpenSSL
  symbols; the separated OpenSSL adapter owned the dependency.
- Enterprise/OpenSSL CTest: 15/15 tests passed after the explicit product-profile
  contract was added. The AnoCrypto-C parity test is part of the separately
  selected integration profile and remains explicitly skipped as
  `unsupported_pending`.
- Missing-SDK configuration was verified to fail when
  `ANOPKI_PRODUCT_PROFILE=enterprise-anocrypto-c` and `AnoCryptoC` was unavailable.
- The adapter compiled against an out-of-tree contract stub only to validate the
  CMake/C++ consumer boundary. That is not real AnoCrypto-C integration evidence.

The reviewed commit has been recorded. A real private CI run and a pinned real
AnoCrypto-C SDK run are still required for durable evidence. Commercial and
production distribution remain prohibited while the Enterprise license is a
placeholder.

## Hosted CI Attempt Evidence

This records an exact GitHub Actions attempt, not a code failure or successful
remote qualification. GitHub Actions reported all 17 jobs as failures after a
billing or spending-limit blocker prevented runner allocation. No hosted test
steps ran, and no artifacts or job logs were produced.

| Evidence field | Value |
| --- | --- |
| enterprise_commit | `22f5ebde6bfe2e3b40f874bb52dd5957152e4f22` |
| community_baseline_commit | `71f0e898c32a7d6e00d0725eeab6ca150ccaa0af` |
| workflow_name | `CI` |
| run_id | `29579430288` |
| run_url | `https://github.com/anothel/AnoPKI-Enterprise/actions/runs/29579430288` |
| event | `push` |
| head_sha | `22f5ebde6bfe2e3b40f874bb52dd5957152e4f22` |
| started_at | `2026-07-17T12:12:35Z` |
| completed_at | `2026-07-17T12:12:41Z` |
| job_count | `17` |
| runner_assigned | `false` |
| steps_executed | `0` |
| artifacts_created | `0` |
| job_logs_created | `0` |
| release_artifact_evidence | `false` |
| classification | `REMOTE_DEFERRED/BLOCKED_EXTERNAL` |
| blocker | `github_actions_billing_or_spending_limit_runner_allocation_blocked` |
| local_validation | `passed` |
| remote_validation | `not_run` |

The exact Enterprise commit remains remotely unverified. The qualification
fields below remain `PENDING` because the hosted attempt executed no code.

## Real Private CI Evidence

Do not replace `PENDING` values until a reviewed commit completes a real private
GitHub Actions run.

| Evidence field | Value |
| --- | --- |
| Reviewed commit SHA | `PENDING` |
| GitHub Actions run URL | `PENDING` |
| Community baseline commit | `ab9d76597df93ac1ac8b7938f4d25ba64f59f8dc` |
| Active OpenSSL version | `PENDING` |
| Enterprise metadata result | `PENDING` |
| AnoCrypto-C SDK integration result | `PENDING` |
| Pending parity result | `PENDING` |
| License status | Commercial placeholder; distribution blocked |
| KCMVP status | Not validated; no evidence |
| Provider status | HSM/KMS/PKCS#11 not implemented |
| Distribution prohibition | Customer and production distribution prohibited |

## Trusted SDK Evidence Lane

A protected manual workflow now exists for an exact AnoCrypto-C source commit.
No trusted run has been recorded yet. Until a reviewed run URL and generated
`anocrypto-sdk-evidence.json` are attached, the SDK integration evidence field
remains `PENDING`. The lane packages and hashes the installed SDK, binds the exact external and
Enterprise commits to the workflow run, and proves the Enterprise/AnoCrypto-C
artifact has no OpenSSL linkage or fallback. It does not change operation parity
from `unsupported_pending`.

| Field | Value |
| --- | --- |
| workflow_present | `true` |
| execution | `not_run` |
| status | `REMOTE_UNVERIFIED` |
| required_secret | `ANOCRYPTO_C_READ_TOKEN` |
| exact_sdk_commit_required | `true` |
| capacity_blocked | `true` |
| parity | `unsupported_pending` |
| production_ready | `false` |
| kcmvp_status | `not_validated` |
