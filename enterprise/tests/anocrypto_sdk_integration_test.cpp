// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "backend_validation_checks.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <system_error>

namespace {
namespace fs = std::filesystem;

std::string escape_json(std::string_view value)
{
    constexpr char hex[] = "0123456789abcdef";
    std::string output;
    for (const unsigned char ch : value)
    {
        if (ch == '"' || ch == '\\') output += '\\';
        if (ch < 0x20)
        {
            output += "\\u00";
            output += hex[ch >> 4];
            output += hex[ch & 0x0f];
        }
        else
        {
            output += static_cast<char>(ch);
        }
    }
    return output;
}

struct StagedEvidence
{
    fs::path directory;
    fs::path file;
    bool owned{false};

    ~StagedEvidence()
    {
        if (!owned) return;
        std::error_code ignored;
        fs::remove(file, ignored);
        fs::remove(directory, ignored);
    }
};

void write_evidence(const fs::path &destination, const anopki::crypto::BackendInfo &info)
{
    const auto kind = fs::symlink_status(destination).type();
    if (kind != fs::file_type::not_found && kind != fs::file_type::regular)
        throw std::runtime_error{"runtime evidence destination is not a regular file"};

    auto staging = destination;
    staging += ".tmp";
    StagedEvidence staged{staging, staging / "runtime.json"};
    if (!fs::create_directory(staging))
        throw std::runtime_error{"runtime evidence staging directory already exists"};
    staged.owned = true;

    std::ofstream output{staged.file, std::ios::binary};
    if (!output) throw std::runtime_error{"could not open runtime evidence"};
    output << "{\n"
           << "  \"backend_id\": \"" << escape_json(info.id) << "\",\n"
           << "  \"dependency\": \"" << escape_json(info.dependency) << "\",\n"
           << "  \"runtime_version\": \"" << escape_json(info.dependency_version) << "\",\n"
           << "  \"build_identity_abi\": " << info.abi_version << ",\n"
           << "  \"build_fingerprint\": \"" << escape_json(info.build_fingerprint) << "\",\n"
           << "  \"readiness\": \"" << anopki::crypto::to_string(info.readiness) << "\",\n"
           << "  \"capabilities\": [";
    const char *separator = "";
    for (const auto capability : info.capabilities)
    {
        output << separator << '"' << anopki::crypto::to_string(capability) << '"';
        separator = ", ";
    }
    output << "]\n}\n";
    output.close();
    if (!output) throw std::runtime_error{"could not write runtime evidence"};
    fs::rename(staged.file, destination);
}
} // namespace

int main(int argc, char **argv)
{
    if (argc > 2 || (argc == 2 && argv[1][0] == '\0'))
    {
        std::cerr << "Usage: anocrypto_sdk_integration_test [runtime-evidence.json]\n";
        return 1;
    }

    try
    {
        const auto &profile = anopki::crypto::selected_product_profile();
        const auto &info = anopki::crypto::selected_backend().info();
        anopki::test::validate_backend(profile, info, "enterprise-anocrypto-c");
        if (argc == 2)
            write_evidence(argv[1], info);
    }
    catch (const std::exception &error)
    {
        std::cerr << "AnoCrypto SDK validation failed: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
