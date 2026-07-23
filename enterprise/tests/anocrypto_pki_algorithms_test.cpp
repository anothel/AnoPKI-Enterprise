// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anopki/core/csr.hpp"
#include "anopki/core/issue.hpp"

#include <openssl/bio.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/rsa.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <stdexcept>
#include <string>
#include <string_view>

namespace {

template <typename T, void (*Free)(T *)>
struct Deleter { void operator()(T *value) const noexcept { Free(value); } };
struct BioDeleter { void operator()(BIO *value) const noexcept { BIO_free(value); } };
using BioPtr = std::unique_ptr<BIO, BioDeleter>;
using KeyPtr = std::unique_ptr<EVP_PKEY, Deleter<EVP_PKEY, EVP_PKEY_free>>;
using ReqPtr = std::unique_ptr<X509_REQ, Deleter<X509_REQ, X509_REQ_free>>;
using CertPtr = std::unique_ptr<X509, Deleter<X509, X509_free>>;
using ExtPtr = std::unique_ptr<X509_EXTENSION, Deleter<X509_EXTENSION, X509_EXTENSION_free>>;

[[noreturn]] void fail(std::string_view message) { throw std::runtime_error{std::string{message}}; }
void require(bool condition, std::string_view message) { if (!condition) fail(message); }

KeyPtr rsa_key(int bits = 2048)
{
    std::unique_ptr<EVP_PKEY_CTX, Deleter<EVP_PKEY_CTX, EVP_PKEY_CTX_free>> context{EVP_PKEY_CTX_new_id(EVP_PKEY_RSA, nullptr)};
    require(context && EVP_PKEY_keygen_init(context.get()) == 1 && EVP_PKEY_CTX_set_rsa_keygen_bits(context.get(), bits) == 1, "RSA setup failed");
    EVP_PKEY *raw = nullptr;
    require(EVP_PKEY_keygen(context.get(), &raw) == 1, "RSA generation failed");
    return KeyPtr{raw};
}

KeyPtr ec_key(int curve = NID_X9_62_prime256v1)
{
    std::unique_ptr<EVP_PKEY_CTX, Deleter<EVP_PKEY_CTX, EVP_PKEY_CTX_free>> context{EVP_PKEY_CTX_new_id(EVP_PKEY_EC, nullptr)};
    require(context && EVP_PKEY_keygen_init(context.get()) == 1 && EVP_PKEY_CTX_set_ec_paramgen_curve_nid(context.get(), curve) == 1, "EC setup failed");
    EVP_PKEY *raw = nullptr;
    require(EVP_PKEY_keygen(context.get(), &raw) == 1, "EC generation failed");
    return KeyPtr{raw};
}

std::string bio_string(BIO *bio)
{
    char *data = nullptr;
    const long size = BIO_get_mem_data(bio, &data);
    require(size > 0 && data != nullptr, "BIO output failed");
    return {data, static_cast<std::size_t>(size)};
}

void set_name(X509_NAME *name, const char *common_name)
{
    require(name != nullptr && X509_NAME_add_entry_by_txt(name, "CN", MBSTRING_ASC,
        reinterpret_cast<const unsigned char *>(common_name), -1, -1, 0) == 1, "name setup failed");
}

ReqPtr csr(EVP_PKEY *public_key, EVP_PKEY *signing_key = nullptr)
{
    ReqPtr request{X509_REQ_new()};
    require(request && X509_REQ_set_version(request.get(), 0) == 1, "CSR setup failed");
    set_name(X509_REQ_get_subject_name(request.get()), "leaf");
    require(X509_REQ_set_pubkey(request.get(), public_key) == 1, "CSR public key failed");
    STACK_OF(X509_EXTENSION) *extensions = sk_X509_EXTENSION_new_null();
    require(extensions != nullptr, "CSR extension stack failed");
    X509V3_CTX context{};
    X509V3_set_ctx_nodb(&context);
    ExtPtr san{X509V3_EXT_conf_nid(nullptr, &context, NID_subject_alt_name, "DNS:leaf.example.test,IP:127.0.0.1")};
    require(san && sk_X509_EXTENSION_push(extensions, san.release()) == 1 && X509_REQ_add_extensions(request.get(), extensions) == 1,
        "CSR extensions failed");
    sk_X509_EXTENSION_pop_free(extensions, X509_EXTENSION_free);
    require(X509_REQ_sign(request.get(), signing_key == nullptr ? public_key : signing_key, EVP_sha256()) > 0, "CSR sign failed");
    return request;
}

std::string csr_pem(X509_REQ *request)
{
    BioPtr bio{BIO_new(BIO_s_mem())};
    require(bio && PEM_write_bio_X509_REQ(bio.get(), request) == 1, "CSR PEM failed");
    return bio_string(bio.get());
}

void add_extension(X509 *certificate, X509 *issuer, int nid, const char *value)
{
    X509V3_CTX context{};
    X509V3_set_ctx_nodb(&context);
    X509V3_set_ctx(&context, issuer, certificate, nullptr, nullptr, 0);
    ExtPtr extension{X509V3_EXT_conf_nid(nullptr, &context, nid, value)};
    require(extension && X509_add_ext(certificate, extension.get(), -1) == 1, "certificate extension failed");
}

CertPtr ca_certificate(EVP_PKEY *key, const char *name)
{
    CertPtr certificate{X509_new()};
    require(certificate && X509_set_version(certificate.get(), 2) == 1 && ASN1_INTEGER_set(X509_get_serialNumber(certificate.get()), 1) == 1,
        "CA setup failed");
    X509_gmtime_adj(X509_getm_notBefore(certificate.get()), -60);
    X509_gmtime_adj(X509_getm_notAfter(certificate.get()), 86400);
    set_name(X509_get_subject_name(certificate.get()), name);
    require(X509_set_issuer_name(certificate.get(), X509_get_subject_name(certificate.get())) == 1 && X509_set_pubkey(certificate.get(), key) == 1,
        "CA identity failed");
    add_extension(certificate.get(), certificate.get(), NID_basic_constraints, "critical,CA:TRUE");
    add_extension(certificate.get(), certificate.get(), NID_key_usage, "critical,keyCertSign,cRLSign,digitalSignature");
    require(X509_sign(certificate.get(), key, EVP_sha256()) > 0, "CA sign failed");
    return certificate;
}

std::string certificate_pem(X509 *certificate)
{
    BioPtr bio{BIO_new(BIO_s_mem())};
    require(bio && PEM_write_bio_X509(bio.get(), certificate) == 1, "certificate PEM failed");
    return bio_string(bio.get());
}

void write_key(const std::filesystem::path &path, EVP_PKEY *key)
{
    BioPtr bio{BIO_new_file(path.string().c_str(), "wb")};
    require(bio && PEM_write_bio_PrivateKey(bio.get(), key, nullptr, nullptr, 0, nullptr, nullptr) == 1, "key write failed");
}

void write_encrypted_key(const std::filesystem::path &path, EVP_PKEY *key)
{
    BioPtr bio{BIO_new_file(path.string().c_str(), "wb")};
    const unsigned char password[] = "test-only-password";
    require(bio && PEM_write_bio_PrivateKey(bio.get(), key, EVP_aes_256_cbc(), password,
        static_cast<int>(sizeof(password) - 1U), nullptr, nullptr) == 1, "encrypted key write failed");
}

void write_text(const std::filesystem::path &path, std::string_view value)
{
    std::ofstream output{path, std::ios::binary | std::ios::trunc};
    output.write(value.data(), static_cast<std::streamsize>(value.size()));
    require(output.good(), "fixture write failed");
}

CertPtr parse_certificate(std::string_view pem)
{
    BioPtr bio{BIO_new_mem_buf(pem.data(), static_cast<int>(pem.size()))};
    return CertPtr{bio ? PEM_read_bio_X509(bio.get(), nullptr, nullptr, nullptr) : nullptr};
}

void expect_error(const auto &function, std::string_view code)
{
    try { function(); }
    catch (const std::runtime_error &error) { require(error.what() == code, "wrong stable error"); return; }
    fail("expected failure");
}

void issue_and_verify(
    const std::filesystem::path &directory,
    EVP_PKEY *leaf_key,
    EVP_PKEY *issuer_key,
    std::string_view signature_algorithm,
    int signature_nid,
    std::string_view suffix)
{
    ReqPtr request_csr = csr(leaf_key);
    CertPtr issuer = ca_certificate(issuer_key, "Algorithm Matrix CA");
    const std::filesystem::path key_path = directory / ("issuer-" + std::string{suffix} + ".pem");
    write_key(key_path, issuer_key);
    anopki::core::IssueRequest request;
    request.csr_pem = csr_pem(request_csr.get());
    request.issuer_certificate_pem = certificate_pem(issuer.get());
    request.issuer_key_ref = "file:" + key_path.string();
    request.signature_algorithm = std::string{signature_algorithm};
    request.basic_constraints_critical = true;
    request.key_usage_critical = true;
    request.key_usage = {"digital_signature"};
    request.extended_key_usage = {"server_auth"};
    request.dns_names = {"leaf.example.test"};
    const anopki::core::IssueResult result = anopki::core::issue_certificate(request);
    CertPtr issued = parse_certificate(result.certificate_pem);
    require(issued && X509_get_signature_nid(issued.get()) == signature_nid, "issued signature algorithm mismatch");
    require(X509_verify(issued.get(), issuer_key) == 1, "issued signature verification failed");
}

}  // namespace

