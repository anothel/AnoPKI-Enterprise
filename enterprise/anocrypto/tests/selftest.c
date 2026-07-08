/* SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise */
#include "anocrypto/anocrypto.h"

int main(void) {
    return anocrypto_self_test() == ANOCRYPTO_OK ? 0 : 1;
}
