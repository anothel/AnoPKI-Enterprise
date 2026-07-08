// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#pragma once

#include <string_view>

namespace anopki::enterprise {

[[nodiscard]] std::string_view edition_name() noexcept;
[[nodiscard]] std::string_view crypto_backend_direction() noexcept;

}  // namespace anopki::enterprise
