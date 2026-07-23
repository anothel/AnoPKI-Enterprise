// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#pragma once

#include "anopki/core/crl.hpp"
#include "anopki/core/csr.hpp"
#include "anopki/core/issue.hpp"
#include "anopki/core/ocsp.hpp"

#include <string>

namespace anopki::crypto::enterprise::pki {

[[nodiscard]] core::CsrInfo inspect_csr_pem(const std::string &csr_pem);
[[nodiscard]] core::IssueResult issue_certificate(const core::IssueRequest &request);
[[nodiscard]] core::GenerateCRLResult generate_crl(const core::GenerateCRLRequest &request);
[[nodiscard]] core::CRLInfo inspect_crl_pem(const std::string &crl_pem);
[[nodiscard]] core::CRLInfo inspect_crl_der(const std::string &crl_der);
[[nodiscard]] core::OCSPRequestInfo inspect_ocsp_request_der(const std::string &request_der);
[[nodiscard]] core::OCSPIssuerInfo inspect_ocsp_issuer_pem(
    const std::string &issuer_certificate_pem,
    const std::string &hash_algorithm);
[[nodiscard]] core::GenerateOCSPResponseResult generate_ocsp_response(
    const core::GenerateOCSPResponseRequest &request);
[[nodiscard]] core::ValidateOCSPResponderResult validate_ocsp_responder(
    const std::string &issuer_certificate_pem,
    const std::string &responder_certificate_pem);

}  // namespace anopki::crypto::enterprise::pki