int main(int argc, char **argv)
{
    try
    {
        require(argc == 2, "expected build directory");
        const std::filesystem::path directory = std::filesystem::path{argv[1]} / "anocrypto-pki-algorithms";
        std::filesystem::create_directories(directory);
        const std::filesystem::path evidence_path = directory / "signing-evidence.json";
#if defined(_WIN32)
        _putenv_s("ANOPKI_ENV", "development");
        _putenv_s("ANOPKI_CORE_SIGNING_EVIDENCE_FILE", evidence_path.string().c_str());
#else
        setenv("ANOPKI_ENV", "development", 1);
        setenv("ANOPKI_CORE_SIGNING_EVIDENCE_FILE", evidence_path.string().c_str(), 1);
#endif
        KeyPtr rsa = rsa_key();
        KeyPtr ec = ec_key();
        const anopki::core::CsrInfo rsa_info = anopki::core::inspect_csr_pem(csr_pem(csr(rsa.get()).get()));
        const anopki::core::CsrInfo ec_info = anopki::core::inspect_csr_pem(csr_pem(csr(ec.get()).get()));
        require(rsa_info.public_key_algorithm == "rsa" && rsa_info.public_key_size_bits == 2048, "RSA CSR mismatch");
        require(ec_info.public_key_algorithm == "ecdsa" && ec_info.public_key_size_bits == 256, "EC CSR mismatch");

        KeyPtr issuer_rsa = rsa_key();
        KeyPtr issuer_ec = ec_key();
        KeyPtr other = rsa_key();
        KeyPtr weak = rsa_key(1024);
        ReqPtr fixture_csr = csr(rsa.get());
        ReqPtr invalid_csr = csr(rsa.get(), other.get());
        CertPtr fixture_issuer = ca_certificate(issuer_rsa.get(), "No Fallback Fixture CA");
        write_text(directory / "valid-csr.pem", csr_pem(fixture_csr.get()));
        write_text(directory / "invalid-csr.pem", csr_pem(invalid_csr.get()));
        write_text(directory / "valid-issuer.pem", certificate_pem(fixture_issuer.get()));
        write_text(directory / "malformed-key.pem", "not a private key");
        write_key(directory / "valid-key.pem", issuer_rsa.get());
        write_key(directory / "wrong-key.pem", other.get());
        write_key(directory / "weak-key.pem", weak.get());
        write_encrypted_key(directory / "encrypted-key.pem", issuer_rsa.get());
        issue_and_verify(directory, rsa.get(), issuer_rsa.get(), "rsa_with_sha256", NID_sha256WithRSAEncryption, "rsa256");
        issue_and_verify(directory, rsa.get(), issuer_rsa.get(), "rsa_with_sha384", NID_sha384WithRSAEncryption, "rsa384");
        issue_and_verify(directory, rsa.get(), issuer_rsa.get(), "rsa_with_sha512", NID_sha512WithRSAEncryption, "rsa512");
        issue_and_verify(directory, ec.get(), issuer_ec.get(), "ecdsa_with_sha256", NID_ecdsa_with_SHA256, "ec256");
        std::ifstream evidence_input{evidence_path, std::ios::binary};
        const std::string evidence{std::istreambuf_iterator<char>{evidence_input}, {}};
        require(evidence.find("\"fallback_used\":false") != std::string::npos &&
                evidence.find("\"result_code\":\"ok\"") != std::string::npos,
            "signing evidence mismatch");

        expect_error([&] { (void)anopki::core::inspect_csr_pem(csr_pem(csr(rsa.get(), other.get()).get())); }, "csr.parse_failed");
        expect_error([&] { (void)anopki::core::inspect_csr_pem(csr_pem(csr(weak.get()).get())); }, "csr.parse_failed");
        KeyPtr p384 = ec_key(NID_secp384r1);
        expect_error([&] { (void)anopki::core::inspect_csr_pem(csr_pem(csr(p384.get()).get())); }, "csr.parse_failed");
        expect_error([&] { (void)anopki::core::inspect_csr_pem("not a CSR"); }, "csr.parse_failed");

        std::cout << "AnoCrypto PKI algorithm matrix tests passed\n";
        return 0;
    }
    catch (const std::exception &error)
    {
        std::cerr << "AnoCrypto PKI algorithm matrix test failed: " << error.what() << '\n';
        return 1;
    }
}
