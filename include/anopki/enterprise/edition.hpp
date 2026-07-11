// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#pragma once

#include <string_view>

namespace anopki::enterprise {

[[nodiscard]] std::string_view edition_name() noexcept;
[[nodiscard]] std::string_view overlay_version() noexcept;
[[nodiscard]] std::string_view overlay_status() noexcept;
[[nodiscard]] std::string_view active_crypto_backend() noexcept;
[[nodiscard]] std::string_view experimental_crypto_backend() noexcept;
[[nodiscard]] std::string_view experimental_crypto_backend_status() noexcept;
[[nodiscard]] std::string_view anocrypto_sdk_package() noexcept;
[[nodiscard]] std::string_view anocrypto_capability_status() noexcept;
[[nodiscard]] std::string_view pki_parity_status() noexcept;
[[nodiscard]] bool validated_mode() noexcept;
[[nodiscard]] std::string_view crypto_backend_direction() noexcept;

}  // namespace anopki::enterprise
