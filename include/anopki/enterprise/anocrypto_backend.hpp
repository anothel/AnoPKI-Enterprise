// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#pragma once

#include "anopki/crypto/backend.hpp"

#include <cstdint>
#include <string>
#include <string_view>

namespace anopki::crypto::enterprise {

struct AnoCryptoDependencyInfo {
    std::string runtime_version;
    std::string build_fingerprint;
    std::uint32_t build_identity_abi{0};
    bool operational{false};
};

// Adapter for the separately built AnoCrypto-C SDK.
// This class contains no cryptographic implementation and never falls back to OpenSSL.
class AnoCryptoBackend final : public Backend {
public:
    AnoCryptoBackend();
    ~AnoCryptoBackend() override;

    AnoCryptoBackend(const AnoCryptoBackend &) = delete;
    AnoCryptoBackend &operator=(const AnoCryptoBackend &) = delete;

    [[nodiscard]] std::string_view name() const noexcept override;
    [[nodiscard]] const AnoCryptoDependencyInfo &dependency_info() const noexcept;

    [[nodiscard]] core::CsrInfo inspect_csr_pem(const std::string &csr_pem) const override;
    [[nodiscard]] core::IssueResult issue_certificate(const core::IssueRequest &request) const override;
    [[nodiscard]] core::GenerateCRLResult generate_crl(const core::GenerateCRLRequest &request) const override;
    [[nodiscard]] core::CRLInfo inspect_crl_pem(const std::string &crl_pem) const override;
    [[nodiscard]] core::CRLInfo inspect_crl_der(const std::string &crl_der) const override;
    [[nodiscard]] core::OCSPRequestInfo inspect_ocsp_request_der(const std::string &request_der) const override;
    [[nodiscard]] core::OCSPIssuerInfo inspect_ocsp_issuer_pem(
        const std::string &issuer_certificate_pem,
        const std::string &hash_algorithm) const override;
    [[nodiscard]] core::GenerateOCSPResponseResult generate_ocsp_response(const core::GenerateOCSPResponseRequest &request) const override;
    [[nodiscard]] core::ValidateOCSPResponderResult validate_ocsp_responder(
        const std::string &issuer_certificate_pem,
        const std::string &responder_certificate_pem) const override;

private:
    AnoCryptoDependencyInfo dependency_info_{};
    bool module_initialized_{false};
};

}  // namespace anopki::crypto::enterprise
