// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anopki/enterprise/edition.hpp"

namespace anopki::enterprise {

std::string_view edition_name() noexcept {
    return "AnoPKI Enterprise";
}

std::string_view crypto_backend_direction() noexcept {
    return "AnoCrypto backend direction with OpenSSL parity gate";
}

}  // namespace anopki::enterprise
