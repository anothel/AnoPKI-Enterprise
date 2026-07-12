// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anopki/crypto/runtime.hpp"
#include "anopki/enterprise/anocrypto_backend.hpp"

#include <cassert>

int main()
{
    const anopki::crypto::enterprise::AnoCryptoBackend backend;
    const anopki::crypto::BackendInfo &info = backend.info();
    assert(info.id == "anocrypto-c");
    assert(info.dependency == "AnoCrypto-C");
    assert(info.readiness == anopki::crypto::BackendReadiness::ready);
    assert(!info.dependency_version.empty());
    assert(!info.build_fingerprint.empty());
    assert(info.abi_version == 1U);
    assert(info.capabilities.empty());
    return 0;
}
