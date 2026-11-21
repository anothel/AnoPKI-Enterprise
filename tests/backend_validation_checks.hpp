// SPDX-License-Identifier: MPL-2.0
#pragma once

#include "anopki/crypto/runtime.hpp"

#include <algorithm>
#include <array>
#include <stdexcept>

namespace anopki::test {

inline void validate_backend(const crypto::ProductProfileInfo &profile, const crypto::BackendInfo &info,
                             std::string_view expected_profile)
{
    using crypto::BackendCapability;
    constexpr std::array required{
        BackendCapability::csr_inspect,
        BackendCapability::certificate_issue,
        BackendCapability::crl_generate,
        BackendCapability::crl_inspect,
        BackendCapability::ocsp_request_inspect,
        BackendCapability::ocsp_issuer_inspect,
        BackendCapability::ocsp_response_generate,
        BackendCapability::ocsp_responder_validate,
    };

    if (expected_profile != "enterprise-anocrypto-c" && expected_profile != "enterprise-openssl")
        throw std::runtime_error{"unexpected configured test profile"};
    const bool expects_anocrypto = expected_profile == "enterprise-anocrypto-c";
    const std::string_view expected_backend = expects_anocrypto ? "anocrypto-c" : "openssl";
    const std::string_view expected_dependency = expects_anocrypto ? "AnoCrypto-C" : "OpenSSL";
    if (profile.id != expected_profile || profile.edition != "enterprise" || profile.selected_backend != expected_backend)
        throw std::runtime_error{"product profile mismatch"};
    if (profile.fallback_enabled)
        throw std::runtime_error{"fallback is enabled"};
    if (info.id != expected_backend || info.dependency != expected_dependency)
        throw std::runtime_error{"backend identity mismatch"};
    if (info.readiness != crypto::BackendReadiness::ready)
        throw std::runtime_error{"backend is not ready"};
    if (info.dependency_version.empty() || info.dependency_version == "unknown")
        throw std::runtime_error{"backend runtime version is unavailable"};
    if (info.abi_version != 1U)
        throw std::runtime_error{"backend identity ABI mismatch"};

    constexpr std::string_view prefix = "sha256:";
    const std::string_view fingerprint = info.build_fingerprint;
    if (!fingerprint.starts_with(prefix) || fingerprint.size() != prefix.size() + 64U ||
        fingerprint.substr(prefix.size()).find_first_not_of("0123456789abcdef") != std::string_view::npos)
        throw std::runtime_error{"invalid backend fingerprint"};

    if (!std::ranges::is_permutation(profile.required_capabilities, required))
        throw std::runtime_error{"product profile capability set mismatch"};
    if (!std::ranges::is_permutation(info.capabilities, required))
        throw std::runtime_error{"backend capability set mismatch"};
}

} // namespace anopki::test
