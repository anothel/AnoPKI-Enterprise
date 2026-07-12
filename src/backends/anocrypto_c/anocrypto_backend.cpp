// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anopki/enterprise/anocrypto_backend.hpp"

#include <anocrypto/anocrypto.h>

#include <stdexcept>

namespace anopki::crypto::enterprise {
namespace {

[[noreturn]] void fail(std::string_view code) {
    throw std::runtime_error{std::string{code}};
}

void require_ok(ano_crypto_status_t status, std::string_view code) {
    if (status != ANO_CRYPTO_OK) {
        fail(code);
    }
}

[[noreturn]] void capability_unavailable() {
    fail("backend.capability_unavailable");
}

}  // namespace

AnoCryptoBackend::AnoCryptoBackend() {
    const char *runtime_version = nullptr;
    require_ok(ano_crypto_version_string(&runtime_version), "backend.version_incompatible");
    if (runtime_version == nullptr || *runtime_version == '\0') {
        fail("backend.version_incompatible");
    }

    ano_crypto_build_identity_t identity{};
    require_ok(ano_crypto_build_identity(&identity), "backend.version_incompatible");
    if (identity.abi_version != ANO_CRYPTO_BUILD_IDENTITY_ABI_VERSION) {
        fail("backend.version_incompatible");
    }

    const char *fingerprint = nullptr;
    require_ok(ano_crypto_build_fingerprint(&fingerprint), "backend.version_incompatible");
    if (fingerprint == nullptr || *fingerprint == '\0') {
        fail("backend.version_incompatible");
    }

    require_ok(ano_crypto_module_init(nullptr), "backend.initialization_failed");
    module_initialized_ = true;

    ano_crypto_module_state_t state = ANO_CRYPTO_MODULE_STATE_UNINITIALIZED;
    require_ok(ano_crypto_module_get_state(&state), "backend.initialization_failed");
    if (state != ANO_CRYPTO_MODULE_STATE_OPERATIONAL) {
        fail("backend.module_not_operational");
    }

    dependency_info_.runtime_version = runtime_version;
    dependency_info_.build_fingerprint = fingerprint;
    dependency_info_.build_identity_abi = identity.abi_version;
    dependency_info_.operational = true;
}

AnoCryptoBackend::~AnoCryptoBackend() {
    if (module_initialized_) {
        (void)ano_crypto_module_shutdown();
    }
}

std::string_view AnoCryptoBackend::name() const noexcept {
    return "anocrypto-c";
}

const AnoCryptoDependencyInfo &AnoCryptoBackend::dependency_info() const noexcept {
    return dependency_info_;
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
