// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anocrypto_backend.hpp"

#include "anocrypto/anocrypto.h"

#include <stdexcept>
#include <string>

namespace anopki::crypto::enterprise {
namespace {

[[noreturn]] void throw_pending()
{
    throw std::runtime_error{"anocrypto.backend_pending"};
}

}  // namespace

std::string_view AnoCryptoBackend::name() const noexcept {
    return "AnoCrypto skeleton";
}

bool AnoCryptoBackend::self_test_ok() const noexcept {
    return anocrypto_self_test() == ANOCRYPTO_OK;
}

std::string_view AnoCryptoBackend::approved_mode_status() const noexcept {
    return anocrypto_approved_mode_status();
}

std::string_view AnoCryptoBackend::deterministic_test_vector_status() const noexcept {
    return anocrypto_deterministic_test_vector_status();
}

std::string_view AnoCryptoBackend::production_status() const noexcept {
    return anocrypto_production_status();
}

core::CsrInfo AnoCryptoBackend::inspect_csr_pem(const std::string &) const {
    throw_pending();
}

core::IssueResult AnoCryptoBackend::issue_certificate(const core::IssueRequest &) const {
    throw_pending();
}

core::GenerateCRLResult AnoCryptoBackend::generate_crl(const core::GenerateCRLRequest &) const {
    throw_pending();
}

core::OCSPRequestInfo AnoCryptoBackend::inspect_ocsp_request_der(const std::string &) const {
    throw_pending();
}

core::GenerateOCSPResponseResult AnoCryptoBackend::generate_ocsp_response(const core::GenerateOCSPResponseRequest &) const {
    throw_pending();
}

core::ValidateOCSPResponderResult AnoCryptoBackend::validate_ocsp_responder(const std::string &, const std::string &) const {
    throw_pending();
}

}  // namespace anopki::crypto::enterprise
