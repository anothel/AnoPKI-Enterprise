// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anopki/enterprise/edition.hpp"

#include <cassert>

int main() {
    assert(anopki::enterprise::edition_name() == "AnoPKI Enterprise");
    assert(anopki::enterprise::overlay_version() == "unreleased");
    assert(anopki::enterprise::overlay_status() == "private-alpha");
    const bool anocrypto = anopki::enterprise::active_crypto_backend() == "anocrypto-c";
    assert(anocrypto || anopki::enterprise::active_crypto_backend() == "openssl");
    assert(anopki::enterprise::experimental_crypto_backend() == "anocrypto-c");
    assert(anopki::enterprise::experimental_crypto_backend_status() == (anocrypto ? "configured" : "external_sdk_not_configured"));
    assert(anopki::enterprise::anocrypto_sdk_package() == "AnoCryptoC::AnoCryptoC");
    assert(anopki::enterprise::anocrypto_capability_status() == (anocrypto ? "pki_operations_complete" : "sdk_capabilities_unverified"));
    assert(anopki::enterprise::pki_parity_status() == (anocrypto ? "local_parity_verified" : "unsupported_pending"));
    assert(!anopki::enterprise::validated_mode());
    return 0;
}
