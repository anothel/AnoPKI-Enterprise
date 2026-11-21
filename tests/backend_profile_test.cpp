// SPDX-License-Identifier: MPL-2.0
#include "backend_validation_checks.hpp"

#include <iostream>

int main()
{
    try
    {
        const auto &profile = anopki::crypto::selected_product_profile();
        const auto &info = anopki::crypto::selected_backend().info();
        anopki::test::validate_backend(profile, info, ANOPKI_EXPECTED_TEST_PROFILE);
    }
    catch (const std::exception &error)
    {
        std::cerr << "Backend profile validation failed: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
