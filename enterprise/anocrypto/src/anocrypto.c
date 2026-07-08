/* SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise */
#include "anocrypto/anocrypto.h"

const char *anocrypto_version(void) {
    return ANOCRYPTO_VERSION;
}

anocrypto_status anocrypto_self_test(void) {
    return ANOCRYPTO_OK;
}
