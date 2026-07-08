// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
package enterprise

const EditionName = "AnoPKI Enterprise"
const CryptoBackendDirection = "AnoCrypto backend direction with OpenSSL parity gate"

func EnabledFeatures() []string {
    return []string{
        "anocrypto-backend-boundary",
        "commercial-license-boundary",
        "future-sso-rbac",
        "future-deploy-adapters",
        "future-siem-export",
    }
}
