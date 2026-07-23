// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anopki/core/crl.hpp"
#include "anopki/core/csr.hpp"
#include "anopki/core/issue.hpp"
#include "anopki/core/ocsp.hpp"
#include "anopki/crypto/runtime.hpp"

#include <anocrypto/ac_module.h>

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <string_view>

namespace {

[[noreturn]] void fail() { throw std::runtime_error{"no-fallback assertion failed"}; }

template <typename Function>
void expect_error(Function function, std::string_view expected)
{
    try { function(); }
    catch (const std::runtime_error &error)
    {
        if (error.what() != expected)
            throw std::runtime_error{"expected " + std::string{expected} + ", got " + error.what()};
        return;
    }
    throw std::runtime_error{"expected error " + std::string{expected}};
}

std::string read(const std::filesystem::path &path)
{
    std::ifstream input{path, std::ios::binary};
    if (!input) fail();
    return {std::istreambuf_iterator<char>{input}, {}};
}

void set_environment(const char *name, const std::string &value)
{
#if defined(_WIN32)
    if (_putenv_s(name, value.c_str()) != 0) fail();
#else
    if (setenv(name, value.c_str(), 1) != 0) fail();
#endif
}

}  // namespace

int run(int argc, char **argv)
{
    if (argc != 2) fail();
    const auto &profile = anopki::crypto::selected_product_profile();
    const auto &backend = anopki::crypto::selected_backend();
    if (profile.id != "enterprise-anocrypto-c" || profile.selected_backend != "anocrypto-c" || profile.fallback_enabled ||
        backend.info().id != "anocrypto-c" || backend.info().capabilities.size() != 8U) fail();

    const std::filesystem::path evidence = std::filesystem::path{argv[1]} / "no-fallback-failure-evidence.json";
    std::error_code ignored;
    std::filesystem::remove(evidence, ignored);
    set_environment("ANOPKI_ENV", "development");
    set_environment("ANOPKI_CORE_SIGNING_EVIDENCE_FILE", evidence.string());
    expect_error([] { (void)anopki::core::inspect_csr_pem("malformed"); }, "csr.parse_failed");
    expect_error([] { (void)anopki::core::issue_certificate({}); }, "issue.csr_parse_failed");
    expect_error([] { (void)anopki::core::generate_crl({}); }, "crl.issuer_parse_failed");
    expect_error([] { (void)anopki::core::inspect_crl_pem("malformed"); }, "crl.parse_failed");
    expect_error([] { (void)anopki::core::inspect_crl_der("malformed"); }, "crl.parse_failed");
    expect_error([] { (void)anopki::core::inspect_ocsp_request_der("malformed"); }, "ocsp.parse_failed");
    expect_error([] { (void)anopki::core::inspect_ocsp_issuer_pem("malformed", "sha1"); }, "ocsp.issuer_parse_failed");
    expect_error([] { (void)anopki::core::generate_ocsp_response({}); }, "ocsp.parse_failed");
    expect_error([] { (void)anopki::core::validate_ocsp_responder("malformed", "malformed"); }, "ocsp.responder_invalid");

    const std::filesystem::path fixtures = std::filesystem::path{argv[1]} / "anocrypto-pki-algorithms";
    const std::string csr = read(fixtures / "valid-csr.pem");
    const std::string invalid_csr = read(fixtures / "invalid-csr.pem");
    const std::string issuer = read(fixtures / "valid-issuer.pem");
    anopki::core::IssueRequest request;
    request.csr_pem = csr;
    request.issuer_certificate_pem = issuer;
    request.signature_algorithm = "rsa_with_sha256";

    request.issuer_key_ref = "file:" + (fixtures / "missing-key.pem").string();
    expect_error([&] { (void)anopki::core::issue_certificate(request); }, "provider.key_not_found");
    request.issuer_key_ref = "file:" + (fixtures / "malformed-key.pem").string();
    expect_error([&] { (void)anopki::core::issue_certificate(request); }, "provider.key_parse_failed");
    request.issuer_key_ref = "file:" + (fixtures / "encrypted-key.pem").string();
    expect_error([&] { (void)anopki::core::issue_certificate(request); }, "provider.key_parse_failed");
    request.issuer_key_ref = "file:" + (fixtures / "weak-key.pem").string();
    expect_error([&] { (void)anopki::core::issue_certificate(request); }, "provider.algorithm_mismatch");
    request.issuer_key_ref = "file:" + (fixtures / "wrong-key.pem").string();
    expect_error([&] { (void)anopki::core::issue_certificate(request); }, "provider.key_binding_mismatch");
    request.issuer_key_ref = "kms:test";
    expect_error([&] { (void)anopki::core::issue_certificate(request); }, "provider.unavailable");
    request.issuer_key_ref = "file:" + (fixtures / "valid-key.pem").string();
    request.signature_algorithm = "ecdsa_with_sha256";
    expect_error([&] { (void)anopki::core::issue_certificate(request); }, "provider.algorithm_mismatch");
    request.signature_algorithm = "rsa_pss_sha256";
    expect_error([&] { (void)anopki::core::issue_certificate(request); }, "provider.algorithm_mismatch");

    set_environment("ANOPKI_ENV", "production");
    request.issuer_key_ref = "file:" + (fixtures / "never-opened.pem").string();
    request.signature_algorithm = "rsa_with_sha256";
    expect_error([&] { (void)anopki::core::issue_certificate(request); }, "provider.exportability_violation");
    set_environment("ANOPKI_ENV", "development");

    expect_error([&] { (void)anopki::core::inspect_csr_pem(invalid_csr); }, "csr.parse_failed");
    expect_error([&] { (void)anopki::core::inspect_ocsp_issuer_pem(issuer, "sha1-signature"); }, "ocsp.create_failed");

    request.issuer_key_ref = "file:" + (fixtures / "valid-key.pem").string();
    set_environment("ANOPKI_CORE_SIGNING_EVIDENCE_FILE", fixtures.string());
    expect_error([&] { (void)anopki::core::issue_certificate(request); }, "provider.evidence_failed");
    set_environment("ANOPKI_CORE_SIGNING_EVIDENCE_FILE", evidence.string());

    if (ano_crypto_module_shutdown() != ANO_CRYPTO_OK) fail();
    expect_error([&] { (void)anopki::core::inspect_csr_pem(csr); }, "csr.parse_failed");
    if (ano_crypto_module_init(nullptr) != ANO_CRYPTO_OK) fail();
    if (std::filesystem::exists(evidence)) fail();
    return 0;
}

int main(int argc, char **argv)
{
    try { return run(argc, argv); }
    catch (const std::exception &error)
    {
        std::cerr << "AnoCrypto no-fallback test failed: " << error.what() << '\n';
        return 1;
    }
}
