# AnoCrypto Integration Skeleton

This directory is a placeholder for the C99 AnoCrypto module and test harness.

It exists to give the Enterprise repository a stable integration boundary while the
real AnoCrypto implementation and certification work proceed separately.

Enable the skeleton build with `-DANOPKI_ENABLE_ANOCRYPTO_BACKEND=ON`. The option
is off by default; OpenSSL remains the compatibility backend until parity evidence
exists.

## Rules

- Do not claim KCMVP validation from this skeleton.
- Treat `placeholder-not-approved`, `placeholder-pending`, and
  `not-production-complete` self-test metadata as blockers for production use.
- Keep the public C ABI stable once real consumers appear.
- Add test vectors and self-tests before connecting signing paths.
- Keep KCMVP submission evidence in private docs until it is approved for release.
