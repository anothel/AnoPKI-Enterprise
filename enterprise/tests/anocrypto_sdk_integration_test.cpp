// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anopki/crypto/runtime.hpp"
#include "anopki/enterprise/anocrypto_backend.hpp"

#include <cassert>
#include <fstream>
#include <string>

namespace {
std::string escape_json(const std::string &value)
{
    std::string output;
    for (const char ch : value)
    {
        switch (ch)
        {
        case '\\': output += "\\\\"; break;
        case '"': output += "\\\""; break;
        case '\n': output += "\\n"; break;
        case '\r': output += "\\r"; break;
        case '\t': output += "\\t"; break;
        default: output += ch; break;
        }
    }
    return output;
}
}

int main(int argc, char **argv)
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

    if (argc == 2)
    {
        std::ofstream output{argv[1], std::ios::binary | std::ios::trunc};
        assert(output.good());
        output << "{\n"
               << "  \"backend_id\": \"" << escape_json(info.id) << "\",\n"
               << "  \"dependency\": \"" << escape_json(info.dependency) << "\",\n"
               << "  \"runtime_version\": \"" << escape_json(info.dependency_version) << "\",\n"
               << "  \"build_identity_abi\": " << info.abi_version << ",\n"
               << "  \"build_fingerprint\": \"" << escape_json(info.build_fingerprint) << "\",\n"
               << "  \"readiness\": \"ready\",\n"
               << "  \"capabilities\": []\n"
               << "}\n";
        assert(output.good());
    }
    return 0;
}
