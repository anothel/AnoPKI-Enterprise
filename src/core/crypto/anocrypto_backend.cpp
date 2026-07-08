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

}  // namespace anopki::crypto::enterprise
