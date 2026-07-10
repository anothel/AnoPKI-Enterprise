/* SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise */
#ifndef ANOCRYPTO_ANOCRYPTO_H
#define ANOCRYPTO_ANOCRYPTO_H

#ifdef __cplusplus
extern "C" {
#endif

#define ANOCRYPTO_VERSION "0.0.0-skeleton"

typedef enum anocrypto_status {
    ANOCRYPTO_OK = 0,
    ANOCRYPTO_ERR_UNIMPLEMENTED = 1,
    ANOCRYPTO_ERR_SELF_TEST_FAILED = 2
} anocrypto_status;

const char *anocrypto_version(void);
const char *anocrypto_approved_mode_status(void);
const char *anocrypto_deterministic_test_vector_status(void);
const char *anocrypto_production_status(void);
anocrypto_status anocrypto_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* ANOCRYPTO_ANOCRYPTO_H */
