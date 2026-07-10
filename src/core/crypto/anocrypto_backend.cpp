// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anocrypto_backend.hpp"

#include "anocrypto/anocrypto.h"

namespace anopki::crypto::enterprise {

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

}  // namespace anopki::crypto::enterprise
