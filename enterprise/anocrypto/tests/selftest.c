/* SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise */
#include "anocrypto/anocrypto.h"

#include <string.h>

int main(void) {
    if (strcmp(anocrypto_version(), ANOCRYPTO_VERSION) != 0) {
        return 1;
    }
    if (strcmp(anocrypto_approved_mode_status(), "placeholder-not-approved") != 0) {
        return 1;
    }
    if (strcmp(anocrypto_deterministic_test_vector_status(), "placeholder-pending") != 0) {
        return 1;
    }
    if (strcmp(anocrypto_production_status(), "not-production-complete") != 0) {
        return 1;
    }
    return anocrypto_self_test() == ANOCRYPTO_OK ? 0 : 1;
}
