// SPDX-License-Identifier: MPL-2.0
#include "backend_validation_checks.hpp"

#include <iostream>

int main()
{
    using namespace anopki::crypto;
    using anopki::test::validate_backend;
    constexpr std::string_view expected = "enterprise-anocrypto-c";
    const std::vector capabilities{
        BackendCapability::csr_inspect, BackendCapability::certificate_issue,
        BackendCapability::crl_generate, BackendCapability::crl_inspect,
        BackendCapability::ocsp_request_inspect, BackendCapability::ocsp_issuer_inspect,
        BackendCapability::ocsp_response_generate, BackendCapability::ocsp_responder_validate,
    };
    const ProductProfileInfo profile{std::string{expected}, "enterprise", "anocrypto-c", false, capabilities};
    const BackendInfo backend{"anocrypto-c", "AnoCrypto-C", "fixture-version",
                              "sha256:" + std::string(64, 'a'), 1U, BackendReadiness::ready, capabilities};
    try
    {
        validate_backend(profile, backend, expected);
        const auto reject = [&](std::string_view why, auto mutate) {
            auto changed_profile = profile;
            auto changed_backend = backend;
            mutate(changed_profile, changed_backend);
            try
            {
                validate_backend(changed_profile, changed_backend, expected);
            }
            catch (const std::runtime_error &error)
            {
                if (error.what() == why) return;
                throw;
            }
            throw std::runtime_error{"invalid fixture accepted: " + std::string{why}};
        };
        reject("product profile mismatch", [](auto &p, auto &) { p.id = "enterprise-openssl"; });
        reject("product profile mismatch", [](auto &p, auto &) { p.edition.clear(); });
        reject("product profile mismatch", [](auto &p, auto &) { p.selected_backend = "openssl"; });
        reject("fallback is enabled", [](auto &p, auto &) { p.fallback_enabled = true; });
        reject("backend identity mismatch", [](auto &, auto &b) { b.id = "openssl"; });
        reject("backend identity mismatch", [](auto &, auto &b) { b.dependency = "OpenSSL"; });
        reject("backend is not ready", [](auto &, auto &b) { b.readiness = BackendReadiness::error; });
        reject("backend is not ready", [](auto &, auto &b) { b.readiness = BackendReadiness::unavailable; });
        reject("backend runtime version is unavailable", [](auto &, auto &b) { b.dependency_version.clear(); });
        reject("backend identity ABI mismatch", [](auto &, auto &b) { b.abi_version = 2U; });
        reject("invalid backend fingerprint", [](auto &, auto &b) { b.build_fingerprint.erase(0, 7); });
        reject("invalid backend fingerprint", [](auto &, auto &b) { b.build_fingerprint.pop_back(); });
        reject("invalid backend fingerprint", [](auto &, auto &b) { b.build_fingerprint.back() = 'z'; });
        reject("product profile capability set mismatch", [](auto &p, auto &) { p.required_capabilities.pop_back(); });
        reject("backend capability set mismatch", [](auto &, auto &b) { b.capabilities.pop_back(); });
        reject("backend capability set mismatch", [](auto &, auto &b) { b.capabilities.back() = b.capabilities.front(); });
        reject("backend capability set mismatch", [](auto &, auto &b) { b.capabilities.back() = static_cast<BackendCapability>(-1); });
    }
    catch (const std::exception &error)
    {
        std::cerr << error.what() << '\n';
        return 1;
    }
    std::cout << "Backend validation accepted valid state and rejected all 17 invalid state fixtures\n";
    return 0;
}
