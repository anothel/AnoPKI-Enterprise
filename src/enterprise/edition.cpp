// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anopki/enterprise/edition.hpp"

namespace anopki::enterprise {

std::string_view edition_name() noexcept {
    return "AnoPKI Enterprise";
}

std::string_view overlay_version() noexcept {
    return "unreleased";
}

std::string_view overlay_status() noexcept {
    return "private-alpha";
}

std::string_view active_crypto_backend() noexcept {
    return "openssl";
}

std::string_view experimental_crypto_backend() noexcept {
    return "anocrypto";
}

std::string_view experimental_crypto_backend_status() noexcept {
    return "skeleton_pending";
}

std::string_view crypto_backend_direction() noexcept {
    return experimental_crypto_backend();
}

}  // namespace anopki::enterprise
