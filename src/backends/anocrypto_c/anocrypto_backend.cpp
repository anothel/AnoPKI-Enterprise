// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anopki/enterprise/anocrypto_backend.hpp"

#include "anopki/crypto/runtime.hpp"
#include "pki.hpp"

#include <anocrypto/anocrypto.h>

#include <array>
#include <string_view>

namespace anopki::crypto::enterprise {
namespace {

void require_ok(ano_crypto_status_t status, BackendErrorCode code)
{
    if (status != ANO_CRYPTO_OK)
    {
        throw BackendError{code};
    }
}

std::string fingerprint_sha256(std::string_view value)
{
    std::array<std::uint8_t, ANO_CRYPTO_HASH_SHA256_DIGEST_SIZE> digest{};
    std::size_t written = 0;
    require_ok(
        ano_crypto_hash_digest(
            ANO_CRYPTO_HASH_ALG_SHA256,
            reinterpret_cast<const std::uint8_t *>(value.data()),
            value.size(),
            digest.data(),
            digest.size(),
            &written),
        BackendErrorCode::initialization_failed);
    if (written != digest.size()) throw BackendError{BackendErrorCode::initialization_failed};
    constexpr char digits[] = "0123456789abcdef";
    std::string result = "sha256:";
    result.reserve(7U + digest.size() * 2U);
    for (const std::uint8_t byte : digest)
    {
        result.push_back(digits[byte >> 4U]);
        result.push_back(digits[byte & 0x0fU]);
    }
    return result;
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

    try
    {
        require_ok(ano_crypto_module_init(nullptr), BackendErrorCode::initialization_failed);
        module_initialized_ = true;

        ano_crypto_module_state_t state = ANO_CRYPTO_MODULE_STATE_UNINITIALIZED;
        require_ok(ano_crypto_module_get_state(&state), BackendErrorCode::initialization_failed);
        if (state != ANO_CRYPTO_MODULE_STATE_OPERATIONAL)
        {
            throw BackendError{BackendErrorCode::module_not_operational};
        }
    }
    catch (...)
    {
        if (module_initialized_)
        {
            (void)ano_crypto_module_shutdown();
            module_initialized_ = false;
        }
        throw;
    }

    info_.dependency_version = runtime_version;
    info_.build_fingerprint = fingerprint_sha256(fingerprint);
    info_.abi_version = identity.abi_version;
    info_.readiness = BackendReadiness::ready;
    info_.capabilities = {
        BackendCapability::csr_inspect,
        BackendCapability::certificate_issue,
        BackendCapability::crl_generate,
        BackendCapability::crl_inspect,
        BackendCapability::ocsp_request_inspect,
        BackendCapability::ocsp_issuer_inspect,
        BackendCapability::ocsp_response_generate,
        BackendCapability::ocsp_responder_validate,
    };
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

core::CsrInfo AnoCryptoBackend::inspect_csr_pem(const std::string &value) const { return pki::inspect_csr_pem(value); }
core::IssueResult AnoCryptoBackend::issue_certificate(const core::IssueRequest &value) const { return pki::issue_certificate(value); }
core::GenerateCRLResult AnoCryptoBackend::generate_crl(const core::GenerateCRLRequest &value) const { return pki::generate_crl(value); }
core::CRLInfo AnoCryptoBackend::inspect_crl_pem(const std::string &value) const { return pki::inspect_crl_pem(value); }
core::CRLInfo AnoCryptoBackend::inspect_crl_der(const std::string &value) const { return pki::inspect_crl_der(value); }
core::OCSPRequestInfo AnoCryptoBackend::inspect_ocsp_request_der(const std::string &value) const { return pki::inspect_ocsp_request_der(value); }
core::OCSPIssuerInfo AnoCryptoBackend::inspect_ocsp_issuer_pem(const std::string &value, const std::string &hash) const { return pki::inspect_ocsp_issuer_pem(value, hash); }
core::GenerateOCSPResponseResult AnoCryptoBackend::generate_ocsp_response(const core::GenerateOCSPResponseRequest &value) const { return pki::generate_ocsp_response(value); }
core::ValidateOCSPResponderResult AnoCryptoBackend::validate_ocsp_responder(const std::string &issuer, const std::string &responder) const { return pki::validate_ocsp_responder(issuer, responder); }

}  // namespace anopki::crypto::enterprise

namespace anopki::crypto {

const Backend &default_backend()
{
    static const enterprise::AnoCryptoBackend backend;
    return backend;
}

}  // namespace anopki::crypto
