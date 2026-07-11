// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anopki/enterprise/anocrypto_backend.hpp"

#include <cassert>
#include <stdexcept>
#include <string_view>

int main() {
    anopki::crypto::enterprise::AnoCryptoBackend backend;
    assert(backend.name() == "anocrypto-c");
    assert(backend.dependency_info().operational);
    assert(!backend.dependency_info().runtime_version.empty());
    assert(!backend.dependency_info().build_fingerprint.empty());
    assert(backend.dependency_info().build_identity_abi == 1U);

    try {
        (void)backend.inspect_csr_pem("unused");
        assert(false);
    } catch (const std::runtime_error &error) {
        assert(std::string_view{error.what()} == "backend.capability_unavailable");
    }
    return 0;
}
