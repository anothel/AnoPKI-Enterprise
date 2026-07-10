// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anocrypto_backend.hpp"

#include <cassert>
#include <string_view>

int main() {
    const anopki::crypto::enterprise::AnoCryptoBackend backend;
    assert(backend.name() == std::string_view{"AnoCrypto skeleton"});
    assert(backend.self_test_ok());
    assert(backend.approved_mode_status() == std::string_view{"placeholder-not-approved"});
    assert(backend.deterministic_test_vector_status() == std::string_view{"placeholder-pending"});
    assert(backend.production_status() == std::string_view{"not-production-complete"});
}
