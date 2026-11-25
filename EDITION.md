# AnoPKI Enterprise Edition

This repository is the private **AnoPKI Enterprise** codebase.

Enterprise is intended to track the Community codebase while adding private
commercial overlays such as the AnoCrypto backend integration, productized
deployment adapters, advanced access control, compliance evidence, and commercial
packaging.

## Important status

OpenSSL remains the default Enterprise backend and compatibility baseline
(`enterprise-openssl`). Selecting `enterprise-anocrypto-c` builds the Enterprise
adapter against an external, installed AnoCrypto-C SDK. The selected profile
runs without an OpenSSL runtime fallback.

[Historical P3-11 evidence](docs/enterprise/anocrypto-handoff-current-status.md)
covers local operation parity, dependency purity, and no-fallback checks for
the recorded configuration. Native verification and protected workflow
verification with the original Q9 SDK remain `NOT_RUN`. Actual product
end-to-end acceptance remains `NOT_RUN` for each Enterprise profile.

The [backend profile release gates](docs/enterprise/backend-profile-release-gates.md)
track the remaining production and external qualification work. The AnoCrypto-C
profile records `production_ready=false` and `kcmvp_status=not_validated`.
