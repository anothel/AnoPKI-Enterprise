// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
package enterprise

const EditionName = "AnoPKI Enterprise"
const OverlayVersion = "unreleased"
const OverlayStatus = "private-alpha"
const ActiveCryptoBackend = "openssl"
const ExperimentalCryptoBackend = "anocrypto"
const ExperimentalCryptoBackendStatus = "skeleton_pending"
const CryptoBackendDirection = ExperimentalCryptoBackend

func EnabledFeatures() []string {
	return []string{
		"anocrypto-backend-boundary",
		"commercial-license-boundary",
		"future-sso-rbac",
		"future-deploy-adapters",
		"future-siem-export",
	}
}
