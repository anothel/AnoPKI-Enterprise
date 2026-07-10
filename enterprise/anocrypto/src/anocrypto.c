/* SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise */
#include "anocrypto/anocrypto.h"

const char *anocrypto_version(void) {
    return ANOCRYPTO_VERSION;
}

const char *anocrypto_approved_mode_status(void) {
    return "placeholder-not-approved";
}

const char *anocrypto_deterministic_test_vector_status(void) {
    return "placeholder-pending";
}

const char *anocrypto_production_status(void) {
    return "not-production-complete";
}

anocrypto_status anocrypto_self_test(void) {
    return ANOCRYPTO_OK;
}
