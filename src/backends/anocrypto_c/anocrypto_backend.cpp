// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anopki/enterprise/anocrypto_backend.hpp"

#include "anopki/crypto/runtime.hpp"

#include <anocrypto/anocrypto.h>

namespace anopki::crypto::enterprise {
namespace {

void require_ok(ano_crypto_status_t status, BackendErrorCode code)
{
    if (status != ANO_CRYPTO_OK)
    {
        throw BackendError{code};
    }
}

[[noreturn]] void capability_unavailable()
{
    throw BackendError{BackendErrorCode::capability_unavailable};
}

}  // namespace

AnoCryptoBackend::AnoCryptoBackend()
{
    info_.id = "anocrypto-c";
    info_.dependency = "AnoCrypto-C";
    info_.readiness = BackendReadiness::unavailable;

    const char *runtime_version = nullptr;
    require_ok(ano_crypto_version_string(&runtime_version), BackendErrorCode::version_incompatible);
    if (runtime_version == nullptr || *runtime_version == '\0')
    {
        throw BackendError{BackendErrorCode::version_incompatible};
    }

    ano_crypto_build_identity_t identity{};
    require_ok(ano_crypto_build_identity(&identity), BackendErrorCode::version_incompatible);
    if (identity.abi_version != ANO_CRYPTO_BUILD_IDENTITY_ABI_VERSION)
    {
        throw BackendError{BackendErrorCode::version_incompatible};
    }

    const char *fingerprint = nullptr;
    require_ok(ano_crypto_build_fingerprint(&fingerprint), BackendErrorCode::version_incompatible);
    if (fingerprint == nullptr || *fingerprint == '\0')
    {
        throw BackendError{BackendErrorCode::version_incompatible};
    }

    require_ok(ano_crypto_module_init(nullptr), BackendErrorCode::initialization_failed);
    module_initialized_ = true;

    ano_crypto_module_state_t state = ANO_CRYPTO_MODULE_STATE_UNINITIALIZED;
    require_ok(ano_crypto_module_get_state(&state), BackendErrorCode::initialization_failed);
    if (state != ANO_CRYPTO_MODULE_STATE_OPERATIONAL)
    {
        throw BackendError{BackendErrorCode::module_not_operational};
    }

    info_.dependency_version = runtime_version;
    info_.build_fingerprint = fingerprint;
    info_.abi_version = identity.abi_version;
    info_.readiness = BackendReadiness::ready;
    // The inspected AnoCrypto-C SDK does not yet expose the asymmetric/PKI
    // operations required by the operation-level AnoPKI backend contract.
    info_.capabilities.clear();
}

AnoCryptoBackend::~AnoCryptoBackend()
{
    if (module_initialized_)
    {
        (void)ano_crypto_module_shutdown();
    }
}

const BackendInfo &AnoCryptoBackend::info() const noexcept
{
    return info_;
}

core::CsrInfo AnoCryptoBackend::inspect_csr_pem(const std::string &) const { capability_unavailable(); }
core::IssueResult AnoCryptoBackend::issue_certificate(const core::IssueRequest &) const { capability_unavailable(); }
core::GenerateCRLResult AnoCryptoBackend::generate_crl(const core::GenerateCRLRequest &) const { capability_unavailable(); }
core::CRLInfo AnoCryptoBackend::inspect_crl_pem(const std::string &) const { capability_unavailable(); }
core::CRLInfo AnoCryptoBackend::inspect_crl_der(const std::string &) const { capability_unavailable(); }
core::OCSPRequestInfo AnoCryptoBackend::inspect_ocsp_request_der(const std::string &) const { capability_unavailable(); }
core::OCSPIssuerInfo AnoCryptoBackend::inspect_ocsp_issuer_pem(const std::string &, const std::string &) const { capability_unavailable(); }
core::GenerateOCSPResponseResult AnoCryptoBackend::generate_ocsp_response(const core::GenerateOCSPResponseRequest &) const { capability_unavailable(); }
core::ValidateOCSPResponderResult AnoCryptoBackend::validate_ocsp_responder(const std::string &, const std::string &) const { capability_unavailable(); }

}  // namespace anopki::crypto::enterprise

namespace anopki::crypto {

const Backend &default_backend()
{
    static const enterprise::AnoCryptoBackend backend;
    return backend;
}

}  // namespace anopki::crypto
