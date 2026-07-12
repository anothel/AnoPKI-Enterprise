// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "anopki/core/crl.hpp"
#include "anopki/core/csr.hpp"
#include "anopki/core/issue.hpp"
#include "anopki/core/ocsp.hpp"
#include "anopki/crypto/runtime.hpp"

#include <cassert>

namespace
{

template <typename Function>
void expect_capability_unavailable(Function function)
{
    try
    {
        function();
        assert(false);
    }
    catch (const anopki::crypto::BackendError &error)
    {
        assert(error.code() == anopki::crypto::BackendErrorCode::capability_unavailable);
    }
}

}  // namespace

int main()
{
    const anopki::crypto::ProductProfileInfo &profile = anopki::crypto::selected_product_profile();
    const anopki::crypto::Backend &backend = anopki::crypto::selected_backend();
    assert(profile.id == "enterprise-anocrypto-c");
    assert(profile.selected_backend == "anocrypto-c");
    assert(!profile.fallback_enabled);
    assert(backend.info().id == "anocrypto-c");
    assert(backend.info().capabilities.empty());

    expect_capability_unavailable([] { (void)anopki::core::inspect_csr_pem("unused"); });
    expect_capability_unavailable([] { (void)anopki::core::issue_certificate({}); });
    expect_capability_unavailable([] { (void)anopki::core::generate_crl({}); });
    expect_capability_unavailable([] { (void)anopki::core::inspect_crl_pem("unused"); });
    expect_capability_unavailable([] { (void)anopki::core::inspect_ocsp_request_der("unused"); });
    expect_capability_unavailable([] { (void)anopki::core::generate_ocsp_response({}); });
    return 0;
}
