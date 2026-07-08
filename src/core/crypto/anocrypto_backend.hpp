// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#pragma once

#include "anopki/crypto/backend.hpp"

#include <string_view>

namespace anopki::crypto::enterprise {

class AnoCryptoBackend final : public Backend {
public:
    [[nodiscard]] std::string_view name() const noexcept override;
    [[nodiscard]] bool self_test_ok() const noexcept;
};

}  // namespace anopki::crypto::enterprise
