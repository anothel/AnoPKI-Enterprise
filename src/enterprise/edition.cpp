// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anopki/enterprise/edition.hpp"

namespace anopki::enterprise {

std::string_view edition_name() noexcept { return "AnoPKI Enterprise"; }
std::string_view overlay_version() noexcept { return "unreleased"; }
std::string_view overlay_status() noexcept { return "private-alpha"; }
std::string_view active_crypto_backend() noexcept { return "openssl"; }
std::string_view experimental_crypto_backend() noexcept { return "anocrypto-c"; }
std::string_view experimental_crypto_backend_status() noexcept { return "external_sdk_not_configured"; }
std::string_view anocrypto_sdk_package() noexcept { return "AnoCryptoC::AnoCryptoC"; }
std::string_view anocrypto_capability_status() noexcept { return "sdk_capabilities_unverified"; }
std::string_view pki_parity_status() noexcept { return "unsupported_pending"; }
bool validated_mode() noexcept { return false; }
std::string_view crypto_backend_direction() noexcept { return experimental_crypto_backend(); }

}  // namespace anopki::enterprise
