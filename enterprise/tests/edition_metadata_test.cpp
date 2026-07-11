// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anopki/enterprise/edition.hpp"

#include <cassert>

int main()
{
    assert(anopki::enterprise::edition_name() == "AnoPKI Enterprise");
    assert(anopki::enterprise::overlay_version() == "unreleased");
    assert(anopki::enterprise::overlay_status() == "private-alpha");
    assert(anopki::enterprise::active_crypto_backend() == "openssl");
    assert(anopki::enterprise::experimental_crypto_backend() == "anocrypto");
    assert(anopki::enterprise::experimental_crypto_backend_status() == "skeleton_pending");
    return 0;
}
