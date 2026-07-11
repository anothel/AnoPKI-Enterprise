// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#pragma once

#include "anopki/crypto/backend.hpp"

#include <string_view>

namespace anopki::crypto::enterprise {

class AnoCryptoBackend final : public Backend {
public:
    [[nodiscard]] std::string_view name() const noexcept override;
    [[nodiscard]] bool self_test_ok() const noexcept;
    [[nodiscard]] std::string_view approved_mode_status() const noexcept;
    [[nodiscard]] std::string_view deterministic_test_vector_status() const noexcept;
    [[nodiscard]] std::string_view production_status() const noexcept;
    [[nodiscard]] core::CsrInfo inspect_csr_pem(const std::string &csr_pem) const override;
    [[nodiscard]] core::IssueResult issue_certificate(const core::IssueRequest &request) const override;
    [[nodiscard]] core::GenerateCRLResult generate_crl(const core::GenerateCRLRequest &request) const override;
    [[nodiscard]] core::OCSPRequestInfo inspect_ocsp_request_der(const std::string &request_der) const override;
    [[nodiscard]] core::GenerateOCSPResponseResult generate_ocsp_response(const core::GenerateOCSPResponseRequest &request) const override;
    [[nodiscard]] core::ValidateOCSPResponderResult validate_ocsp_responder(
        const std::string &issuer_certificate_pem,
        const std::string &responder_certificate_pem) const override;
};

}  // namespace anopki::crypto::enterprise
