# Enterprise Private Alpha Checklist

> Historical pre-P3-11 checklist. See `anocrypto-handoff-current-status.md` for
> the current local AnoCrypto-C parity state. Production/customer gates below
> remain in force.

This checklist gates internal-only Enterprise alpha builds. Passing it does not
mean AnoCrypto, KCMVP, SSO/RBAC, HSM/KMS, deployment adapters, or commercial
packaging are production-ready.

## Required Gates

| Gate | Required evidence | Alpha status |
| --- | --- | --- |
| Community upstream sync | `community` remote reviewed, `community/main` fetched, shared-file conflicts resolved toward Community unless an Enterprise overlay reason is documented. | Required before each alpha cut. |
| Community baseline tests | Community checkout passes docs validation, boundary validation, CMake build, CTest, and Go tests applicable to the alpha source revision. | Required before each alpha cut. |
| Enterprise boundary validation | `python scripts\validate-enterprise-boundary.py` exits `enterprise boundary ok`. | Required. |
| Enterprise docs validation | `python scripts\validate-docs.py` exits `docs ok`. | Required. |
| Secret scan | `python scripts\security-baseline-scan.py` exits `secret baseline scan ok`; no customer secrets, private keys, cloud tokens, or production credentials are committed. | Required. |
| AnoCrypto-C SDK boundary | Default build requires no SDK. Enabling `-DANOPKI_PRODUCT_PROFILE=enterprise-anocrypto-c` requires a real installed `AnoCryptoC::AnoCryptoC` package and runs `anocrypto_sdk_integration`. | External SDK adapter only; no embedded algorithms. |
| Backend parity | OpenSSL parity fixture reports `semantic_equal`; AnoCrypto reports `unsupported_pending` for all five PKI operations. | AnoCrypto PKI pending. |
| License notice review | `ENTERPRISE-LICENSE-NOTICE.md` reviewed for the alpha package; upstream MPL-2.0 notices remain intact. | Required; commercial terms still placeholder. |
| Unsupported features list | Alpha notes list every unavailable Enterprise feature. | Required. |
| KCMVP claim status | KCMVP wording is target, planned, preparation, or readiness only unless approved certification evidence exists. | No certification claim. |
| HSM/KMS/PKCS#11 status | Real providers are not required for alpha; mock/skeleton paths only unless explicit provider evidence exists. | Not implemented. |

## Unsupported In Private Alpha

- AnoCrypto PKI operation backend: unsupported, not implemented.
- KCMVP cryptographic module approval: unsupported; no evidence.
- SSO/OIDC/SAML and RBAC/ABAC operator directory integration.
- Real HSM, KMS, and PKCS#11 provider implementations.
- Productized deployment adapters and rollback automation.
- SIEM export, tamper-evident audit storage, and compliance reports.
- Reviewed commercial license terms and customer packaging.

## Command Set

Run from `anopki-enterprise` unless noted:

```powershell
python scripts\validate-enterprise-boundary.py
python scripts\validate-docs.py
python scripts\security-baseline-scan.py
cd service
go test ./...
cd ..
cmake -S . -B .tmp\private-alpha-cmake -DOPENSSL_ROOT_DIR="$env:OPENSSL_ROOT_DIR"
cmake --build .tmp\private-alpha-cmake --config Debug
ctest --test-dir .tmp\private-alpha-cmake -C Debug --output-on-failure

# Optional trusted SDK integration lane only:
cmake -S . -B .tmp\anocrypto-sdk-cmake -DANOPKI_PRODUCT_PROFILE=enterprise-anocrypto-c -DANOCRYPTO_SDK_ROOT="<installed-sdk-prefix>"
cmake --build .tmp\anocrypto-sdk-cmake --config Debug --target anocrypto_sdk_integration_test
ctest --test-dir .tmp\anocrypto-sdk-cmake -C Debug -L anocrypto_sdk_integration --output-on-failure
```

Run from `anopki-community` for upstream baseline before cutting an Enterprise
alpha:

```powershell
python scripts\validate-community-boundary.py
python scripts\validate-docs.py
cd service
go test ./...
cd ..
cmake -S . -B .tmp\community-alpha-cmake -DOPENSSL_ROOT_DIR="$env:OPENSSL_ROOT_DIR"
cmake --build .tmp\community-alpha-cmake --config Debug
ctest --test-dir .tmp\community-alpha-cmake -C Debug --output-on-failure
```

Remove `.tmp\private-alpha-cmake` and `.tmp\community-alpha-cmake` after local
runs. Do not package generated build directories, caches, keys, credentials, or
private customer material.
