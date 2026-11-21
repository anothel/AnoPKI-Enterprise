// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include <anocrypto/ac_module.h>
#include <dlfcn.h>

#include <cstdio>

int main()
{
    Dl_info info{};
    if (dladdr(reinterpret_cast<const void *>(&ano_crypto_module_init), &info) == 0 ||
        info.dli_fname == nullptr || ano_crypto_module_init(nullptr) != ANO_CRYPTO_OK ||
        ano_crypto_module_shutdown() != ANO_CRYPTO_OK)
    {
        return 1;
    }
    return std::puts(info.dli_fname) == EOF ? 1 : 0;
}
